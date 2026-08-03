"""Integration tests for select and switch entity properties and async actions."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.mhi_nova_link.select import NovaRcLouverSelect, NovaRcVaneSelect
from custom_components.mhi_nova_link.switch import NovaRc3DAutoSwitch

from tests.conftest import make_coordinator


def _coord(zone_data: dict):
    return make_coordinator(zones=[{**zone_data, "zoneId": 1}])


def _api_coord(zone_data: dict):
    api = SimpleNamespace(host="gateway.local", async_set_zone_state=AsyncMock())
    coord = SimpleNamespace(
        data=[{**zone_data, "zoneId": 1}],
        config_entry=SimpleNamespace(domain="mhi_nova_link", entry_id="e"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
        async_request_refresh=AsyncMock(),
    )
    return coord, api


# ---------------------------------------------------------------------------
# NovaRcLouverSelect
# ---------------------------------------------------------------------------


def test_louver_current_option_maps_gateway_value() -> None:
    """current_option should translate the gateway value to a UI label."""
    assert NovaRcLouverSelect(_coord({"louverPosition": "POSITION_2"}), 1).current_option == "Position 2   ↘"


def test_louver_current_option_none_when_absent() -> None:
    """current_option should return None when no position is set."""
    assert NovaRcLouverSelect(_coord({}), 1).current_option is None


def test_louver_options_from_patch_options() -> None:
    """options should be built from patchOptions.louverPosition."""
    entity = NovaRcLouverSelect(_coord({"patchOptions": {"louverPosition": ["POSITION_1", "AUTO"]}}), 1)
    assert "Auto ↺" in entity.options
    assert len(entity.options) == 2


def test_louver_options_default_list_when_no_patch_options() -> None:
    """options should fall back to the default five positions."""
    assert len(NovaRcLouverSelect(_coord({}), 1).options) == 5


@pytest.mark.parametrize(
    ("gateway_val", "expected_icon"),
    [
        ("POSITION_1", "mdi:arrow-top-right"),
        ("POSITION_2", "mdi:arrow-right-top"),
        ("POSITION_3", "mdi:arrow-bottom-right"),
        ("POSITION_4", "mdi:arrow-down-right"),
        ("AUTO", "mdi:sync"),
        (None, "mdi:arrow-up-down-bold"),
    ],
)
def test_louver_icon(gateway_val: str | None, expected_icon: str) -> None:
    """icon should reflect the current louver position."""
    assert NovaRcLouverSelect(_coord({"louverPosition": gateway_val}), 1).icon == expected_icon


@pytest.mark.asyncio
async def test_louver_async_select_option_maps_label_to_gateway_value() -> None:
    """async_select_option should translate UI label to the gateway value."""
    coord, api = _api_coord({})
    await NovaRcLouverSelect(coord, 1).async_select_option("Auto ↺")
    api.async_set_zone_state.assert_awaited_once_with(1, louver_position="AUTO")


@pytest.mark.asyncio
async def test_louver_async_select_option_passes_through_unknown_value() -> None:
    """An unknown option should be forwarded as-is to the API."""
    coord, api = _api_coord({})
    await NovaRcLouverSelect(coord, 1).async_select_option("CUSTOM")
    api.async_set_zone_state.assert_awaited_once_with(1, louver_position="CUSTOM")


# ---------------------------------------------------------------------------
# NovaRcVaneSelect
# ---------------------------------------------------------------------------


def test_vane_current_option_maps_gateway_value() -> None:
    """current_option should translate the vane gateway value."""
    assert NovaRcVaneSelect(_coord({"vanePosition": "SPOT"}), 1).current_option == "Spot"


def test_vane_current_option_none_when_absent() -> None:
    """current_option should return None when no position is set."""
    assert NovaRcVaneSelect(_coord({}), 1).current_option is None


def test_vane_options_from_patch_options() -> None:
    """options should reflect patchOptions.vanePosition."""
    entity = NovaRcVaneSelect(_coord({"patchOptions": {"vanePosition": ["POSITION_1", "WIDE", "AUTO"]}}), 1)
    assert "Wide" in entity.options


def test_vane_options_default_when_no_patch_options() -> None:
    """Default vane options should include all eight positions."""
    assert len(NovaRcVaneSelect(_coord({}), 1).options) == 8


@pytest.mark.parametrize(
    ("gateway_val", "expected_icon"),
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
def test_vane_icon(gateway_val: str | None, expected_icon: str) -> None:
    """icon should reflect the current vane position."""
    assert NovaRcVaneSelect(_coord({"vanePosition": gateway_val}), 1).icon == expected_icon


@pytest.mark.asyncio
async def test_vane_async_select_option_maps_label_to_gateway_value() -> None:
    """async_select_option should send the gateway value to the API."""
    coord, api = _api_coord({})
    await NovaRcVaneSelect(coord, 1).async_select_option("Wide")
    api.async_set_zone_state.assert_awaited_once_with(1, vane_position="WIDE")


# ---------------------------------------------------------------------------
# NovaRc3DAutoSwitch
# ---------------------------------------------------------------------------


def test_3d_auto_switch_on_when_enabled() -> None:
    assert NovaRc3DAutoSwitch(_coord({"flap3dAuto": True}), 1).is_on is True


def test_3d_auto_switch_off_when_disabled() -> None:
    assert NovaRc3DAutoSwitch(_coord({"flap3dAuto": False}), 1).is_on is False


def test_3d_auto_switch_off_when_key_absent() -> None:
    assert NovaRc3DAutoSwitch(_coord({}), 1).is_on is False


@pytest.mark.asyncio
async def test_3d_auto_switch_turn_on() -> None:
    """async_turn_on should call async_set_zone_state with flap3d_auto=True."""
    coord, api = _api_coord({"flap3dAuto": False})
    await NovaRc3DAutoSwitch(coord, 1).async_turn_on()
    api.async_set_zone_state.assert_awaited_once_with(1, flap3d_auto=True)
    coord.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_3d_auto_switch_turn_off() -> None:
    """async_turn_off should call async_set_zone_state with flap3d_auto=False."""
    coord, api = _api_coord({"flap3dAuto": True})
    await NovaRc3DAutoSwitch(coord, 1).async_turn_off()
    api.async_set_zone_state.assert_awaited_once_with(1, flap3d_auto=False)
    coord.async_request_refresh.assert_awaited_once()
