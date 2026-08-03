"""Configure pytest for the NOVA_RC integration test suite."""

from pathlib import Path
import sys

# Add the repository root to sys.path once so that all test modules can import
# custom_components.mhi_nova_link.* without per-file sys.path manipulation.
_REPO_ROOT = str(Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
