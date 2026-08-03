"""Unit tests for climate entity properties and actions."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

_integration_dir = Path(__file__).resolve().parents[1]
_config_dir = _integration_dir.parent.parent
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

from homeassistant.components.climate import HVACAction, HVACMode  # noqa: E402

from custom_components.mhi_nova_link.climate import (  # noqa: E402
    FAN_POWERFUL,
    SWING_AUTO,
    NovaRcZoneClimate,
)


def _make_coordinator(zone_data: dict) -> SimpleNamespace:
    """Return a minimal coordinator stub with one zone."""
    return SimpleNamespace(
        data=[zone_data],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )


def _make_climate(zone_data: dict, zone_id: int = 1) -> NovaRcZoneClimate:
    """Return a climate entity for a single zone."""
    coordinator = _make_coordinator({**zone_data, "zoneId": zone_id})
    return NovaRcZoneClimate(coordinator, zone_id)


# ---------------------------------------------------------------------------
# hvac_mode property
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("running", "operation_mode", "expected"),
    [
        (False, "COOLING", HVACMode.OFF),
        (True, "COOLING", HVACMode.COOL),
        (True, "HEATING", HVACMode.HEAT),
        (True, "AUTO", HVACMode.AUTO),
        (True, "DRY", HVACMode.DRY),
        (True, "FAN", HVACMode.FAN_ONLY),
        (True, "UNKNOWN_MODE", HVACMode.AUTO),  # unmapped → AUTO fallback
    ],
)
def test_hvac_mode(
    running: bool,
    operation_mode: str,
    expected: HVACMode,
) -> None:
    """hvac_mode should map gateway values to the correct HA mode."""
    climate = _make_climate({"running": running, "operationMode": operation_mode})
    assert climate.hvac_mode == expected


# ---------------------------------------------------------------------------
# hvac_action property
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("running", "operation_mode", "expected"),
    [
        (False, "COOLING", HVACAction.OFF),
        (True, "COOLING", HVACAction.COOLING),
        (True, "HEATING", HVACAction.HEATING),
        (True, "DRY", HVACAction.DRYING),
        (True, "FAN", HVACAction.FAN),
        (True, "AUTO", HVACAction.IDLE),
    ],
)
def test_hvac_action(
    running: bool,
    operation_mode: str,
    expected: HVACAction,
) -> None:
    """hvac_action should reflect the current operating action."""
    climate = _make_climate({"running": running, "operationMode": operation_mode})
    assert climate.hvac_action == expected


# ---------------------------------------------------------------------------
# icon property
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("running", "operation_mode", "expected_icon"),
    [
        (True, "COOLING", "mdi:snowflake"),
        (True, "HEATING", "mdi:fire"),
        (True, "DRY", "mdi:water-percent"),
        (True, "FAN", "mdi:fan"),
        (True, "AUTO", "mdi:thermostat-auto"),
        (False, "COOLING", "mdi:air-conditioner"),  # OFF mode
    ],
)
def test_icon(running: bool, operation_mode: str, expected_icon: str) -> None:
    """The icon should reflect the current HVAC mode."""
    climate = _make_climate({"running": running, "operationMode": operation_mode})
    assert climate.icon == expected_icon


# ---------------------------------------------------------------------------
# temperature properties
# ---------------------------------------------------------------------------


def test_current_temperature_reads_room_air_temperature() -> None:
    """current_temperature should read roomAirTemperature from zone data."""
    climate = _make_climate({"roomAirTemperature": 21.5})
    assert climate.current_temperature == 21.5


def test_current_temperature_returns_none_when_missing() -> None:
    """current_temperature should return None when the value is absent."""
    climate = _make_climate({})
    assert climate.current_temperature is None


def test_target_temperature_reads_setpoint() -> None:
    """target_temperature should read the setpoint field."""
    climate = _make_climate({"setpoint": 23.0})
    assert climate.target_temperature == 23.0


def test_min_temp_reads_cooling_lower_bound() -> None:
    """min_temp should come from temperatureRangeCooling.lower."""
    climate = _make_climate(
        {"temperatureRangeCooling": {"lower": 16.0, "upper": 30.0}}
    )
    assert climate.min_temp == 16.0


def test_min_temp_defaults_to_18_when_missing() -> None:
    """min_temp should default to 18.0 when range is absent."""
    climate = _make_climate({})
    assert climate.min_temp == 18.0


def test_max_temp_reads_heating_upper_bound() -> None:
    """max_temp should come from temperatureRangeHeating.upper."""
    climate = _make_climate(
        {"temperatureRangeHeating": {"lower": 16.0, "upper": 32.0}}
    )
    assert climate.max_temp == 32.0


def test_max_temp_defaults_to_30_when_missing() -> None:
    """max_temp should default to 30.0 when range is absent."""
    climate = _make_climate({})
    assert climate.max_temp == 30.0


# ---------------------------------------------------------------------------
# fan_mode property
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_fan", "expected"),
    [
        ("AUTO", "auto"),
        ("LOW", "low"),
        ("MEDIUM", "medium"),
        ("HIGH", "high"),
        ("POWERFUL", FAN_POWERFUL),
        ("UNKNOWN", "auto"),  # unmapped → AUTO fallback
    ],
)
def test_fan_mode(raw_fan: str, expected: str) -> None:
    """fan_mode should map gateway fan speed to HA fan mode strings."""
    climate = _make_climate({"fanSpeed": raw_fan})
    assert climate.fan_mode == expected


# ---------------------------------------------------------------------------
# swing_modes property
# ---------------------------------------------------------------------------


def test_swing_modes_maps_gateway_positions() -> None:
    """swing_modes should map gateway vane/louver options to UI labels."""
    climate = _make_climate(
        {
            "patchOptions": {
                "vanePosition": ["AUTO", "POSITION_1", "POSITION_3"],
            }
        }
    )
    modes = climate.swing_modes
    assert "auto" in modes
    assert "Position 1" in modes
    assert "Position 3" in modes


def test_swing_modes_falls_back_to_auto_when_no_options() -> None:
    """swing_modes should default to [auto] when no patch options exist."""
    climate = _make_climate({})
    assert climate.swing_modes == [SWING_AUTO]


def test_swing_mode_reads_vane_position() -> None:
    """swing_mode should read the vanePosition field from zone data."""
    climate = _make_climate({"vanePosition": "POSITION_2"})
    assert climate.swing_mode == "Position 2"


def test_swing_mode_reads_louver_position_fallback() -> None:
    """swing_mode should fall back to louverPosition when vanePosition is absent."""
    climate = _make_climate({"louverPosition": "AUTO"})
    assert climate.swing_mode == SWING_AUTO


def test_swing_mode_returns_none_when_no_position() -> None:
    """swing_mode should return None when neither vane nor louver is set."""
    climate = _make_climate({})
    assert climate.swing_mode is None


# ---------------------------------------------------------------------------
# async_set_hvac_mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_set_hvac_mode_off_calls_running_false() -> None:
    """Setting HVAC mode to OFF should call async_set_zone_state with running=False."""
    api = SimpleNamespace(
        host="gateway",
        async_set_zone_state=AsyncMock(),
    )
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1, "running": True, "operationMode": "COOLING"}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    climate = NovaRcZoneClimate(coordinator, 1)
    await climate.async_set_hvac_mode(HVACMode.OFF)
    api.async_set_zone_state.assert_awaited_once_with(1, running=False)


@pytest.mark.asyncio
async def test_async_set_hvac_mode_no_airflow_wait_when_already_running() -> None:
    """HVAC mode change should not request airflow wait when the unit is already running."""
    api = SimpleNamespace(
        host="gateway",
        async_set_zone_state=AsyncMock(),
    )
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1, "running": True, "operationMode": "COOLING"}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    climate = NovaRcZoneClimate(coordinator, 1)
    await climate.async_set_hvac_mode(HVACMode.HEAT)
    api.async_set_zone_state.assert_awaited_once_with(
        1,
        running=True,
        operation_mode="HEATING",
        wait_for_airflow_after_start=False,
    )


# ---------------------------------------------------------------------------
# async_set_swing_mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_set_swing_mode_maps_label_to_gateway_value() -> None:
    """async_set_swing_mode should translate UI labels to gateway values."""
    api = SimpleNamespace(
        host="gateway",
        async_set_zone_state=AsyncMock(),
    )
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1, "running": True}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    climate = NovaRcZoneClimate(coordinator, 1)
    await climate.async_set_swing_mode("Position 3")
    api.async_set_zone_state.assert_awaited_once_with(1, vane_position="POSITION_3")


@pytest.mark.asyncio
async def test_async_set_swing_mode_passes_through_unknown_value() -> None:
    """An unknown swing mode should be forwarded to the gateway as-is."""
    api = SimpleNamespace(
        host="gateway",
        async_set_zone_state=AsyncMock(),
    )
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1, "running": True}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    climate = NovaRcZoneClimate(coordinator, 1)
    await climate.async_set_swing_mode("CUSTOM_VALUE")
    api.async_set_zone_state.assert_awaited_once_with(1, vane_position="CUSTOM_VALUE")
