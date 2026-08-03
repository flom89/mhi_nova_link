"""Unit tests for select and switch entity properties and actions."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

_integration_dir = Path(__file__).resolve().parents[1]
_config_dir = _integration_dir.parent.parent
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

from custom_components.mhi_nova_link.select import (  # noqa: E402
    NovaRcLouverSelect,
    NovaRcVaneSelect,
)
from custom_components.mhi_nova_link.switch import NovaRc3DAutoSwitch  # noqa: E402


def _coordinator(zone_data: dict) -> SimpleNamespace:
    """Return a minimal coordinator stub with one zone."""
    return SimpleNamespace(
        data=[{**zone_data, "zoneId": 1}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )


# ---------------------------------------------------------------------------
# NovaRcLouverSelect
# ---------------------------------------------------------------------------


def test_louver_select_current_option_maps_gateway_value() -> None:
    """current_option should translate gateway position to UI label."""
    coordinator = _coordinator({"louverPosition": "POSITION_2"})
    entity = NovaRcLouverSelect(coordinator, 1)
    assert entity.current_option == "Position 2   ↘"


def test_louver_select_current_option_returns_none_for_missing_value() -> None:
    """current_option should return None when no position is set."""
    coordinator = _coordinator({})
    entity = NovaRcLouverSelect(coordinator, 1)
    assert entity.current_option is None


def test_louver_select_options_from_patch_options() -> None:
    """options should be built from patchOptions.louverPosition when present."""
    coordinator = _coordinator(
        {"patchOptions": {"louverPosition": ["POSITION_1", "AUTO"]}}
    )
    entity = NovaRcLouverSelect(coordinator, 1)
    options = entity.options
    assert len(options) == 2
    assert "Auto ↺" in options


def test_louver_select_options_fallback_when_no_patch_options() -> None:
    """options should fall back to the default list when patchOptions is absent."""
    coordinator = _coordinator({})
    entity = NovaRcLouverSelect(coordinator, 1)
    assert len(entity.options) == 5  # default: POSITION_1..4 + AUTO


@pytest.mark.parametrize(
    ("current_option", "expected_icon"),
    [
        ("Position 1   ↗", "mdi:arrow-top-right"),
        ("Position 2   ↘", "mdi:arrow-right-top"),
        ("Position 3  ↘↘", "mdi:arrow-bottom-right"),
        ("Position 4   ↓", "mdi:arrow-down-right"),
        ("Auto ↺", "mdi:sync"),
        (None, "mdi:arrow-up-down-bold"),
    ],
)
def test_louver_select_icon(current_option: str | None, expected_icon: str) -> None:
    """icon should reflect the current louver position."""
    gateway_value: str | None = None
    if current_option == "Position 1   ↗":
        gateway_value = "POSITION_1"
    elif current_option == "Position 2   ↘":
        gateway_value = "POSITION_2"
    elif current_option == "Position 3  ↘↘":
        gateway_value = "POSITION_3"
    elif current_option == "Position 4   ↓":
        gateway_value = "POSITION_4"
    elif current_option == "Auto ↺":
        gateway_value = "AUTO"

    coordinator = _coordinator({"louverPosition": gateway_value})
    entity = NovaRcLouverSelect(coordinator, 1)
    assert entity.icon == expected_icon


@pytest.mark.asyncio
async def test_louver_select_async_select_option_maps_label_to_gateway_value() -> None:
    """async_select_option should translate UI labels to gateway values."""
    api = SimpleNamespace(host="gateway", async_set_zone_state=AsyncMock())
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    entity = NovaRcLouverSelect(coordinator, 1)
    await entity.async_select_option("Auto ↺")
    api.async_set_zone_state.assert_awaited_once_with(1, louver_position="AUTO")


@pytest.mark.asyncio
async def test_louver_select_async_select_option_passes_through_unknown_value() -> None:
    """An unknown option should be forwarded to the gateway as-is."""
    api = SimpleNamespace(host="gateway", async_set_zone_state=AsyncMock())
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    entity = NovaRcLouverSelect(coordinator, 1)
    await entity.async_select_option("CUSTOM_VALUE")
    api.async_set_zone_state.assert_awaited_once_with(1, louver_position="CUSTOM_VALUE")


# ---------------------------------------------------------------------------
# NovaRcVaneSelect
# ---------------------------------------------------------------------------


def test_vane_select_current_option_maps_gateway_value() -> None:
    """current_option should translate gateway vane position to UI label."""
    coordinator = _coordinator({"vanePosition": "SPOT"})
    entity = NovaRcVaneSelect(coordinator, 1)
    assert entity.current_option == "Spot"


def test_vane_select_current_option_returns_none_for_missing_value() -> None:
    """current_option should return None when no position is set."""
    coordinator = _coordinator({})
    entity = NovaRcVaneSelect(coordinator, 1)
    assert entity.current_option is None


def test_vane_select_options_from_patch_options() -> None:
    """options should be built from patchOptions.vanePosition when present."""
    coordinator = _coordinator(
        {"patchOptions": {"vanePosition": ["POSITION_1", "WIDE", "AUTO"]}}
    )
    entity = NovaRcVaneSelect(coordinator, 1)
    options = entity.options
    assert "Position 1" in options
    assert "Wide" in options
    assert "Auto" in options


def test_vane_select_options_fallback_when_no_patch_options() -> None:
    """options should default to all positions when patchOptions is absent."""
    coordinator = _coordinator({})
    entity = NovaRcVaneSelect(coordinator, 1)
    assert len(entity.options) == 8  # POSITION_1..5, SPOT, WIDE, AUTO


@pytest.mark.parametrize(
    ("gateway_value", "expected_icon"),
    [
        ("POSITION_1", "mdi:arrow-left"),
        ("POSITION_2", "mdi:arrow-left"),
        ("POSITION_3", "mdi:arrow-up"),
        ("POSITION_4", "mdi:arrow-right"),
        ("POSITION_5", "mdi:arrow-right"),
        ("SPOT", "mdi:target"),
        ("WIDE", "mdi:arrow-expand-horizontal"),
        ("AUTO", "mdi:sync"),
        (None, "mdi:arrow-left-right-bold"),
    ],
)
def test_vane_select_icon(gateway_value: str | None, expected_icon: str) -> None:
    """icon should match the current vane position."""
    coordinator = _coordinator({"vanePosition": gateway_value})
    entity = NovaRcVaneSelect(coordinator, 1)
    assert entity.icon == expected_icon


@pytest.mark.asyncio
async def test_vane_select_async_select_option_maps_label_to_gateway_value() -> None:
    """async_select_option should translate UI labels to gateway values."""
    api = SimpleNamespace(host="gateway", async_set_zone_state=AsyncMock())
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    entity = NovaRcVaneSelect(coordinator, 1)
    await entity.async_select_option("Wide")
    api.async_set_zone_state.assert_awaited_once_with(1, vane_position="WIDE")


# ---------------------------------------------------------------------------
# NovaRc3DAutoSwitch
# ---------------------------------------------------------------------------


def test_3d_auto_switch_is_on_when_enabled() -> None:
    """Switch should be on when flap3dAuto is True."""
    coordinator = _coordinator({"flap3dAuto": True})
    entity = NovaRc3DAutoSwitch(coordinator, 1)
    assert entity.is_on is True


def test_3d_auto_switch_is_off_when_disabled() -> None:
    """Switch should be off when flap3dAuto is False."""
    coordinator = _coordinator({"flap3dAuto": False})
    entity = NovaRc3DAutoSwitch(coordinator, 1)
    assert entity.is_on is False


def test_3d_auto_switch_is_off_when_key_absent() -> None:
    """Switch should default to off when flap3dAuto is absent."""
    coordinator = _coordinator({})
    entity = NovaRc3DAutoSwitch(coordinator, 1)
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_3d_auto_switch_turn_on_calls_api_with_true() -> None:
    """async_turn_on should call async_set_zone_state with flap3d_auto=True."""
    api = SimpleNamespace(host="gateway", async_set_zone_state=AsyncMock())
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1, "flap3dAuto": False}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    entity = NovaRc3DAutoSwitch(coordinator, 1)
    await entity.async_turn_on()
    api.async_set_zone_state.assert_awaited_once_with(1, flap3d_auto=True)
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_3d_auto_switch_turn_off_calls_api_with_false() -> None:
    """async_turn_off should call async_set_zone_state with flap3d_auto=False."""
    api = SimpleNamespace(host="gateway", async_set_zone_state=AsyncMock())
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1, "flap3dAuto": True}],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    entity = NovaRc3DAutoSwitch(coordinator, 1)
    await entity.async_turn_off()
    api.async_set_zone_state.assert_awaited_once_with(1, flap3d_auto=False)
    coordinator.async_request_refresh.assert_awaited_once()
