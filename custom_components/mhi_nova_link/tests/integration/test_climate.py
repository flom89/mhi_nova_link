"""Integration tests for climate entity properties and async actions.

The coordinator and API are replaced by lightweight stubs — no real HA
instance or network connection is required.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from homeassistant.components.climate import HVACAction, HVACMode

from custom_components.mhi_nova_link.climate import (
    FAN_POWERFUL,
    SWING_AUTO,
    NovaRcZoneClimate,
)


def _coordinator(zone_data: dict, zone_id: int = 1) -> SimpleNamespace:
    """Build a minimal coordinator stub for a single zone."""
    return SimpleNamespace(
        data=[{**zone_data, "zoneId": zone_id}],
        config_entry=SimpleNamespace(domain="mhi_nova_link", entry_id="test-entry"),
        api=SimpleNamespace(host="gateway.local"),
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )


def _climate(zone_data: dict, zone_id: int = 1) -> NovaRcZoneClimate:
    return NovaRcZoneClimate(_coordinator(zone_data, zone_id), zone_id)


# ---------------------------------------------------------------------------
# hvac_mode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("running", "mode", "expected"),
    [
        (False, "COOLING", HVACMode.OFF),
        (True, "COOLING", HVACMode.COOL),
        (True, "HEATING", HVACMode.HEAT),
        (True, "AUTO", HVACMode.AUTO),
        (True, "DRY", HVACMode.DRY),
        (True, "FAN", HVACMode.FAN_ONLY),
        (True, "UNKNOWN", HVACMode.AUTO),  # unmapped → AUTO fallback
    ],
)
def test_hvac_mode(running: bool, mode: str, expected: HVACMode) -> None:
    """hvac_mode should map gateway state to the correct HA mode."""
    assert _climate({"running": running, "operationMode": mode}).hvac_mode == expected


# ---------------------------------------------------------------------------
# hvac_action
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("running", "mode", "expected"),
    [
        (False, "COOLING", HVACAction.OFF),
        (True, "COOLING", HVACAction.COOLING),
        (True, "HEATING", HVACAction.HEATING),
        (True, "DRY", HVACAction.DRYING),
        (True, "FAN", HVACAction.FAN),
        (True, "AUTO", HVACAction.IDLE),
    ],
)
def test_hvac_action(running: bool, mode: str, expected: HVACAction) -> None:
    """hvac_action should reflect the current operating action."""
    assert _climate({"running": running, "operationMode": mode}).hvac_action == expected


# ---------------------------------------------------------------------------
# icon
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("running", "mode", "expected_icon"),
    [
        (True, "COOLING", "mdi:snowflake"),
        (True, "HEATING", "mdi:fire"),
        (True, "DRY", "mdi:water-percent"),
        (True, "FAN", "mdi:fan"),
        (True, "AUTO", "mdi:thermostat-auto"),
        (False, "COOLING", "mdi:air-conditioner"),
    ],
)
def test_icon(running: bool, mode: str, expected_icon: str) -> None:
    """icon should reflect the current HVAC mode."""
    assert _climate({"running": running, "operationMode": mode}).icon == expected_icon


# ---------------------------------------------------------------------------
# Temperature properties
# ---------------------------------------------------------------------------


def test_current_temperature() -> None:
    """current_temperature should read roomAirTemperature."""
    assert _climate({"roomAirTemperature": 21.5}).current_temperature == 21.5


def test_current_temperature_none_when_absent() -> None:
    """current_temperature should return None when absent."""
    assert _climate({}).current_temperature is None


def test_target_temperature() -> None:
    """target_temperature should read the setpoint field."""
    assert _climate({"setpoint": 23.0}).target_temperature == 23.0


def test_min_temp_reads_cooling_lower_bound() -> None:
    """min_temp should come from temperatureRangeCooling.lower."""
    assert _climate({"temperatureRangeCooling": {"lower": 16.0, "upper": 30.0}}).min_temp == 16.0


def test_min_temp_defaults_to_18() -> None:
    """min_temp should default to 18.0."""
    assert _climate({}).min_temp == 18.0


def test_max_temp_reads_heating_upper_bound() -> None:
    """max_temp should come from temperatureRangeHeating.upper."""
    assert _climate({"temperatureRangeHeating": {"lower": 16.0, "upper": 32.0}}).max_temp == 32.0


def test_max_temp_defaults_to_30() -> None:
    """max_temp should default to 30.0."""
    assert _climate({}).max_temp == 30.0


# ---------------------------------------------------------------------------
# fan_mode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AUTO", "auto"),
        ("LOW", "low"),
        ("MEDIUM", "medium"),
        ("HIGH", "high"),
        ("POWERFUL", FAN_POWERFUL),
        ("UNKNOWN", "auto"),  # unmapped → AUTO fallback
    ],
)
def test_fan_mode(raw: str, expected: str) -> None:
    """fan_mode should map gateway fan speed to HA labels."""
    assert _climate({"fanSpeed": raw}).fan_mode == expected


# ---------------------------------------------------------------------------
# swing modes
# ---------------------------------------------------------------------------


def test_swing_modes_from_patch_options() -> None:
    """swing_modes should map gateway vane options to UI labels."""
    climate = _climate({"patchOptions": {"vanePosition": ["AUTO", "POSITION_1", "POSITION_3"]}})
    assert "auto" in climate.swing_modes
    assert "Position 1" in climate.swing_modes


def test_swing_modes_defaults_to_auto() -> None:
    """swing_modes should default to [auto] when no patch options exist."""
    assert _climate({}).swing_modes == [SWING_AUTO]


def test_swing_mode_reads_vane_position() -> None:
    """swing_mode should read vanePosition."""
    assert _climate({"vanePosition": "POSITION_2"}).swing_mode == "Position 2"


def test_swing_mode_falls_back_to_louver_position() -> None:
    """swing_mode should fall back to louverPosition."""
    assert _climate({"louverPosition": "AUTO"}).swing_mode == SWING_AUTO


def test_swing_mode_none_when_absent() -> None:
    """swing_mode should return None when both fields are absent."""
    assert _climate({}).swing_mode is None


# ---------------------------------------------------------------------------
# async actions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_hvac_mode_off_sends_running_false() -> None:
    """Setting OFF should call async_set_zone_state with running=False."""
    api = SimpleNamespace(host="gw", async_set_zone_state=AsyncMock())
    coord = SimpleNamespace(
        data=[{"zoneId": 1, "running": True}],
        config_entry=SimpleNamespace(domain="mhi_nova_link", entry_id="e"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    await NovaRcZoneClimate(coord, 1).async_set_hvac_mode(HVACMode.OFF)
    api.async_set_zone_state.assert_awaited_once_with(1, running=False)


@pytest.mark.asyncio
async def test_set_hvac_mode_requests_airflow_wait_when_starting() -> None:
    """Changing mode when the unit is off should set wait_for_airflow_after_start=True."""
    api = SimpleNamespace(host="gw", async_set_zone_state=AsyncMock())
    coord = SimpleNamespace(
        data=[{"zoneId": 1, "running": False}],
        config_entry=SimpleNamespace(domain="mhi_nova_link", entry_id="e"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    await NovaRcZoneClimate(coord, 1).async_set_hvac_mode(HVACMode.COOL)
    api.async_set_zone_state.assert_awaited_once_with(
        1, running=True, operation_mode="COOLING", wait_for_airflow_after_start=True
    )


@pytest.mark.asyncio
async def test_set_hvac_mode_no_airflow_wait_when_already_running() -> None:
    """Changing mode on a running unit should NOT wait for airflow."""
    api = SimpleNamespace(host="gw", async_set_zone_state=AsyncMock())
    coord = SimpleNamespace(
        data=[{"zoneId": 1, "running": True}],
        config_entry=SimpleNamespace(domain="mhi_nova_link", entry_id="e"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    await NovaRcZoneClimate(coord, 1).async_set_hvac_mode(HVACMode.HEAT)
    api.async_set_zone_state.assert_awaited_once_with(
        1, running=True, operation_mode="HEATING", wait_for_airflow_after_start=False
    )


@pytest.mark.asyncio
async def test_set_temperature_forwards_setpoint() -> None:
    """async_set_temperature should forward the setpoint to the API."""
    api = SimpleNamespace(host="gw", async_set_zone_state=AsyncMock())
    coord = SimpleNamespace(
        data=[{"zoneId": 1, "running": True}],
        config_entry=SimpleNamespace(domain="mhi_nova_link", entry_id="e"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    await NovaRcZoneClimate(coord, 1).async_set_temperature(temperature=22.5)
    api.async_set_zone_state.assert_awaited_once_with(1, setpoint=22.5)


@pytest.mark.asyncio
async def test_set_fan_mode_maps_powerful_label() -> None:
    """Fan mode 'Power' should be sent as 'POWERFUL' to the API."""
    api = SimpleNamespace(host="gw", async_set_zone_state=AsyncMock())
    coord = SimpleNamespace(
        data=[{"zoneId": 1, "running": True}],
        config_entry=SimpleNamespace(domain="mhi_nova_link", entry_id="e"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    await NovaRcZoneClimate(coord, 1).async_set_fan_mode("Power")
    api.async_set_zone_state.assert_awaited_once_with(1, fan_speed="POWERFUL")


@pytest.mark.asyncio
async def test_set_swing_mode_maps_position_label() -> None:
    """Swing mode label should be translated to the gateway value."""
    api = SimpleNamespace(host="gw", async_set_zone_state=AsyncMock())
    coord = SimpleNamespace(
        data=[{"zoneId": 1, "running": True}],
        config_entry=SimpleNamespace(domain="mhi_nova_link", entry_id="e"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    await NovaRcZoneClimate(coord, 1).async_set_swing_mode("Position 3")
    api.async_set_zone_state.assert_awaited_once_with(1, vane_position="POSITION_3")
