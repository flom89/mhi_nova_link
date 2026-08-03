"""Diagnostics tests for MHI Nova Link."""

from types import SimpleNamespace

import pytest

from custom_components.mhi_nova_link.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_diagnostics_redacts_sensitive_values_and_includes_runtime_data() -> None:
    """Diagnostics should redact credentials while exposing safe runtime metadata."""
    coordinator = SimpleNamespace(
        data=[{"zoneId": 1}, {"zoneId": 2}],
        gpios={"SYSTEM_STOP": False},
        gateway_update={"installed_version": "3.2.5"},
    )
    entry = SimpleNamespace(
        entry_id="entry-id",
        title="CompTrol 4Web NOVA RC (gateway.local)",
        data={
            "host": "gateway.local",
            "username": "user",
            "password": "secret",
            "ssl_fingerprint": "aa" * 32,
            "analytics_anonymous_id": "anon-id",
        },
        options={},
        runtime_data=SimpleNamespace(coordinator=coordinator),
    )

    diagnostics = await async_get_config_entry_diagnostics(SimpleNamespace(), entry)

    assert diagnostics["entry"]["data"]["host"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["username"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["password"] == "**REDACTED**"
    assert diagnostics["runtime"]["zone_count"] == 2
    assert diagnostics["runtime"]["gateway_update"]["installed_version"] == "3.2.5"
