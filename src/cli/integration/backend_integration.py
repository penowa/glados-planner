# src/cli/integration/backend_integration.py
"""
Singleton principal que gerencia todas as conexões com o backend.
"""
class BackendIntegration:
    """Gerencia todas as conexões com o backend."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._agenda_bridge = None
            self._reading_bridge = None
            self._llm_bridge = None
            self._obsidian_bridge = None
            self._database_bridge = None
            
    @property
    def agenda(self):
        if self._agenda_bridge is None:
            from .agenda_bridge import AgendaBridge
            self._agenda_bridge = AgendaBridge(self)
        return self._agenda_bridge
    
    @property
    def reading(self):
        if self._reading_bridge is None:
            from .reading_bridge import ReadingBridge
            self._reading_bridge = ReadingBridge(self)
        return self._reading_bridge
    
    @property
    def llm(self):
        if self._llm_bridge is None:
            from .llm_bridge import LLMBridge
            self._llm_bridge = LLMBridge(self)
        return self._llm_bridge
    
    @property
    def obsidian(self):
        if self._obsidian_bridge is None:
            from .obsidian_bridge import ObsidianBridge
            self._obsidian_bridge = ObsidianBridge(self)
        return self._obsidian_bridge
    
    @property
    def database(self):
        if self._database_bridge is None:
            from .database_bridge import DatabaseBridge
            self._database_bridge = DatabaseBridge(self)
        return self._database_bridge
    
    def is_ready(self) -> bool:
        """Verifica se todos os módulos estão prontos."""
        return all([
            self._agenda_bridge is not None,
            self._llm_bridge is not None
        ])

# Instância global
backend = BackendIntegration()

def get_backend():
    return backend
