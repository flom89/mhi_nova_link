"""Run quality-focused regression tests for NOVA_RC."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import frame

CONF_SSL_FINGERPRINT = "ssl_fingerprint"

config_dir = Path(__file__).resolve().parents[3]
if str(config_dir) not in sys.path:
    sys.path.insert(0, str(config_dir))

import custom_components.mhi_nova_link as integration_module  # noqa: E402
import custom_components.mhi_nova_link.config_flow as config_flow_module  # noqa: E402


class DummyConfigEntries:
    """Minimal config-entry manager used by the regression tests."""

    def __init__(self) -> None:
        """Initialize the minimal entry registry stub."""
        self._entries: dict[str, object] = {}

    async def async_forward_entry_setups(
        self, entry: object, platforms: tuple[object, ...]
    ) -> None:
        """Record platform setup calls without doing any real Home Assistant work."""
        self._entries[entry.entry_id] = platforms

    async def async_unload_platforms(
        self, entry: object, platforms: tuple[object, ...]
    ) -> bool:
        """Pretend to unload platforms successfully."""
        self._entries.pop(entry.entry_id, None)
        return True

    def async_update_entry(
        self,
        entry: object,
        *,
        data: dict[str, str] | None = None,
        options: dict[str, str] | None = None,
        title: str | None = None,
    ) -> None:
        """Mimic Home Assistant's in-memory entry update behavior."""
        if data is not None:
            entry.data = data
        if options is not None:
            entry.options = options
        if title is not None:
            entry.title = title


class DummyHass(SimpleNamespace):
    """Minimal Home Assistant stub for the regression tests."""

    def __init__(self) -> None:
        """Initialize the minimal Home Assistant stub."""
        super().__init__(data={}, config_entries=DummyConfigEntries())
        self.loop_thread_id = 0
        self.loop = SimpleNamespace(_thread_id=0, call_soon_threadsafe=lambda cb: cb())
        frame._hass.hass = self  # noqa: SLF001


@pytest.fixture(name="hass")
def hass_fixture() -> DummyHass:
    """Provide a lightweight Home Assistant stub for integration tests."""
    return DummyHass()


class DummyConfigEntry(SimpleNamespace):
    """Minimal config-entry stub for setup/unload regression tests."""

    def __init__(self, domain: str, data: dict[str, str]) -> None:
        """Initialize the minimal config-entry stub."""
        super().__init__(
            domain=domain,
            data=data,
            options={},
            entry_id="entry-id",
            title="NOVA_RC",
        )

    def add_to_hass(self, hass: object) -> None:
        """Register the entry with Home Assistant for test purposes."""
        hass.config_entries._entries[self.entry_id] = self  # noqa: SLF001


@pytest.fixture(name="integration_module")
def integration_module_fixture() -> object:
    """Return the integration package from the custom component path."""
    return integration_module


@pytest.fixture(name="config_flow_module")
def config_flow_module_fixture() -> object:
    """Return the integration config flow module."""
    return config_flow_module


async def test_config_flow_creates_entry_when_login_succeeds(
    config_flow_module: object,
    hass: DummyHass,
) -> None:
    """A successful login should create a config entry."""
    with (
        patch(
            "custom_components.mhi_nova_link.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch(
            "custom_components.mhi_nova_link.config_flow.NovaRcApiClient"
        ) as client_cls,
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
                CONF_PASSWORD: "secret",
                CONF_SSL_FINGERPRINT: "",
            }
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "CompTrol 4Web NOVA RC (gateway.local)"


async def test_config_flow_returns_form_for_invalid_auth(
    config_flow_module: object,
    hass: DummyHass,
) -> None:
    """Authentication errors should surface as a form error."""
    with (
        patch(
            "custom_components.mhi_nova_link.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch(
            "custom_components.mhi_nova_link.config_flow.NovaRcApiClient"
        ) as client_cls,
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
                CONF_PASSWORD: "secret",
                CONF_SSL_FINGERPRINT: "",
            }
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_config_flow_returns_form_for_invalid_fingerprint_format(
    config_flow_module: object,
    hass: DummyHass,
) -> None:
    """Invalid fingerprint input should fail validation before login."""
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
                CONF_PASSWORD: "secret",
                CONF_SSL_FINGERPRINT: "invalid-fingerprint",
            }
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_ssl_fingerprint_format"}


async def test_config_flow_returns_form_for_invalid_gateway_certificate(
    config_flow_module: object,
    hass: DummyHass,
) -> None:
    """Certificate validation failures should map to a dedicated flow error."""
    with (
        patch(
            "custom_components.mhi_nova_link.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch(
            "custom_components.mhi_nova_link.config_flow.NovaRcApiClient"
        ) as client_cls,
    ):
        client = client_cls.return_value
        client.async_login = AsyncMock(
            side_effect=config_flow_module.InvalidCertificate
        )

        flow = config_flow_module.NovaRcConfigFlow()
        flow.hass = hass
        flow.context = {}

        result = await flow.async_step_user(
            {
                CONF_HOST: "gateway.local",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "secret",
                CONF_SSL_FINGERPRINT: "aa" * 32,
            }
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_ssl_fingerprint"}


async def test_config_flow_auto_pins_fingerprint_for_self_signed_gateway(
    config_flow_module: object,
    hass: DummyHass,
) -> None:
    """When no fingerprint is provided, the flow should auto-discover and store one."""
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
                CONF_PASSWORD: "secret",
                CONF_SSL_FINGERPRINT: "",
            }
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SSL_FINGERPRINT] == "cc" * 32


async def test_setup_and_unload_entry(
    integration_module: object,
    hass: DummyHass,
) -> None:
    """The integration should set up and unload config entries cleanly."""
    entry = DummyConfigEntry(
        domain=integration_module.DOMAIN,
        data={
            CONF_HOST: "gateway.local",
            CONF_USERNAME: "user",
            CONF_PASSWORD: "secret",
            CONF_SSL_FINGERPRINT: "aa" * 32,
        },
    )
    entry.options = {CONF_SSL_FINGERPRINT: "bb" * 32}
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.mhi_nova_link.async_get_clientsession",
            return_value=object(),
        ),
        patch("custom_components.mhi_nova_link.NovaRcApiClient") as client_cls,
        patch(
            "custom_components.mhi_nova_link.coordinator.NovaRcDataUpdateCoordinator.async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ) as refresh_mock,
    ):
        client = client_cls.return_value
        client.async_login = AsyncMock(return_value=True)

        assert await integration_module.async_setup_entry(hass, entry)
        client_cls.assert_called_once()
        assert client_cls.call_args.kwargs["ssl_fingerprint"] == "bb" * 32
        assert entry.title == "CompTrol 4Web NOVA RC (gateway.local)"
        assert entry.entry_id in hass.data[integration_module.DOMAIN]
        assert refresh_mock.await_count == 1

        assert await integration_module.async_unload_entry(hass, entry)
        assert (
            integration_module.DOMAIN not in hass.data
            or entry.entry_id not in hass.data[integration_module.DOMAIN]
        )


async def test_setup_auto_pins_fingerprint_when_missing(
    integration_module: object,
    hass: DummyHass,
) -> None:
    """Setup should auto-discover and pin a fingerprint for self-signed gateways."""
    entry = DummyConfigEntry(
        domain=integration_module.DOMAIN,
        data={
            CONF_HOST: "gateway.local",
            CONF_USERNAME: "user",
            CONF_PASSWORD: "secret",
        },
    )
    entry.options = {}
    entry.add_to_hass(hass)

    first_client = AsyncMock()
    first_client.async_login = AsyncMock(
        side_effect=integration_module.InvalidCertificate
    )
    first_client.async_get_tls_fingerprint = AsyncMock(return_value="dd" * 32)

    fallback_client = AsyncMock()
    fallback_client.async_login = AsyncMock(return_value=True)

    with (
        patch(
            "custom_components.mhi_nova_link.async_get_clientsession",
            return_value=object(),
        ),
        patch(
            "custom_components.mhi_nova_link.NovaRcApiClient",
            side_effect=[first_client, fallback_client],
        ),
        patch(
            "custom_components.mhi_nova_link.coordinator.NovaRcDataUpdateCoordinator.async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ) as refresh_mock,
    ):
        assert await integration_module.async_setup_entry(hass, entry)
        assert entry.data[CONF_SSL_FINGERPRINT] == "dd" * 32
        assert entry.entry_id in hass.data[integration_module.DOMAIN]
        assert refresh_mock.await_count == 1
