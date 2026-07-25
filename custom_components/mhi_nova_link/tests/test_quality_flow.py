"""Quality-focused regression tests for the MHI Nova integration."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import frame

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
            title="MHI Nova",
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
            "custom_components.mhi_nova.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch("custom_components.mhi_nova.config_flow.SKlimaApiClient") as client_cls,
    ):
        client = client_cls.return_value
        client.async_login = AsyncMock(return_value=True)

        flow = config_flow_module.SKlimaConfigFlow()
        flow.hass = hass
        flow.context = {}
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = lambda: None  # noqa: SLF001

        result = await flow.async_step_user(
            {
                CONF_HOST: "gateway.local",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "secret",
            }
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MHI NovaLink (gateway.local)"


async def test_config_flow_returns_form_for_invalid_auth(
    config_flow_module: object,
    hass: DummyHass,
) -> None:
    """Authentication errors should surface as a form error."""
    with (
        patch(
            "custom_components.mhi_nova.config_flow.async_get_clientsession",
            return_value=object(),
        ),
        patch("custom_components.mhi_nova.config_flow.SKlimaApiClient") as client_cls,
    ):
        client = client_cls.return_value
        client.async_login = AsyncMock(side_effect=config_flow_module.InvalidAuth)

        flow = config_flow_module.SKlimaConfigFlow()
        flow.hass = hass
        flow.context = {}

        result = await flow.async_step_user(
            {
                CONF_HOST: "gateway.local",
                CONF_USERNAME: "user",
                CONF_PASSWORD: "secret",
            }
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


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
        },
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.mhi_nova.async_get_clientsession", return_value=object()
        ),
        patch("custom_components.mhi_nova.SKlimaApiClient") as client_cls,
        patch(
            "custom_components.mhi_nova.coordinator.SKlimaDataUpdateCoordinator.async_config_entry_first_refresh",
            new_callable=AsyncMock,
        ) as refresh_mock,
    ):
        client = client_cls.return_value
        client.async_login = AsyncMock(return_value=True)

        assert await integration_module.async_setup_entry(hass, entry)
        assert entry.entry_id in hass.data[integration_module.DOMAIN]
        assert refresh_mock.await_count == 1

        assert await integration_module.async_unload_entry(hass, entry)
        assert (
            integration_module.DOMAIN not in hass.data
            or entry.entry_id not in hass.data[integration_module.DOMAIN]
        )
