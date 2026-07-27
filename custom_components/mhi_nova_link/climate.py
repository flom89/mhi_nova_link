"""Implement the climate entity for NOVA_RC zones."""

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NovaRcDataUpdateCoordinator
from .entity import NovaRcZoneEntity

_LOGGER = logging.getLogger(__name__)

# Map gateway mode names to Home Assistant HVAC modes.
HVAC_MODE_MAP = {
    "COOLING": HVACMode.COOL,
    "HEATING": HVACMode.HEAT,
    "AUTO": HVACMode.AUTO,
    "DRY": HVACMode.DRY,
    "FAN": HVACMode.FAN_ONLY,
}

HVAC_MODE_REVERSE_MAP = {v: k for k, v in HVAC_MODE_MAP.items()}

# Define the custom "Power" fan mode as UI text.
FAN_POWERFUL = "Power"

# Map fan mode values between Home Assistant and the gateway.
FAN_MODE_MAP = {
    "AUTO": FAN_AUTO,
    "LOW": FAN_LOW,
    "MEDIUM": FAN_MEDIUM,
    "HIGH": FAN_HIGH,
    "POWERFUL": FAN_POWERFUL,
}

FAN_MODE_REVERSE_MAP = {
    FAN_AUTO: "AUTO",
    FAN_LOW: "LOW",
    FAN_MEDIUM: "MEDIUM",
    FAN_HIGH: "HIGH",
    FAN_POWERFUL: "POWERFUL",
}

# Default string for auto swing mode.
SWING_AUTO = "auto"

# Map swing mode values from the gateway to user-friendly labels.
SWING_MODE_MAP = {
    "AUTO": SWING_AUTO,
    "POSITION_1": "Position 1",
    "POSITION_2": "Position 2",
    "POSITION_3": "Position 3",
    "POSITION_4": "Position 4",
    "POSITION_5": "Position 5",
}

SWING_MODE_REVERSE_MAP = {v: k for k, v in SWING_MODE_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate entities from the coordinator data."""
    coordinator: NovaRcDataUpdateCoordinator = hass.data[entry.domain][entry.entry_id]

    entities = [
        NovaRcZoneClimate(coordinator, zone["zoneId"]) for zone in coordinator.data
    ]
    async_add_entities(entities)


class NovaRcZoneClimate(NovaRcZoneEntity, ClimateEntity):
    """Represent one NOVA_RC zone as a climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = True
    _attr_translation_key = "mhi_nova_zone"

    def __init__(self, coordinator: NovaRcDataUpdateCoordinator, zone_id: int) -> None:
        """Initialize the climate entity for a single zone."""
        super().__init__(coordinator, zone_id)

        self._attr_unique_id = f"{coordinator.api.host}_zone_{zone_id}"

        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.SWING_MODE
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
        )

        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.AUTO,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
        ]

        self._attr_fan_modes = [
            FAN_AUTO,
            FAN_LOW,
            FAN_MEDIUM,
            FAN_HIGH,
            FAN_POWERFUL,
        ]

    @property
    def icon(self) -> str:
        """Return an icon based on the current operating mode."""
        mode = self.hvac_mode
        if mode == HVACMode.COOL:
            return "mdi:snowflake"
        if mode == HVACMode.HEAT:
            return "mdi:fire"
        if mode == HVACMode.DRY:
            return "mdi:water-percent"
        if mode == HVACMode.FAN_ONLY:
            return "mdi:fan"
        if mode == HVACMode.AUTO:
            return "mdi:thermostat-auto"
        return "mdi:air-conditioner"

    @property
    def current_temperature(self) -> float | None:
        """Return the current room temperature."""
        return self._zone_data.get("roomAirTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._zone_data.get("setpoint")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        data = self._zone_data
        if not data.get("running", False):
            return HVACMode.OFF

        raw_mode = data.get("operationMode")
        return HVAC_MODE_MAP.get(raw_mode, HVACMode.AUTO)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        data = self._zone_data
        if not data.get("running", False):
            return HVACAction.OFF

        mode = self.hvac_mode
        if mode == HVACMode.COOL:
            return HVACAction.COOLING
        if mode == HVACMode.HEAT:
            return HVACAction.HEATING
        if mode == HVACMode.DRY:
            return HVACAction.DRYING
        if mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN

        return HVACAction.IDLE

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan mode."""
        raw_fan = self._zone_data.get("fanSpeed")
        return FAN_MODE_MAP.get(raw_fan, FAN_AUTO)

    @property
    def swing_modes(self) -> list[str] | None:
        """Return the available swing modes from the API."""
        patch_opts = self._zone_data.get("patchOptions") or {}
        raw_positions = (
            patch_opts.get("vanePosition") or patch_opts.get("louverPosition") or []
        )

        modes = []
        for raw in raw_positions:
            if mapped := SWING_MODE_MAP.get(raw):
                modes.append(mapped)
            else:
                modes.append(raw)
        return modes or [SWING_AUTO]

    @property
    def swing_mode(self) -> str | None:
        """Return the current swing mode."""
        raw_vane = self._zone_data.get("vanePosition") or self._zone_data.get(
            "louverPosition"
        )
        return SWING_MODE_MAP.get(raw_vane, raw_vane)

    @property
    def min_temp(self) -> float:
        """Return the minimum target temperature."""
        temp_range = self._zone_data.get("temperatureRangeCooling") or {}
        return temp_range.get("lower", 18.0)

    @property
    def max_temp(self) -> float:
        """Return the maximum target temperature."""
        temp_range = self._zone_data.get("temperatureRangeHeating") or {}
        return temp_range.get("upper", 30.0)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Turn the HVAC mode on or off."""
        was_running = bool(self._zone_data.get("running"))
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.api.async_set_zone_state(self.zone_id, running=False)
        else:
            mhi_mode = HVAC_MODE_REVERSE_MAP.get(hvac_mode)
            await self.coordinator.api.async_set_zone_state(
                self.zone_id,
                running=True,
                operation_mode=mhi_mode,
                wait_for_airflow_after_start=not was_running,
            )
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.coordinator.api.async_set_zone_state(self.zone_id, setpoint=temp)
            await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        if mhi_fan := FAN_MODE_REVERSE_MAP.get(fan_mode):
            await self.coordinator.api.async_set_zone_state(
                self.zone_id, fan_speed=mhi_fan
            )
            await self.coordinator.async_request_refresh()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set the swing mode."""
        raw_vane = SWING_MODE_REVERSE_MAP.get(swing_mode, swing_mode)
        await self.coordinator.api.async_set_zone_state(
            self.zone_id, vane_position=raw_vane
        )
        await self.coordinator.async_request_refresh()
