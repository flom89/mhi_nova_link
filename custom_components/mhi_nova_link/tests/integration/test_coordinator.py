"""Integration tests for NovaRcDataUpdateCoordinator.

Tests verify how the coordinator wires together API calls,
enriches zone data with notifications, and maps errors.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.mhi_nova_link.api import (
    CannotConnect,
    InvalidAuth,
    InvalidCertificate,
)
from custom_components.mhi_nova_link.coordinator import NovaRcDataUpdateCoordinator


class _MinimalHass:
    """Bare-minimum hass stub — only what the coordinator constructor touches."""

    def __init__(self) -> None:
        self.data: dict = {}
        self.loop_thread_id = 0
        self.loop = SimpleNamespace(_thread_id=0)


def _make_coordinator(api: object) -> NovaRcDataUpdateCoordinator:
    return NovaRcDataUpdateCoordinator(  # type: ignore[arg-type]
        hass=_MinimalHass(),
        api=api,
    )


# ---------------------------------------------------------------------------
# _async_update_data — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_data_returns_zone_list_on_success() -> None:
    """Successful API calls should populate coordinator.data with zone dicts."""
    zones = [{"zoneId": 1, "running": True}]
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=zones),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    coordinator = _make_coordinator(api)
    with patch("homeassistant.helpers.frame.report_usage"):
        data = await coordinator._async_update_data()
    assert data == zones


@pytest.mark.asyncio
async def test_update_data_attaches_notifications_to_every_zone() -> None:
    """Active notifications should be attached to each zone dict."""
    zones = [{"zoneId": 1}, {"zoneId": 2}]
    notifications = {"notifications": [{"notificationId": 5, "active": True}]}
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=zones),
        async_get_notifications=AsyncMock(return_value=notifications),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    coordinator = _make_coordinator(api)
    with patch("homeassistant.helpers.frame.report_usage"):
        data = await coordinator._async_update_data()
    for zone in data:
        assert zone["notifications"] == notifications


@pytest.mark.asyncio
async def test_update_data_stores_gpios_on_coordinator() -> None:
    """GPIO state returned by the API should be stored on coordinator.gpios."""
    gpios = {"FREE_COOLING": True, "SYSTEM_FAULT": False}
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=[]),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value=gpios),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    coordinator = _make_coordinator(api)
    with patch("homeassistant.helpers.frame.report_usage"):
        await coordinator._async_update_data()
    assert coordinator.gpios == gpios


@pytest.mark.asyncio
async def test_update_data_stores_gateway_update_on_coordinator() -> None:
    """Gateway update info should be stored on coordinator.gateway_update."""
    update_info = {"installed_version": "3.2.5", "update_available": True}
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=[]),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value=update_info),
    )
    coordinator = _make_coordinator(api)
    with patch("homeassistant.helpers.frame.report_usage"):
        await coordinator._async_update_data()
    assert coordinator.gateway_update == update_info


@pytest.mark.asyncio
async def test_update_data_does_not_attach_notifications_when_empty() -> None:
    """When the notification dict is empty, zone dicts should not get a key added."""
    zones = [{"zoneId": 1}]
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=zones),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    coordinator = _make_coordinator(api)
    with patch("homeassistant.helpers.frame.report_usage"):
        data = await coordinator._async_update_data()
    assert "notifications" not in data[0]


# ---------------------------------------------------------------------------
# _async_update_data — error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_data_raises_config_entry_auth_failed_on_invalid_auth() -> None:
    """InvalidAuth from the API should be re-raised as ConfigEntryAuthFailed."""
    from homeassistant.exceptions import ConfigEntryAuthFailed

    api = SimpleNamespace(
        async_get_zones=AsyncMock(side_effect=InvalidAuth),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    coordinator = _make_coordinator(api)
    with (
        patch("homeassistant.helpers.frame.report_usage"),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_data_raises_update_failed_on_cannot_connect() -> None:
    """CannotConnect should be wrapped in UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = SimpleNamespace(
        async_get_zones=AsyncMock(side_effect=CannotConnect("timeout")),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    coordinator = _make_coordinator(api)
    with (
        patch("homeassistant.helpers.frame.report_usage"),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_data_raises_update_failed_on_invalid_certificate() -> None:
    """InvalidCertificate should be wrapped in UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = SimpleNamespace(
        async_get_zones=AsyncMock(side_effect=InvalidCertificate("bad cert")),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    coordinator = _make_coordinator(api)
    with (
        patch("homeassistant.helpers.frame.report_usage"),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_data_wraps_unexpected_exceptions_in_update_failed() -> None:
    """Any unexpected exception should be wrapped in UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    api = SimpleNamespace(
        async_get_zones=AsyncMock(side_effect=RuntimeError("oops")),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    coordinator = _make_coordinator(api)
    with (
        patch("homeassistant.helpers.frame.report_usage"),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()
