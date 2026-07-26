"""Run regression tests for NOVA_RC sensor entities."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from homeassistant.const import Platform


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
        ("entity", "sensor", "indoor_unit_temperature", "name"),
        ("entity", "sensor", "indoor_unit_setpoint", "name"),
        ("entity", "sensor", "indoor_unit_operation_mode", "name"),
        ("entity", "sensor", "indoor_unit_fan_speed", "name"),
        ("entity", "sensor", "indoor_capacity", "name"),
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

    async def add_entities(entities: list[object]) -> None:
        added_entities.extend(entities)

    await integration_module.async_setup_entry(hass, entry, add_entities)

    assert len(added_entities) == 12
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

    async def add_entities(entities: list[object]) -> None:
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

    async def add_entities(entities: list[object]) -> None:
        added_entities.extend(entities)

    await binary_sensor_module.async_setup_entry(hass, entry, add_entities)

    assert any(
        isinstance(entity, binary_sensor_module.NovaRcAvailableBinarySensor)
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


def test_indoor_unit_temperature_sensor_reads_time_series_dataset_when_direct_value_missing(
    integration_module: object,
) -> None:
    """The indoor unit temperature sensor should fall back to the time-series dataset."""
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

    assert sensor.native_value == 18.2


def test_operation_mode_sensor_reads_time_series_dataset_when_zone_value_missing(
    integration_module: object,
) -> None:
    """The operation mode sensor should fall back to the time-series payload."""
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

    assert sensor.native_value == "cooling"


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


def test_normalize_gateway_update_payload_extracts_versions_and_flags() -> None:
    """Gateway update payload normalization should expose software and update status."""
    api_module = _load_api_helpers()

    normalized = api_module.normalize_gateway_update_payload(
        {
            "data": {
                "system": {
                    "information": {
                        "installedVersion": {"asString": "3.2.5"},
                        "installedBundleDescription": "production",
                        "installedBundleBuild": "master/ct4web:123",
                    }
                },
                "update": {
                    "cloud": {
                        "availableSoftwareRelease": {"version": {"asString": "3.2.6"}},
                        "settings": {
                            "automaticCheck": False,
                            "automaticInstall": False,
                        },
                    }
                },
            }
        }
    )

    assert normalized["installed_version"] == "3.2.5"
    assert normalized["available_version"] == "3.2.6"
    assert normalized["update_available"] is True


def test_gpios_query_requests_expected_fields() -> None:
    """The GPIO query should request id, function and value."""
    graphql_module = _load_graphql_module()

    query = graphql_module.GET_GPIOS_QUERY

    assert "query GetGpios" in query
    assert "gpios" in query
    assert "id" in query
    assert "function" in query
    assert "value" in query


def test_normalize_gpios_payload_maps_functions_to_booleans() -> None:
    """GPIO payloads should normalize into a function-to-state mapping."""
    api_module = _load_api_helpers()

    payload = {
        "data": {
            "gpio": {
                "gpios": [
                    {"function": "FREE_COOLING", "value": False},
                    {"function": "FREE_COOLING_ACTIVE", "value": True},
                    {"function": "SYSTEM_STOP", "value": False},
                    {"function": "SYSTEM_FAULT", "value": True},
                ]
            }
        }
    }

    assert api_module.normalize_gpios_payload(payload) == {
        "FREE_COOLING": False,
        "FREE_COOLING_ACTIVE": True,
        "SYSTEM_STOP": False,
        "SYSTEM_FAULT": True,
    }


def test_build_time_series_period_uses_rolling_utc_range() -> None:
    """The time-series period should end in UTC now and use the configured lookback."""
    api_module = _load_api_helpers()

    period = api_module.build_time_series_period()

    assert period["startDate"].endswith("Z")
    assert period["endDate"].endswith("Z")

    start = api_module.datetime.fromisoformat(
        period["startDate"].replace("Z", "+00:00")
    )
    end = api_module.datetime.fromisoformat(period["endDate"].replace("Z", "+00:00"))

    assert end > start
    assert (end - start) == api_module.TIME_SERIES_LOOKBACK


def test_normalize_ssl_fingerprint_accepts_colon_separated_values() -> None:
    """SSL fingerprint normalization should support colon-separated SHA256 values."""
    api_module = _load_api_helpers()

    normalized = api_module.normalize_ssl_fingerprint("AA:BB:CC" + ":11" * 29)

    assert normalized is not None
    assert len(normalized) == 64
    assert ":" not in normalized


def test_normalize_ssl_fingerprint_rejects_invalid_length() -> None:
    """SSL fingerprint normalization should reject non-SHA256 lengths."""
    api_module = _load_api_helpers()

    with pytest.raises(ValueError):
        api_module.normalize_ssl_fingerprint("abcd")
