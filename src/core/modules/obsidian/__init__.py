# src/core/modules/obsidian/__init__.py
from .vault_manager import ObsidianVaultManager, ObsidianNote
from . import templates

__all__ = [
    "ObsidianVaultManager",
    "ObsidianNote",
    "templates"
]
