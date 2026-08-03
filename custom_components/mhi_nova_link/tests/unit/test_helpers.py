"""Unit tests for helpers.py — pure Python, no HA instance, no network.

Covers:
- get_dataset_value (all data shapes)
- get_zone_time_series_datasets (timeSeries / nested data)
- get_dataset_option_label
- dataset_is_on (string labels, bool, numeric, enum options)
- _normalize_enum_token
"""

import pytest

from custom_components.mhi_nova_link.helpers import (
    _normalize_enum_token,
    dataset_is_on,
    get_dataset_option_label,
    get_dataset_value,
    get_zone_time_series_datasets,
)


# ---------------------------------------------------------------------------
# get_dataset_value
# ---------------------------------------------------------------------------


def test_get_dataset_value_absent_data_key_returns_none() -> None:
    """A dataset without a 'data' key should return None."""
    assert get_dataset_value({}) is None


def test_get_dataset_value_scalar_int() -> None:
    """Scalar integer data should be returned directly."""
    assert get_dataset_value({"data": 42}) == 42


def test_get_dataset_value_scalar_float() -> None:
    """Scalar float data should be returned directly."""
    assert get_dataset_value({"data": 3.14}) == 3.14


def test_get_dataset_value_scalar_bool() -> None:
    """Scalar boolean data should be returned directly."""
    assert get_dataset_value({"data": True}) is True


def test_get_dataset_value_scalar_string() -> None:
    """Scalar string data should be returned directly."""
    assert get_dataset_value({"data": "hello"}) == "hello"


def test_get_dataset_value_empty_list_returns_none() -> None:
    """An empty list should return None."""
    assert get_dataset_value({"data": []}) is None


def test_get_dataset_value_single_element_list_unwraps() -> None:
    """A single-element list should unwrap the inner value."""
    assert get_dataset_value({"data": [{"value": 7}]}) == 7


def test_get_dataset_value_picks_latest_timestamp_from_list() -> None:
    """The item with the latest timestamp should be selected."""
    dataset = {
        "data": [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 10},
            {"timestamp": "2024-01-05T00:00:00Z", "value": 50},
            {"timestamp": "2024-01-03T00:00:00Z", "value": 30},
        ]
    }
    assert get_dataset_value(dataset) == 50


def test_get_dataset_value_last_element_without_timestamps() -> None:
    """When there are no timestamps, the last list element should be returned."""
    assert get_dataset_value({"data": [{"value": 1}, {"value": 2}, {"value": 3}]}) == 3


def test_get_dataset_value_dict_value_key() -> None:
    """A dict with a 'value' key should return its value."""
    assert get_dataset_value({"data": {"value": 99}}) == 99


def test_get_dataset_value_dict_current_value_key() -> None:
    """A dict with 'currentValue' should use that key."""
    assert get_dataset_value({"data": {"currentValue": 55}}) == 55


def test_get_dataset_value_dict_latest_value_key() -> None:
    """A dict with 'latestValue' should use that key."""
    assert get_dataset_value({"data": {"latestValue": 33}}) == 33


def test_get_dataset_value_dict_raw_value_fallback() -> None:
    """rawValue should be used when no standard key is present."""
    assert get_dataset_value({"data": {"rawValue": "raw"}}) == "raw"


def test_get_dataset_value_dict_nested_data_key() -> None:
    """A nested 'data' key should be recursively resolved."""
    assert get_dataset_value({"data": {"data": 7}}) == 7


def test_get_dataset_value_dict_normal_key() -> None:
    """A dict with 'normal' key (but no standard keys) should return it."""
    assert get_dataset_value({"data": {"normal": True}}) is True


def test_get_dataset_value_dict_values_list() -> None:
    """A dict with 'values' list should return the last element."""
    assert get_dataset_value({"data": {"values": [1, 2, 3]}}) == 3


def test_get_dataset_value_none_data_returns_none() -> None:
    """A data value of None should return None."""
    assert get_dataset_value({"data": None}) is None


# ---------------------------------------------------------------------------
# get_zone_time_series_datasets
# ---------------------------------------------------------------------------


def test_get_zone_time_series_datasets_reads_time_series_key() -> None:
    """Datasets under zone.timeSeries should be extracted."""
    zone = {
        "timeSeries": {
            "dataSets": [{"id": "fan_speed", "data": [{"value": "AUTO"}]}]
        }
    }
    assert "fan_speed" in get_zone_time_series_datasets(zone)


def test_get_zone_time_series_datasets_reads_nested_data_time_series() -> None:
    """Datasets under zone.data.timeSeries should also be extracted."""
    zone = {
        "data": {
            "timeSeries": {
                "dataSets": [{"id": "operation_mode", "data": [{"value": "COOLING"}]}]
            }
        }
    }
    assert "operation_mode" in get_zone_time_series_datasets(zone)


def test_get_zone_time_series_datasets_empty_zone_returns_empty() -> None:
    """An empty zone dict should return empty datasets."""
    assert get_zone_time_series_datasets({}) == {}


def test_get_zone_time_series_datasets_skips_items_without_id() -> None:
    """Items without an id should be skipped."""
    zone = {
        "timeSeries": {
            "dataSets": [
                {"data": [{"value": 1}]},
                {"id": "compressor_active", "data": [{"value": True}]},
            ]
        }
    }
    result = get_zone_time_series_datasets(zone)
    assert list(result.keys()) == ["compressor_active"]


def test_get_zone_time_series_datasets_reads_nested_datasets_within_item() -> None:
    """Nested dataSets entries within an item should also be collected."""
    zone = {
        "timeSeries": {
            "datasets": [
                {
                    "id": "outer",
                    "dataSets": [{"id": "inner_dataset", "data": [{"value": 1}]}],
                }
            ]
        }
    }
    datasets = get_zone_time_series_datasets(zone)
    assert "outer" in datasets
    assert "inner_dataset" in datasets


def test_get_zone_time_series_datasets_lowercase_datasets_alias() -> None:
    """The lowercase 'datasets' key should work as an alias for 'dataSets'."""
    zone = {
        "timeSeries": {
            "datasets": [{"id": "setpoint", "data": [{"value": 22.0}]}]
        }
    }
    assert "setpoint" in get_zone_time_series_datasets(zone)


# ---------------------------------------------------------------------------
# get_dataset_option_label
# ---------------------------------------------------------------------------


def test_get_dataset_option_label_returns_label_for_matching_value() -> None:
    """The label matching the value should be returned."""
    dataset = {
        "options": {
            "options": [
                {"value": 1, "label": "Active"},
                {"value": 0, "label": "Inactive"},
            ]
        }
    }
    assert get_dataset_option_label(dataset, 1) == "Active"
    assert get_dataset_option_label(dataset, 0) == "Inactive"


def test_get_dataset_option_label_returns_none_when_no_match() -> None:
    """None should be returned when no option matches the value."""
    dataset = {"options": {"options": [{"value": 5, "label": "High"}]}}
    assert get_dataset_option_label(dataset, 99) is None


def test_get_dataset_option_label_returns_none_when_options_absent() -> None:
    """None should be returned when the options structure is absent."""
    assert get_dataset_option_label({}, 1) is None


# ---------------------------------------------------------------------------
# dataset_is_on
# ---------------------------------------------------------------------------


def test_dataset_is_on_bool_true() -> None:
    """Boolean True value should return True."""
    assert dataset_is_on("any_id", {"data": True}) is True


def test_dataset_is_on_bool_false() -> None:
    """Boolean False value should return False."""
    assert dataset_is_on("any_id", {"data": False}) is False


@pytest.mark.parametrize(
    "value",
    ["active", "enabled", "on", "open", "true", "1", "Ja", "yes", "y", "aktiv", "ein"],
)
def test_dataset_is_on_truthy_string_values(value: str) -> None:
    """Common truthy string values should be recognized."""
    assert dataset_is_on("any_id", {"data": value}) is True


@pytest.mark.parametrize(
    "value",
    [
        "inactive",
        "disabled",
        "off",
        "closed",
        "false",
        "0",
        "Nein",
        "no",
        "n",
        "inaktiv",
        "aus",
    ],
)
def test_dataset_is_on_falsy_string_values(value: str) -> None:
    """Common falsy string values should be recognized."""
    assert dataset_is_on("any_id", {"data": value}) is False


def test_dataset_is_on_known_sensor_id_defaults_to_false_for_unknown_string() -> None:
    """Known sensor IDs should default to False when the value is unresolvable."""
    for sensor_id in ("compressor_active", "defrosting_active", "filter_sign"):
        assert dataset_is_on(sensor_id, {"data": "unknown_value"}) is False


def test_dataset_is_on_nonzero_int_is_truthy() -> None:
    """Nonzero integers without enum options should be coerced to True."""
    assert dataset_is_on("any_id", {"data": 5}) is True


def test_dataset_is_on_zero_int_is_falsy() -> None:
    """Zero without enum options should be coerced to False."""
    assert dataset_is_on("any_id", {"data": 0}) is False


def test_dataset_is_on_numeric_enum_active_label() -> None:
    """A numeric value matching an 'active' label should return True."""
    dataset = {
        "data": [{"value": 1}],
        "options": {
            "options": [
                {"value": 1, "label": "active"},
                {"value": 0, "label": "inactive"},
            ]
        },
    }
    assert dataset_is_on("any_id", dataset) is True


def test_dataset_is_on_numeric_enum_inactive_label() -> None:
    """A numeric value matching an 'inactive' label should return False."""
    dataset = {
        "data": [{"value": 0}],
        "options": {
            "options": [
                {"value": 1, "label": "active"},
                {"value": 0, "label": "inactive"},
            ]
        },
    }
    assert dataset_is_on("any_id", dataset) is False


# ---------------------------------------------------------------------------
# _normalize_enum_token
# ---------------------------------------------------------------------------


def test_normalize_enum_token_strips_template_wrapper() -> None:
    """${...} template wrappers should be stripped, leaving the last dot segment."""
    result = _normalize_enum_token(
        "${dataSets.nova.enumeratedOptions.foo.active}"
    )
    assert result == "active"


def test_normalize_enum_token_reduces_dot_path_to_last_segment() -> None:
    """Dot-separated paths should reduce to the final segment."""
    assert _normalize_enum_token("some.path.to.value") == "value"


def test_normalize_enum_token_lowercases_and_strips() -> None:
    """Values should be lowercased and surrounding whitespace trimmed."""
    assert _normalize_enum_token("  ACTIVE  ") == "active"


def test_normalize_enum_token_plain_value_unchanged() -> None:
    """A plain lowercase value without dots or templates should be returned as-is."""
    assert _normalize_enum_token("normal") == "normal"
