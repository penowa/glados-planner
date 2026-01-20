# src/cli/integration/reading_bridge.py
"""
Ponte para o módulo de leitura.
"""
class ReadingBridge:
    def __init__(self, backend_integration):
        self.backend = backend_integration
        self._reading_manager = None
        
    @property
    def reading_manager(self):
        if self._reading_manager is None:
            try:
                from src.core.modules.reading_manager import ReadingManager
                self._reading_manager = ReadingManager()
            except ImportError as e:
                print(f"⚠️ ReadingManager não disponível: {e}")
                self._reading_manager = None
        return self._reading_manager
    
    def get_active_books(self):
        """Obtém livros em leitura ativa."""
        if not self.reading_manager:
            return []
        
        try:
            # Implementar chamada real
            return []
        except Exception as e:
            print(f"Erro ao obter livros ativos: {e}")
            return []
