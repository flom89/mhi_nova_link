"""Tests for operation-lock restore persistence and fail-safe behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.mhi_nova_link.const import (
    CONF_GPIO_RESTORE_ENABLED,
    CONF_GPIO_RESTORE_SYSTEM_STOP,
    CONF_GPIO_RESTORE_VALIDITY_MINUTES,
)
from custom_components.mhi_nova_link.coordinator import (
    _RESTORE_FIRST_WRITEBACK_DELAY_SECONDS,
    _RESTORE_POST_RETRY_VERIFY_DELAY_SECONDS,
    _RESTORE_RECHECK_DELAY_SECONDS,
    GPIO_SOURCE_SYSTEM_STOP,
    NovaRcDataUpdateCoordinator,
)


class DummyHass(SimpleNamespace):
    """Minimal Home Assistant stub for coordinator tests."""

    def __init__(self) -> None:
        """Initialize a lightweight object with required Home Assistant fields."""
        super().__init__(data={})
        self.created_tasks: list[object] = []

    def async_create_task(self, coro: object) -> object:
        """Record created tasks so tests can assert scheduling behavior."""
        self.created_tasks.append(coro)
        return coro


class DummyConfigEntry(SimpleNamespace):
    """Minimal config-entry stub for coordinator tests."""

    def async_on_unload(self, func: object) -> None:
        """Accept unload callbacks required by DataUpdateCoordinator."""


def _build_coordinator(
    *,
    restore_enabled: bool = True,
    restore_system_stop: bool = True,
    restore_validity_minutes: int = 120,
) -> tuple[NovaRcDataUpdateCoordinator, SimpleNamespace]:
    """Create a coordinator with deterministic test doubles."""
    hass = DummyHass()
    api = SimpleNamespace(async_set_zone_state=AsyncMock(return_value=True))
    entry = DummyConfigEntry(
        entry_id="entry-id",
        options={
            CONF_GPIO_RESTORE_ENABLED: restore_enabled,
            CONF_GPIO_RESTORE_SYSTEM_STOP: restore_system_stop,
            CONF_GPIO_RESTORE_VALIDITY_MINUTES: restore_validity_minutes,
        },
        data={},
    )
    coordinator = NovaRcDataUpdateCoordinator(hass, api, entry)
    coordinator.async_request_refresh = AsyncMock()
    coordinator._restore_store = SimpleNamespace(
        async_load=AsyncMock(return_value=None),
        async_save=AsyncMock(),
    )
    return coordinator, api


@pytest.mark.asyncio
async def test_capture_restore_snapshot_persists_zone_state() -> None:
    """Capture should store and persist zone state when restore is enabled."""
    coordinator, _ = _build_coordinator()
    coordinator.data = [
        {
            "zoneId": 1,
            "running": True,
            "operationMode": "AUTO",
            "setpoint": 22.5,
            "fanSpeed": "HIGH",
            "vanePosition": "AUTO",
            "louverPosition": "POSITION_2",
        }
    ]

    await coordinator.async_capture_restore_snapshot(GPIO_SOURCE_SYSTEM_STOP)

    snapshot = coordinator._restore_state["snapshots"][GPIO_SOURCE_SYSTEM_STOP]
    assert isinstance(snapshot, dict)
    assert snapshot["source"] == GPIO_SOURCE_SYSTEM_STOP
    assert snapshot["zones"][0]["zoneId"] == 1
    assert snapshot["zones"][0]["operationMode"] == "AUTO"
    coordinator._restore_store.async_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_capture_restore_snapshot_sets_restore_disabled_status() -> None:
    """Capture should expose a clear status when restore is not enabled."""
    coordinator, _ = _build_coordinator(restore_enabled=False)
    coordinator.data = [{"zoneId": 1, "running": True}]

    await coordinator.async_capture_restore_snapshot(GPIO_SOURCE_SYSTEM_STOP)

    assert coordinator.restore_diagnostics["last_event"]["state"] == "restore_disabled"


@pytest.mark.asyncio
async def test_restore_after_release_sets_restore_disabled_status() -> None:
    """Restore should expose a clear status when restore is not enabled."""
    coordinator, _ = _build_coordinator(restore_enabled=False)
    coordinator._restore_state_loaded = True

    await coordinator.async_restore_after_release(GPIO_SOURCE_SYSTEM_STOP)

    assert coordinator.restore_diagnostics["last_event"]["state"] == "restore_disabled"


@pytest.mark.asyncio
async def test_restore_after_release_skips_expired_snapshot() -> None:
    """Expired snapshots should be dropped without applying restore."""
    coordinator, _ = _build_coordinator(restore_validity_minutes=1)
    coordinator._restore_state_loaded = True
    coordinator._restore_state["snapshots"][GPIO_SOURCE_SYSTEM_STOP] = {
        "created_at": (datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        "source": GPIO_SOURCE_SYSTEM_STOP,
        "zones": [{"zoneId": 1, "running": True}],
    }
    coordinator._async_apply_snapshot = AsyncMock()
    coordinator._schedule_restore_validation = Mock()

    await coordinator.async_restore_after_release(GPIO_SOURCE_SYSTEM_STOP)

    coordinator._async_apply_snapshot.assert_not_awaited()
    coordinator._schedule_restore_validation.assert_not_called()
    assert coordinator._restore_state["snapshots"][GPIO_SOURCE_SYSTEM_STOP] is None


@pytest.mark.asyncio
async def test_restore_validation_retries_once_on_mismatch() -> None:
    """Validation should trigger one retry when restored values drift."""
    coordinator, _ = _build_coordinator()
    snapshot = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": GPIO_SOURCE_SYSTEM_STOP,
        "zones": [{"zoneId": 1, "running": True}],
    }

    coordinator._snapshot_matches_current_state = Mock(return_value=False)
    coordinator._async_snapshot_matches_gateway_state = AsyncMock(return_value=False)
    coordinator._async_apply_snapshot = AsyncMock(return_value=True)
    coordinator._async_clear_snapshot = AsyncMock()
    scheduled_at = datetime.now(UTC)

    sleep_mock = AsyncMock()
    with patch("custom_components.mhi_nova_link.coordinator.asyncio.sleep", new=sleep_mock):
        await coordinator._async_validate_restore(
            GPIO_SOURCE_SYSTEM_STOP,
            snapshot,
            scheduled_at,
        )

    assert coordinator._async_apply_snapshot.await_count == 2
    assert coordinator._async_snapshot_matches_gateway_state.await_count == 2
    assert coordinator.async_request_refresh.await_count == 2
    sleep_mock.assert_any_await(_RESTORE_FIRST_WRITEBACK_DELAY_SECONDS)
    sleep_mock.assert_any_await(_RESTORE_RECHECK_DELAY_SECONDS)
    sleep_mock.assert_any_await(_RESTORE_POST_RETRY_VERIFY_DELAY_SECONDS)
    coordinator._async_clear_snapshot.assert_awaited_once_with(GPIO_SOURCE_SYSTEM_STOP)


@pytest.mark.asyncio
async def test_restore_validation_success_after_initial_delay_without_retry() -> None:
    """Validation should stop after the first check when restored values already match."""
    coordinator, _ = _build_coordinator()
    snapshot = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": GPIO_SOURCE_SYSTEM_STOP,
        "zones": [{"zoneId": 1, "running": True}],
    }

    coordinator._snapshot_matches_current_state = Mock(return_value=True)
    coordinator._async_snapshot_matches_gateway_state = AsyncMock(return_value=False)
    coordinator._async_apply_snapshot = AsyncMock(return_value=True)
    coordinator._async_clear_snapshot = AsyncMock()
    scheduled_at = datetime.now(UTC)

    sleep_mock = AsyncMock()
    with patch("custom_components.mhi_nova_link.coordinator.asyncio.sleep", new=sleep_mock):
        await coordinator._async_validate_restore(
            GPIO_SOURCE_SYSTEM_STOP,
            snapshot,
            scheduled_at,
        )

    coordinator._async_apply_snapshot.assert_awaited_once_with(snapshot)
    coordinator._async_snapshot_matches_gateway_state.assert_not_awaited()
    coordinator.async_request_refresh.assert_awaited_once()
    sleep_mock.assert_any_await(_RESTORE_FIRST_WRITEBACK_DELAY_SECONDS)
    sleep_mock.assert_any_await(_RESTORE_RECHECK_DELAY_SECONDS)
    coordinator._async_clear_snapshot.assert_awaited_once_with(GPIO_SOURCE_SYSTEM_STOP)


@pytest.mark.asyncio
async def test_restore_validation_uses_zone_query_match_before_retry() -> None:
    """Gateway zone-query match should skip retry even when coordinator state lags."""
    coordinator, _ = _build_coordinator()
    snapshot = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": GPIO_SOURCE_SYSTEM_STOP,
        "zones": [{"zoneId": 1, "running": True}],
    }

    coordinator._snapshot_matches_current_state = Mock(return_value=False)
    coordinator._async_snapshot_matches_gateway_state = AsyncMock(return_value=True)
    coordinator._async_apply_snapshot = AsyncMock(return_value=True)
    coordinator._async_clear_snapshot = AsyncMock()
    scheduled_at = datetime.now(UTC)

    sleep_mock = AsyncMock()
    with patch("custom_components.mhi_nova_link.coordinator.asyncio.sleep", new=sleep_mock):
        await coordinator._async_validate_restore(
            GPIO_SOURCE_SYSTEM_STOP,
            snapshot,
            scheduled_at,
        )

    coordinator._async_snapshot_matches_gateway_state.assert_awaited_once_with(snapshot)
    coordinator._async_apply_snapshot.assert_awaited_once_with(snapshot)
    assert coordinator.async_request_refresh.await_count == 2
    coordinator._async_clear_snapshot.assert_awaited_once_with(GPIO_SOURCE_SYSTEM_STOP)


@pytest.mark.asyncio
async def test_restore_validation_skips_when_user_interacted_after_release() -> None:
    """Restore should not write back when user interacted after release."""
    coordinator, _ = _build_coordinator()
    snapshot = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": GPIO_SOURCE_SYSTEM_STOP,
        "zones": [{"zoneId": 1, "running": True}],
    }
    coordinator._async_apply_snapshot = AsyncMock(return_value=True)
    coordinator._async_clear_snapshot = AsyncMock()

    scheduled_at = datetime.now(UTC)
    coordinator._last_user_interaction_at = scheduled_at + timedelta(seconds=1)

    with patch("custom_components.mhi_nova_link.coordinator.asyncio.sleep", new=AsyncMock()):
        await coordinator._async_validate_restore(
            GPIO_SOURCE_SYSTEM_STOP,
            snapshot,
            scheduled_at,
        )

    coordinator._async_apply_snapshot.assert_not_awaited()
    coordinator._async_clear_snapshot.assert_awaited_once_with(GPIO_SOURCE_SYSTEM_STOP)


@pytest.mark.asyncio
async def test_restore_after_release_applies_snapshot_and_schedules_validation() -> None:
    """Restore should schedule delayed writeback and validation."""
    coordinator, _ = _build_coordinator()
    coordinator._restore_state_loaded = True
    snapshot = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": GPIO_SOURCE_SYSTEM_STOP,
        "zones": [{"zoneId": 1, "running": True}],
    }
    coordinator._restore_state["snapshots"][GPIO_SOURCE_SYSTEM_STOP] = snapshot
    coordinator._schedule_restore_validation = Mock()

    await coordinator.async_restore_after_release(GPIO_SOURCE_SYSTEM_STOP)

    coordinator._schedule_restore_validation.assert_called_once()
    called_source, called_snapshot, called_scheduled_at = (
        coordinator._schedule_restore_validation.call_args.args
    )
    assert called_source == GPIO_SOURCE_SYSTEM_STOP
    assert called_snapshot == snapshot
    assert isinstance(called_scheduled_at, datetime)


def test_mark_user_interaction_without_status_emit_keeps_restore_event() -> None:
    """Lock toggle bookkeeping should not overwrite restore lifecycle status."""
    coordinator, _ = _build_coordinator()

    coordinator._set_restore_status(GPIO_SOURCE_SYSTEM_STOP, state="writeback_scheduled")
    coordinator.async_mark_user_interaction("switch.async_turn_off_system_stop", emit_status=False)

    diagnostics = coordinator.restore_diagnostics
    assert diagnostics["last_event"]["state"] == "writeback_scheduled"
    assert diagnostics["last_user_interaction_at"] is not None


def test_restore_option_falls_back_to_entry_data() -> None:
    """Restore enablement should also honor migrated settings in entry data."""
    coordinator, _ = _build_coordinator(restore_enabled=False)
    coordinator.config_entry.options = {}
    coordinator.config_entry.data = {
        CONF_GPIO_RESTORE_ENABLED: True,
        CONF_GPIO_RESTORE_SYSTEM_STOP: True,
    }

    assert coordinator._restore_enabled_for_source(GPIO_SOURCE_SYSTEM_STOP)


def test_restore_option_handles_string_bools() -> None:
    """Restore settings stored as strings should be interpreted correctly."""
    coordinator, _ = _build_coordinator(restore_enabled=False)
    coordinator.config_entry.options = {
        CONF_GPIO_RESTORE_ENABLED: "true",
        CONF_GPIO_RESTORE_SYSTEM_STOP: "true",
    }

    assert coordinator._restore_enabled_for_source(GPIO_SOURCE_SYSTEM_STOP)


def test_restore_option_from_mapping_proxy_options() -> None:
    """Restore settings should be read from Mapping-like config containers."""
    coordinator, _ = _build_coordinator(restore_enabled=False)
    coordinator.config_entry.options = MappingProxyType(
        {
            CONF_GPIO_RESTORE_ENABLED: True,
            CONF_GPIO_RESTORE_SYSTEM_STOP: True,
        }
    )
    coordinator.config_entry.data = MappingProxyType({})

    assert coordinator._restore_enabled_for_source(GPIO_SOURCE_SYSTEM_STOP)
