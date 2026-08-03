"""Unit tests for _get_update_interval (coordinator module, pure Python).

No HA instance or network required — only environment-variable logic is tested.
"""

import pytest

from custom_components.mhi_nova_link.const import DEFAULT_POLL_INTERVAL
from custom_components.mhi_nova_link.coordinator import _get_update_interval


def _entry(poll_interval=None):
    """Return a minimal entry stub with optional poll_interval option."""
    from types import SimpleNamespace
    options = {}
    if poll_interval is not None:
        options["poll_interval"] = poll_interval
    return SimpleNamespace(options=options)


def test_returns_default_when_no_entry_and_no_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When nothing is configured, the default poll interval should be used."""
    monkeypatch.delenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", raising=False)
    assert _get_update_interval(None).total_seconds() == DEFAULT_POLL_INTERVAL


def test_reads_interval_from_entry_options() -> None:
    """Entry options take the highest precedence."""
    assert _get_update_interval(_entry(42)).total_seconds() == 42


def test_reads_from_primary_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """NOVA_RC_UPDATE_INTERVAL_SECONDS should override the default."""
    monkeypatch.setenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", "30")
    monkeypatch.delenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", raising=False)
    assert _get_update_interval(None).total_seconds() == 30


def test_reads_from_legacy_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """MHI_NOVALINK_UPDATE_INTERVAL_SECONDS should work as a fallback."""
    monkeypatch.delenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", raising=False)
    monkeypatch.setenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", "25")
    assert _get_update_interval(None).total_seconds() == 25


def test_entry_options_supersede_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entry options should take priority over environment variables."""
    monkeypatch.setenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", "99")
    assert _get_update_interval(_entry(10)).total_seconds() == 10


def test_falls_back_to_env_when_options_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An entry without poll_interval in options should fall back to the env var."""
    monkeypatch.setenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", "55")
    monkeypatch.delenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", raising=False)
    assert _get_update_interval(_entry()).total_seconds() == 55


def test_invalid_env_value_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-numeric env value should produce a warning and use the default."""
    monkeypatch.setenv("NOVA_RC_UPDATE_INTERVAL_SECONDS", "not_a_number")
    monkeypatch.delenv("MHI_NOVALINK_UPDATE_INTERVAL_SECONDS", raising=False)
    assert _get_update_interval(None).total_seconds() == DEFAULT_POLL_INTERVAL


def test_clamps_to_minimum_one_second() -> None:
    """Zero or negative values should be clamped to 1 second."""
    assert _get_update_interval(_entry(0)).total_seconds() == 1
    assert _get_update_interval(_entry(-5)).total_seconds() == 1
