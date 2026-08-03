"""Functional smoke tests — verify manifest existence and package importability."""

from pathlib import Path
import sys


def test_manifest_exists() -> None:
    """The integration must ship a manifest.json file."""
    integration_dir = Path(__file__).resolve().parents[2]
    assert (integration_dir / "manifest.json").is_file()


def test_hacs_json_exists() -> None:
    """The repository must include a hacs.json descriptor."""
    repo_root = Path(__file__).resolve().parents[4]
    assert (repo_root / "hacs.json").is_file()


def test_import_integration_package() -> None:
    """The integration package must be importable without errors."""
    integration_dir = Path(__file__).resolve().parents[2]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link as integration  # noqa: PLC0415

    assert integration.__file__ is not None


def test_all_platform_modules_importable() -> None:
    """Every platform module must be importable without errors."""
    integration_dir = Path(__file__).resolve().parents[2]
    config_dir = integration_dir.parent.parent
    if str(config_dir) not in sys.path:
        sys.path.insert(0, str(config_dir))

    import custom_components.mhi_nova_link.binary_sensor  # noqa: PLC0415
    import custom_components.mhi_nova_link.climate  # noqa: PLC0415
    import custom_components.mhi_nova_link.config_flow  # noqa: PLC0415
    import custom_components.mhi_nova_link.coordinator  # noqa: PLC0415
    import custom_components.mhi_nova_link.select  # noqa: PLC0415
    import custom_components.mhi_nova_link.sensor  # noqa: PLC0415
    import custom_components.mhi_nova_link.switch  # noqa: PLC0415
    import custom_components.mhi_nova_link.telemetry  # noqa: PLC0415
