"""Tests for operation-lock restore persistence and fail-safe behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.mhi_nova_link.const import (
    CONF_GPIO_RESTORE_ENABLED,
    CONF_GPIO_RESTORE_SYSTEM_STOP,
    CONF_GPIO_RESTORE_VALIDITY_MINUTES,
)
from custom_components.mhi_nova_link.coordinator import (
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
    coordinator._async_apply_snapshot = AsyncMock(return_value=True)
    coordinator._async_clear_snapshot = AsyncMock()

    with patch("custom_components.mhi_nova_link.coordinator.asyncio.sleep", new=AsyncMock()):
        await coordinator._async_validate_restore(GPIO_SOURCE_SYSTEM_STOP, snapshot)

    coordinator._async_apply_snapshot.assert_awaited_once_with(snapshot)
    assert coordinator.async_request_refresh.await_count == 2
    coordinator._async_clear_snapshot.assert_awaited_once_with(GPIO_SOURCE_SYSTEM_STOP)


@pytest.mark.asyncio
async def test_restore_after_release_applies_snapshot_and_schedules_validation() -> None:
    """Restore should apply snapshot and schedule delayed validation."""
    coordinator, _ = _build_coordinator()
    coordinator._restore_state_loaded = True
    snapshot = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": GPIO_SOURCE_SYSTEM_STOP,
        "zones": [{"zoneId": 1, "running": True}],
    }
    coordinator._restore_state["snapshots"][GPIO_SOURCE_SYSTEM_STOP] = snapshot
    coordinator._async_apply_snapshot = AsyncMock(return_value=True)
    coordinator._schedule_restore_validation = Mock()

    await coordinator.async_restore_after_release(GPIO_SOURCE_SYSTEM_STOP)

    coordinator._async_apply_snapshot.assert_awaited_once_with(snapshot)
    coordinator._schedule_restore_validation.assert_called_once_with(
        GPIO_SOURCE_SYSTEM_STOP,
        snapshot,
    )
