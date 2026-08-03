"""Unit and integration tests for the NOVA_RC API client."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
import sys
from types import TracebackType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

# Ensure the custom_components path is resolvable
_integration_dir = Path(__file__).resolve().parents[1]
_config_dir = _integration_dir.parent.parent
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

from custom_components.mhi_nova_link.api import (  # noqa: E402
    CannotConnect,
    InvalidAuth,
    InvalidCertificate,
    NovaRcApiClient,
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


def test_normalize_ssl_fingerprint_returns_none_for_none() -> None:
    """None input should pass through as None."""
    assert normalize_ssl_fingerprint(None) is None


def test_normalize_ssl_fingerprint_returns_none_for_empty_string() -> None:
    """An empty string should normalize to None."""
    assert normalize_ssl_fingerprint("") is None


def test_normalize_ssl_fingerprint_strips_colons_and_spaces() -> None:
    """Colons and spaces should be removed from the fingerprint."""
    raw = "AA:BB:CC" + ":DD" * 29  # 32 pairs = 64 hex chars
    result = normalize_ssl_fingerprint(raw)
    assert result is not None
    assert ":" not in result
    assert result == raw.replace(":", "").lower()


def test_normalize_ssl_fingerprint_lowercases_hex() -> None:
    """Fingerprint characters should be lowercased."""
    raw = "AA" * 32
    result = normalize_ssl_fingerprint(raw)
    assert result == "aa" * 32


def test_normalize_ssl_fingerprint_raises_for_wrong_length() -> None:
    """A fingerprint with the wrong number of characters should raise ValueError."""
    with pytest.raises(ValueError, match="64 hex"):
        normalize_ssl_fingerprint("aabb")


def test_normalize_ssl_fingerprint_raises_for_non_hex() -> None:
    """A fingerprint with non-hex characters should raise ValueError."""
    with pytest.raises(ValueError):
        normalize_ssl_fingerprint("ZZ" * 32)


# ---------------------------------------------------------------------------
# normalize_zones_payload
# ---------------------------------------------------------------------------


def test_normalize_zones_payload_filters_offline_zones() -> None:
    """OfflineZone entries should be excluded from the result."""
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


def test_normalize_zones_payload_handles_single_zone_response() -> None:
    """A single-zone payload (zone key instead of zones) should be handled."""
    payload = {
        "data": {
            "xybus": {
                "zone": {"__typename": "XYBusZone", "zoneId": 5}
            }
        }
    }
    result = normalize_zones_payload(payload)
    assert len(result) == 1
    assert result[0]["zoneId"] == 5


def test_normalize_zones_payload_returns_empty_for_missing_data() -> None:
    """Empty or malformed data should return an empty list."""
    assert normalize_zones_payload({}) == []
    assert normalize_zones_payload({"data": {}}) == []


def test_normalize_zones_payload_returns_empty_when_single_zone_is_offline() -> None:
    """A single offline zone should yield an empty list."""
    payload = {
        "data": {
            "xybus": {
                "zone": {"__typename": "OfflineZone", "zoneId": 3}
            }
        }
    }
    result = normalize_zones_payload(payload)
    assert result == []


# ---------------------------------------------------------------------------
# normalize_notifications_payload
# ---------------------------------------------------------------------------


def test_normalize_notifications_payload_extracts_active_notifications() -> None:
    """Active notifications should be separated from inactive ones."""
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


def test_normalize_notifications_payload_extracts_errors() -> None:
    """Errors with a priority should be included."""
    payload = {
        "data": {
            "notification": {
                "notifications": [],
                "errors": [
                    {"name": "E01", "priority": 1},
                    {"name": "E02", "priority": None},
                ],
            }
        }
    }
    result = normalize_notifications_payload(payload)
    assert len(result["errors"]) == 1
    assert result["errors"][0]["name"] == "E01"


def test_normalize_notifications_payload_returns_empty_for_bad_input() -> None:
    """Malformed notification payload should return an empty dict."""
    result = normalize_notifications_payload({"data": {"notification": "bad"}})
    assert result == {}


# ---------------------------------------------------------------------------
# normalize_gpios_payload
# ---------------------------------------------------------------------------


def test_normalize_gpios_payload_converts_values_to_bool() -> None:
    """GPIO values should be cast to bool."""
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
    assert result["FREE_COOLING"] is True
    assert result["SYSTEM_FAULT"] is False


def test_normalize_gpios_payload_skips_entries_without_function() -> None:
    """GPIO items without a function key should be skipped."""
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


def test_normalize_gpios_payload_returns_empty_for_missing_data() -> None:
    """Missing GPIO data should return an empty dict."""
    assert normalize_gpios_payload({}) == {}


# ---------------------------------------------------------------------------
# normalize_gateway_update_payload
# ---------------------------------------------------------------------------


def test_normalize_gateway_update_payload_extracts_version_and_availability() -> None:
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


def test_normalize_gateway_update_payload_no_available_release() -> None:
    """When no update is available, update_available should be False."""
    payload = {
        "data": {
            "system": {
                "information": {
                    "installedVersion": {"asString": "3.2.5"},
                }
            },
            "update": {"cloud": {"availableSoftwareRelease": None}},
        }
    }
    result = normalize_gateway_update_payload(payload)
    assert result["update_available"] is False
    assert result["available_version"] is None


def test_normalize_gateway_update_payload_handles_empty_payload() -> None:
    """An empty payload should return default None values."""
    result = normalize_gateway_update_payload({})
    assert result["installed_version"] is None
    assert result["update_available"] is False


# ---------------------------------------------------------------------------
# normalize_time_series_payload
# ---------------------------------------------------------------------------


def test_normalize_time_series_payload_uses_dataSets_fallback_key() -> None:
    """The dataSets fallback key should work the same as dataSetsWithData."""
    payload = {
        "data": {
            "timeSeries": {
                "dataSets": [
                    {"id": "operation_mode", "data": [{"value": "COOLING"}]}
                ]
            }
        }
    }
    result = normalize_time_series_payload(payload)
    assert "operation_mode" in result


def test_normalize_time_series_payload_skips_items_without_id() -> None:
    """Dataset items without an 'id' key should be skipped."""
    payload = {
        "data": {
            "timeSeries": {
                "dataSetsWithData": [
                    {"data": [{"value": 1}]},
                    {"id": "fan_speed", "data": [{"value": "AUTO"}]},
                ]
            }
        }
    }
    result = normalize_time_series_payload(payload)
    assert list(result.keys()) == ["fan_speed"]


# ---------------------------------------------------------------------------
# build_time_series_period
# ---------------------------------------------------------------------------


def test_build_time_series_period_returns_start_before_end() -> None:
    """The generated period should have start before end."""
    period = build_time_series_period()
    assert period["startDate"] < period["endDate"]
    assert period["endDate"].endswith("Z")
    assert period["startDate"].endswith("Z")


# ---------------------------------------------------------------------------
# build_time_series_identifiers
# ---------------------------------------------------------------------------


def test_build_time_series_identifiers_returns_empty_when_no_zone_id() -> None:
    """A zone dict without a zoneId should produce no identifiers."""
    assert build_time_series_identifiers({}) == []


def test_build_time_series_identifiers_includes_outdoor_unit_ids() -> None:
    """Outdoor-unit identifiers should use the zone ID as reference."""
    ids = build_time_series_identifiers({"zoneId": 7, "indoorUnits": []})
    outdoor_refs = {
        item["reference"] for item in ids if item["reference"].startswith("/outdoor")
    }
    assert "/outdoor_unit/7" in outdoor_refs


# ---------------------------------------------------------------------------
# Fake HTTP helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal fake aiohttp response."""

    def __init__(
        self,
        status: int = 200,
        body: dict[str, Any] | None = None,
        text_body: str | None = None,
    ) -> None:
        """Initialize the fake response."""
        self.status = status
        self._body = body or {}
        self._text = text_body or ""

    async def text(self) -> str:
        """Return response text."""
        return self._text

    async def json(self) -> dict[str, Any]:
        """Return response JSON body."""
        return self._body


class _FakeSession:
    """Fake aiohttp.ClientSession that returns a preset response."""

    def __init__(self, response: _FakeResponse) -> None:
        """Initialize with a response."""
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> "_FakeContextManager":
        """Record the call and return a context manager."""
        self.calls.append({"url": url, **kwargs})
        return _FakeContextManager(self.response)


class _FakeContextManager:
    """Async context manager wrapping a _FakeResponse."""

    def __init__(self, response: _FakeResponse) -> None:
        """Initialize."""
        self._response = response

    async def __aenter__(self) -> _FakeResponse:
        """Enter the context."""
        return self._response

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the context."""


def _make_client(session: _FakeSession, host: str = "gateway.local") -> NovaRcApiClient:
    """Create a NovaRcApiClient with a fake session."""
    return NovaRcApiClient(host=host, session=session)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# NovaRcApiClient.async_get_zones
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_get_zones_returns_zones_on_success() -> None:
    """async_get_zones should return a list of XYBusZone dicts on HTTP 200."""
    body = {
        "data": {
            "xybus": {
                "zones": [{"__typename": "XYBusZone", "zoneId": 1, "available": True}]
            }
        }
    }
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    # Disable time-series attachment to keep test focused.
    client._time_series_update_interval = None  # type: ignore[assignment]
    with patch.object(client, "_attach_time_series_data", new_callable=AsyncMock):
        zones = await client.async_get_zones()
    assert len(zones) == 1
    assert zones[0]["zoneId"] == 1


@pytest.mark.asyncio
async def test_async_get_zones_raises_invalid_auth_on_401() -> None:
    """async_get_zones should raise InvalidAuth when the gateway returns 401."""
    session = _FakeSession(_FakeResponse(401, text_body="Unauthorized"))
    client = _make_client(session)
    with pytest.raises(InvalidAuth):
        await client.async_get_zones()


@pytest.mark.asyncio
async def test_async_get_zones_raises_cannot_connect_on_500() -> None:
    """async_get_zones should raise CannotConnect when the gateway returns a 5xx error."""
    session = _FakeSession(_FakeResponse(500, text_body="Server Error"))
    client = _make_client(session)
    with pytest.raises(CannotConnect):
        await client.async_get_zones()


@pytest.mark.asyncio
async def test_async_get_zones_raises_cannot_connect_on_graphql_error() -> None:
    """async_get_zones should raise CannotConnect when the response contains GraphQL errors."""
    body = {"errors": [{"message": "some error"}]}
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    with pytest.raises(CannotConnect):
        await client.async_get_zones()


@pytest.mark.asyncio
async def test_async_get_zones_raises_cannot_connect_on_client_error() -> None:
    """async_get_zones should raise CannotConnect when an aiohttp error occurs."""
    session = MagicMock()
    session.post.side_effect = aiohttp.ClientError("network error")
    client = _make_client(session)
    with pytest.raises(CannotConnect):
        await client.async_get_zones()


@pytest.mark.asyncio
async def test_async_get_zones_raises_invalid_certificate_on_tls_mismatch() -> None:
    """async_get_zones should raise InvalidCertificate on a TLS fingerprint mismatch."""
    session = MagicMock()
    session.post.side_effect = (
        aiohttp.client_exceptions.ServerFingerprintMismatch(b"", b"", "", 0)
    )
    client = _make_client(session)
    with pytest.raises(InvalidCertificate):
        await client.async_get_zones()


# ---------------------------------------------------------------------------
# NovaRcApiClient.async_get_notifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_get_notifications_returns_normalized_payload() -> None:
    """async_get_notifications should return a normalized notification dict."""
    body = {
        "data": {
            "notification": {
                "notifications": [{"notificationId": 99, "active": True}],
                "errors": [],
                "notificationCount": 1,
            }
        }
    }
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    result = await client.async_get_notifications()
    assert len(result["notifications"]) == 1


@pytest.mark.asyncio
async def test_async_get_notifications_returns_empty_on_http_error() -> None:
    """A non-200 HTTP status should return an empty dict (non-fatal)."""
    session = _FakeSession(_FakeResponse(503, text_body="unavailable"))
    client = _make_client(session)
    result = await client.async_get_notifications()
    assert result == {}


@pytest.mark.asyncio
async def test_async_get_notifications_returns_empty_on_graphql_error() -> None:
    """GraphQL errors in the notification response should return an empty dict."""
    body = {"errors": [{"message": "forbidden"}]}
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    result = await client.async_get_notifications()
    assert result == {}


@pytest.mark.asyncio
async def test_async_get_notifications_raises_invalid_auth_on_403() -> None:
    """A 403 response should raise InvalidAuth."""
    session = _FakeSession(_FakeResponse(403, text_body="Forbidden"))
    client = _make_client(session)
    with pytest.raises(InvalidAuth):
        await client.async_get_notifications()


# ---------------------------------------------------------------------------
# NovaRcApiClient.async_get_gpios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_get_gpios_returns_function_state_map() -> None:
    """async_get_gpios should return a function-to-bool mapping."""
    body = {
        "data": {
            "gpio": {
                "gpios": [
                    {"function": "FREE_COOLING", "value": True},
                    {"function": "SYSTEM_STOP", "value": False},
                ]
            }
        }
    }
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    result = await client.async_get_gpios()
    assert result == {"FREE_COOLING": True, "SYSTEM_STOP": False}


@pytest.mark.asyncio
async def test_async_get_gpios_returns_empty_on_http_error() -> None:
    """A non-200 HTTP status should return an empty dict."""
    session = _FakeSession(_FakeResponse(500, text_body="error"))
    client = _make_client(session)
    result = await client.async_get_gpios()
    assert result == {}


# ---------------------------------------------------------------------------
# NovaRcApiClient.async_get_gateway_update_information
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_get_gateway_update_information_returns_version_data() -> None:
    """async_get_gateway_update_information should return parsed version data."""
    body = {
        "data": {
            "system": {
                "information": {
                    "installedVersion": {"asString": "3.2.5"},
                    "installedBundleDescription": "desc",
                    "installedBundleBuild": "100",
                }
            },
            "update": {
                "cloud": {
                    "availableSoftwareRelease": None,
                    "settings": {"automaticCheck": False, "automaticInstall": False},
                }
            },
        }
    }
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    result = await client.async_get_gateway_update_information()
    assert result["installed_version"] == "3.2.5"
    assert result["update_available"] is False


@pytest.mark.asyncio
async def test_async_get_gateway_update_information_returns_empty_on_error() -> None:
    """An HTTP error should return an empty dict."""
    session = _FakeSession(_FakeResponse(503, text_body="down"))
    client = _make_client(session)
    result = await client.async_get_gateway_update_information()
    assert result == {}


# ---------------------------------------------------------------------------
# NovaRcApiClient.async_set_zone_state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_set_zone_state_returns_true_on_success() -> None:
    """A successful mutation should return True."""
    body = {
        "data": {"xybus": {"zone": {"patch": {"id": "job-1", "done": True}}}}
    }
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    result = await client.async_set_zone_state(1, setpoint=22.0)
    assert result is True
    assert len(session.calls) == 1
    assert session.calls[0]["json"]["variables"]["zoneId"] == 1
    assert session.calls[0]["json"]["variables"]["patch"]["setpoint"] == 22.0


@pytest.mark.asyncio
async def test_async_set_zone_state_returns_true_when_no_fields_given() -> None:
    """Calling with no fields to update should return True without making a request."""
    session = _FakeSession(_FakeResponse(200, {}))
    client = _make_client(session)
    result = await client.async_set_zone_state(1)
    assert result is True
    assert len(session.calls) == 0


@pytest.mark.asyncio
async def test_async_set_zone_state_returns_false_on_http_error() -> None:
    """An HTTP error response should return False."""
    session = _FakeSession(_FakeResponse(500, text_body="error"))
    client = _make_client(session)
    result = await client.async_set_zone_state(1, running=True)
    assert result is False


@pytest.mark.asyncio
async def test_async_set_zone_state_returns_false_on_graphql_error() -> None:
    """A GraphQL error in the mutation response should return False."""
    body = {"errors": [{"message": "bad mutation"}]}
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    result = await client.async_set_zone_state(1, running=True)
    assert result is False


@pytest.mark.asyncio
async def test_async_set_zone_state_raises_invalid_auth_on_403() -> None:
    """A 403 response should raise InvalidAuth."""
    session = _FakeSession(_FakeResponse(403, text_body="Forbidden"))
    client = _make_client(session)
    with pytest.raises(InvalidAuth):
        await client.async_set_zone_state(1, running=True)


@pytest.mark.asyncio
async def test_async_set_zone_state_includes_all_patch_fields() -> None:
    """All settable fields should be included in the mutation payload."""
    body = {"data": {"xybus": {"zone": {"patch": {"id": "j2", "done": False}}}}}
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    await client.async_set_zone_state(
        3,
        running=True,
        setpoint=21.0,
        operation_mode="COOLING",
        fan_speed="HIGH",
        louver_position="AUTO",
        vane_position="POSITION_1",
        flap3d_auto=False,
    )
    patch_data = session.calls[0]["json"]["variables"]["patch"]
    assert patch_data["running"] is True
    assert patch_data["setpoint"] == 21.0
    assert patch_data["operationMode"] == "COOLING"
    assert patch_data["fanSpeed"] == "HIGH"
    assert patch_data["louverPosition"] == "AUTO"
    assert patch_data["vanePosition"] == "POSITION_1"
    assert patch_data["flap3dAuto"] is False


# ---------------------------------------------------------------------------
# NovaRcApiClient.async_login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_login_stores_credentials_and_returns_true() -> None:
    """A successful login should store credentials and return True."""
    body = {
        "data": {
            "xybus": {
                "zones": [{"__typename": "XYBusZone", "zoneId": 1}]
            }
        }
    }
    session = _FakeSession(_FakeResponse(200, body))
    client = _make_client(session)
    with patch.object(client, "_attach_time_series_data", new_callable=AsyncMock):
        result = await client.async_login(username="admin", ******)
    assert result is True
    assert client.username == "admin"
    assert client.password == "secret"


@pytest.mark.asyncio
async def test_async_login_raises_invalid_auth_on_401() -> None:
    """A 401 response during login should propagate InvalidAuth."""
    session = _FakeSession(_FakeResponse(401, text_body="Unauthorized"))
    client = _make_client(session)
    with pytest.raises(InvalidAuth):
        await client.async_login(username="admin", ******)


# ---------------------------------------------------------------------------
# NovaRcApiClient host normalization
# ---------------------------------------------------------------------------


def test_client_normalizes_https_prefix_in_host() -> None:
    """The host should strip the https:// prefix when building the endpoint."""
    session = MagicMock()
    client = NovaRcApiClient(host="https://my-gateway.local", session=session)
    assert "https://my-gateway.local/graphql/" == client.endpoint


def test_client_adds_https_scheme_when_missing() -> None:
    """The client should always use HTTPS for the endpoint."""
    session = MagicMock()
    client = NovaRcApiClient(host="my-gateway.local", session=session)
    assert client.endpoint.startswith("https://")
