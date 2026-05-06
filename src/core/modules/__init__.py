"""Exports leves para módulos do core."""

from importlib import import_module
from typing import Any

__all__ = [
    "ObsidianVaultManager",
    "ZathuraConfigManager",
    "LatexExporter",
    "LatexExportRequest",
    "LatexExportResult",
    "LatexMetadata",
    "LatexExportValidationError",
]


def __getattr__(name: str) -> Any:
    if name == "ObsidianVaultManager":
        return getattr(import_module(".obsidian", __name__), name)
    if name == "ZathuraConfigManager":
        return getattr(import_module(".zathura_config_manager", __name__), name)
    if name in {
        "LatexExporter",
        "LatexExportRequest",
        "LatexExportResult",
        "LatexMetadata",
        "LatexExportValidationError",
    }:
        return getattr(import_module(".LaTex", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
