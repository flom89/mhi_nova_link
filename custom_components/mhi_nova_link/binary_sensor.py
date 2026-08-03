"""Implement binary sensor entities for NOVA_RC."""

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NovaRcConfigEntry
from .coordinator import NovaRcDataUpdateCoordinator
from .entity import NovaRcZoneEntity, build_gateway_device_info
from .helpers import dataset_is_on, get_dataset_value, get_zone_time_series_datasets


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry | NovaRcConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator: NovaRcDataUpdateCoordinator
    if hasattr(entry, "runtime_data"):
        coordinator = entry.runtime_data.coordinator
    else:
        coordinator = hass.data[entry.domain][entry.entry_id]

    entities: list[BinarySensorEntity] = [
        NovaRcFreeCoolingBinarySensor(coordinator),
        NovaRcFreeCoolingActiveBinarySensor(coordinator),
        NovaRcSystemStopBinarySensor(coordinator),
        NovaRcSystemFaultBinarySensor(coordinator),
        NovaRcGatewayUpdateAvailableBinarySensor(coordinator),
    ]
    for zone in coordinator.data:
        zone_id = zone.get("zoneId")
        if zone_id is None:
            continue

        entities.append(NovaRcRunningBinarySensor(coordinator, zone_id))
        entities.append(NovaRcAvailableBinarySensor(coordinator, zone_id))
        entities.append(NovaRc3DAutoBinarySensor(coordinator, zone_id))
        entities.append(NovaRcTemperatureRangeBinarySensor(coordinator, zone_id))
        entities.append(NovaRcCriticalErrorBinarySensor(coordinator, zone_id))
        entities.append(NovaRcMaintenanceBinarySensor(coordinator, zone_id))
        entities.append(NovaRcCompressorBinarySensor(coordinator, zone_id))
        entities.append(NovaRcDefrostingBinarySensor(coordinator, zone_id))
        entities.append(NovaRcNotificationsBinarySensor(coordinator, zone_id))

        indoor_unit_ids: list[int] = []
        for indoor_unit in zone.get("indoorUnits", []) or []:
            indoor_unit_id = indoor_unit.get("indoorUnitId")
            if not isinstance(indoor_unit_id, int):
                continue
            if indoor_unit_id in indoor_unit_ids:
                continue
            indoor_unit_ids.append(indoor_unit_id)

        for indoor_unit_id in indoor_unit_ids:
            entities.append(
                NovaRcIndoorUnitRunningBinarySensor(
                    coordinator, zone_id, indoor_unit_id
                )
            )
            entities.append(
                NovaRcIndoorUnitFilterBinarySensor(coordinator, zone_id, indoor_unit_id)
            )

    async_add_entities(entities)


class NovaRcBaseBinarySensor(NovaRcZoneEntity, BinarySensorEntity):
    """Base implementation for zone binary sensors."""


class NovaRcGatewayBinarySensor(
    CoordinatorEntity[NovaRcDataUpdateCoordinator], BinarySensorEntity
):
    """Base implementation for gateway-level GPIO binary sensors."""

    _attr_has_entity_name = True
    _gpio_function: str

    def __init__(self, coordinator: NovaRcDataUpdateCoordinator) -> None:
        """Initialize a gateway-level GPIO binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.api.host}_gateway_gpio_{self._gpio_function.lower()}"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device metadata for the gateway."""
        entry_id = (
            self.coordinator.config_entry.entry_id
            if self.coordinator.config_entry
            else "unknown"
        )
        return build_gateway_device_info(
            entry_id,
            identifier_suffix="gateway",
            name="Digital IOs",
        )

    @property
    def is_on(self) -> bool:
        """Return whether the GPIO function is active."""
        return bool(self.coordinator.gpios.get(self._gpio_function, False))


class NovaRcGatewayUpdateAvailableBinarySensor(
    CoordinatorEntity[NovaRcDataUpdateCoordinator], BinarySensorEntity
):
    """Gateway-level binary sensor indicating whether a software update is available."""

    _attr_translation_key = "gateway_update_available"
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: NovaRcDataUpdateCoordinator) -> None:
        """Initialize the gateway update-availability sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.host}_gateway_update_available"

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device metadata for the gateway info device."""
        entry_id = (
            self.coordinator.config_entry.entry_id
            if self.coordinator.config_entry
            else "unknown"
        )
        return build_gateway_device_info(
            entry_id,
            identifier_suffix="gateway_info",
            name="Gateway",
        )

    @property
    def is_on(self) -> bool:
        """Return whether the gateway reports an available software update."""
        return bool(self.coordinator.gateway_update.get("update_available", False))


class NovaRcFreeCoolingBinarySensor(NovaRcGatewayBinarySensor):
    """Gateway free cooling request state."""

    _attr_translation_key = "sequencing_stop"
    _gpio_function = "FREE_COOLING"


class NovaRcFreeCoolingActiveBinarySensor(NovaRcGatewayBinarySensor):
    """Gateway free cooling active state."""

    _attr_translation_key = "sequencing_stop_active"
    _gpio_function = "FREE_COOLING_ACTIVE"


class NovaRcSystemStopBinarySensor(NovaRcGatewayBinarySensor):
    """Gateway system stop state."""

    _attr_translation_key = "system_stop"
    _gpio_function = "SYSTEM_STOP"


class NovaRcSystemFaultBinarySensor(NovaRcGatewayBinarySensor):
    """Gateway system fault state."""

    _attr_translation_key = "system_fault"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _gpio_function = "SYSTEM_FAULT"


class NovaRcRunningBinarySensor(NovaRcBaseBinarySensor):
    """Zone is running."""

    _attr_translation_key = "running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the running state sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_running"

    @property
    def is_on(self) -> bool:
        """Return whether the zone is currently running."""
        return self._zone_data.get("running", False)


class NovaRcAvailableBinarySensor(NovaRcBaseBinarySensor):
    """Zone is available."""

    _attr_translation_key = "available"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the availability sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_available"

    @property
    def is_on(self) -> bool:
        """Return whether the zone is available."""
        return self._zone_data.get("available", False)


class NovaRc3DAutoBinarySensor(NovaRcBaseBinarySensor):
    """3D auto mode."""

    _attr_translation_key = "three_d_auto"

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the 3D auto state sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_3d_auto"

    @property
    def is_on(self) -> bool:
        """Return whether 3D auto is enabled."""
        return self._zone_data.get("flap3dAuto", False)


class NovaRcTemperatureRangeBinarySensor(NovaRcBaseBinarySensor):
    """Temperature range is enabled."""

    _attr_translation_key = "temperature_range"

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
        zone_id: int,
    ) -> None:
        """Initialize the temperature range sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_temp_range"

    @property
    def is_on(self) -> bool:
        """Return whether temperature range mode is enabled."""
        return self._zone_data.get("temperatureRangeEnable", False)


class NovaRcCriticalErrorBinarySensor(NovaRcBaseBinarySensor):
    """Critical error."""

    _attr_translation_key = "critical_error"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
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


class NovaRcMaintenanceBinarySensor(NovaRcBaseBinarySensor):
    """Maintenance required."""

    _attr_translation_key = "maintenance_required"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
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


class NovaRcCompressorBinarySensor(NovaRcBaseBinarySensor):
    """Compressor activity state."""

    _attr_translation_key = "compressor_active"

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
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

        if dataset and dataset_is_on("compressor_active", dataset):
            return True

        frequency_dataset = datasets.get("ou_indication_compressor_frequency")
        if not frequency_dataset:
            return False

        frequency = get_dataset_value(frequency_dataset)
        return isinstance(frequency, (int, float)) and frequency > 0


class NovaRcDefrostingBinarySensor(NovaRcBaseBinarySensor):
    """Defrosting activity state."""

    _attr_translation_key = "defrosting_active"

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
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


class NovaRcIndoorUnitRunningBinarySensor(NovaRcBaseBinarySensor):
    """Running state for an individual indoor unit."""

    _attr_translation_key = "indoor_unit_running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
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


class NovaRcIndoorUnitFilterBinarySensor(NovaRcBaseBinarySensor):
    """Filter reminder for an individual indoor unit."""

    _attr_translation_key = "indoor_unit_filter_sign"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
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


class NovaRcNotificationsBinarySensor(NovaRcBaseBinarySensor):
    """Gateway notifications present for the zone."""

    _attr_translation_key = "notifications"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: NovaRcDataUpdateCoordinator,
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
