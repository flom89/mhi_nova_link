"""Integration tests for NovaRcApiClient.

Each test exercises one API method against a fake HTTP session.
No real network connection is required.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.mhi_nova_link.api import (
    CannotConnect,
    InvalidAuth,
    InvalidCertificate,
    NovaRcApiClient,
)

from .conftest import FakeResponse, FakeSession


def _client(session: Any, host: str = "gateway.local") -> NovaRcApiClient:
    """Construct a client with a fake session."""
    return NovaRcApiClient(host=host, session=session)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# host / endpoint normalisation
# ---------------------------------------------------------------------------


def test_client_strips_https_prefix_from_host() -> None:
    """The https:// prefix should be stripped when building the endpoint."""
    client = _client(MagicMock(), host="https://my-gateway.local")
    assert client.endpoint == "https://my-gateway.local/graphql/"


def test_client_adds_https_when_scheme_missing() -> None:
    """A bare hostname should get an https:// scheme added."""
    client = _client(MagicMock(), host="my-gateway.local")
    assert client.endpoint.startswith("https://")


# ---------------------------------------------------------------------------
# async_get_zones
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_zones_returns_zones_on_200() -> None:
    """async_get_zones should return parsed zone dicts on HTTP 200."""
    body = {
        "data": {
            "xybus": {
                "zones": [{"__typename": "XYBusZone", "zoneId": 1, "available": True}]
            }
        }
    }
    session = FakeSession(FakeResponse(200, body))
    client = _client(session)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(client, "_attach_time_series_data", AsyncMock())
        zones = await client.async_get_zones()
    assert len(zones) == 1
    assert zones[0]["zoneId"] == 1


@pytest.mark.asyncio
async def test_get_zones_raises_invalid_auth_on_401() -> None:
    """A 401 response should raise InvalidAuth."""
    session = FakeSession(FakeResponse(401, text_body="Unauthorized"))
    with pytest.raises(InvalidAuth):
        await _client(session).async_get_zones()


@pytest.mark.asyncio
async def test_get_zones_raises_invalid_auth_on_403() -> None:
    """A 403 response should raise InvalidAuth."""
    session = FakeSession(FakeResponse(403, text_body="Forbidden"))
    with pytest.raises(InvalidAuth):
        await _client(session).async_get_zones()


@pytest.mark.asyncio
async def test_get_zones_raises_cannot_connect_on_5xx() -> None:
    """A 5xx HTTP response should raise CannotConnect."""
    session = FakeSession(FakeResponse(503, text_body="Service Unavailable"))
    with pytest.raises(CannotConnect):
        await _client(session).async_get_zones()


@pytest.mark.asyncio
async def test_get_zones_raises_cannot_connect_on_graphql_error() -> None:
    """A GraphQL error in the response body should raise CannotConnect."""
    body = {"errors": [{"message": "internal error"}]}
    session = FakeSession(FakeResponse(200, body))
    with pytest.raises(CannotConnect):
        await _client(session).async_get_zones()


@pytest.mark.asyncio
async def test_get_zones_raises_cannot_connect_on_client_error() -> None:
    """An aiohttp.ClientError should be wrapped in CannotConnect."""
    session = MagicMock()
    session.post.side_effect = aiohttp.ClientError("network down")
    with pytest.raises(CannotConnect):
        await _client(session).async_get_zones()


@pytest.mark.asyncio
async def test_get_zones_raises_invalid_certificate_on_tls_mismatch() -> None:
    """A TLS fingerprint mismatch should raise InvalidCertificate."""
    session = MagicMock()
    session.post.side_effect = aiohttp.client_exceptions.ServerFingerprintMismatch(
        b"", b"", "", 0
    )
    with pytest.raises(InvalidCertificate):
        await _client(session).async_get_zones()


# ---------------------------------------------------------------------------
# async_get_notifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_notifications_returns_normalized_dict() -> None:
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
    result = await _client(FakeSession(FakeResponse(200, body))).async_get_notifications()
    assert len(result["notifications"]) == 1


@pytest.mark.asyncio
async def test_get_notifications_returns_empty_on_http_error() -> None:
    """A non-200 HTTP status should return an empty dict (non-fatal)."""
    result = await _client(
        FakeSession(FakeResponse(503, text_body="down"))
    ).async_get_notifications()
    assert result == {}


@pytest.mark.asyncio
async def test_get_notifications_returns_empty_on_graphql_error() -> None:
    """GraphQL errors in the response should return an empty dict."""
    body = {"errors": [{"message": "forbidden"}]}
    result = await _client(FakeSession(FakeResponse(200, body))).async_get_notifications()
    assert result == {}


@pytest.mark.asyncio
async def test_get_notifications_raises_invalid_auth_on_403() -> None:
    """A 403 response should raise InvalidAuth."""
    with pytest.raises(InvalidAuth):
        await _client(FakeSession(FakeResponse(403, text_body="Forbidden"))).async_get_notifications()


# ---------------------------------------------------------------------------
# async_get_gpios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_gpios_returns_function_state_map() -> None:
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
    result = await _client(FakeSession(FakeResponse(200, body))).async_get_gpios()
    assert result == {"FREE_COOLING": True, "SYSTEM_STOP": False}


@pytest.mark.asyncio
async def test_get_gpios_returns_empty_on_http_error() -> None:
    """A non-200 HTTP status should return an empty dict."""
    result = await _client(FakeSession(FakeResponse(500, text_body="err"))).async_get_gpios()
    assert result == {}


# ---------------------------------------------------------------------------
# async_get_gateway_update_information
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_gateway_update_returns_version_data() -> None:
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
    result = await _client(
        FakeSession(FakeResponse(200, body))
    ).async_get_gateway_update_information()
    assert result["installed_version"] == "3.2.5"
    assert result["update_available"] is False


@pytest.mark.asyncio
async def test_get_gateway_update_returns_empty_on_http_error() -> None:
    """An HTTP error should return an empty dict."""
    result = await _client(
        FakeSession(FakeResponse(503, text_body="down"))
    ).async_get_gateway_update_information()
    assert result == {}


# ---------------------------------------------------------------------------
# async_set_zone_state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_zone_state_returns_true_and_sends_correct_patch() -> None:
    """A successful mutation should return True and send the correct patch payload."""
    body = {"data": {"xybus": {"zone": {"patch": {"id": "job-1", "done": True}}}}}
    session = FakeSession(FakeResponse(200, body))
    result = await _client(session).async_set_zone_state(1, setpoint=22.0)
    assert result is True
    assert len(session.calls) == 1
    variables = session.calls[0]["json"]["variables"]
    assert variables["zoneId"] == 1
    assert variables["patch"]["setpoint"] == 22.0


@pytest.mark.asyncio
async def test_set_zone_state_returns_true_immediately_when_no_fields() -> None:
    """When no patch fields are provided, no HTTP request should be made."""
    session = FakeSession(FakeResponse(200, {}))
    result = await _client(session).async_set_zone_state(1)
    assert result is True
    assert len(session.calls) == 0


@pytest.mark.asyncio
async def test_set_zone_state_returns_false_on_http_error() -> None:
    """A non-200 HTTP response should return False."""
    result = await _client(
        FakeSession(FakeResponse(500, text_body="error"))
    ).async_set_zone_state(1, running=True)
    assert result is False


@pytest.mark.asyncio
async def test_set_zone_state_returns_false_on_graphql_error() -> None:
    """A GraphQL error body should return False."""
    body = {"errors": [{"message": "mutation failed"}]}
    result = await _client(
        FakeSession(FakeResponse(200, body))
    ).async_set_zone_state(1, running=True)
    assert result is False


@pytest.mark.asyncio
async def test_set_zone_state_raises_invalid_auth_on_403() -> None:
    """A 403 response should raise InvalidAuth."""
    with pytest.raises(InvalidAuth):
        await _client(
            FakeSession(FakeResponse(403, text_body="Forbidden"))
        ).async_set_zone_state(1, running=True)


@pytest.mark.asyncio
async def test_set_zone_state_sends_all_patch_fields() -> None:
    """All settable fields should appear in the mutation payload."""
    body = {"data": {"xybus": {"zone": {"patch": {"id": "j2", "done": False}}}}}
    session = FakeSession(FakeResponse(200, body))
    await _client(session).async_set_zone_state(
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
# async_login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_login_stores_credentials_and_returns_true() -> None:
    """A successful login should store credentials and return True."""
    body = {
        "data": {
            "xybus": {"zones": [{"__typename": "XYBusZone", "zoneId": 1}]}
        }
    }
    session = FakeSession(FakeResponse(200, body))
    client = _client(session)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(client, "_attach_time_series_data", AsyncMock())
        result = await client.async_login("admin", "s3cr3t")
    assert result is True
    assert client.username == "admin"


@pytest.mark.asyncio
async def test_async_login_raises_invalid_auth_on_401() -> None:
    """A 401 response during login should propagate InvalidAuth."""
    session = FakeSession(FakeResponse(401, text_body="Unauthorized"))
    with pytest.raises(InvalidAuth):
        await _client(session).async_login("admin", "wrong")
