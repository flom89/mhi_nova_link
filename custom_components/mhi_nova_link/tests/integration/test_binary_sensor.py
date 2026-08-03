"""Integration tests for binary sensor entity properties.

All sensors are exercised against lightweight coordinator stubs —
no HA instance or network connection is required.
"""

import pytest

from custom_components.mhi_nova_link.binary_sensor import (
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

from tests.conftest import make_coordinator


def _coord(zone_data: dict, gpios: dict | None = None, gateway_update: dict | None = None):
    return make_coordinator(
        zones=[{**zone_data, "zoneId": 1}],
        gpios=gpios,
        gateway_update=gateway_update,
    )


def _indoor_coord(indoor_data: dict):
    return make_coordinator(
        zones=[{
            "zoneId": 1,
            "indoorUnits": [{**indoor_data, "indoorUnitId": 7}],
        }]
    )


# ---------------------------------------------------------------------------
# Zone-level sensors
# ---------------------------------------------------------------------------


def test_running_sensor_on_when_running() -> None:
    assert NovaRcRunningBinarySensor(_coord({"running": True}), 1).is_on is True


def test_running_sensor_off_when_not_running() -> None:
    assert NovaRcRunningBinarySensor(_coord({"running": False}), 1).is_on is False


def test_available_sensor_on_when_available() -> None:
    assert NovaRcAvailableBinarySensor(_coord({"available": True}), 1).is_on is True


def test_available_sensor_off_when_not_available() -> None:
    assert NovaRcAvailableBinarySensor(_coord({"available": False}), 1).is_on is False


def test_3d_auto_sensor_on_when_enabled() -> None:
    assert NovaRc3DAutoBinarySensor(_coord({"flap3dAuto": True}), 1).is_on is True


def test_3d_auto_sensor_off_when_disabled() -> None:
    assert NovaRc3DAutoBinarySensor(_coord({"flap3dAuto": False}), 1).is_on is False


def test_temperature_range_sensor_on_when_enabled() -> None:
    assert NovaRcTemperatureRangeBinarySensor(
        _coord({"temperatureRangeEnable": True}), 1
    ).is_on is True


def test_temperature_range_sensor_off_when_disabled() -> None:
    assert NovaRcTemperatureRangeBinarySensor(
        _coord({"temperatureRangeEnable": False}), 1
    ).is_on is False


# ---------------------------------------------------------------------------
# Critical error / maintenance
# ---------------------------------------------------------------------------


def test_critical_error_sensor_on_when_count_positive() -> None:
    assert NovaRcCriticalErrorBinarySensor(
        _coord({"error": {"criticalCount": 2}}), 1
    ).is_on is True


def test_critical_error_sensor_off_when_count_zero() -> None:
    assert NovaRcCriticalErrorBinarySensor(
        _coord({"error": {"criticalCount": 0}}), 1
    ).is_on is False


def test_critical_error_sensor_off_when_error_key_absent() -> None:
    assert NovaRcCriticalErrorBinarySensor(_coord({}), 1).is_on is False


def test_maintenance_sensor_on_when_count_positive() -> None:
    assert NovaRcMaintenanceBinarySensor(
        _coord({"error": {"maintenanceCount": 1}}), 1
    ).is_on is True


def test_maintenance_sensor_off_when_count_zero() -> None:
    assert NovaRcMaintenanceBinarySensor(
        _coord({"error": {"maintenanceCount": 0}}), 1
    ).is_on is False


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def test_notifications_sensor_on_when_notifications_present() -> None:
    assert NovaRcNotificationsBinarySensor(
        _coord({"notifications": {"notifications": [{"id": 1}]}}), 1
    ).is_on is True


def test_notifications_sensor_off_when_empty() -> None:
    assert NovaRcNotificationsBinarySensor(
        _coord({"notifications": {"notifications": []}}), 1
    ).is_on is False


def test_notifications_sensor_off_when_key_absent() -> None:
    assert NovaRcNotificationsBinarySensor(_coord({}), 1).is_on is False


# ---------------------------------------------------------------------------
# Time-series-driven sensors
# ---------------------------------------------------------------------------


def test_defrosting_sensor_on_when_dataset_flag_true() -> None:
    zone = {
        "timeSeries": {
            "dataSets": [
                {"id": "defrosting_active", "reference": "/indoor_unit/1", "data": [{"value": True}]}
            ]
        }
    }
    assert NovaRcDefrostingBinarySensor(_coord(zone), 1).is_on is True


def test_defrosting_sensor_off_when_dataset_absent() -> None:
    assert NovaRcDefrostingBinarySensor(_coord({}), 1).is_on is False


def test_compressor_sensor_off_when_no_datasets() -> None:
    assert NovaRcCompressorBinarySensor(_coord({}), 1).is_on is False


def test_compressor_sensor_on_when_frequency_positive() -> None:
    zone = {
        "timeSeries": {
            "dataSets": [
                {"id": "compressor_active", "reference": "/indoor_unit/1", "data": [{"value": False}]},
                {"id": "ou_indication_compressor_frequency", "reference": "/outdoor_unit/1", "data": [{"value": 35}]},
            ]
        }
    }
    assert NovaRcCompressorBinarySensor(_coord(zone), 1).is_on is True


# ---------------------------------------------------------------------------
# GPIO sensors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sensor_cls", "func"),
    [
        (NovaRcFreeCoolingBinarySensor, "FREE_COOLING"),
        (NovaRcFreeCoolingActiveBinarySensor, "FREE_COOLING_ACTIVE"),
        (NovaRcSystemStopBinarySensor, "SYSTEM_STOP"),
        (NovaRcSystemFaultBinarySensor, "SYSTEM_FAULT"),
    ],
)
def test_gpio_sensor_on_when_active(sensor_cls: type, func: str) -> None:
    assert sensor_cls(_coord({}, gpios={func: True})).is_on is True


@pytest.mark.parametrize(
    ("sensor_cls", "func"),
    [
        (NovaRcFreeCoolingBinarySensor, "FREE_COOLING"),
        (NovaRcFreeCoolingActiveBinarySensor, "FREE_COOLING_ACTIVE"),
        (NovaRcSystemStopBinarySensor, "SYSTEM_STOP"),
        (NovaRcSystemFaultBinarySensor, "SYSTEM_FAULT"),
    ],
)
def test_gpio_sensor_off_when_inactive(sensor_cls: type, func: str) -> None:
    assert sensor_cls(_coord({}, gpios={func: False})).is_on is False


def test_gpio_sensor_off_when_key_absent() -> None:
    assert NovaRcFreeCoolingBinarySensor(_coord({}, gpios={})).is_on is False


# ---------------------------------------------------------------------------
# Gateway update sensor
# ---------------------------------------------------------------------------


def test_gateway_update_sensor_on_when_update_available() -> None:
    assert NovaRcGatewayUpdateAvailableBinarySensor(
        _coord({}, gateway_update={"update_available": True})
    ).is_on is True


def test_gateway_update_sensor_off_when_no_update() -> None:
    assert NovaRcGatewayUpdateAvailableBinarySensor(
        _coord({}, gateway_update={"update_available": False})
    ).is_on is False


# ---------------------------------------------------------------------------
# Indoor unit sensors
# ---------------------------------------------------------------------------


def test_indoor_unit_running_reads_state_running() -> None:
    assert NovaRcIndoorUnitRunningBinarySensor(
        _indoor_coord({"state": {"running": True}}), 1, 7
    ).is_on is True


def test_indoor_unit_running_reads_top_level_running_fallback() -> None:
    assert NovaRcIndoorUnitRunningBinarySensor(
        _indoor_coord({"running": True}), 1, 7
    ).is_on is True


def test_indoor_unit_running_off_when_not_running() -> None:
    assert NovaRcIndoorUnitRunningBinarySensor(
        _indoor_coord({"state": {"running": False}}), 1, 7
    ).is_on is False


def test_indoor_unit_filter_on_when_filter_sign_true() -> None:
    assert NovaRcIndoorUnitFilterBinarySensor(
        _indoor_coord({"filterSign": True}), 1, 7
    ).is_on is True


def test_indoor_unit_filter_reads_state_fallback() -> None:
    assert NovaRcIndoorUnitFilterBinarySensor(
        _indoor_coord({"state": {"filterSign": True}}), 1, 7
    ).is_on is True


def test_indoor_unit_filter_off_when_false() -> None:
    assert NovaRcIndoorUnitFilterBinarySensor(
        _indoor_coord({"filterSign": False}), 1, 7
    ).is_on is False
