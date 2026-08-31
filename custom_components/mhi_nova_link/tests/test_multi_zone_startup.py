"""Regression tests for lightweight multi-zone startup."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.mhi_nova_link.api import NovaRcApiClient
from custom_components.mhi_nova_link.coordinator import NovaRcDataUpdateCoordinator


class DummyHass(SimpleNamespace):
    """Minimal Home Assistant stub that schedules background work."""

    def __init__(self) -> None:
        super().__init__(data={})

    def async_create_task(self, coro: object) -> asyncio.Task[None]:
        """Schedule a coroutine on the running test loop."""
        return asyncio.create_task(coro)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_time_series_enrichment_is_sequential() -> None:
    """Historical queries should never run concurrently across zones."""
    client = NovaRcApiClient("gateway.local", AsyncMock())
    active_requests = 0
    maximum_active_requests = 0

    async def attach(zone: dict[str, object]) -> None:
        nonlocal active_requests, maximum_active_requests
        active_requests += 1
        maximum_active_requests = max(maximum_active_requests, active_requests)
        await asyncio.sleep(0)
        active_requests -= 1

    client._attach_time_series_data = attach  # type: ignore[method-assign]
    await client.async_enrich_time_series([{"zoneId": zone_id} for zone_id in range(4)])

    assert maximum_active_requests == 1


@pytest.mark.asyncio
async def test_initial_refresh_reuses_login_zones_and_background_enrichment() -> None:
    """First refresh should complete before optional history is available."""
    enrichment_started = asyncio.Event()
    enrichment_release = asyncio.Event()

    async def enrich(zones: list[dict[str, object]]) -> None:
        enrichment_started.set()
        await enrichment_release.wait()
        for zone in zones:
            zone["timeSeries"] = {"dataSets": []}

    initial_zones = [{"zoneId": zone_id} for zone_id in range(1, 5)]
    api = SimpleNamespace(
        take_initial_zones=lambda: initial_zones,
        async_get_zones=AsyncMock(),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value=({}, {})),
        async_get_gateway_update_information=AsyncMock(return_value={}),
        async_enrich_time_series=enrich,
    )
    coordinator = NovaRcDataUpdateCoordinator(DummyHass(), api)

    zones = await coordinator._async_update_data()
    coordinator.data = zones

    assert zones == initial_zones
    api.async_get_zones.assert_not_awaited()
    await enrichment_started.wait()
    enrichment_release.set()
    await coordinator._time_series_enrichment_task
    assert all("timeSeries" in zone for zone in zones)


@pytest.mark.asyncio
async def test_time_series_failure_does_not_fail_lightweight_refresh() -> None:
    """An optional history failure must not prevent a multi-zone setup."""
    api = SimpleNamespace(
        take_initial_zones=lambda: [{"zoneId": zone_id} for zone_id in range(1, 5)],
        async_get_zones=AsyncMock(),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value=({}, {})),
        async_get_gateway_update_information=AsyncMock(return_value={}),
        async_enrich_time_series=AsyncMock(side_effect=RuntimeError("gateway busy")),
    )
    coordinator = NovaRcDataUpdateCoordinator(DummyHass(), api)

    zones = await coordinator._async_update_data()
    await coordinator._time_series_enrichment_task

    assert len(zones) == 4
    api.async_get_zones.assert_not_awaited()
    api.async_enrich_time_series.assert_awaited_once_with(zones)


@pytest.mark.asyncio
async def test_new_refresh_replaces_stale_time_series_enrichment() -> None:
    """A newer zone refresh should supersede its unfinished history request."""
    first_started = asyncio.Event()
    release_second = asyncio.Event()
    completed_zones: list[list[dict[str, object]]] = []

    async def enrich(zones: list[dict[str, object]]) -> None:
        if zones[0]["zoneId"] == 1:
            first_started.set()
            await asyncio.Event().wait()
        await release_second.wait()
        completed_zones.append(zones)

    api = SimpleNamespace(async_enrich_time_series=enrich)
    coordinator = NovaRcDataUpdateCoordinator(DummyHass(), api)
    first_zones = [{"zoneId": 1}]
    second_zones = [{"zoneId": 2}]

    coordinator._async_schedule_time_series_enrichment(first_zones)
    await first_started.wait()
    coordinator._async_schedule_time_series_enrichment(second_zones)
    release_second.set()
    await coordinator._time_series_enrichment_task

    assert completed_zones == [second_zones]
