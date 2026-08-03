"""Run regression tests for NOVA_RC sensor entities."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import Platform, UnitOfElectricCurrent, UnitOfPower


@pytest.fixture(name="integration_module")
def integration_module_fixture() -> object:
    """Import the integration package from the custom component path."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.sensor as sensor_module  # noqa: PLC0415

    return sensor_module


def _load_api_helpers() -> object:
    """Import the API helper functions after the custom-components path is configured."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.api as api_module  # noqa: PLC0415

    return api_module


def _load_graphql_module() -> object:
    """Import the GraphQL query module after the custom-components path is configured."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.graphql as graphql_module  # noqa: PLC0415

    return graphql_module


def _load_helpers_module() -> object:
    """Import the dataset helper functions after the custom-components path is configured."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.helpers as helpers_module  # noqa: PLC0415

    return helpers_module


def _load_entity_module() -> object:
    """Import the shared entity base helpers."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.entity as entity_module  # noqa: PLC0415

    return entity_module


def _load_coordinator_module() -> object:
    """Import the coordinator module after the custom-components path is configured."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.coordinator as coordinator_module  # noqa: PLC0415

    return coordinator_module


def _load_select_module() -> object:
    """Import the select module after the custom-components path is configured."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.select as select_module  # noqa: PLC0415

    return select_module


def _load_switch_module() -> object:
    """Import the switch module after the custom-components path is configured."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.switch as switch_module  # noqa: PLC0415

    return switch_module


def _load_climate_module() -> object:
    """Import the climate module after the custom-components path is configured."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.climate as climate_module  # noqa: PLC0415

    return climate_module


def _load_binary_sensor_module() -> object:
    """Import the binary sensor module after the custom-components path setup."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.binary_sensor as binary_sensor_module  # noqa: PLC0415

    return binary_sensor_module


def test_integration_loads_sensor_and_binary_sensor_platforms() -> None:
    """The integration should forward the sensor and binary sensor platforms."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link as integration_module  # noqa: PLC0415

    assert Platform.SENSOR in integration_module.PLATFORMS
    assert Platform.BINARY_SENSOR in integration_module.PLATFORMS


def test_zone_entity_uses_zone_name_for_device_info() -> None:
    """The shared zone entity base should expose the zone name through device info."""
    entity_module = _load_entity_module()
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 3,
                "name": "Living room",
                "displayName": "Living",
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    class DummyZoneEntity(entity_module.NovaRcZoneEntity):
        """Simple stub entity used for the shared-base regression test."""

    entity = DummyZoneEntity(coordinator, 3)

    assert entity.device_info["name"] == "Living room"
    assert "sw_version" not in entity.device_info


@pytest.mark.asyncio
async def test_coordinator_keeps_last_installed_version_until_new_one_arrives() -> None:
    """Coordinator should retain the previous installed version when payload omits it."""
    coordinator_module = _load_coordinator_module()
    api = SimpleNamespace(
        async_get_zones=AsyncMock(return_value=[]),
        async_get_notifications=AsyncMock(return_value=[]),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(
            return_value={"installed_version": None, "update_available": True}
        ),
    )
    coordinator = coordinator_module.NovaRcDataUpdateCoordinator(
        SimpleNamespace(),
        api,
    )
    coordinator.gateway_update = {
        "installed_version": "3.2.5",
        "update_available": False,
    }

    await coordinator._async_update_data()

    assert coordinator.gateway_update["installed_version"] == "3.2.5"
    assert coordinator.gateway_update["update_available"] is True


def test_zone_entity_device_info_falls_back_to_latest_received_version() -> None:
    """Use the latest received version when installed version is not available."""
    entity_module = _load_entity_module()
    coordinator = SimpleNamespace(
        data=[{"zoneId": 3, "name": "Living room"}],
        gateway_update={"available_version": "3.2.6"},
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    class DummyZoneEntity(entity_module.NovaRcZoneEntity):
        """Simple stub entity used for the shared-base regression test."""

    entity = DummyZoneEntity(coordinator, 3)

    assert entity.device_info["sw_version"] == "3.2.6"


def test_zone_entity_device_info_omits_sw_version_when_unknown() -> None:
    """Do not report a null software version when no version is known."""
    entity_module = _load_entity_module()
    coordinator = SimpleNamespace(
        data=[{"zoneId": 3, "name": "Living room"}],
        gateway_update={},
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    class DummyZoneEntity(entity_module.NovaRcZoneEntity):
        """Simple stub entity used for the shared-base regression test."""

    entity = DummyZoneEntity(coordinator, 3)

    assert "sw_version" not in entity.device_info


def test_setpoint_sensor_reads_zone_value(integration_module: object) -> None:
    """The setpoint sensor should expose the current setpoint from the zone payload."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "setpoint": 23.0,
                "indoorUnits": [],
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcSetpointSensor(coordinator, 1)

    assert sensor.native_value == 23.0


def test_indoor_unit_temperature_sensor_reads_indoor_unit_state(
    integration_module: object,
) -> None:
    """The indoor unit temperature sensor should read the indoor unit room temperature."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 2,
                "setpoint": 21.0,
                "indoorUnits": [
                    {
                        "indoorUnitId": 7,
                        "displayName": "Office",
                        "state": {"roomAirTemperature": 19.5, "running": True},
                    }
                ],
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcIndoorUnitTemperatureSensor(coordinator, 2, 7)

    assert sensor.native_value == 19.5


def test_build_time_series_identifiers_uses_zone_and_indoor_unit_references() -> None:
    """The time-series request builder should create identifiers for indoor and outdoor units."""
    api_module = _load_api_helpers()
    identifiers = api_module.build_time_series_identifiers(
        {
            "zoneId": 1,
            "indoorUnits": [{"indoorUnitId": 3}],
        }
    )

    assert {"reference": "/indoor_unit/3", "id": "compressor_active"} in identifiers
    assert {
        "reference": "/outdoor_unit/1",
        "id": "ou_indication_air_temp",
    } in identifiers
    assert {
        "reference": "/outdoor_unit/1",
        "id": "ou_indication_comp_current",
    } in identifiers


def test_build_time_series_identifiers_deduplicates_repeated_references() -> None:
    """Identifier generation should avoid duplicate reference/id pairs."""
    api_module = _load_api_helpers()

    identifiers = api_module.build_time_series_identifiers(
        {
            "zoneId": 1,
            "indoorUnits": [{"indoorUnitId": 1}, {"indoorUnitId": 1}],
        }
    )

    unique_pairs = {
        (item["reference"], item["id"])
        for item in identifiers
        if "reference" in item and "id" in item
    }

    assert len(unique_pairs) == len(identifiers)


def test_build_time_series_identifiers_use_zone_scoped_outdoor_reference() -> None:
    """Outdoor-unit identifiers should stay scoped to the current zone id."""
    api_module = _load_api_helpers()

    zone_1_ids = api_module.build_time_series_identifiers(
        {"zoneId": 1, "indoorUnits": []}
    )
    zone_2_ids = api_module.build_time_series_identifiers(
        {"zoneId": 2, "indoorUnits": []}
    )

    assert {
        "reference": "/outdoor_unit/1",
        "id": "ou_indication_air_temp",
    } in zone_1_ids
    assert {
        "reference": "/outdoor_unit/2",
        "id": "ou_indication_air_temp",
    } in zone_2_ids
    assert {
        "reference": "/outdoor_unit/2",
        "id": "ou_indication_air_temp",
    } not in zone_1_ids


def test_translation_assets_cover_entity_and_config_strings() -> None:
    """The translations should include the entity labels used by the integration."""
    integration_dir = Path(__file__).resolve().parents[1]

    with (integration_dir / "strings.json").open(encoding="utf-8") as handle:
        strings = json.load(handle)

    with (integration_dir / "translations" / "en.json").open(
        encoding="utf-8"
    ) as handle:
        translations = json.load(handle)

    expected_paths = [
        ("config", "step", "user", "data", "host"),
        ("config", "step", "user", "data", "ssl_fingerprint"),
        ("entity", "binary_sensor", "gateway_update_available", "name"),
        ("entity", "binary_sensor", "indoor_unit_running", "name"),
        ("entity", "binary_sensor", "sequencing_stop", "name"),
        ("entity", "binary_sensor", "sequencing_stop_active", "name"),
        ("entity", "binary_sensor", "system_stop", "name"),
        ("entity", "binary_sensor", "system_fault", "name"),
        ("entity", "sensor", "gateway_software_version", "name"),
        ("entity", "select", "louver_position", "name"),
        ("entity", "select", "vane_position", "name"),
        ("entity", "sensor", "indoor_unit_temperature", "name"),
        ("entity", "sensor", "indoor_unit_setpoint", "name"),
        ("entity", "sensor", "indoor_unit_operation_mode", "name"),
        ("entity", "sensor", "indoor_unit_fan_speed", "name"),
        ("entity", "sensor", "indoor_capacity", "name"),
        ("entity", "sensor", "compressor_current", "name"),
        ("entity", "sensor", "compressor_power", "name"),
        ("entity", "sensor", "cooling_temperature_min", "name"),
        ("entity", "sensor", "cooling_temperature_max", "name"),
        ("entity", "sensor", "heating_temperature_min", "name"),
        ("entity", "sensor", "heating_temperature_max", "name"),
        ("entity", "sensor", "indoor_heat_exchanger_1_low_temp", "name"),
        ("entity", "sensor", "outdoor_heat_exchanger_1_low_temp", "name"),
        ("entity", "sensor", "outdoor_heat_exchanger_1_high_temp", "name"),
    ]

    for path in expected_paths:
        node = strings
        for part in path:
            node = node[part]
        assert node is not None

    for path in expected_paths:
        node = translations
        for part in path:
            node = node[part]
        assert node is not None


def test_zone_query_keeps_zone_level_fields_separate_from_indoor_unit_reads() -> None:
    """The zone query should stay focused on zone-level data and avoid direct unit lookups."""
    graphql_module = _load_graphql_module()

    assert "zoneId" in graphql_module.GET_ZONES_QUERY
    assert "available" in graphql_module.GET_ZONES_QUERY
    assert "indoorUnits {" in graphql_module.GET_ZONES_QUERY
    assert "indoorUnit(indoorUnitId:" not in graphql_module.GET_ZONES_QUERY
    assert "fanSpeedAutoPermission" not in graphql_module.GET_ZONES_QUERY
    assert "blockedBy" not in graphql_module.GET_ZONES_QUERY


def test_normalize_zones_payload_keeps_unavailable_zones() -> None:
    """Unavailable zones should still be preserved so the availability entity can report false."""
    api_module = _load_api_helpers()

    payload = {
        "data": {
            "xybus": {
                "zones": [
                    {
                        "__typename": "XYBusZone",
                        "zoneId": 7,
                        "available": False,
                        "displayName": "Garage",
                    }
                ]
            }
        }
    }

    normalized = api_module.normalize_zones_payload(payload)

    assert len(normalized) == 1
    assert normalized[0]["zoneId"] == 7
    assert normalized[0]["available"] is False


@pytest.mark.asyncio
async def test_setup_entry_creates_meaningful_zone_sensors(
    integration_module: object,
) -> None:
    """The sensor setup should expose the zone-level sensors from the gateway payload."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "displayName": "Gallery",
                "indoorUnits": [
                    {
                        "indoorUnitId": 7,
                        "displayName": "Gallery Unit",
                        "state": {"roomAirTemperature": 21.5, "running": True},
                    }
                ],
            }
        ],
        gpios={
            "FREE_COOLING": False,
            "FREE_COOLING_ACTIVE": False,
            "SYSTEM_STOP": False,
            "SYSTEM_FAULT": False,
        },
        gateway_update={"installed_version": "3.2.5", "update_available": False},
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )
    hass = SimpleNamespace(data={"mhi_nova": {"entry-id": coordinator}})
    entry = SimpleNamespace(domain="mhi_nova", entry_id="entry-id")

    added_entities: list[object] = []

    def add_entities(entities: list[object]) -> None:
        added_entities.extend(entities)

    await integration_module.async_setup_entry(hass, entry, add_entities)

    assert len(added_entities) == 18
    assert any(
        isinstance(entity, integration_module.NovaRcGatewaySoftwareVersionSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcTemperatureSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcSetpointSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcOperationModeSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcFanSpeedSensor)
        for entity in added_entities
    )
    assert not any(
        isinstance(entity, integration_module.NovaRcIndoorUnitTemperatureSensor)
        for entity in added_entities
    )


@pytest.mark.asyncio
async def test_setup_entry_creates_indoor_unit_sensors_for_multi_indoor_zone(
    integration_module: object,
) -> None:
    """Indoor-unit sensors should only be added for zones with multiple indoor units."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "displayName": "Gallery",
                "indoorUnits": [
                    {
                        "indoorUnitId": 7,
                        "displayName": "Gallery Unit 1",
                        "state": {"roomAirTemperature": 21.5, "running": True},
                    },
                    {
                        "indoorUnitId": 8,
                        "displayName": "Gallery Unit 2",
                        "state": {"roomAirTemperature": 22.1, "running": True},
                    },
                    {
                        "indoorUnitId": 8,
                        "displayName": "Gallery Unit 2 duplicate",
                        "state": {"roomAirTemperature": 22.1, "running": True},
                    },
                ],
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )
    hass = SimpleNamespace(data={"mhi_nova": {"entry-id": coordinator}})
    entry = SimpleNamespace(domain="mhi_nova", entry_id="entry-id")

    added_entities: list[object] = []

    def add_entities(entities: list[object]) -> None:
        added_entities.extend(entities)

    await integration_module.async_setup_entry(hass, entry, add_entities)

    assert any(
        isinstance(entity, integration_module.NovaRcIndoorUnitTemperatureSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcIndoorUnitSetpointSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcIndoorUnitOperationModeSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcIndoorUnitFanSpeedSensor)
        for entity in added_entities
    )

    indoor_temp_entities = [
        entity
        for entity in added_entities
        if isinstance(entity, integration_module.NovaRcIndoorUnitTemperatureSensor)
    ]
    assert len(indoor_temp_entities) == 2


@pytest.mark.asyncio
async def test_setup_entry_creates_time_series_sensors(
    integration_module: object,
) -> None:
    """The sensor setup should expose the time-series-derived sensors from the gateway payload."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "displayName": "Gallery",
                "indoorUnits": [],
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )
    hass = SimpleNamespace(data={"mhi_nova": {"entry-id": coordinator}})
    entry = SimpleNamespace(domain="mhi_nova", entry_id="entry-id")

    added_entities: list[object] = []

    def add_entities(entities: list[object]) -> None:
        added_entities.extend(entities)

    await integration_module.async_setup_entry(hass, entry, add_entities)

    assert any(
        isinstance(entity, integration_module.NovaRcOutdoorAirTemperatureSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcCompressorFrequencySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcCompressorCurrentSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcCompressorPowerSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcProtectionStateSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcIndoorCapacitySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcIndoorHeatExchanger1LowTempSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcOutdoorHeatExchanger1LowTempSensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, integration_module.NovaRcOutdoorHeatExchanger1HighTempSensor)
        for entity in added_entities
    )


@pytest.mark.asyncio
async def test_select_setup_entry_creates_zone_select_entities() -> None:
    """Select platform setup should create louver and vane entities per zone."""
    select_module = _load_select_module()

    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "displayName": "Gallery",
                "indoorUnits": [],
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )
    hass = SimpleNamespace(data={"mhi_nova": {"entry-id": coordinator}})
    entry = SimpleNamespace(domain="mhi_nova", entry_id="entry-id")

    added_entities: list[object] = []

    def add_entities(entities: list[object]) -> None:
        added_entities.extend(entities)

    await select_module.async_setup_entry(hass, entry, add_entities)

    assert len(added_entities) == 2
    assert any(
        isinstance(entity, select_module.NovaRcLouverSelect)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, select_module.NovaRcVaneSelect) for entity in added_entities
    )


@pytest.mark.asyncio
async def test_switch_setup_entry_creates_zone_switch_entities() -> None:
    """Switch platform setup should create one 3D auto switch per zone."""
    switch_module = _load_switch_module()

    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "displayName": "Gallery",
                "indoorUnits": [],
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )
    hass = SimpleNamespace(data={"mhi_nova": {"entry-id": coordinator}})
    entry = SimpleNamespace(domain="mhi_nova", entry_id="entry-id")

    added_entities: list[object] = []

    def add_entities(entities: list[object]) -> None:
        added_entities.extend(entities)

    await switch_module.async_setup_entry(hass, entry, add_entities)

    assert len(added_entities) == 1
    assert isinstance(added_entities[0], switch_module.NovaRc3DAutoSwitch)


@pytest.mark.asyncio
async def test_binary_sensor_setup_creates_indoor_unit_running_entities() -> None:
    """The binary sensor setup should expose per-indoor-unit running state."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.binary_sensor as binary_sensor_module  # noqa: PLC0415

    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "displayName": "Gallery",
                "indoorUnits": [
                    {
                        "indoorUnitId": 7,
                        "displayName": "Gallery Unit",
                        "state": {"roomAirTemperature": 21.5, "running": True},
                    }
                ],
            }
        ],
        gateway_update={"update_available": True},
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )
    hass = SimpleNamespace(data={"mhi_nova": {"entry-id": coordinator}})
    entry = SimpleNamespace(domain="mhi_nova", entry_id="entry-id")

    added_entities: list[object] = []

    def add_entities(entities: list[object]) -> None:
        added_entities.extend(entities)

    await binary_sensor_module.async_setup_entry(hass, entry, add_entities)

    assert any(
        isinstance(entity, binary_sensor_module.NovaRcRunningBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcAvailableBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRc3DAutoBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcTemperatureRangeBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcCriticalErrorBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcMaintenanceBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcCompressorBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcDefrostingBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcNotificationsBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcIndoorUnitRunningBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcIndoorUnitFilterBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcFreeCoolingBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcFreeCoolingActiveBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcSystemStopBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, binary_sensor_module.NovaRcSystemFaultBinarySensor)
        for entity in added_entities
    )
    assert any(
        isinstance(
            entity, binary_sensor_module.NovaRcGatewayUpdateAvailableBinarySensor
        )
        for entity in added_entities
    )


def test_indoor_unit_temperature_sensor_reads_direct_room_temperature(
    integration_module: object,
) -> None:
    """The indoor unit temperature sensor should also read direct room temperature values."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 2,
                "setpoint": 21.0,
                "indoorUnits": [
                    {
                        "indoorUnitId": 7,
                        "displayName": "Office",
                        "roomAirTemperature": 19.5,
                    }
                ],
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcIndoorUnitTemperatureSensor(coordinator, 2, 7)

    assert sensor.native_value == 19.5


def test_indoor_capacity_sensor_uses_kw_unit(integration_module: object) -> None:
    """The indoor capacity sensor should expose deci-kW values in kW."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 2,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "iu_indication_capacity",
                            "reference": "/indoor_unit/2",
                            "data": [{"value": 15.0}],
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcIndoorCapacitySensor(coordinator, 2)

    assert sensor.native_unit_of_measurement == UnitOfPower.KILO_WATT
    assert sensor.native_value == 1.5


def test_temperature_range_sensors_read_cooling_and_heating_bounds(
    integration_module: object,
) -> None:
    """Temperature range sensors should expose cooling and heating min/max values."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 2,
                "indoorUnits": [],
                "temperatureRangeCooling": {"lower": 18, "upper": 24},
                "temperatureRangeHeating": {"lower": 20, "upper": 30},
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    cooling_min = integration_module.NovaRcCoolingTemperatureMinSensor(coordinator, 2)
    cooling_max = integration_module.NovaRcCoolingTemperatureMaxSensor(coordinator, 2)
    heating_min = integration_module.NovaRcHeatingTemperatureMinSensor(coordinator, 2)
    heating_max = integration_module.NovaRcHeatingTemperatureMaxSensor(coordinator, 2)

    assert cooling_min.native_value == 18.0
    assert cooling_max.native_value == 24.0
    assert heating_min.native_value == 20.0
    assert heating_max.native_value == 30.0


def test_compressor_current_and_power_sensors_use_ampere_and_230v(
    integration_module: object,
) -> None:
    """Compressor current should be exposed in A and power derived with 230V."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 2,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "ou_indication_comp_current",
                            "reference": "/outdoor_unit/2",
                            "data": [{"value": 4.2}],
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    current_sensor = integration_module.NovaRcCompressorCurrentSensor(coordinator, 2)
    power_sensor = integration_module.NovaRcCompressorPowerSensor(coordinator, 2)

    assert current_sensor.native_unit_of_measurement == UnitOfElectricCurrent.AMPERE
    assert current_sensor.native_value == 4.2
    assert power_sensor.native_unit_of_measurement == UnitOfPower.WATT
    assert power_sensor.native_value == 966.0


def test_compressor_frequency_sensor_scales_raw_dataset_value(
    integration_module: object,
) -> None:
    """Compressor frequency should convert deci-hertz values to hertz."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 2,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "ou_indication_compressor_frequency",
                            "reference": "/outdoor_unit/2",
                            "data": [{"value": 35}],
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcCompressorFrequencySensor(coordinator, 2)

    assert sensor.native_value == 3.5


def test_get_dataset_value_uses_latest_timestamped_point() -> None:
    """Dataset helpers should choose the newest known datapoint when timestamps are present."""
    helpers_module = _load_helpers_module()

    dataset = {
        "data": [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 20},
            {"timestamp": "2024-01-03T00:00:00Z", "value": 24},
        ]
    }

    assert helpers_module.get_dataset_value(dataset) == 24


def test_dataset_is_on_parses_yes_no_labels() -> None:
    """Boolean helpers should understand common yes/no labels from the gateway."""
    helpers_module = _load_helpers_module()

    assert helpers_module.dataset_is_on("compressor_active", {"data": {"value": "Ja"}})
    assert not helpers_module.dataset_is_on(
        "compressor_active", {"data": {"value": "Nein"}}
    )


def test_compressor_binary_sensor_uses_frequency_fallback_when_active_flag_is_false() -> (
    None
):
    """Compressor should be considered active when frequency is above zero."""
    binary_sensor_module = _load_binary_sensor_module()

    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "compressor_active",
                            "reference": "/indoor_unit/1",
                            "data": [{"value": False}],
                        },
                        {
                            "id": "ou_indication_compressor_frequency",
                            "reference": "/outdoor_unit/1",
                            "data": [{"value": 35}],
                        },
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    entity = binary_sensor_module.NovaRcCompressorBinarySensor(coordinator, 1)

    assert entity.is_on


def test_compressor_binary_sensor_stays_off_when_frequency_is_zero() -> None:
    """Compressor should stay off when active flag is false and frequency is zero."""
    binary_sensor_module = _load_binary_sensor_module()

    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "compressor_active",
                            "reference": "/indoor_unit/1",
                            "data": [{"value": False}],
                        },
                        {
                            "id": "ou_indication_compressor_frequency",
                            "reference": "/outdoor_unit/1",
                            "data": [{"value": 0}],
                        },
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    entity = binary_sensor_module.NovaRcCompressorBinarySensor(coordinator, 1)

    assert not entity.is_on


def test_protection_state_sensor_parses_nested_normal_value(
    integration_module: object,
) -> None:
    """The protection state sensor should extract a nested normal-state value from the time-series payload."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "ou_indication_protection_state_comp",
                            "reference": "/outdoor_unit/1",
                            "data": {"normal": True},
                            "options": {
                                "options": [{"value": "normal", "label": "Normal"}]
                            },
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcProtectionStateSensor(coordinator, 1)

    assert sensor.native_value == "normal"


def test_protection_state_sensor_truncates_dot_separated_values(
    integration_module: object,
) -> None:
    """Dot-separated gateway values should be reduced to the last segment only."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "ou_indication_protection_state_comp",
                            "reference": "/outdoor_unit/1",
                            "data": {
                                "value": "dataSets.nova.enumeratedOptions.ou_indication_protection_state_comp.normal"
                            },
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcProtectionStateSensor(coordinator, 1)

    assert sensor.native_value == "normal"


def test_protection_state_sensor_truncates_wrapped_template_values(
    integration_module: object,
) -> None:
    """Template-wrapped dot-path values should also reduce to the final segment."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "ou_indication_protection_state_comp",
                            "reference": "/outdoor_unit/1",
                            "data": {
                                "value": "${dataSets.nova.enumeratedOptions.ou_indication_protection_state_comp.normal}"
                            },
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcProtectionStateSensor(coordinator, 1)

    assert sensor.native_value == "normal"


def test_protection_state_sensor_uses_option_label_when_numeric_value_is_present(
    integration_module: object,
) -> None:
    """Numeric values should resolve to the option label and then be trimmed."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "ou_indication_protection_state_comp",
                            "reference": "/outdoor_unit/1",
                            "data": [{"value": 6}],
                            "options": {
                                "options": [
                                    {
                                        "value": 6,
                                        "label": "${dataSets.nova.enumeratedOptions.ou_indication_protection_state_comp.low_pressure_protection_control}",
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcProtectionStateSensor(coordinator, 1)

    assert sensor.native_value == "low_pressure_protection_control"


def test_indoor_unit_temperature_sensor_returns_none_when_direct_value_missing(
    integration_module: object,
) -> None:
    """Indoor unit temperature should not fall back to time-series when zone data is missing."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 2,
                "setpoint": 21.0,
                "indoorUnits": [
                    {
                        "indoorUnitId": 7,
                        "displayName": "Office",
                    }
                ],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "iu_room_air_temperature",
                            "reference": "/indoor_unit/2",
                            "data": [{"value": 18.2}],
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcIndoorUnitTemperatureSensor(coordinator, 2, 7)

    assert sensor.native_value is None


def test_operation_mode_sensor_returns_none_when_zone_value_missing(
    integration_module: object,
) -> None:
    """Operation mode should not fall back to time-series when zone data is missing."""
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "operation_mode",
                            "reference": "/indoor_unit/1",
                            "data": [{"value": "COOLING"}],
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    sensor = integration_module.NovaRcOperationModeSensor(coordinator, 1)

    assert sensor.native_value is None


def test_normalize_time_series_payload_collects_datasets_by_id() -> None:
    """Time-series payloads should be normalized into a lookup keyed by dataset id."""
    api_module = _load_api_helpers()
    datasets = api_module.normalize_time_series_payload(
        {
            "data": {
                "timeSeries": {
                    "dataSetsWithData": [
                        {
                            "id": "compressor_active",
                            "reference": "/indoor_unit/1",
                            "data": [{"value": True}],
                        }
                    ]
                }
            }
        }
    )

    assert datasets["compressor_active"]["data"][0]["value"] is True


def test_zone_query_requests_richer_zone_detail_fields() -> None:
    """The zone query should request the richer detail fields from the gateway."""
    graphql_module = _load_graphql_module()

    query = graphql_module.GET_ZONES_QUERY

    assert "sequencingState" in query
    assert "controllingModeChangeProgress" in query
    assert "manualOperationTimeout" in query
    assert "controlProgram" in query
    assert "operationMode" in query


def test_update_query_requests_installed_version_and_available_release() -> None:
    """The update query should include installed and available software versions."""
    graphql_module = _load_graphql_module()

    query = graphql_module.GET_UPDATE_CLOUD_SETTINGS_QUERY

    assert "installedVersion" in query
    assert "installedBundleBuild" in query
    assert "availableSoftwareRelease" in query
    assert "automaticCheck" in query


def test_get_zone_query_requests_airflow_and_patch_options() -> None:
    """The targeted GetZone query should request airflow and patch option fields."""
    graphql_module = _load_graphql_module()

    query = graphql_module.GET_ZONE_QUERY

    assert "query GetZone($zoneId: Int!)" in query
    assert "louverPosition" in query
    assert "vanePosition" in query
    assert "patchOptions" in query


def test_notifications_query_avoids_schema_volatile_object_fields() -> None:
    """Notifications query should avoid object fields that require nested sub-selections."""
    graphql_module = _load_graphql_module()

    query = graphql_module.GET_NOTIFICATIONS_QUERY

    assert "confirmedBy" not in query
    assert "\n      error\n" not in query
    assert "\n      source\n" not in query
    assert "\n    sources\n" not in query


def test_louver_select_returns_none_when_direct_zone_value_missing() -> None:
    """Louver select should not use time-series values when the direct zone value is missing."""
    select_module = _load_select_module()

    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "louver_position",
                            "reference": "/indoor_unit/1",
                            "data": [
                                {
                                    "value": "${dataSets.nova.enumeratedOptions.louver_position.POSITION_3}"
                                }
                            ],
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    entity = select_module.NovaRcLouverSelect(coordinator, 1)

    assert entity.current_option is None


def test_vane_select_returns_none_when_direct_zone_value_missing() -> None:
    """Vane select should not use time-series values when the direct zone value is missing."""
    select_module = _load_select_module()

    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "indoorUnits": [],
                "timeSeries": {
                    "dataSets": [
                        {
                            "id": "vane_position",
                            "reference": "/indoor_unit/1",
                            "data": [{"value": 5}],
                            "options": {
                                "options": [
                                    {
                                        "value": 5,
                                        "label": "${dataSets.nova.enumeratedOptions.vane_position.WIDE}",
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=SimpleNamespace(host="gateway"),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
    )

    entity = select_module.NovaRcVaneSelect(coordinator, 1)

    assert entity.current_option is None


@pytest.mark.asyncio
async def test_climate_async_set_hvac_mode_uses_startup_airflow_wait() -> None:
    """HVAC mode changes should request airflow wait only when starting from off."""
    climate_module = _load_climate_module()

    api = SimpleNamespace(host="gateway", async_set_zone_state=AsyncMock())
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "running": False,
                "operationMode": "AUTO",
                "fanSpeed": "AUTO",
                "patchOptions": {},
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
        async_request_refresh=AsyncMock(),
    )

    climate = climate_module.NovaRcZoneClimate(coordinator, 1)

    await climate.async_set_hvac_mode(HVACMode.COOL)

    api.async_set_zone_state.assert_awaited_once_with(
        1,
        running=True,
        operation_mode="COOLING",
        wait_for_airflow_after_start=True,
    )
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_climate_async_set_temperature_forwards_setpoint() -> None:
    """Temperature changes should forward setpoint updates to the API."""
    climate_module = _load_climate_module()

    api = SimpleNamespace(host="gateway", async_set_zone_state=AsyncMock())
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "running": True,
                "operationMode": "HEATING",
                "fanSpeed": "AUTO",
                "patchOptions": {},
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
        async_request_refresh=AsyncMock(),
    )

    climate = climate_module.NovaRcZoneClimate(coordinator, 1)

    await climate.async_set_temperature(temperature=22.5)

    api.async_set_zone_state.assert_awaited_once_with(1, setpoint=22.5)
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_climate_async_set_fan_mode_maps_gateway_value() -> None:
    """Fan mode updates should map Home Assistant mode labels to gateway values."""
    climate_module = _load_climate_module()

    api = SimpleNamespace(host="gateway", async_set_zone_state=AsyncMock())
    coordinator = SimpleNamespace(
        data=[
            {
                "zoneId": 1,
                "running": True,
                "operationMode": "AUTO",
                "fanSpeed": "AUTO",
                "patchOptions": {},
            }
        ],
        config_entry=SimpleNamespace(domain="mhi_nova", entry_id="entry-id"),
        api=api,
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
        async_request_refresh=AsyncMock(),
    )

    climate = climate_module.NovaRcZoneClimate(coordinator, 1)

    await climate.async_set_fan_mode("Power")

    api.async_set_zone_state.assert_awaited_once_with(1, fan_speed="POWERFUL")
    coordinator.async_request_refresh.assert_awaited_once()
