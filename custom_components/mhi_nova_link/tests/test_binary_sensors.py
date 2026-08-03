"""Unit tests for binary sensor entity properties."""

from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

_integration_dir = Path(__file__).resolve().parents[1]
_config_dir = _integration_dir.parent.parent
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

from custom_components.mhi_nova_link.binary_sensor import (  # noqa: E402
    NovaRc3DAutoBinarySensor,
    NovaRcAvailableBinarySensor,
    NovaRcCompressorBinarySensor,
    NovaRcCriticalErrorBinarySensor,
    NovaRcDefrostingBinarySensor,
    NovaRcFreeCoolingActiveBinarySensor,
    NovaRcFreeCoolingBinarySensor,
    NovaRcGatewayUpdateAvailableBinarySensor,
    NovaRcIndoorUnitFilterBinarySensor,
    NovaRcIndoorUnitRunningBinarySensor,
    NovaRcMaintenanceBinarySensor,
    NovaRcNotificationsBinarySensor,
    NovaRcRunningBinarySensor,
    NovaRcSystemFaultBinarySensor,
    NovaRcSystemStopBinarySensor,
    NovaRcTemperatureRangeBinarySensor,
)


def _coordinator(zone_data: dict, gpios: dict | None = None, gateway_update: dict | None = None) -> SimpleNamespace:
    """Build a minimal coordinator with one zone."""
    return SimpleNamespace(
        data=[{**zone_data, "zoneId": 1}],
        gpios=gpios or {},
        gateway_update=gateway_update or {},
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
    )


# ---------------------------------------------------------------------------
# Zone-level running / available
# ---------------------------------------------------------------------------


def test_running_binary_sensor_is_on_when_running() -> None:
    """Running sensor should be on when the zone is running."""
    coordinator = _coordinator({"running": True})
    entity = NovaRcRunningBinarySensor(coordinator, 1)
    assert entity.is_on is True


def test_running_binary_sensor_is_off_when_not_running() -> None:
    """Running sensor should be off when the zone is not running."""
    coordinator = _coordinator({"running": False})
    entity = NovaRcRunningBinarySensor(coordinator, 1)
    assert entity.is_on is False


def test_available_binary_sensor_is_on_when_available() -> None:
    """Available sensor should be on when the zone is available."""
    coordinator = _coordinator({"available": True})
    entity = NovaRcAvailableBinarySensor(coordinator, 1)
    assert entity.is_on is True


def test_available_binary_sensor_is_off_when_not_available() -> None:
    """Available sensor should be off when the zone is not available."""
    coordinator = _coordinator({"available": False})
    entity = NovaRcAvailableBinarySensor(coordinator, 1)
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# 3D auto
# ---------------------------------------------------------------------------


def test_3d_auto_binary_sensor_is_on_when_enabled() -> None:
    """3D auto sensor should be on when flap3dAuto is True."""
    coordinator = _coordinator({"flap3dAuto": True})
    entity = NovaRc3DAutoBinarySensor(coordinator, 1)
    assert entity.is_on is True


def test_3d_auto_binary_sensor_is_off_when_disabled() -> None:
    """3D auto sensor should be off when flap3dAuto is False."""
    coordinator = _coordinator({"flap3dAuto": False})
    entity = NovaRc3DAutoBinarySensor(coordinator, 1)
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# Temperature range
# ---------------------------------------------------------------------------


def test_temperature_range_binary_sensor_is_on_when_enabled() -> None:
    """Temperature range sensor should be on when temperatureRangeEnable is True."""
    coordinator = _coordinator({"temperatureRangeEnable": True})
    entity = NovaRcTemperatureRangeBinarySensor(coordinator, 1)
    assert entity.is_on is True


def test_temperature_range_binary_sensor_is_off_when_disabled() -> None:
    """Temperature range sensor should be off when temperatureRangeEnable is False."""
    coordinator = _coordinator({"temperatureRangeEnable": False})
    entity = NovaRcTemperatureRangeBinarySensor(coordinator, 1)
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# Critical error / maintenance
# ---------------------------------------------------------------------------


def test_critical_error_sensor_is_on_when_critical_count_positive() -> None:
    """Critical error sensor should be on when criticalCount > 0."""
    coordinator = _coordinator({"error": {"criticalCount": 2}})
    entity = NovaRcCriticalErrorBinarySensor(coordinator, 1)
    assert entity.is_on is True


def test_critical_error_sensor_is_off_when_critical_count_zero() -> None:
    """Critical error sensor should be off when criticalCount == 0."""
    coordinator = _coordinator({"error": {"criticalCount": 0}})
    entity = NovaRcCriticalErrorBinarySensor(coordinator, 1)
    assert entity.is_on is False


def test_critical_error_sensor_is_off_when_error_key_absent() -> None:
    """Critical error sensor should default to off when error key is missing."""
    coordinator = _coordinator({})
    entity = NovaRcCriticalErrorBinarySensor(coordinator, 1)
    assert entity.is_on is False


def test_maintenance_sensor_is_on_when_maintenance_count_positive() -> None:
    """Maintenance sensor should be on when maintenanceCount > 0."""
    coordinator = _coordinator({"error": {"maintenanceCount": 1}})
    entity = NovaRcMaintenanceBinarySensor(coordinator, 1)
    assert entity.is_on is True


def test_maintenance_sensor_is_off_when_maintenance_count_zero() -> None:
    """Maintenance sensor should be off when maintenanceCount == 0."""
    coordinator = _coordinator({"error": {"maintenanceCount": 0}})
    entity = NovaRcMaintenanceBinarySensor(coordinator, 1)
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def test_notifications_sensor_is_on_when_notifications_present() -> None:
    """Notifications sensor should be on when there are active notifications."""
    coordinator = _coordinator(
        {"notifications": {"notifications": [{"notificationId": 1}]}}
    )
    entity = NovaRcNotificationsBinarySensor(coordinator, 1)
    assert entity.is_on is True


def test_notifications_sensor_is_off_when_no_notifications() -> None:
    """Notifications sensor should be off when no notifications are present."""
    coordinator = _coordinator({"notifications": {"notifications": []}})
    entity = NovaRcNotificationsBinarySensor(coordinator, 1)
    assert entity.is_on is False


def test_notifications_sensor_is_off_when_notifications_key_absent() -> None:
    """Notifications sensor should default to off when the notifications key is absent."""
    coordinator = _coordinator({})
    entity = NovaRcNotificationsBinarySensor(coordinator, 1)
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# Compressor / defrosting (time-series driven)
# ---------------------------------------------------------------------------


def test_defrosting_sensor_is_on_when_dataset_flag_is_true() -> None:
    """Defrosting sensor should be on when the dataset flag is True."""
    coordinator = _coordinator(
        {
            "timeSeries": {
                "dataSets": [
                    {
                        "id": "defrosting_active",
                        "reference": "/indoor_unit/1",
                        "data": [{"value": True}],
                    }
                ]
            }
        }
    )
    entity = NovaRcDefrostingBinarySensor(coordinator, 1)
    assert entity.is_on is True


def test_defrosting_sensor_is_off_when_dataset_absent() -> None:
    """Defrosting sensor should be off when the dataset is absent."""
    coordinator = _coordinator({})
    entity = NovaRcDefrostingBinarySensor(coordinator, 1)
    assert entity.is_on is False


def test_compressor_sensor_is_off_when_both_flag_and_frequency_absent() -> None:
    """Compressor sensor should be off when there is no compressor dataset at all."""
    coordinator = _coordinator({})
    entity = NovaRcCompressorBinarySensor(coordinator, 1)
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# GPIO binary sensors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sensor_cls", "gpio_function"),
    [
        (NovaRcFreeCoolingBinarySensor, "FREE_COOLING"),
        (NovaRcFreeCoolingActiveBinarySensor, "FREE_COOLING_ACTIVE"),
        (NovaRcSystemStopBinarySensor, "SYSTEM_STOP"),
        (NovaRcSystemFaultBinarySensor, "SYSTEM_FAULT"),
    ],
)
def test_gpio_binary_sensor_is_on_when_gpio_is_active(
    sensor_cls: type,
    gpio_function: str,
) -> None:
    """Gateway GPIO sensors should be on when the corresponding GPIO is True."""
    coordinator = _coordinator({}, gpios={gpio_function: True})
    entity = sensor_cls(coordinator)
    assert entity.is_on is True


@pytest.mark.parametrize(
    ("sensor_cls", "gpio_function"),
    [
        (NovaRcFreeCoolingBinarySensor, "FREE_COOLING"),
        (NovaRcFreeCoolingActiveBinarySensor, "FREE_COOLING_ACTIVE"),
        (NovaRcSystemStopBinarySensor, "SYSTEM_STOP"),
        (NovaRcSystemFaultBinarySensor, "SYSTEM_FAULT"),
    ],
)
def test_gpio_binary_sensor_is_off_when_gpio_is_inactive(
    sensor_cls: type,
    gpio_function: str,
) -> None:
    """Gateway GPIO sensors should be off when the corresponding GPIO is False."""
    coordinator = _coordinator({}, gpios={gpio_function: False})
    entity = sensor_cls(coordinator)
    assert entity.is_on is False


def test_gpio_binary_sensor_is_off_when_gpio_key_absent() -> None:
    """Gateway GPIO sensors should default to off when the key is absent."""
    coordinator = _coordinator({}, gpios={})
    entity = NovaRcFreeCoolingBinarySensor(coordinator)
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# Gateway update available
# ---------------------------------------------------------------------------


def test_gateway_update_available_sensor_is_on_when_update_available() -> None:
    """Gateway update sensor should be on when an update is available."""
    coordinator = _coordinator({}, gateway_update={"update_available": True})
    entity = NovaRcGatewayUpdateAvailableBinarySensor(coordinator)
    assert entity.is_on is True


def test_gateway_update_available_sensor_is_off_when_no_update() -> None:
    """Gateway update sensor should be off when no update is available."""
    coordinator = _coordinator({}, gateway_update={"update_available": False})
    entity = NovaRcGatewayUpdateAvailableBinarySensor(coordinator)
    assert entity.is_on is False


# ---------------------------------------------------------------------------
# Indoor unit binary sensors
# ---------------------------------------------------------------------------


def _indoor_coordinator(indoor_data: dict) -> SimpleNamespace:
    """Build a coordinator stub with one zone containing one indoor unit."""
    return SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [{**indoor_data, "indoorUnitId": 7}],
            }
        ],
        gpios={},
        gateway_update={},
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda cb: lambda: None,
    )


def test_indoor_unit_running_sensor_reads_state_running() -> None:
    """Indoor unit running sensor should read state.running."""
    coordinator = _indoor_coordinator({"state": {"running": True}})
    entity = NovaRcIndoorUnitRunningBinarySensor(coordinator, 1, 7)
    assert entity.is_on is True


def test_indoor_unit_running_sensor_reads_top_level_running_fallback() -> None:
    """Indoor unit running sensor should fall back to the top-level running field."""
    coordinator = _indoor_coordinator({"running": True})
    entity = NovaRcIndoorUnitRunningBinarySensor(coordinator, 1, 7)
    assert entity.is_on is True


def test_indoor_unit_running_sensor_is_off_when_not_running() -> None:
    """Indoor unit running sensor should be off when the unit is not running."""
    coordinator = _indoor_coordinator({"state": {"running": False}})
    entity = NovaRcIndoorUnitRunningBinarySensor(coordinator, 1, 7)
    assert entity.is_on is False


def test_indoor_unit_filter_sensor_is_on_when_filter_sign_true() -> None:
    """Indoor unit filter sensor should be on when filterSign is truthy."""
    coordinator = _indoor_coordinator({"filterSign": True})
    entity = NovaRcIndoorUnitFilterBinarySensor(coordinator, 1, 7)
    assert entity.is_on is True


def test_indoor_unit_filter_sensor_reads_state_filter_sign_fallback() -> None:
    """Indoor unit filter sensor should read filterSign from state as fallback."""
    coordinator = _indoor_coordinator({"state": {"filterSign": True}})
    entity = NovaRcIndoorUnitFilterBinarySensor(coordinator, 1, 7)
    assert entity.is_on is True


def test_indoor_unit_filter_sensor_is_off_when_false() -> None:
    """Indoor unit filter sensor should be off when filterSign is False."""
    coordinator = _indoor_coordinator({"filterSign": False})
    entity = NovaRcIndoorUnitFilterBinarySensor(coordinator, 1, 7)
    assert entity.is_on is False
