"""Implement select entities for NOVA_RC airflow controls."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NovaRcConfigEntry
from .coordinator import NovaRcDataUpdateCoordinator
from .entity import NovaRcZoneEntity

# Position mapping (gateway values to UI text)
LOUVER_MAP = {
    "POSITION_1": "Position 1   ↗",
    "POSITION_2": "Position 2   ↘",
    "POSITION_3": "Position 3  ↘↘",
    "POSITION_4": "Position 4   ↓",
    "AUTO": "Auto ↺",
}
LOUVER_REVERSE_MAP = {v: k for k, v in LOUVER_MAP.items()}

VANE_MAP = {
    "POSITION_1": "Position 1",
    "POSITION_2": "Position 2",
    "POSITION_3": "Position 3",
    "POSITION_4": "Position 4",
    "POSITION_5": "Position 5",
    "SPOT": "Spot",
    "WIDE": "Wide",
    "AUTO": "Auto",
}
VANE_REVERSE_MAP = {v: k for k, v in VANE_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry | NovaRcConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entities for each zone."""
    coordinator: NovaRcDataUpdateCoordinator
    if hasattr(entry, "runtime_data"):
        coordinator = entry.runtime_data.coordinator
    else:
        coordinator = hass.data[entry.domain][entry.entry_id]

    entities: list[SelectEntity] = []
    for zone in coordinator.data:
        zone_id = zone.get("zoneId")
        if zone_id is None:
            continue
        entities.append(NovaRcLouverSelect(coordinator, zone_id))
        entities.append(NovaRcVaneSelect(coordinator, zone_id))

    async_add_entities(entities)


class NovaRcBaseSelect(NovaRcZoneEntity, SelectEntity):
    """Base implementation for NOVA_RC select entities."""


class NovaRcLouverSelect(NovaRcBaseSelect):
    """Select entity for the louver position."""

    _attr_translation_key = "louver_position"

    def __init__(self, coordinator: NovaRcDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_louver"

    @property
    def icon(self) -> str:
        """Return an icon matching the current louver position."""
        match self.current_option:
            case "Position 1":
                return "mdi:arrow-top-right"
            case "Position 2":
                return "mdi:arrow-right-top"
            case "Position 3":
                return "mdi:arrow-bottom-right"
            case "Position 4":
                return "mdi:arrow-down-right"
            case "Auto":
                return "mdi:sync"
            case _:
                return "mdi:arrow-up-down-bold"

    @property
    def options(self) -> list[str]:
        """Return the available louver position options from the gateway patch options."""
        patch_opts = self._zone_data.get("patchOptions") or {}
        raw_opts = patch_opts.get("louverPosition") or [
            "POSITION_1",
            "POSITION_2",
            "POSITION_3",
            "POSITION_4",
            "AUTO",
        ]
        return [LOUVER_MAP.get(opt, opt) for opt in raw_opts]

    @property
    def current_option(self) -> str | None:
        """Return the current position."""
        raw = self._zone_data.get("louverPosition")
        if raw is None:
            return None
        if not isinstance(raw, str):
            return str(raw)
        return LOUVER_MAP.get(raw, raw)

    async def async_select_option(self, option: str) -> None:
        """Change the louver position on the gateway."""
        raw_val = LOUVER_REVERSE_MAP.get(option, option)
        await self.coordinator.api.async_set_zone_state(
            self.zone_id, louver_position=raw_val
        )
        await self.coordinator.async_request_refresh()


class NovaRcVaneSelect(NovaRcBaseSelect):
    """Select entity for the vane position."""

    _attr_translation_key = "vane_position"

    def __init__(self, coordinator: NovaRcDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_vane"

    @property
    def icon(self) -> str:
        """Return an icon matching the current vane position."""
        match self.current_option:
            case "Position 1" | "Position 2":
                return "mdi:arrow-left"
            case "Position 3":
                return "mdi:arrow-up"
            case "Position 4" | "Position 5":
                return "mdi:arrow-right"
            case "Spot":
                return "mdi:target"
            case "Wide":
                return "mdi:arrow-expand-horizontal"
            case "Auto":
                return "mdi:sync"
            case _:
                return "mdi:arrow-left-right-bold"

    @property
    def options(self) -> list[str]:
        """Return the available vane position options from the gateway patch options."""
        patch_opts = self._zone_data.get("patchOptions") or {}
        raw_opts = patch_opts.get("vanePosition") or [
            "POSITION_1",
            "POSITION_2",
            "POSITION_3",
            "POSITION_4",
            "POSITION_5",
            "SPOT",
            "WIDE",
            "AUTO",
        ]
        return [VANE_MAP.get(opt, opt) for opt in raw_opts]

    @property
    def current_option(self) -> str | None:
        """Return the current position."""
        raw = self._zone_data.get("vanePosition")
        if raw is None:
            return None
        if not isinstance(raw, str):
            return str(raw)
        return VANE_MAP.get(raw, raw)

    async def async_select_option(self, option: str) -> None:
        """Change the vane position on the gateway."""
        raw_val = VANE_REVERSE_MAP.get(option, option)
        await self.coordinator.api.async_set_zone_state(
            self.zone_id, vane_position=raw_val
        )
        await self.coordinator.async_request_refresh()
