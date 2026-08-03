"""Functional tests for the config flow and options flow.

These are lightweight contract tests — no real HA instance needed.
The config flow is exercised through its public API with mocked
client and session stubs.
"""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType

_integration_dir = Path(__file__).resolve().parents[2]
_config_dir = _integration_dir.parent.parent
if str(_config_dir) not in sys.path:
    sys.path.insert(0, str(_config_dir))

import custom_components.mhi_nova_link as integration_module  # noqa: E402
import custom_components.mhi_nova_link.config_flow as config_flow_module  # noqa: E402

CONF_SSL_FINGERPRINT = "ssl_fingerprint"


class _DummyConfigEntries:
    def __init__(self) -> None:
        self._entries: dict = {}

    async def async_forward_entry_setups(self, entry, platforms) -> None:
        self._entries[entry.entry_id] = platforms

    async def async_unload_platforms(self, entry, platforms) -> bool:
        self._entries.pop(entry.entry_id, None)
        return True

    def async_update_entry(self, entry, *, data=None, options=None, title=None) -> None:
        if data is not None:
            entry.data = data
        if options is not None:
            entry.options = options
        if title is not None:
            entry.title = title


class _DummyHass(SimpleNamespace):
    def __init__(self) -> None:
        super().__init__(data={}, config_entries=_DummyConfigEntries())
        self.loop_thread_id = 0
        self.loop = SimpleNamespace(_thread_id=0, call_soon_threadsafe=lambda cb: cb())
        self.created_tasks: list = []

    def async_create_task(self, coro) -> object:
        self.created_tasks.append(coro)
        return coro


@pytest.fixture
def hass() -> _DummyHass:
    return _DummyHass()


@pytest.fixture(autouse=True)
def _patch_frame_usage():
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


# ---------------------------------------------------------------------------
# Config flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_config_flow_success_proceeds_to_analytics_then_creates_entry(
    hass: _DummyHass,
) -> None:
    """A successful login should show the analytics form then create an entry."""
    with (
        patch(
            "custom_components.mhi_nova_link.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch("custom_components.mhi_nova_link.config_flow.NovaRcApiClient") as client_cls,
    ):
        client = client_cls.return_value
        client.async_login = AsyncMock(return_value=True)

        flow = config_flow_module.NovaRcConfigFlow()
        flow.hass = hass
        flow.context = {}
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = lambda: None  # noqa: SLF001

        result = await flow.async_step_user(
            {
                CONF_HOST: "gateway.local",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "s3cr3t",
                CONF_SSL_FINGERPRINT: "",
            }
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "analytics"

    result2 = await flow.async_step_analytics(
        {config_flow_module.CONF_ANALYTICS_OPT_IN: False}
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "CompTrol 4Web NOVA RC (gateway.local)"


@pytest.mark.asyncio
async def test_config_flow_returns_form_error_for_invalid_auth(
    hass: _DummyHass,
) -> None:
    """Authentication errors should surface as a form-level error."""
    with (
        patch(
            "custom_components.mhi_nova_link.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch("custom_components.mhi_nova_link.config_flow.NovaRcApiClient") as client_cls,
    ):
        client = client_cls.return_value
        client.async_login = AsyncMock(side_effect=config_flow_module.InvalidAuth)

        flow = config_flow_module.NovaRcConfigFlow()
        flow.hass = hass
        flow.context = {}

        result = await flow.async_step_user(
            {
                CONF_HOST: "gateway.local",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "wrong",
                CONF_SSL_FINGERPRINT: "",
            }
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_config_flow_returns_error_for_invalid_fingerprint_format(
    hass: _DummyHass,
) -> None:
    """An invalid SSL fingerprint should fail before attempting login."""
    with patch(
        "custom_components.mhi_nova_link.config_flow.async_get_clientsession",
        return_value=object(),
    ):
        flow = config_flow_module.NovaRcConfigFlow()
        flow.hass = hass
        flow.context = {}

        result = await flow.async_step_user(
            {
                CONF_HOST: "gateway.local",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "s3cr3t",
                CONF_SSL_FINGERPRINT: "not-valid-hex",
            }
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_ssl_fingerprint_format"}


@pytest.mark.asyncio
async def test_config_flow_auto_pins_fingerprint_for_self_signed_cert(
    hass: _DummyHass,
) -> None:
    """When no fingerprint is given and the cert is self-signed, one should be auto-pinned."""
    first_client = AsyncMock()
    first_client.async_login = AsyncMock(
        side_effect=config_flow_module.InvalidCertificate
    )
    first_client.async_get_tls_fingerprint = AsyncMock(return_value="cc" * 32)

    fallback_client = AsyncMock()
    fallback_client.async_login = AsyncMock(return_value=True)

    with (
        patch(
            "custom_components.mhi_nova_link.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch(
            "custom_components.mhi_nova_link.config_flow.NovaRcApiClient",
            side_effect=[first_client, fallback_client],
        ),
    ):
        flow = config_flow_module.NovaRcConfigFlow()
        flow.hass = hass
        flow.context = {}
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = lambda: None  # noqa: SLF001

        result = await flow.async_step_user(
            {
                CONF_HOST: "gateway.local",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "s3cr3t",
                CONF_SSL_FINGERPRINT: "",
            }
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "analytics"

    result2 = await flow.async_step_analytics(
        {config_flow_module.CONF_ANALYTICS_OPT_IN: False}
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_SSL_FINGERPRINT] == "cc" * 32


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_options_flow_accepts_updated_credentials(hass: _DummyHass) -> None:
    """Options flow should persist updated credentials."""
    entry = SimpleNamespace(
        options={},
        data={
            CONF_HOST: "gateway.local",
            CONF_USERNAME: "old-user",
            CONF_PASSWORD: "old-secret",
            CONF_SSL_FINGERPRINT: "",
        },
    )
    flow = config_flow_module.NovaRcOptionsFlow(entry)
    flow.hass = hass

    result = await flow.async_step_init(
        {
            "poll_interval": 10,
            "time_series_poll_interval": 60,
            CONF_SSL_FINGERPRINT: "",
            CONF_USERNAME: "new-user",
            CONF_PASSWORD: "new-secret",
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_USERNAME] == "new-user"


@pytest.mark.asyncio
async def test_options_flow_generates_analytics_id_on_opt_in(
    hass: _DummyHass,
) -> None:
    """Enabling analytics in options should generate and persist an anonymous ID."""
    entry = SimpleNamespace(
        options={},
        data={
            CONF_HOST: "gateway.local",
            CONF_USERNAME: "user",
            CONF_PASSWORD: "s3cr3t",
            CONF_SSL_FINGERPRINT: "",
            config_flow_module.CONF_ANALYTICS_OPT_IN: False,
        },
    )
    flow = config_flow_module.NovaRcOptionsFlow(entry)
    flow.hass = hass

    result = await flow.async_step_init(
        {
            "poll_interval": 10,
            "time_series_poll_interval": 60,
            CONF_SSL_FINGERPRINT: "",
            CONF_USERNAME: "user",
            CONF_PASSWORD: "s3cr3t",
            config_flow_module.CONF_ANALYTICS_OPT_IN: True,
        }
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][config_flow_module.CONF_ANALYTICS_OPT_IN] is True
    assert result["data"].get(config_flow_module.ANALYTICS_ANONYMOUS_ID_KEY)
