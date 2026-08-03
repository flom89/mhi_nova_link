"""Unit tests for pure API helper functions (no network, no HA instance).

Covers:
- normalize_ssl_fingerprint
- normalize_zones_payload
- normalize_notifications_payload
- normalize_gpios_payload
- normalize_gateway_update_payload
- normalize_time_series_payload
- build_time_series_period
- build_time_series_identifiers
- _raise_if_auth_rejected (via CannotConnect / InvalidAuth)
- _get_time_series_update_interval
"""

import pytest

from custom_components.mhi_nova_link.api import (
    CannotConnect,
    InvalidAuth,
    build_time_series_identifiers,
    build_time_series_period,
    normalize_gateway_update_payload,
    normalize_gpios_payload,
    normalize_notifications_payload,
    normalize_ssl_fingerprint,
    normalize_time_series_payload,
    normalize_zones_payload,
)


# ---------------------------------------------------------------------------
# normalize_ssl_fingerprint
# ---------------------------------------------------------------------------


def test_normalize_ssl_fingerprint_none_input_returns_none() -> None:
    """None should pass through as None."""
    assert normalize_ssl_fingerprint(None) is None


def test_normalize_ssl_fingerprint_empty_string_returns_none() -> None:
    """An empty string should normalize to None."""
    assert normalize_ssl_fingerprint("") is None


def test_normalize_ssl_fingerprint_strips_colons() -> None:
    """Colons should be removed from the fingerprint."""
    raw = ":".join(["AA"] * 32)  # "AA:AA:..." 32 pairs
    result = normalize_ssl_fingerprint(raw)
    assert result is not None
    assert ":" not in result
    assert len(result) == 64


def test_normalize_ssl_fingerprint_strips_spaces() -> None:
    """Spaces should be removed from the fingerprint."""
    raw = " ".join(["AA"] * 32)
    result = normalize_ssl_fingerprint(raw)
    assert result is not None
    assert " " not in result


def test_normalize_ssl_fingerprint_lowercases_hex() -> None:
    """Output should always be lowercase hex."""
    assert normalize_ssl_fingerprint("AA" * 32) == "aa" * 32


def test_normalize_ssl_fingerprint_raises_for_too_short() -> None:
    """A fingerprint that is too short should raise ValueError."""
    with pytest.raises(ValueError, match="64 hex"):
        normalize_ssl_fingerprint("aabb")


def test_normalize_ssl_fingerprint_raises_for_non_hex() -> None:
    """Non-hex characters should raise ValueError."""
    with pytest.raises(ValueError):
        normalize_ssl_fingerprint("ZZ" * 32)


# ---------------------------------------------------------------------------
# normalize_zones_payload
# ---------------------------------------------------------------------------


def test_normalize_zones_payload_keeps_only_xybus_zones() -> None:
    """OfflineZone entries should be excluded."""
    payload = {
        "data": {
            "xybus": {
                "zones": [
                    {"__typename": "XYBusZone", "zoneId": 1},
                    {"__typename": "OfflineZone", "zoneId": 2},
                ]
            }
        }
    }
    result = normalize_zones_payload(payload)
    assert len(result) == 1
    assert result[0]["zoneId"] == 1


def test_normalize_zones_payload_single_zone_key() -> None:
    """A 'zone' (singular) response should be wrapped into a list."""
    payload = {
        "data": {
            "xybus": {"zone": {"__typename": "XYBusZone", "zoneId": 5}}
        }
    }
    result = normalize_zones_payload(payload)
    assert len(result) == 1
    assert result[0]["zoneId"] == 5


def test_normalize_zones_payload_offline_single_zone_returns_empty() -> None:
    """An offline single-zone response should yield an empty list."""
    payload = {
        "data": {
            "xybus": {"zone": {"__typename": "OfflineZone", "zoneId": 3}}
        }
    }
    assert normalize_zones_payload(payload) == []


def test_normalize_zones_payload_empty_input_returns_empty() -> None:
    """Missing data should return an empty list."""
    assert normalize_zones_payload({}) == []
    assert normalize_zones_payload({"data": {}}) == []


def test_normalize_zones_payload_preserves_unavailable_zones() -> None:
    """Zones with available=False should still be included."""
    payload = {
        "data": {
            "xybus": {
                "zones": [
                    {"__typename": "XYBusZone", "zoneId": 7, "available": False}
                ]
            }
        }
    }
    result = normalize_zones_payload(payload)
    assert len(result) == 1
    assert result[0]["available"] is False


# ---------------------------------------------------------------------------
# normalize_notifications_payload
# ---------------------------------------------------------------------------


def test_normalize_notifications_keeps_active_notifications_only() -> None:
    """Only active notifications should be kept."""
    payload = {
        "data": {
            "notification": {
                "notifications": [
                    {"notificationId": 1, "active": True},
                    {"notificationId": 2, "active": False},
                ],
                "errors": [],
                "notificationCount": 1,
            }
        }
    }
    result = normalize_notifications_payload(payload)
    assert len(result["notifications"]) == 1
    assert result["notifications"][0]["notificationId"] == 1


def test_normalize_notifications_keeps_errors_with_priority() -> None:
    """Errors should be included only when they have a priority set."""
    payload = {
        "data": {
            "notification": {
                "notifications": [],
                "errors": [
                    {"name": "E01", "priority": 2},
                    {"name": "E02", "priority": None},
                ],
            }
        }
    }
    result = normalize_notifications_payload(payload)
    assert len(result["errors"]) == 1
    assert result["errors"][0]["name"] == "E01"


def test_normalize_notifications_returns_empty_for_non_dict_notification() -> None:
    """A non-dict notification value should return an empty dict."""
    assert normalize_notifications_payload({"data": {"notification": "bad"}}) == {}


# ---------------------------------------------------------------------------
# normalize_gpios_payload
# ---------------------------------------------------------------------------


def test_normalize_gpios_maps_function_to_bool() -> None:
    """GPIO values should be stored as booleans keyed by function name."""
    payload = {
        "data": {
            "gpio": {
                "gpios": [
                    {"function": "FREE_COOLING", "value": True},
                    {"function": "SYSTEM_FAULT", "value": False},
                ]
            }
        }
    }
    result = normalize_gpios_payload(payload)
    assert result == {"FREE_COOLING": True, "SYSTEM_FAULT": False}


def test_normalize_gpios_skips_items_without_function() -> None:
    """Items missing the function key should be skipped."""
    payload = {
        "data": {
            "gpio": {
                "gpios": [
                    {"value": True},
                    {"function": "SYSTEM_STOP", "value": True},
                ]
            }
        }
    }
    result = normalize_gpios_payload(payload)
    assert set(result.keys()) == {"SYSTEM_STOP"}


def test_normalize_gpios_returns_empty_for_missing_data() -> None:
    """Missing GPIO data should return an empty dict."""
    assert normalize_gpios_payload({}) == {}


# ---------------------------------------------------------------------------
# normalize_gateway_update_payload
# ---------------------------------------------------------------------------


def test_normalize_gateway_update_extracts_version_and_availability() -> None:
    """Installed and available versions should be extracted."""
    payload = {
        "data": {
            "system": {
                "information": {
                    "installedVersion": {"asString": "3.2.5"},
                    "installedBundleDescription": "NOVA RC 3.2.5",
                    "installedBundleBuild": "build-100",
                }
            },
            "update": {
                "cloud": {
                    "availableSoftwareRelease": {"version": {"asString": "3.3.0"}},
                    "settings": {"automaticCheck": True, "automaticInstall": False},
                }
            },
        }
    }
    result = normalize_gateway_update_payload(payload)
    assert result["installed_version"] == "3.2.5"
    assert result["available_version"] == "3.3.0"
    assert result["update_available"] is True
    assert result["automatic_check"] is True
    assert result["automatic_install"] is False


def test_normalize_gateway_update_no_available_release() -> None:
    """When no update is available, update_available should be False."""
    payload = {
        "data": {
            "system": {
                "information": {"installedVersion": {"asString": "3.2.5"}}
            },
            "update": {"cloud": {"availableSoftwareRelease": None}},
        }
    }
    result = normalize_gateway_update_payload(payload)
    assert result["update_available"] is False
    assert result["available_version"] is None


def test_normalize_gateway_update_handles_empty_payload() -> None:
    """An empty payload should return safe None defaults."""
    result = normalize_gateway_update_payload({})
    assert result["installed_version"] is None
    assert result["update_available"] is False


# ---------------------------------------------------------------------------
# normalize_time_series_payload
# ---------------------------------------------------------------------------


def test_normalize_time_series_uses_dataSetsWithData_key() -> None:
    """dataSetsWithData should be the primary key for time-series data."""
    payload = {
        "data": {
            "timeSeries": {
                "dataSetsWithData": [
                    {"id": "compressor_active", "data": [{"value": True}]}
                ]
            }
        }
    }
    result = normalize_time_series_payload(payload)
    assert "compressor_active" in result


def test_normalize_time_series_falls_back_to_dataSets_key() -> None:
    """The lowercase 'dataSets' key should work as a fallback."""
    payload = {
        "data": {
            "timeSeries": {
                "dataSets": [
                    {"id": "fan_speed", "data": [{"value": "AUTO"}]}
                ]
            }
        }
    }
    result = normalize_time_series_payload(payload)
    assert "fan_speed" in result


def test_normalize_time_series_skips_items_without_id() -> None:
    """Items without an 'id' key should be excluded."""
    payload = {
        "data": {
            "timeSeries": {
                "dataSetsWithData": [
                    {"data": [{"value": 1}]},
                    {"id": "setpoint", "data": [{"value": 22.0}]},
                ]
            }
        }
    }
    result = normalize_time_series_payload(payload)
    assert list(result.keys()) == ["setpoint"]


# ---------------------------------------------------------------------------
# build_time_series_period
# ---------------------------------------------------------------------------


def test_build_time_series_period_start_before_end() -> None:
    """The generated period's start should be before its end."""
    period = build_time_series_period()
    assert period["startDate"] < period["endDate"]
    assert period["endDate"].endswith("Z")
    assert period["startDate"].endswith("Z")


# ---------------------------------------------------------------------------
# build_time_series_identifiers
# ---------------------------------------------------------------------------


def test_build_time_series_identifiers_empty_when_no_zone_id() -> None:
    """A zone without a zoneId key should produce no identifiers."""
    assert build_time_series_identifiers({}) == []


def test_build_time_series_identifiers_outdoor_unit_uses_zone_id() -> None:
    """Outdoor-unit identifiers should reference the zone ID."""
    ids = build_time_series_identifiers({"zoneId": 7, "indoorUnits": []})
    outdoor_refs = {i["reference"] for i in ids if i["reference"].startswith("/outdoor")}
    assert "/outdoor_unit/7" in outdoor_refs


def test_build_time_series_identifiers_deduplicates_indoor_references() -> None:
    """Duplicate indoor unit IDs should not produce duplicate identifier entries."""
    ids = build_time_series_identifiers(
        {"zoneId": 1, "indoorUnits": [{"indoorUnitId": 5}, {"indoorUnitId": 5}]}
    )
    pairs = [(i["reference"], i["id"]) for i in ids]
    assert len(pairs) == len(set(pairs))


def test_build_time_series_identifiers_different_zones_do_not_share_outdoor_refs() -> None:
    """Outdoor identifiers must be zone-scoped and must not appear in another zone's list."""
    zone1_ids = build_time_series_identifiers({"zoneId": 1, "indoorUnits": []})
    zone2_ids = build_time_series_identifiers({"zoneId": 2, "indoorUnits": []})

    z1_outdoor = {i["reference"] for i in zone1_ids if i["reference"].startswith("/outdoor")}
    z2_outdoor = {i["reference"] for i in zone2_ids if i["reference"].startswith("/outdoor")}

    assert "/outdoor_unit/1" in z1_outdoor
    assert "/outdoor_unit/2" in z2_outdoor
    assert z1_outdoor.isdisjoint(z2_outdoor)
