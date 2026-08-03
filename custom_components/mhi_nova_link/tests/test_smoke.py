"""Run smoke tests for the NOVA_RC custom integration."""

import sys
from pathlib import Path


def test_manifest_exists() -> None:
    """The integration should ship with its manifest metadata."""
    integration_dir = Path(__file__).resolve().parents[1]
    assert (integration_dir / "manifest.json").is_file()


def test_import_integration_package() -> None:
    """The integration package should be importable from the custom_components path."""
    integration_dir = Path(__file__).resolve().parents[1]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link as integration  # noqa: PLC0415

    assert integration.__file__ is not None
