from pathlib import Path
from typing import Optional

from .vault_manager import ObsidianVaultManager


class LazyObsidianVaultManager:
    """Proxy que posterga o carregamento completo do vault até o primeiro uso real."""

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = Path(vault_path).expanduser().resolve() if vault_path else None
        self._manager: Optional[ObsidianVaultManager] = None

    def is_connected(self) -> bool:
        """Validação leve do path, sem escanear o vault."""
        return bool(self.vault_path and self.vault_path.exists() and self.vault_path.is_dir())

    def ensure_loaded(self) -> ObsidianVaultManager:
        """Carrega o manager real apenas quando necessário."""
        if self._manager is None:
            self._manager = ObsidianVaultManager.instance(
                str(self.vault_path) if self.vault_path else None
            )
        return self._manager

    def __getattr__(self, item):
        return getattr(self.ensure_loaded(), item)
