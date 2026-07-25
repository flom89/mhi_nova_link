"""Sensor platform for MHI Nova / S-Klima zones."""

import inspect
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SKlimaDataUpdateCoordinator
from .entity import SKlimaZoneEntity
from .helpers import get_dataset_value, get_zone_time_series_datasets

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the meaningful sensors from the coordinator data."""
    coordinator: SKlimaDataUpdateCoordinator = hass.data[entry.domain][entry.entry_id]

    entities: list[SensorEntity] = []
    for zone in coordinator.data:
        zone_id = zone["zoneId"]
        entities.append(SKlimaTemperatureSensor(coordinator, zone_id))
        entities.append(SKlimaSetpointSensor(coordinator, zone_id))
        entities.append(SKlimaOperationModeSensor(coordinator, zone_id))
        entities.append(SKlimaFanSpeedSensor(coordinator, zone_id))
        entities.append(SKlimaOutdoorAirTemperatureSensor(coordinator, zone_id))
        entities.append(SKlimaCompressorFrequencySensor(coordinator, zone_id))
        entities.append(SKlimaProtectionStateSensor(coordinator, zone_id))

    result = async_add_entities(entities)
    if inspect.isawaitable(result):
        await result


class SKlimaBaseSensor(SKlimaZoneEntity, SensorEntity):
    """Base implementation for S-Klima sensors."""

    @property
    def available(self) -> bool:
        """Return whether the zone is currently available from the gateway."""
        available = self._zone_data.get("available")
        return True if available is None else bool(available)


class SKlimaTemperatureSensor(SKlimaBaseSensor):
    """Room temperature sensor."""

    _attr_translation_key = "room_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: SKlimaDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize the room-temperature sensor for a zone."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_temp"

    @property
    def native_value(self) -> float | None:
        """Return the current room temperature from the zone payload."""
        return self._zone_data.get("roomAirTemperature")


class SKlimaSetpointSensor(SKlimaBaseSensor):
    """Setpoint sensor."""

    _attr_translation_key = "setpoint"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: SKlimaDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize the setpoint sensor for a zone."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_setpoint"

    @property
    def native_value(self) -> float | None:
        """Return the active target temperature from the zone payload."""
        return self._zone_data.get("setpoint")


class SKlimaOperationModeSensor(SKlimaBaseSensor):
    """Operation mode sensor."""

    _attr_translation_key = "operation_mode"
    _attr_icon = "mdi:thermostat-cog"

    def __init__(self, coordinator: SKlimaDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize the operation mode sensor for a zone."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_mode"

    @property
    def native_value(self) -> str | None:
        """Return the human-friendly operation mode name."""
        data = self._zone_data
        if data.get("running") is False:
            return "off"

        raw_mode = data.get("operationMode")
        if raw_mode is None:
            datasets = get_zone_time_series_datasets(data)
            dataset = datasets.get("operation_mode")
            if dataset is None:
                return None
            value = get_dataset_value(dataset)
            if isinstance(value, str):
                raw_mode = value
            elif isinstance(value, (int, float)):
                raw_mode = str(value)

        mode_translation = {
            "COOLING": "cooling",
            "HEATING": "heating",
            "AUTO": "auto",
            "DRY": "dry",
            "FAN": "fan",
        }
        return mode_translation.get(raw_mode, raw_mode.lower() if raw_mode else None)


class SKlimaFanSpeedSensor(SKlimaBaseSensor):
    """Fan speed sensor."""

    _attr_translation_key = "fan_speed"
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: SKlimaDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize the fan-speed sensor for a zone."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_fan"

    @property
    def native_value(self) -> str | None:
        """Return the mapped fan speed state for the zone."""
        raw_fan = self._zone_data.get("fanSpeed")
        if raw_fan is None:
            datasets = get_zone_time_series_datasets(self._zone_data)
            dataset = datasets.get("fan_speed")
            if dataset is None:
                return None
            value = get_dataset_value(dataset)
            if isinstance(value, str):
                raw_fan = value
            elif isinstance(value, (int, float)):
                raw_fan = str(value)

        fan_translation = {
            "LOW": "low",
            "MEDIUM": "medium",
            "HIGH": "high",
            "POWERFUL": "powerful",
            "AUTO": "auto",
        }
        return fan_translation.get(raw_fan, raw_fan.lower() if raw_fan else None)


class SKlimaIndoorUnitTemperatureSensor(SKlimaBaseSensor):
    """Temperature sensor for an individual indoor unit."""

    _attr_translation_key = "indoor_unit_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
        indoor_unit_id: int,
    ) -> None:
        """Initialize the indoor-unit temperature sensor."""
        super().__init__(coordinator, zone_id)
        self.indoor_unit_id = indoor_unit_id
        self._attr_unique_id = (
            f"{coordinator.api.host}_zone_{zone_id}_indoor_{indoor_unit_id}_temp"
        )

    @property
    def _indoor_unit_data(self) -> dict[str, Any]:
        return self.get_indoor_unit_data(self.indoor_unit_id)

    @property
    def native_value(self) -> float | None:
        """Return the indoor-unit room temperature."""
        state = self._indoor_unit_data.get("state") or {}
        value = state.get("roomAirTemperature")
        if value is None:
            value = self._indoor_unit_data.get("roomAirTemperature")

        if value is None:
            datasets = get_zone_time_series_datasets(self._zone_data)
            dataset = datasets.get("iu_room_air_temperature")
            if not dataset:
                return None
            value = get_dataset_value(dataset)

        return float(value) if isinstance(value, (int, float)) else None


class SKlimaIndoorUnitSetpointSensor(SKlimaBaseSensor):
    """Setpoint sensor for an individual indoor unit."""

    _attr_translation_key = "indoor_unit_setpoint"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
        indoor_unit_id: int,
    ) -> None:
        """Initialize the indoor-unit setpoint sensor."""
        super().__init__(coordinator, zone_id)
        self.indoor_unit_id = indoor_unit_id
        self._attr_unique_id = (
            f"{coordinator.api.host}_zone_{zone_id}_indoor_{indoor_unit_id}_setpoint"
        )

    @property
    def _indoor_unit_data(self) -> dict[str, Any]:
        return self.get_indoor_unit_data(self.indoor_unit_id)

    @property
    def native_value(self) -> float | None:
        """Return the indoor-unit setpoint."""
        state = self._indoor_unit_data.get("state") or {}
        value = state.get("setpoint")
        if value is None:
            value = self._indoor_unit_data.get("setpoint")

        return float(value) if isinstance(value, (int, float)) else None


class SKlimaIndoorUnitOperationModeSensor(SKlimaBaseSensor):
    """Operation mode sensor for an individual indoor unit."""

    _attr_translation_key = "indoor_unit_operation_mode"

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
        indoor_unit_id: int,
    ) -> None:
        """Initialize the indoor-unit operation-mode sensor."""
        super().__init__(coordinator, zone_id)
        self.indoor_unit_id = indoor_unit_id
        self._attr_unique_id = (
            f"{coordinator.api.host}_zone_{zone_id}_indoor_{indoor_unit_id}_mode"
        )

    @property
    def _indoor_unit_data(self) -> dict[str, Any]:
        return self.get_indoor_unit_data(self.indoor_unit_id)

    @property
    def native_value(self) -> str | None:
        """Return the indoor-unit operation mode."""
        state = self._indoor_unit_data.get("state") or {}
        raw_mode = state.get("operationMode")
        if raw_mode is None:
            raw_mode = self._indoor_unit_data.get("operationMode")
        if raw_mode is None:
            return None

        mode_translation = {
            "COOLING": "cooling",
            "HEATING": "heating",
            "AUTO": "auto",
            "DRY": "dry",
            "FAN": "fan",
        }
        return mode_translation.get(raw_mode, raw_mode.lower() if raw_mode else None)


class SKlimaIndoorUnitFanSpeedSensor(SKlimaBaseSensor):
    """Fan speed sensor for an individual indoor unit."""

    _attr_translation_key = "indoor_unit_fan_speed"

    def __init__(
        self,
        coordinator: SKlimaDataUpdateCoordinator,
        zone_id: int,
        indoor_unit_id: int,
    ) -> None:
        """Initialize the indoor-unit fan-speed sensor."""
        super().__init__(coordinator, zone_id)
        self.indoor_unit_id = indoor_unit_id
        self._attr_unique_id = (
            f"{coordinator.api.host}_zone_{zone_id}_indoor_{indoor_unit_id}_fan"
        )

    @property
    def _indoor_unit_data(self) -> dict[str, Any]:
        return self.get_indoor_unit_data(self.indoor_unit_id)

    @property
    def native_value(self) -> str | None:
        """Return the indoor-unit fan speed."""
        state = self._indoor_unit_data.get("state") or {}
        raw_fan = state.get("fanSpeed")
        if raw_fan is None:
            raw_fan = self._indoor_unit_data.get("fanSpeed")
        if raw_fan is None:
            return None

        fan_translation = {
            "LOW": "low",
            "MEDIUM": "medium",
            "HIGH": "high",
            "POWERFUL": "powerful",
            "AUTO": "auto",
        }
        return fan_translation.get(raw_fan, raw_fan.lower() if raw_fan else None)


class SKlimaOutdoorAirTemperatureSensor(SKlimaBaseSensor):
    """Outdoor air temperature sensor derived from the time series payload."""

    _attr_translation_key = "outdoor_air_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: SKlimaDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize the outdoor-air temperature sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_outdoor_temp"

    @property
    def native_value(self) -> float | None:
        """Return the outdoor air temperature from the time-series payload."""
        datasets = get_zone_time_series_datasets(self._zone_data)
        value = get_dataset_value(datasets.get("ou_indication_air_temp", {}))
        return float(value) if isinstance(value, (int, float)) else None


class SKlimaCompressorFrequencySensor(SKlimaBaseSensor):
    """Compressor frequency sensor derived from the time series payload."""

    _attr_translation_key = "compressor_frequency"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "Hz"

    def __init__(self, coordinator: SKlimaDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize the compressor-frequency sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_compressor_freq"

    @property
    def native_value(self) -> float | None:
        """Return the compressor frequency from the time-series payload."""
        datasets = get_zone_time_series_datasets(self._zone_data)
        value = get_dataset_value(
            datasets.get("ou_indication_compressor_frequency", {})
        )
        return float(value) if isinstance(value, (int, float)) else None


class SKlimaProtectionStateSensor(SKlimaBaseSensor):
    """Outdoor unit protection state sensor derived from the time series payload."""

    _attr_translation_key = "protection_state"

    def __init__(self, coordinator: SKlimaDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize the protection-state sensor."""
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}_protection_state"

    @property
    def native_value(self) -> str | None:
        """Return a human-readable protection state extracted from time series data."""
        datasets = get_zone_time_series_datasets(self._zone_data)
        dataset = datasets.get("ou_indication_protection_state_comp")
        if not dataset:
            return None

        value = get_dataset_value(dataset)
        if isinstance(value, (int, float)):
            options = dataset.get("options", {}).get("options", [])
            if isinstance(options, list):
                for option in options:
                    if isinstance(option, dict) and option.get("value") == value:
                        label = option.get("label")
                        if isinstance(label, str):
                            return _normalize_state_value(label)
        if isinstance(value, str):
            return _normalize_state_value(value)
        if isinstance(value, bool):
            return "normal" if value else "abnormal"
        return str(value) if value is not None else None


def _normalize_state_value(value: str) -> str:
    """Trim a gateway-style dotted path down to the final segment."""
    if not isinstance(value, str):
        return value

    cleaned = value.strip()
    if cleaned.startswith("${") and cleaned.endswith("}"):
        cleaned = cleaned[2:-1].strip()

    parts = cleaned.split(".")
    return parts[-1] if parts else cleaned
