"""Run smoke tests for the NOVA_RC custom integration."""

from pathlib import Path

import custom_components.mhi_nova_link as integration


def test_manifest_exists() -> None:
    """The integration should ship with its manifest metadata."""
    integration_dir = Path(__file__).resolve().parents[1]
    assert (integration_dir / "manifest.json").is_file()


def test_import_integration_package() -> None:
    """The integration package should be importable from the custom_components path."""
    assert integration.__file__ is not None
