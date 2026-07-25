"""Binary sensors for MHI NovaLink."""

import inspect
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SKlimaDataUpdateCoordinator
from .entity import SKlimaZoneEntity
from .helpers import dataset_is_on, get_zone_time_series_datasets

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator: SKlimaDataUpdateCoordinator = hass.data[entry.domain][entry.entry_id]

    entities: list[BinarySensorEntity] = []
    for zone in coordinator.data:
        zone_id = zone.get("zoneId")
        if zone_id is None:
            continue

        entities.append(SKlimaAvailableBinarySensor(coordinator, zone_id))
        entities.append(SKlimaNotificationsBinarySensor(coordinator, zone_id))

        for indoor_unit in zone.get("indoorUnits", []) or []:
            indoor_unit_id = indoor_unit.get("indoorUnitId")
            if indoor_unit_id is None:
                continue
            entities.append(
                SKlimaIndoorUnitRunningBinarySensor(
                    coordinator, zone_id, indoor_unit_id
                )
            )

    result = async_add_entities(entities)
    if inspect.isawaitable(result):
        await result


class SKlimaBaseBinarySensor(SKlimaZoneEntity, BinarySensorEntity):
    """Base implementation for zone binary sensors."""


class SKlimaRunningBinarySensor(SKlimaBaseBinarySensor):
    """Zone is running."""

    _attr_translation_key = "running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the running state sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_running"

    @property
    def is_on(self) -> bool:
        """Return whether the zone is currently running."""
        return self._zone_data.get("running", False)


class SKlimaAvailableBinarySensor(SKlimaBaseBinarySensor):
    """Zone is available."""

    _attr_translation_key = "available"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the availability sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_available"

    @property
    def is_on(self) -> bool:
        """Return whether the zone is available."""
        return self._zone_data.get("available", False)


class SKlima3DAutoBinarySensor(SKlimaBaseBinarySensor):
    """3D auto mode."""

    _attr_translation_key = "three_d_auto"

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the 3D auto state sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_3d_auto"

    @property
    def is_on(self) -> bool:
        """Return whether 3D auto is enabled."""
        return self._zone_data.get("flap3dAuto", False)


class SKlimaTemperatureRangeBinarySensor(SKlimaBaseBinarySensor):
    """Temperature range is enabled."""

    _attr_translation_key = "temperature_range"

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the temperature range sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_temp_range"

    @property
    def is_on(self) -> bool:
        """Return whether temperature range mode is enabled."""
        return self._zone_data.get("temperatureRangeEnable", False)


class SKlimaCriticalErrorBinarySensor(SKlimaBaseBinarySensor):
    """Critical error."""

    _attr_translation_key = "critical_error"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the critical error sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_critical_error"

    @property
    def is_on(self) -> bool:
        """Return whether the zone reports a critical error."""
        error = self._zone_data.get("error") or {}
        return error.get("criticalCount", 0) > 0


class SKlimaMaintenanceBinarySensor(SKlimaBaseBinarySensor):
    """Maintenance required."""

    _attr_translation_key = "maintenance_required"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the maintenance sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_maintenance"

    @property
    def is_on(self) -> bool:
        """Return whether the zone needs maintenance."""
        error = self._zone_data.get("error") or {}
        return error.get("maintenanceCount", 0) > 0


class SKlimaCompressorBinarySensor(SKlimaBaseBinarySensor):
    """Compressor activity state."""

    _attr_translation_key = "compressor_active"

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the compressor activity binary sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_compressor"

    @property
    def is_on(self) -> bool:
        """Return whether the compressor is currently active."""
        datasets = get_zone_time_series_datasets(self._zone_data)
        dataset = datasets.get("compressor_active")
        if not dataset:
            return False
        return dataset_is_on("compressor_active", dataset)


class SKlimaDefrostingBinarySensor(SKlimaBaseBinarySensor):
    """Defrosting activity state."""

    _attr_translation_key = "defrosting_active"

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the defrosting binary sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_defrosting"

    @property
    def is_on(self) -> bool:
        """Return whether the gateway reports active defrosting."""
        datasets = get_zone_time_series_datasets(self._zone_data)
        dataset = datasets.get("defrosting_active")
        if not dataset:
            return False
        return dataset_is_on("defrosting_active", dataset)


class SKlimaFilterBinarySensor(SKlimaBaseBinarySensor):
    """Filter replacement reminder."""

    _attr_translation_key = "filter_sign"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the filter reminder binary sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_filter"

    @property
    def is_on(self) -> bool:
        """Return whether the filter reminder is active."""
        datasets = get_zone_time_series_datasets(self._zone_data)
        dataset = datasets.get("filter_sign")
        if not dataset:
            return False
        return dataset_is_on("filter_sign", dataset)


class SKlimaIndoorUnitRunningBinarySensor(SKlimaBaseBinarySensor):
    """Running state for an individual indoor unit."""

    _attr_translation_key = "indoor_unit_running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
        indoor_unit_id: int,
    ) -> None:
        """Initialize the indoor-unit running binary sensor."""
        super().__init__(coordinator, zone_id)
        self.indoor_unit_id = indoor_unit_id
        self._attr_unique_id = (
            f"{coordinator.api.host}_zone_{zone_id}_indoor_{indoor_unit_id}_running"
        )

    @property
    def _indoor_unit_data(self) -> dict[str, Any]:
        return self.get_indoor_unit_data(self.indoor_unit_id)

    @property
    def is_on(self) -> bool:
        """Return whether the indoor unit is currently running."""
        state = self._indoor_unit_data.get("state") or {}
        value = state.get("running")
        if value is None:
            value = self._indoor_unit_data.get("running")
        return bool(value)


class SKlimaIndoorUnitFilterBinarySensor(SKlimaBaseBinarySensor):
    """Filter reminder for an individual indoor unit."""

    _attr_translation_key = "indoor_unit_filter_sign"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
        indoor_unit_id: int,
    ) -> None:
        """Initialize the indoor-unit filter binary sensor."""
        super().__init__(coordinator, zone_id)
        self.indoor_unit_id = indoor_unit_id
        self._attr_unique_id = (
            f"{coordinator.api.host}_zone_{zone_id}_indoor_{indoor_unit_id}_filter"
        )

    @property
    def _indoor_unit_data(self) -> dict[str, Any]:
        return self.get_indoor_unit_data(self.indoor_unit_id)

    @property
    def is_on(self) -> bool:
        """Return whether the indoor unit filter reminder is active."""
        value = self._indoor_unit_data.get("filterSign")
        if value is None:
            state = self._indoor_unit_data.get("state") or {}
            value = state.get("filterSign")
        return bool(value)


class SKlimaNotificationsBinarySensor(SKlimaBaseBinarySensor):
    """Gateway notifications present for the zone."""

    _attr_translation_key = "notifications"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the notifications binary sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_notifications"

    @property
    def is_on(self) -> bool:
        """Return whether the zone currently has active notifications."""
        notifications = self._zone_data.get("notifications") or {}
        if isinstance(notifications, dict):
            items = notifications.get("notifications") or []
            return bool(items)
        return False
