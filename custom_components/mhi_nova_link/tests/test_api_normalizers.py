"""Comprehensive unit tests for all normalize_* and build_* functions in api.py."""

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.mhi_nova_link.api import (
    InvalidAuth,
    _get_time_series_update_interval,
    _raise_if_auth_rejected,
    build_time_series_identifiers,
    build_time_series_period,
    normalize_gateway_update_payload,
    normalize_gpio_active_high_payload,
    normalize_gpios_payload,
    normalize_notifications_payload,
    normalize_ssl_fingerprint,
    normalize_time_series_payload,
    normalize_zones_payload,
)
from custom_components.mhi_nova_link.const import DEFAULT_TIME_SERIES_POLL_INTERVAL

# ---------------------------------------------------------------------------
# normalize_ssl_fingerprint
# ---------------------------------------------------------------------------


class TestNormalizeSslFingerprint:
    """Tests for normalize_ssl_fingerprint."""

    def test_none_returns_none(self) -> None:
        assert normalize_ssl_fingerprint(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert normalize_ssl_fingerprint("") is None
        assert normalize_ssl_fingerprint("   ") is None

    def test_valid_lowercase_hex_is_returned_unchanged(self) -> None:
        fp = "a" * 64
        assert normalize_ssl_fingerprint(fp) == fp

    def test_uppercase_is_lowercased(self) -> None:
        fp = "A" * 64
        assert normalize_ssl_fingerprint(fp) == "a" * 64

    def test_colon_separated_fingerprint_is_normalized(self) -> None:
        # 32 pairs of "aa" joined with colons
        raw = ":".join(["aa"] * 32)
        assert normalize_ssl_fingerprint(raw) == "aa" * 32

    def test_space_separated_fingerprint_is_normalized(self) -> None:
        raw = " ".join(["aa"] * 32)
        assert normalize_ssl_fingerprint(raw) == "aa" * 32

    def test_too_short_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="64 hex"):
            normalize_ssl_fingerprint("abc")

    def test_too_long_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="64 hex"):
            normalize_ssl_fingerprint("a" * 65)

    def test_non_hex_characters_raise_value_error(self) -> None:
        with pytest.raises(ValueError):
            normalize_ssl_fingerprint("g" * 64)


# ---------------------------------------------------------------------------
# _raise_if_auth_rejected
# ---------------------------------------------------------------------------


class TestRaiseIfAuthRejected:
    """Tests for _raise_if_auth_rejected."""

    def test_401_raises_invalid_auth(self) -> None:
        with pytest.raises(InvalidAuth):
            _raise_if_auth_rejected(401, "Unauthorized", "TestOp")

    def test_403_raises_invalid_auth(self) -> None:
        with pytest.raises(InvalidAuth):
            _raise_if_auth_rejected(403, "Forbidden", "TestOp")

    def test_200_does_not_raise(self) -> None:
        _raise_if_auth_rejected(200, "OK", "TestOp")

    def test_500_does_not_raise(self) -> None:
        _raise_if_auth_rejected(500, "Server Error", "TestOp")


# ---------------------------------------------------------------------------
# _get_time_series_update_interval
# ---------------------------------------------------------------------------


class TestGetTimeSeriesUpdateInterval:
    """Tests for _get_time_series_update_interval."""

    def test_none_returns_default(self) -> None:
        assert _get_time_series_update_interval(None) == DEFAULT_TIME_SERIES_POLL_INTERVAL

    def test_integer_value_is_used(self) -> None:
        assert _get_time_series_update_interval(120) == 120

    def test_string_integer_is_parsed(self) -> None:
        assert _get_time_series_update_interval("90") == 90

    def test_zero_is_clamped_to_one(self) -> None:
        assert _get_time_series_update_interval(0) == 1

    def test_negative_is_clamped_to_one(self) -> None:
        assert _get_time_series_update_interval(-10) == 1

    def test_invalid_string_returns_default(self) -> None:
        assert _get_time_series_update_interval("not_a_number") == DEFAULT_TIME_SERIES_POLL_INTERVAL

    def test_env_var_is_read_when_none_provided(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NOVA_RC_TIME_SERIES_UPDATE_INTERVAL_SECONDS", "45")
        assert _get_time_series_update_interval(None) == 45

    def test_configured_value_takes_precedence_over_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NOVA_RC_TIME_SERIES_UPDATE_INTERVAL_SECONDS", "999")
        assert _get_time_series_update_interval(60) == 60


# ---------------------------------------------------------------------------
# build_time_series_period
# ---------------------------------------------------------------------------


class TestBuildTimeSeriesPeriod:
    """Tests for build_time_series_period."""

    def test_returns_start_and_end_keys(self) -> None:
        period = build_time_series_period()
        assert "startDate" in period
        assert "endDate" in period

    def test_end_is_approximately_now(self) -> None:
        before = datetime.now(UTC).replace(microsecond=0)
        period = build_time_series_period()
        after = datetime.now(UTC)
        # Parse the endDate string back to check it's within expected range
        end_str = period["endDate"].replace("Z", "+00:00")
        end = datetime.fromisoformat(end_str)
        # Allow one-second tolerance as the function truncates microseconds
        assert before - timedelta(seconds=1) <= end <= after

    def test_default_lookback_is_30_days(self) -> None:
        period = build_time_series_period()
        start_str = period["startDate"].replace("Z", "+00:00")
        end_str = period["endDate"].replace("Z", "+00:00")
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
        delta = end - start
        assert abs(delta.days - 30) <= 1  # allow ±1 day for timing

    def test_custom_lookback_is_respected(self) -> None:
        period = build_time_series_period(lookback=timedelta(days=7))
        start_str = period["startDate"].replace("Z", "+00:00")
        end_str = period["endDate"].replace("Z", "+00:00")
        delta = datetime.fromisoformat(end_str) - datetime.fromisoformat(start_str)
        assert abs(delta.days - 7) <= 1

    def test_timestamps_end_with_z(self) -> None:
        period = build_time_series_period()
        assert period["startDate"].endswith("Z")
        assert period["endDate"].endswith("Z")


# ---------------------------------------------------------------------------
# build_time_series_identifiers
# ---------------------------------------------------------------------------


class TestBuildTimeSeriesIdentifiers:
    """Tests for build_time_series_identifiers."""

    def test_missing_zone_id_returns_empty(self) -> None:
        assert build_time_series_identifiers({}) == []

    def test_outdoor_ids_use_zone_reference(self) -> None:
        ids = build_time_series_identifiers({"zoneId": 5, "indoorUnits": []})
        outdoor = [i for i in ids if i["reference"].startswith("/outdoor_unit/")]
        assert all(i["reference"] == "/outdoor_unit/5" for i in outdoor)

    def test_indoor_ids_use_indoor_unit_reference(self) -> None:
        ids = build_time_series_identifiers({"zoneId": 1, "indoorUnits": [{"indoorUnitId": 3}]})
        indoor = [i for i in ids if i["reference"] == "/indoor_unit/3"]
        assert len(indoor) > 0

    def test_zone_id_also_included_as_indoor_reference(self) -> None:
        ids = build_time_series_identifiers({"zoneId": 2, "indoorUnits": []})
        indoor = [i for i in ids if i["reference"] == "/indoor_unit/2"]
        assert len(indoor) > 0

    def test_duplicate_indoor_unit_ids_are_deduplicated(self) -> None:
        ids = build_time_series_identifiers(
            {
                "zoneId": 1,
                "indoorUnits": [{"indoorUnitId": 1}, {"indoorUnitId": 1}],
            }
        )
        pairs = [(i["reference"], i["id"]) for i in ids]
        assert len(pairs) == len(set(pairs))

    def test_none_indoor_unit_id_is_skipped(self) -> None:
        ids = build_time_series_identifiers({"zoneId": 1, "indoorUnits": [{"indoorUnitId": None}]})
        assert all(i["reference"] != "/indoor_unit/None" for i in ids)

    def test_ou_dataset_ids_map_to_outdoor_reference(self) -> None:
        ids = build_time_series_identifiers({"zoneId": 4, "indoorUnits": []})
        ou_ids = {i["id"] for i in ids if i["id"].startswith("ou_")}
        assert "ou_indication_air_temp" in ou_ids
        ou_refs = {i["reference"] for i in ids if i["id"].startswith("ou_")}
        assert ou_refs == {"/outdoor_unit/4"}


# ---------------------------------------------------------------------------
# normalize_zones_payload
# ---------------------------------------------------------------------------


class TestNormalizeZonesPayload:
    """Tests for normalize_zones_payload."""

    def test_empty_response_returns_empty_list(self) -> None:
        assert normalize_zones_payload({}) == []

    def test_zones_list_is_filtered_by_typename(self) -> None:
        payload = {
            "data": {
                "xybus": {
                    "zones": [
                        {"__typename": "XYBusZone", "zoneId": 1},
                        {"__typename": "OfflineZone", "zoneId": 2},
                        {"__typename": "XYBusZone", "zoneId": 3},
                    ]
                }
            }
        }
        result = normalize_zones_payload(payload)
        assert len(result) == 2
        assert all(z["__typename"] == "XYBusZone" for z in result)

    def test_single_zone_response_is_handled(self) -> None:
        payload = {
            "data": {"xybus": {"zone": {"__typename": "XYBusZone", "zoneId": 7, "name": "Office"}}}
        }
        result = normalize_zones_payload(payload)
        assert len(result) == 1
        assert result[0]["zoneId"] == 7

    def test_unavailable_zone_is_preserved(self) -> None:
        payload = {
            "data": {
                "xybus": {
                    "zones": [
                        {
                            "__typename": "XYBusZone",
                            "zoneId": 7,
                            "available": False,
                        }
                    ]
                }
            }
        }
        result = normalize_zones_payload(payload)
        assert len(result) == 1
        assert result[0]["available"] is False

    def test_non_dict_items_in_zones_are_skipped(self) -> None:
        payload = {
            "data": {
                "xybus": {
                    "zones": [
                        {"__typename": "XYBusZone", "zoneId": 1},
                        "not_a_dict",
                        None,
                    ]
                }
            }
        }
        result = normalize_zones_payload(payload)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# normalize_notifications_payload
# ---------------------------------------------------------------------------


class TestNormalizeNotificationsPayload:
    """Tests for normalize_notifications_payload."""

    def test_empty_response_returns_empty_notifications_and_errors(self) -> None:
        result = normalize_notifications_payload({})
        assert result["notifications"] == []
        assert result["errors"] == []

    def test_active_notifications_are_extracted(self) -> None:
        payload = {
            "data": {
                "notification": {
                    "notifications": [
                        {"notificationId": 1, "active": True},
                        {"notificationId": 2, "active": False},
                        {"notificationId": 3, "active": True},
                    ],
                    "errors": [],
                    "notificationCount": 2,
                    "sources": None,
                }
            }
        }
        result = normalize_notifications_payload(payload)
        assert len(result["notifications"]) == 2
        assert all(n["active"] is True for n in result["notifications"])

    def test_errors_with_priority_are_extracted(self) -> None:
        payload = {
            "data": {
                "notification": {
                    "notifications": [],
                    "errors": [
                        {"name": "E01", "priority": 1},
                        {"name": "E02", "priority": None},
                        {"name": "E03", "priority": 2},
                    ],
                    "notificationCount": 0,
                }
            }
        }
        result = normalize_notifications_payload(payload)
        assert len(result["errors"]) == 2

    def test_notification_count_is_preserved(self) -> None:
        payload = {
            "data": {
                "notification": {
                    "notifications": [],
                    "errors": [],
                    "notificationCount": 5,
                }
            }
        }
        result = normalize_notifications_payload(payload)
        assert result["notification_count"] == 5

    def test_non_dict_notification_value_returns_empty(self) -> None:
        payload = {"data": {"notification": "invalid"}}
        assert normalize_notifications_payload(payload) == {}


# ---------------------------------------------------------------------------
# normalize_gpios_payload
# ---------------------------------------------------------------------------


class TestNormalizeGpiosPayload:
    """Tests for normalize_gpios_payload."""

    def test_empty_response_returns_empty_dict(self) -> None:
        assert normalize_gpios_payload({}) == {}

    def test_gpio_states_are_mapped_by_function(self) -> None:
        payload = {
            "data": {
                "gpio": {
                    "gpios": [
                        {"function": "FREE_COOLING", "value": True},
                        {"function": "SYSTEM_STOP", "value": False},
                    ]
                }
            }
        }
        result = normalize_gpios_payload(payload)
        assert result["FREE_COOLING"] is True
        assert result["SYSTEM_STOP"] is False

    def test_items_without_function_are_skipped(self) -> None:
        payload = {
            "data": {
                "gpio": {
                    "gpios": [
                        {"function": None, "value": True},
                        {"function": "VALID", "value": False},
                    ]
                }
            }
        }
        result = normalize_gpios_payload(payload)
        assert list(result.keys()) == ["VALID"]

    def test_non_dict_items_in_gpios_are_skipped(self) -> None:
        payload = {
            "data": {
                "gpio": {
                    "gpios": [
                        "not_a_dict",
                        {"function": "VALID", "value": True},
                    ]
                }
            }
        }
        result = normalize_gpios_payload(payload)
        assert result == {"VALID": True}

    def test_value_is_coerced_to_bool(self) -> None:
        payload = {
            "data": {
                "gpio": {
                    "gpios": [
                        {"function": "FLAG", "value": 1},
                        {"function": "ZERO", "value": 0},
                    ]
                }
            }
        }
        result = normalize_gpios_payload(payload)
        assert result["FLAG"] is True
        assert result["ZERO"] is False


class TestNormalizeGpioActiveHighPayload:
    """Tests for normalize_gpio_active_high_payload."""

    def test_empty_response_returns_empty_dict(self) -> None:
        assert normalize_gpio_active_high_payload({}) == {}

    def test_gpio_active_high_states_are_mapped_by_function(self) -> None:
        payload = {
            "data": {
                "gpio": {
                    "gpios": [
                        {"function": "FREE_COOLING", "activeHigh": True},
                        {"function": "SYSTEM_STOP", "activeHigh": False},
                    ]
                }
            }
        }
        result = normalize_gpio_active_high_payload(payload)
        assert result["FREE_COOLING"] is True
        assert result["SYSTEM_STOP"] is False

    def test_items_without_active_high_are_skipped(self) -> None:
        payload = {
            "data": {
                "gpio": {
                    "gpios": [
                        {"function": "MISSING"},
                        {"function": "VALID", "activeHigh": True},
                    ]
                }
            }
        }
        result = normalize_gpio_active_high_payload(payload)
        assert result == {"VALID": True}


# ---------------------------------------------------------------------------
# normalize_time_series_payload
# ---------------------------------------------------------------------------


class TestNormalizeTimeSeriesPayload:
    """Tests for normalize_time_series_payload."""

    def test_empty_response_returns_empty_dict(self) -> None:
        assert normalize_time_series_payload({}) == {}

    def test_datasets_are_keyed_by_id(self) -> None:
        payload = {
            "data": {
                "timeSeries": {
                    "dataSetsWithData": [
                        {"id": "compressor_active", "data": []},
                        {"id": "fan_speed", "data": [{"timestamp": "t", "value": 2}]},
                    ]
                }
            }
        }
        result = normalize_time_series_payload(payload)
        assert "compressor_active" in result
        assert "fan_speed" in result

    def test_falls_back_to_dataSets_key(self) -> None:
        payload = {
            "data": {
                "timeSeries": {
                    "dataSets": [
                        {"id": "setpoint", "data": []},
                    ]
                }
            }
        }
        result = normalize_time_series_payload(payload)
        assert "setpoint" in result

    def test_items_without_id_are_skipped(self) -> None:
        payload = {
            "data": {
                "timeSeries": {
                    "dataSetsWithData": [
                        {"id": None, "data": []},
                        {"data": []},
                        {"id": "valid_id", "data": []},
                    ]
                }
            }
        }
        result = normalize_time_series_payload(payload)
        assert list(result.keys()) == ["valid_id"]

    def test_non_list_datasets_returns_empty(self) -> None:
        payload = {"data": {"timeSeries": {"dataSetsWithData": "not_a_list"}}}
        assert normalize_time_series_payload(payload) == {}


# ---------------------------------------------------------------------------
# normalize_gateway_update_payload
# ---------------------------------------------------------------------------


class TestNormalizeGatewayUpdatePayload:
    """Tests for normalize_gateway_update_payload."""

    def test_empty_response_returns_all_none_fields(self) -> None:
        result = normalize_gateway_update_payload({})
        assert result["installed_version"] is None
        assert result["available_version"] is None
        assert result["update_available"] is False

    def test_installed_version_is_extracted(self) -> None:
        payload = {
            "data": {
                "system": {
                    "information": {
                        "installedVersion": {"asString": "3.2.5"},
                        "installedBundleDescription": "Bundle A",
                        "installedBundleBuild": "build-1",
                    }
                },
                "update": {"cloud": {}},
            }
        }
        result = normalize_gateway_update_payload(payload)
        assert result["installed_version"] == "3.2.5"
        assert result["installed_bundle_description"] == "Bundle A"
        assert result["installed_bundle_build"] == "build-1"

    def test_available_version_triggers_update_available_flag(self) -> None:
        payload = {
            "data": {
                "system": {"information": {}},
                "update": {
                    "cloud": {
                        "availableSoftwareRelease": {"version": {"asString": "3.3.0"}},
                        "settings": {
                            "automaticCheck": True,
                            "automaticInstall": False,
                        },
                    }
                },
            }
        }
        result = normalize_gateway_update_payload(payload)
        assert result["available_version"] == "3.3.0"
        assert result["update_available"] is True
        assert result["automatic_check"] is True
        assert result["automatic_install"] is False

    def test_no_available_version_means_no_update(self) -> None:
        payload = {
            "data": {
                "system": {"information": {}},
                "update": {"cloud": {"availableSoftwareRelease": {}}},
            }
        }
        result = normalize_gateway_update_payload(payload)
        assert result["update_available"] is False
        assert result["available_version"] is None

    def test_non_dict_system_is_handled_gracefully(self) -> None:
        payload: dict[str, object] = {"data": {"system": None, "update": {}}}
        result = normalize_gateway_update_payload(payload)
        assert result["installed_version"] is None
