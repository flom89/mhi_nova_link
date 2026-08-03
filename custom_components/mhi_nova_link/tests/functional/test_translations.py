"""Functional tests — verify translation files cover all entity strings.

These tests act as contracts: if a translation key is missing the UI will
show a raw key string instead of a human-readable name.
"""

import json
from pathlib import Path


_INTEGRATION_DIR = Path(__file__).resolve().parents[2]


def _load_json(rel_path: str) -> dict:
    with (_INTEGRATION_DIR / rel_path).open(encoding="utf-8") as f:
        return json.load(f)


def _deep_get(data: dict, path: tuple) -> object:
    """Traverse a nested dict by a tuple of keys."""
    node = data
    for key in path:
        node = node[key]
    return node


# All translation paths that must exist in both strings.json and en.json
_REQUIRED_PATHS: list[tuple] = [
    # Config flow
    ("config", "step", "user", "data", "host"),
    ("config", "step", "user", "data", "ssl_fingerprint"),
    # Binary sensors
    ("entity", "binary_sensor", "gateway_update_available", "name"),
    ("entity", "binary_sensor", "indoor_unit_running", "name"),
    ("entity", "binary_sensor", "sequencing_stop", "name"),
    ("entity", "binary_sensor", "sequencing_stop_active", "name"),
    ("entity", "binary_sensor", "system_stop", "name"),
    ("entity", "binary_sensor", "system_fault", "name"),
    ("entity", "binary_sensor", "running", "name"),
    ("entity", "binary_sensor", "available", "name"),
    # Sensors
    ("entity", "sensor", "gateway_software_version", "name"),
    # Select
    ("entity", "select", "louver_position", "name"),
    ("entity", "select", "vane_position", "name"),
    # Indoor unit sensors
    ("entity", "sensor", "indoor_unit_temperature", "name"),
    ("entity", "sensor", "indoor_unit_setpoint", "name"),
    ("entity", "sensor", "indoor_unit_operation_mode", "name"),
    ("entity", "sensor", "indoor_unit_fan_speed", "name"),
    # Zone sensors
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


def test_strings_json_contains_required_keys() -> None:
    """strings.json must contain all required translation keys."""
    strings = _load_json("strings.json")
    for path in _REQUIRED_PATHS:
        try:
            value = _deep_get(strings, path)
            assert value is not None, f"strings.json key {path!r} is None"
        except KeyError as exc:
            raise AssertionError(
                f"strings.json is missing required key: {path!r}"
            ) from exc


def test_en_translations_contain_required_keys() -> None:
    """translations/en.json must contain all required translation keys."""
    translations = _load_json("translations/en.json")
    for path in _REQUIRED_PATHS:
        try:
            value = _deep_get(translations, path)
            assert value is not None, f"translations/en.json key {path!r} is None"
        except KeyError as exc:
            raise AssertionError(
                f"translations/en.json is missing required key: {path!r}"
            ) from exc


def test_strings_and_translations_agree_on_config_step_keys() -> None:
    """Both files must expose the same set of config step data fields."""
    strings = _load_json("strings.json")
    translations = _load_json("translations/en.json")

    strings_keys = set(
        strings.get("config", {}).get("step", {}).get("user", {}).get("data", {}).keys()
    )
    en_keys = set(
        translations.get("config", {}).get("step", {}).get("user", {}).get("data", {}).keys()
    )

    assert strings_keys == en_keys, (
        f"Config step data keys differ:\n"
        f"  strings.json only: {strings_keys - en_keys}\n"
        f"  en.json only:      {en_keys - strings_keys}"
    )
