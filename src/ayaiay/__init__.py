"""AyAiAy CLI and SDK for the AI agents marketplace."""

__version__ = "1.0.1"
__author__ = "Philipp Frenzel"

from ayaiay.client import AyAiAyClient
from ayaiay.models import LockFile, Pack, PackVersion, SearchResult
from ayaiay.package_manager import PackageManager
from ayaiay.validator import validate_manifest

__all__ = [
    "AyAiAyClient",
    "LockFile",
    "Pack",
    "PackageManager",
    "PackVersion",
    "SearchResult",
    "validate_manifest",
]
