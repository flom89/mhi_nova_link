"""Implement switch entities for NOVA_RC controls."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NovaRcConfigEntry
from .coordinator import NovaRcDataUpdateCoordinator
from .entity import NovaRcZoneEntity, build_gateway_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry | NovaRcConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 3D auto switch for each zone."""
    coordinator: NovaRcDataUpdateCoordinator
    if hasattr(entry, "runtime_data"):
        coordinator = entry.runtime_data.coordinator
    else:
        coordinator = hass.data[entry.domain][entry.entry_id]

    entities: list[SwitchEntity] = [
        NovaRcSystemStopSwitch(coordinator),
        NovaRcFreeCoolingSwitch(coordinator),
    ]
    for zone in coordinator.data:
        zone_id = zone.get("zoneId")
        if zone_id is None:
            continue
        entities.append(NovaRc3DAutoSwitch(coordinator, zone_id))

    async_add_entities(entities)


class NovaRc3DAutoSwitch(NovaRcZoneEntity, SwitchEntity):
    """Switch for 3D auto mode."""

    _attr_translation_key = "three_d_auto"
    _attr_icon = "mdi:axis-arrow"

    def __init__(self, coordinator: NovaRcDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize a switch for a specific gateway zone."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_3d_auto"

    @property
    def is_on(self) -> bool:
        """Return whether 3D auto mode is enabled."""
        return bool(self._zone_data.get("flap3dAuto", False))

    @property
    def available(self) -> bool:
        """Return whether this control is available in the UI."""
        return super().available and not getattr(self.coordinator, "is_user_control_locked", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable 3D auto mode on the gateway."""
        if getattr(self.coordinator, "is_user_control_locked", False):
            raise HomeAssistantError("Betriebssperre aktiv: Änderung nicht erlaubt")
        mark_user_interaction = getattr(self.coordinator, "async_mark_user_interaction", None)
        if callable(mark_user_interaction):
            mark_user_interaction("switch.async_turn_on_3d_auto")
        await self.coordinator.api.async_set_zone_state(self.zone_id, flap3d_auto=True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable 3D auto mode on the gateway."""
        if getattr(self.coordinator, "is_user_control_locked", False):
            raise HomeAssistantError("Betriebssperre aktiv: Änderung nicht erlaubt")
        mark_user_interaction = getattr(self.coordinator, "async_mark_user_interaction", None)
        if callable(mark_user_interaction):
            mark_user_interaction("switch.async_turn_off_3d_auto")
        await self.coordinator.api.async_set_zone_state(self.zone_id, flap3d_auto=False)
        await self.coordinator.async_request_refresh()


class NovaRcGatewayControlSwitch(CoordinatorEntity[NovaRcDataUpdateCoordinator], SwitchEntity):
    """Base switch for active-high controlled gateway input GPIOs."""

    _attr_has_entity_name = True
    _allow_during_system_stop_lock = False
    _gpio_id: str
    _gpio_function: str

    def __init__(self, coordinator: NovaRcDataUpdateCoordinator) -> None:
        """Initialize a gateway-level GPIO control switch."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.api.host}_gateway_gpio_control_{self._gpio_function.lower()}"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device metadata for the gateway IO device."""
        entry_id = (
            self.coordinator.config_entry.entry_id if self.coordinator.config_entry else "unknown"
        )
        return build_gateway_device_info(
            entry_id,
            identifier_suffix="gateway",
            name="Digital IOs",
        )

    @property
    def is_on(self) -> bool:
        """Return whether the associated function is logically forced active."""
        active_high = self.coordinator.gpio_active_high.get(self._gpio_function, True)
        return not active_high

    @property
    def available(self) -> bool:
        """Return whether this control is available in the UI."""
        return super().available and (
            self._allow_during_system_stop_lock
            or not getattr(self.coordinator, "is_user_control_locked", False)
        )

    def _ensure_write_allowed(self) -> None:
        """Block user writes while operation lock is active."""
        if (
            getattr(self.coordinator, "is_user_control_locked", False)
            and not self._allow_during_system_stop_lock
        ):
            raise HomeAssistantError("Betriebssperre aktiv: Änderung nicht erlaubt")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the logical active state by using LOW as active level."""
        self._ensure_write_allowed()
        mark_user_interaction = getattr(self.coordinator, "async_mark_user_interaction", None)
        if callable(mark_user_interaction):
            mark_user_interaction(f"switch.async_turn_on_{self._gpio_function.lower()}")
        capture_restore = getattr(self.coordinator, "async_capture_restore_snapshot", None)
        if callable(capture_restore):
            await capture_restore(self._gpio_function)
        result = await self.coordinator.api.async_set_gpio_active_high(self._gpio_id, False)
        if result:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the logical active state by using HIGH as active level."""
        self._ensure_write_allowed()
        mark_user_interaction = getattr(self.coordinator, "async_mark_user_interaction", None)
        if callable(mark_user_interaction):
            mark_user_interaction(f"switch.async_turn_off_{self._gpio_function.lower()}")
        result = await self.coordinator.api.async_set_gpio_active_high(self._gpio_id, True)
        if result:
            await self.coordinator.async_request_refresh()
            restore_after_release = getattr(self.coordinator, "async_restore_after_release", None)
            if callable(restore_after_release):
                await restore_after_release(self._gpio_function)


class NovaRcSystemStopSwitch(NovaRcGatewayControlSwitch):
    """Switch to control Betriebssperre via SYSTEM_STOP input interpretation."""

    _attr_translation_key = "betriebssperre"
    _allow_during_system_stop_lock = True
    _gpio_id = "/gpio/system_stop"
    _gpio_function = "SYSTEM_STOP"


class NovaRcFreeCoolingSwitch(NovaRcGatewayControlSwitch):
    """Switch to control Externe Kühlung via FREE_COOLING input interpretation."""

    _attr_translation_key = "externe_kuehlung"
    _gpio_id = "/gpio/sequencing_stop"
    _gpio_function = "FREE_COOLING"
