"""Implement switch entities for NOVA_RC controls."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NovaRcConfigEntry
from .coordinator import NovaRcDataUpdateCoordinator
from .entity import NovaRcZoneEntity


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

    entities: list[SwitchEntity] = []
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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable 3D auto mode on the gateway."""
        await self.coordinator.api.async_set_zone_state(self.zone_id, flap3d_auto=True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable 3D auto mode on the gateway."""
        await self.coordinator.api.async_set_zone_state(self.zone_id, flap3d_auto=False)
        await self.coordinator.async_request_refresh()
