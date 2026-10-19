"""Tests for GraphQL API request handling."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.mhi_nova_link.api import NovaRcApiClient


@pytest.mark.asyncio
async def test_login_handles_null_zones_response() -> None:
    """A JSON null response should be normalized as an empty zones response."""
    response = MagicMock()
    response.status = 200
    response.text = AsyncMock(return_value="null")
    response.json = AsyncMock(return_value=None)
    request_context = MagicMock()
    request_context.__aenter__ = AsyncMock(return_value=response)
    request_context.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.post.return_value = request_context
    client = NovaRcApiClient("gateway.local", session)

    assert await client.async_login("username", "password")
    assert client.take_initial_zones() == []


@pytest.mark.asyncio
async def test_set_zone_state_returns_false_for_null_response() -> None:
    response = MagicMock()
    response.status = 200
    response.text = AsyncMock(return_value="null")
    response.json = AsyncMock(return_value=None)
    request_context = MagicMock()
    request_context.__aenter__ = AsyncMock(return_value=response)
    request_context.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.post.return_value = request_context
    client = NovaRcApiClient("gateway.local", session)

    assert await client.async_set_zone_state(1, setpoint=20) is False


@pytest.mark.asyncio
async def test_set_gpio_active_high_returns_false_for_null_response() -> None:
    response = MagicMock()
    response.status = 200
    response.text = AsyncMock(return_value="null")
    response.json = AsyncMock(return_value=None)
    request_context = MagicMock()
    request_context.__aenter__ = AsyncMock(return_value=response)
    request_context.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.post.return_value = request_context
    client = NovaRcApiClient("gateway.local", session)

    assert await client.async_set_gpio_active_high("/gpio/test", True) is False
