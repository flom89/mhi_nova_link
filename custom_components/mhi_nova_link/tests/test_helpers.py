"""Unit tests for helpers.py edge cases."""

from pathlib import Path
import sys

import pytest

_integration_dir = Path(__file__).resolve().parents[1]
_config_dir = _integration_dir.parent.parent
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

from custom_components.mhi_nova_link.helpers import (  # noqa: E402
    _normalize_enum_token,
    dataset_is_on,
    get_dataset_option_label,
    get_dataset_value,
    get_zone_time_series_datasets,
)


# ---------------------------------------------------------------------------
# get_dataset_value
# ---------------------------------------------------------------------------


def test_get_dataset_value_returns_none_for_absent_data_key() -> None:
    """A dataset without a 'data' key should return None."""
    assert get_dataset_value({}) is None


def test_get_dataset_value_returns_scalar_directly() -> None:
    """Scalar data values should be returned as-is."""
    assert get_dataset_value({"data": 42}) == 42
    assert get_dataset_value({"data": 3.14}) == 3.14
    assert get_dataset_value({"data": True}) is True
    assert get_dataset_value({"data": "hello"}) == "hello"


def test_get_dataset_value_returns_none_for_empty_list() -> None:
    """An empty list should return None."""
    assert get_dataset_value({"data": []}) is None


def test_get_dataset_value_returns_value_for_single_element_list() -> None:
    """A single-element list should unwrap to the element's value."""
    assert get_dataset_value({"data": [{"value": 7}]}) == 7


def test_get_dataset_value_picks_latest_timestamp_from_list() -> None:
    """When multiple timestamped items are present, the latest should be selected."""
    dataset = {
        "data": [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 10},
            {"timestamp": "2024-01-05T00:00:00Z", "value": 50},
            {"timestamp": "2024-01-03T00:00:00Z", "value": 30},
        ]
    }
    assert get_dataset_value(dataset) == 50


def test_get_dataset_value_returns_last_element_when_no_timestamps() -> None:
    """Without timestamps, the last value in the list should be returned."""
    dataset = {"data": [{"value": 1}, {"value": 2}, {"value": 3}]}
    assert get_dataset_value(dataset) == 3


def test_get_dataset_value_reads_value_key_from_dict() -> None:
    """A dict with a 'value' key should return its value."""
    assert get_dataset_value({"data": {"value": 99}}) == 99


def test_get_dataset_value_reads_current_value_key_from_dict() -> None:
    """A dict with 'currentValue' should use that key."""
    assert get_dataset_value({"data": {"currentValue": 55}}) == 55


def test_get_dataset_value_reads_rawValue_when_other_keys_absent() -> None:
    """rawValue should be used when no standard extraction key is present."""
    assert get_dataset_value({"data": {"rawValue": "raw"}}) == "raw"


def test_get_dataset_value_reads_nested_data_key() -> None:
    """A nested 'data' key inside a dict should be recursively resolved."""
    assert get_dataset_value({"data": {"data": 7}}) == 7


def test_get_dataset_value_reads_normal_key_when_present() -> None:
    """A dict with 'normal' key but without standard keys should return normal."""
    assert get_dataset_value({"data": {"normal": True}}) is True


def test_get_dataset_value_reads_values_list_from_dict() -> None:
    """A dict with 'values' list should return the last element."""
    dataset = {"data": {"values": [1, 2, 3]}}
    assert get_dataset_value(dataset) == 3


def test_get_dataset_value_returns_data_unchanged_for_unexpected_type() -> None:
    """When data is an unexpected type, the raw data should be returned."""
    dataset = {"data": None}
    assert get_dataset_value(dataset) is None


# ---------------------------------------------------------------------------
# get_zone_time_series_datasets
# ---------------------------------------------------------------------------


def test_get_zone_time_series_datasets_reads_timeSeries_key() -> None:
    """Datasets under zone.timeSeries should be extracted."""
    zone = {
        "timeSeries": {
            "dataSets": [
                {"id": "fan_speed", "data": [{"value": "AUTO"}]},
            ]
        }
    }
    datasets = get_zone_time_series_datasets(zone)
    assert "fan_speed" in datasets


def test_get_zone_time_series_datasets_reads_nested_data_timeSeries() -> None:
    """Datasets under zone.data.timeSeries should also be extracted."""
    zone = {
        "data": {
            "timeSeries": {
                "dataSets": [
                    {"id": "operation_mode", "data": [{"value": "COOLING"}]}
                ]
            }
        }
    }
    datasets = get_zone_time_series_datasets(zone)
    assert "operation_mode" in datasets


def test_get_zone_time_series_datasets_returns_empty_for_empty_zone() -> None:
    """An empty zone should return an empty datasets dict."""
    assert get_zone_time_series_datasets({}) == {}


def test_get_zone_time_series_datasets_skips_items_without_id() -> None:
    """Dataset items without an id should be skipped."""
    zone = {
        "timeSeries": {
            "dataSets": [
                {"data": [{"value": 1}]},
                {"id": "compressor_active", "data": [{"value": True}]},
            ]
        }
    }
    datasets = get_zone_time_series_datasets(zone)
    assert list(datasets.keys()) == ["compressor_active"]


def test_get_zone_time_series_datasets_reads_nested_datasets_within_item() -> None:
    """Nested dataSets inside an item should also be extracted."""
    zone = {
        "timeSeries": {
            "datasets": [
                {
                    "id": "outer",
                    "dataSets": [
                        {"id": "inner_dataset", "data": [{"value": 1}]},
                    ],
                }
            ]
        }
    }
    datasets = get_zone_time_series_datasets(zone)
    assert "outer" in datasets
    assert "inner_dataset" in datasets


def test_get_zone_time_series_datasets_prefers_datasets_alternative_key() -> None:
    """The lowercase 'datasets' key should work as an alias for 'dataSets'."""
    zone = {
        "timeSeries": {
            "datasets": [
                {"id": "setpoint", "data": [{"value": 22.0}]},
            ]
        }
    }
    datasets = get_zone_time_series_datasets(zone)
    assert "setpoint" in datasets


# ---------------------------------------------------------------------------
# get_dataset_option_label
# ---------------------------------------------------------------------------


def test_get_dataset_option_label_returns_label_for_matching_value() -> None:
    """Should return the label when the option matches the value."""
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
    """Should return None when no option matches the value."""
    dataset = {
        "options": {
            "options": [{"value": 5, "label": "High"}]
        }
    }
    assert get_dataset_option_label(dataset, 99) is None


def test_get_dataset_option_label_returns_none_when_options_absent() -> None:
    """Should return None when the options key is absent."""
    assert get_dataset_option_label({}, 1) is None


# ---------------------------------------------------------------------------
# dataset_is_on
# ---------------------------------------------------------------------------


def test_dataset_is_on_returns_true_for_bool_true() -> None:
    """A boolean True value should return True."""
    assert dataset_is_on("any_id", {"data": True}) is True


def test_dataset_is_on_returns_false_for_bool_false() -> None:
    """A boolean False value should return False."""
    assert dataset_is_on("any_id", {"data": False}) is False


@pytest.mark.parametrize(
    "value",
    ["active", "enabled", "on", "open", "true", "1", "Ja", "yes", "y", "aktiv", "ein"],
)
def test_dataset_is_on_recognizes_truthy_strings(value: str) -> None:
    """Common truthy string values should be recognized as on."""
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
def test_dataset_is_on_recognizes_falsy_strings(value: str) -> None:
    """Common falsy string values should be recognized as off."""
    assert dataset_is_on("any_id", {"data": value}) is False


def test_dataset_is_on_returns_false_for_known_sensor_id_when_no_value() -> None:
    """Known sensor IDs with unresolvable value should default to False."""
    assert dataset_is_on("compressor_active", {"data": "unknown_value"}) is False
    assert dataset_is_on("defrosting_active", {"data": "unknown_value"}) is False
    assert dataset_is_on("filter_sign", {"data": "unknown_value"}) is False


def test_dataset_is_on_coerces_nonzero_integer_to_true() -> None:
    """A nonzero integer without matching options should coerce to True."""
    assert dataset_is_on("any_id", {"data": 5}) is True


def test_dataset_is_on_coerces_zero_integer_to_false() -> None:
    """Zero integer without matching options should coerce to False."""
    assert dataset_is_on("any_id", {"data": 0}) is False


def test_dataset_is_on_with_numeric_enum_option_active_label() -> None:
    """Numeric value matching an 'active' option label should return True."""
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


def test_dataset_is_on_with_numeric_enum_option_inactive_label() -> None:
    """Numeric value matching an 'inactive' option label should return False."""
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
    """${...} template wrappers should be stripped."""
    result = _normalize_enum_token("${dataSets.nova.enumeratedOptions.foo.active}")
    # After stripping and lowercasing, should end with 'active'
    assert result == "active"


def test_normalize_enum_token_trims_dot_path_to_last_segment() -> None:
    """Dot-separated paths should reduce to the final segment."""
    result = _normalize_enum_token("some.path.to.value")
    assert result == "value"


def test_normalize_enum_token_lowercases_and_strips_whitespace() -> None:
    """Values should be lowercased and stripped of surrounding whitespace."""
    result = _normalize_enum_token("  ACTIVE  ")
    assert result == "active"
