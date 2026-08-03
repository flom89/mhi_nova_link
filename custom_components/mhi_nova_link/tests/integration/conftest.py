"""Shared fixtures and helpers for integration tests.

Integration tests verify how components interact with each other
using lightweight HA stubs and mocked HTTP sessions — no real network
or full HA boot required.
"""

from types import TracebackType
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Fake HTTP session helpers shared across integration test modules
# ---------------------------------------------------------------------------


class FakeResponse:
    """Minimal fake aiohttp response."""

    def __init__(
        self,
        status: int = 200,
        body: dict[str, Any] | None = None,
        text_body: str | None = None,
    ) -> None:
        """Initialise with a preset status and body."""
        self.status = status
        self._body = body or {}
        self._text = text_body or ""

    async def text(self) -> str:
        """Return the response text."""
        return self._text

    async def json(self) -> dict[str, Any]:
        """Return the parsed response body."""
        return self._body


class FakeContextManager:
    """Async context manager wrapping a FakeResponse."""

    def __init__(self, response: FakeResponse) -> None:
        """Initialise with the response to return."""
        self._response = response

    async def __aenter__(self) -> FakeResponse:
        """Enter the context."""
        return self._response

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the context."""


class FakeSession:
    """Fake aiohttp.ClientSession that returns a preconfigured response."""

    def __init__(self, response: FakeResponse) -> None:
        """Initialise with the response to return for every POST request."""
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeContextManager:
        """Record the call and return a context manager wrapping the response."""
        self.calls.append({"url": url, **kwargs})
        return FakeContextManager(self.response)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_response_200() -> FakeResponse:
    """Return a 200-OK response with an empty body."""
    return FakeResponse(200, {})


@pytest.fixture
def fake_session_200(fake_response_200: FakeResponse) -> FakeSession:
    """Return a fake session that responds with HTTP 200."""
    return FakeSession(fake_response_200)
