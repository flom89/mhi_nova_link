"""Regression tests for debounced zone availability reporting."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.mhi_nova_link.coordinator import NovaRcDataUpdateCoordinator


class DummyHass(SimpleNamespace):
    """Minimal Home Assistant stub that schedules background work."""

    def __init__(self) -> None:
        super().__init__(data={})

    def async_create_task(self, coro: object) -> asyncio.Task[None]:
        """Schedule a coroutine on the running test loop."""
        return asyncio.create_task(coro)  # type: ignore[arg-type]


def _make_coordinator(zones_sequence: list[list[dict[str, object]]]) -> NovaRcDataUpdateCoordinator:
    api = SimpleNamespace(
        async_get_zones=AsyncMock(side_effect=zones_sequence),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value=({}, {})),
        async_get_gateway_update_information=AsyncMock(return_value={}),
    )
    return NovaRcDataUpdateCoordinator(DummyHass(), api)


@pytest.mark.asyncio
async def test_single_poll_dropout_is_absorbed() -> None:
    """A single missed/offline poll must not flip the zone unavailable."""
    online_zone = {"zoneId": 1, "available": True, "roomAirTemperature": 21.5}
    coordinator = _make_coordinator(
        [
            [online_zone],
            [],  # zone briefly missing from the response (OfflineZone typename)
            [online_zone],
        ]
    )

    first = await coordinator._async_update_data()
    coordinator.data = first
    assert first[0]["available"] is True

    second = await coordinator._async_update_data()
    coordinator.data = second
    assert len(second) == 1
    assert second[0]["available"] is True
    assert second[0]["roomAirTemperature"] == 21.5

    third = await coordinator._async_update_data()
    assert third[0]["available"] is True


@pytest.mark.asyncio
async def test_sustained_dropout_marks_zone_unavailable() -> None:
    """Only a sustained outage should surface the zone as unavailable."""
    online_zone = {"zoneId": 1, "available": True, "roomAirTemperature": 21.5}
    coordinator = _make_coordinator([[online_zone], [], []])

    first = await coordinator._async_update_data()
    coordinator.data = first

    second = await coordinator._async_update_data()
    coordinator.data = second
    assert second[0]["available"] is True

    third = await coordinator._async_update_data()
    assert third[0]["available"] is False
    # Last known-good values are still exposed instead of vanishing.
    assert third[0]["roomAirTemperature"] == 21.5


@pytest.mark.asyncio
async def test_zone_reported_offline_recovers_immediately() -> None:
    """As soon as the gateway reports the zone online again, it recovers."""
    online_zone = {"zoneId": 1, "available": True, "roomAirTemperature": 21.5}
    offline_zone = {"zoneId": 1, "available": False}
    recovered_zone = {"zoneId": 1, "available": True, "roomAirTemperature": 22.0}
    coordinator = _make_coordinator([[online_zone], [offline_zone], [recovered_zone]])

    first = await coordinator._async_update_data()
    coordinator.data = first

    second = await coordinator._async_update_data()
    coordinator.data = second
    assert second[0]["available"] is True  # single blip absorbed

    third = await coordinator._async_update_data()
    assert third[0]["available"] is True
    assert third[0]["roomAirTemperature"] == 22.0
