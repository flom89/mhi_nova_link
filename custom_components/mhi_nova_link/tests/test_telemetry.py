"""Telemetry tests for the MHI Nova Link integration."""

from collections.abc import Callable
import logging
from types import TracebackType
from typing import Any
from unittest.mock import patch

from aiohttp import ClientError
import pytest

from mhi_nova_link import telemetry


class _DummyHass:
    """Minimal Home Assistant stub for telemetry tests."""

    async def async_add_executor_job(self, func: Callable[[], str]) -> str:
        """Run executor jobs inline for tests."""
        return func()


class _FakeResponse:
    """Minimal response object used by the fake session."""

    def __init__(self, status: int, text: str = "") -> None:
        """Initialize the fake response."""
        self.status = status
        self._text = text

    async def text(self) -> str:
        """Return the configured response body."""
        return self._text


class _FakeRequestContextManager:
    """Async context manager wrapper for fake responses."""

    def __init__(self, response: _FakeResponse) -> None:
        """Initialize the async context manager."""
        self._response = response

    async def __aenter__(self) -> _FakeResponse:
        """Enter the async context manager."""
        return self._response

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager."""
        return


class _FakeSession:
    """Fake aiohttp session that returns preconfigured responses."""

    def __init__(self, response: _FakeResponse) -> None:
        """Initialize the fake session."""
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _FakeRequestContextManager:
        """Record the request and return a fake response wrapper."""
        self.calls.append({"url": url, **kwargs})
        return _FakeRequestContextManager(self.response)


@pytest.mark.asyncio
async def test_async_send_analytics_ping_logs_debug_on_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A successful telemetry request should log a debug success message."""
    hass = _DummyHass()
    session = _FakeSession(_FakeResponse(201, "created"))

    with (
        patch.object(telemetry, "async_get_clientsession", return_value=session),
        patch.object(telemetry, "HA_VERSION", "2026.7.0"),
        patch.object(telemetry, "_get_integration_version", return_value="1.2.0"),
        caplog.at_level(logging.DEBUG),
    ):
        await telemetry.async_send_analytics_ping(hass, "anon-id")

    assert len(session.calls) == 1
    assert session.calls[0]["json"]["anonymous_id"] == "anon-id"
    assert "Telemetry ping sent (status 201)" in caplog.text


@pytest.mark.asyncio
async def test_async_send_analytics_ping_logs_warning_on_rejected_status(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A rejected telemetry request should log a warning with status and body."""
    hass = _DummyHass()
    session = _FakeSession(_FakeResponse(401, '{"code":"42501","message":"rls"}'))

    with (
        patch.object(telemetry, "async_get_clientsession", return_value=session),
        patch.object(telemetry, "HA_VERSION", "2026.7.0"),
        patch.object(telemetry, "_get_integration_version", return_value="1.2.0"),
        caplog.at_level(logging.WARNING),
    ):
        await telemetry.async_send_analytics_ping(hass, "anon-id")

    assert len(session.calls) == 1
    assert "Telemetry ping rejected (status 401):" in caplog.text
    assert '"code":"42501"' in caplog.text


@pytest.mark.asyncio
async def test_async_send_analytics_ping_logs_warning_on_request_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Network errors should be logged as non-critical warnings."""
    hass = _DummyHass()

    with (
        patch.object(
            telemetry,
            "async_get_clientsession",
            side_effect=ClientError("network down"),
        ),
        patch.object(telemetry, "HA_VERSION", "2026.7.0"),
        patch.object(telemetry, "_get_integration_version", return_value="1.2.0"),
        caplog.at_level(logging.WARNING),
    ):
        await telemetry.async_send_analytics_ping(hass, "anon-id")

    assert "Telemetry ping request failed (non-critical, ignored)" in caplog.text


@pytest.mark.asyncio
async def test_async_send_analytics_ping_skips_when_env_disabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The telemetry disable environment flag should short-circuit requests."""
    hass = _DummyHass()

    with (
        patch.dict("os.environ", {"MHI_NOVALINK_DISABLE_ANALYTICS": "1"}, clear=False),
        patch.object(telemetry, "async_get_clientsession") as session_getter,
        caplog.at_level(logging.DEBUG),
    ):
        await telemetry.async_send_analytics_ping(hass, "anon-id")

    session_getter.assert_not_called()
    assert "Telemetry disabled via environment variable" in caplog.text
