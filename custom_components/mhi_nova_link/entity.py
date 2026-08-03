"""Provide shared entity helpers for NOVA_RC zones."""

from typing import Any

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NovaRcDataUpdateCoordinator


class NovaRcZoneEntity(CoordinatorEntity[NovaRcDataUpdateCoordinator]):
    """Common base for zone-scoped entities in the custom integration.

    The integration is centered around gateway zones, so this shared base keeps the
    device metadata and zone lookup logic consistent across entities.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: NovaRcDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize the entity for a specific gateway zone."""
        super().__init__(coordinator)
        self.zone_id = zone_id

    @property
    def _zone_data(self) -> dict[str, Any]:
        """Return the latest zone payload for the entity."""
        for zone in self.coordinator.data:
            if zone.get("zoneId") == self.zone_id:
                return zone
        return {}

    @property
    def device_info(self) -> dict[str, Any]:
        """Return Home Assistant device metadata for the zone."""
        zone_name = (
            self._zone_data.get("name")
            or self._zone_data.get("displayName")
            or f"Zone {self.zone_id}"
        )
        sw_version = (
            getattr(self.coordinator, "gateway_update", {}).get("installed_version")
            or getattr(self.coordinator, "gateway_update", {}).get("available_version")
        )
        device_info: dict[str, Any] = {
            "identifiers": {
                (
                    DOMAIN,
                    f"{self.coordinator.config_entry.entry_id}_{self.zone_id}",
                )
            },
            "name": f"{zone_name}",
            "manufacturer": "STULZ GmbH",
            "model": "CompTrol 4Web NOVA RC",
        }
        if sw_version is not None:
            device_info["sw_version"] = sw_version
        return device_info

    def get_indoor_unit_data(self, indoor_unit_id: int) -> dict[str, Any]:
        """Return the payload for a specific indoor unit attached to the zone."""
        for indoor_unit in self._zone_data.get("indoorUnits", []) or []:
            if indoor_unit.get("indoorUnitId") == indoor_unit_id:
                return indoor_unit
        return {}
