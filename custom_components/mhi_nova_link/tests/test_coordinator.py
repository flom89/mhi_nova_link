"""Unit tests for the NovaRcDataUpdateCoordinator and _get_update_interval."""

import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

_integration_dir = Path(__file__).resolve().parents[1]
_config_dir = _integration_dir.parent.parent
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

from custom_components.mhi_nova_link.api import (  # noqa: E402
    CannotConnect,
    InvalidAuth,
    InvalidCertificate,
)
from custom_components.mhi_nova_link.coordinator import (  # noqa: E402
    NovaRcDataUpdateCoordinator,
    _get_update_interval,
)


# ---------------------------------------------------------------------------
# _get_update_interval
# ---------------------------------------------------------------------------


def test_get_update_interval_returns_default_when_no_entry_and_no_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default interval should be returned when no config and no env var is set."""
    monkeypatch.delenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", raising=False)
    interval = _get_update_interval(None)
    from custom_components.mhi_nova_link.const import DEFAULT_POLL_INTERVAL

    assert interval.total_seconds() == DEFAULT_POLL_INTERVAL


def test_get_update_interval_reads_from_entry_options() -> None:
    """The interval should come from entry.options when present."""
    entry = SimpleNamespace(options={"poll_interval": 42})
    interval = _get_update_interval(entry)
    assert interval.total_seconds() == 42


def test_get_update_interval_reads_from_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The NOVA_RC_UPDATE_INTERVAL_SECONDS env var should override the default."""
    monkeypatch.setenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", "30")
    monkeypatch.delenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", raising=False)
    interval = _get_update_interval(None)
    assert interval.total_seconds() == 30


def test_get_update_interval_reads_from_legacy_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The legacy env var MHI_NOVALINK_UPDATE_INTERVAL_SECONDS should work as a fallback."""
    monkeypatch.delenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", raising=False)
    monkeypatch.setenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", "25")
    interval = _get_update_interval(None)
    assert interval.total_seconds() == 25


def test_get_update_interval_ignores_invalid_value_and_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-numeric interval values should log a warning and fall back to the default."""
    monkeypatch.setenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", "bad_value")
    monkeypatch.delenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", raising=False)
    from custom_components.mhi_nova_link.const import DEFAULT_POLL_INTERVAL

    interval = _get_update_interval(None)
    assert interval.total_seconds() == DEFAULT_POLL_INTERVAL


def test_get_update_interval_clamps_to_minimum_of_one_second() -> None:
    """Zero or negative interval values should be clamped to 1 second."""
    entry = SimpleNamespace(options={"poll_interval": 0})
    interval = _get_update_interval(entry)
    assert interval.total_seconds() == 1


def test_get_update_interval_entry_options_supersedes_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Entry options should take precedence over the environment variable."""
    monkeypatch.setenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", "99")
    entry = SimpleNamespace(options={"poll_interval": 10})
    interval = _get_update_interval(entry)
    assert interval.total_seconds() == 10


def test_get_update_interval_falls_back_to_env_when_options_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Entry options without poll_interval should fall back to env var."""
    monkeypatch.setenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", "55")
    monkeypatch.delenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", raising=False)
    entry = SimpleNamespace(options={})
    interval = _get_update_interval(entry)
    assert interval.total_seconds() == 55


# ---------------------------------------------------------------------------
# Helpers for coordinator tests
# ---------------------------------------------------------------------------


class _DummyHass:
    """Minimal hass stub for coordinator tests."""

    def __init__(self) -> None:
        self.data: dict = {}
        self.loop_thread_id = 0
        self.loop = SimpleNamespace(_thread_id=0)


def _make_coordinator(
    hass: _DummyHass,
    api: object,
    entry: object | None = None,
) -> NovaRcDataUpdateCoordinator:
    """Build a coordinator with lightweight stubs."""
    return NovaRcDataUpdateCoordinator(hass=hass, api=api, entry=entry)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# NovaRcDataUpdateCoordinator._async_update_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_update_data_returns_zone_data_on_success() -> None:
    """Successful API calls should populate coordinator.data with zone data."""
    zones = [{"zoneId": 1, "running": True}]
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=zones),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    hass = _DummyHass()
    coordinator = _make_coordinator(hass, api)

    with patch("homeassistant.helpers.frame.report_usage"):
        data = await coordinator._async_update_data()

    assert data == zones
    assert coordinator.gpios == {}
    assert coordinator.gateway_update == {}


@pytest.mark.asyncio
async def test_async_update_data_attaches_notifications_to_all_zones() -> None:
    """Notifications should be attached to every zone in the result."""
    zones = [{"zoneId": 1}, {"zoneId": 2}]
    notifications = {"notifications": [{"notificationId": 5, "active": True}]}
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=zones),
        async_get_notifications=AsyncMock(return_value=notifications),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    hass = _DummyHass()
    coordinator = _make_coordinator(hass, api)

    with patch("homeassistant.helpers.frame.report_usage"):
        data = await coordinator._async_update_data()

    for zone in data:
        assert zone["notifications"] == notifications


@pytest.mark.asyncio
async def test_async_update_data_raises_config_entry_auth_failed_on_invalid_auth() -> (
    None
):
    """An InvalidAuth error from the API should raise ConfigEntryAuthFailed."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    api = SimpleNamespace(
        async_get_zones=AsyncMock(side_effect=InvalidAuth),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    hass = _DummyHass()
    coordinator = _make_coordinator(hass, api)

    with (
        patch("homeassistant.helpers.frame.report_usage"),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_async_update_data_raises_update_failed_on_cannot_connect() -> None:
    """A CannotConnect error should raise UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = SimpleNamespace(
        async_get_zones=AsyncMock(side_effect=CannotConnect("timeout")),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    hass = _DummyHass()
    coordinator = _make_coordinator(hass, api)

    with (
        patch("homeassistant.helpers.frame.report_usage"),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_async_update_data_raises_update_failed_on_invalid_certificate() -> None:
    """An InvalidCertificate error should raise UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = SimpleNamespace(
        async_get_zones=AsyncMock(side_effect=InvalidCertificate("bad cert")),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    hass = _DummyHass()
    coordinator = _make_coordinator(hass, api)

    with (
        patch("homeassistant.helpers.frame.report_usage"),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_async_update_data_raises_update_failed_on_unexpected_error() -> None:
    """An unexpected exception should be wrapped in UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = SimpleNamespace(
        async_get_zones=AsyncMock(side_effect=RuntimeError("oops")),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    hass = _DummyHass()
    coordinator = _make_coordinator(hass, api)

    with (
        patch("homeassistant.helpers.frame.report_usage"),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_async_update_data_stores_gpios_on_coordinator() -> None:
    """GPIO state should be stored on the coordinator after a successful update."""
    gpios = {"FREE_COOLING": True, "SYSTEM_FAULT": False}
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=[]),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value=gpios),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    hass = _DummyHass()
    coordinator = _make_coordinator(hass, api)

    with patch("homeassistant.helpers.frame.report_usage"):
        await coordinator._async_update_data()

    assert coordinator.gpios == gpios


@pytest.mark.asyncio
async def test_async_update_data_stores_gateway_update_on_coordinator() -> None:
    """Gateway update info should be stored on the coordinator."""
    update_info = {"installed_version": "3.2.5", "update_available": True}
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=[]),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value=update_info),
    )
    hass = _DummyHass()
    coordinator = _make_coordinator(hass, api)

    with patch("homeassistant.helpers.frame.report_usage"):
        await coordinator._async_update_data()

    assert coordinator.gateway_update == update_info
