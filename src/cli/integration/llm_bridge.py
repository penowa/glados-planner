# src/cli/integration/llm_bridge.py
"""
Ponte para o sistema de LLM.
"""
class LLMBridge:
    def __init__(self, backend_integration):
        self.backend = backend_integration
        self._llm = None
        
    @property
    def llm(self):
        if self._llm is None:
            try:
                from src.core.llm.local_llm import LocalLLM
                self._llm = LocalLLM()
            except ImportError as e:
                print(f"⚠️ LocalLLM não disponível: {e}")
                self._llm = None
        return self._llm
    
    def query(self, question: str, context: str = None, user_name: str = "Usuário"):
        """Faz uma consulta ao LLM."""
        if not self.llm:
            return "Sistema de LLM não disponível. Por favor, inicialize o backend."
        
        try:
            return self.llm.generate(
                query=question,
                user_name=user_name,
                use_semantic=True,
                context=context
            )
        except Exception as e:
            return f"Erro ao consultar LLM: {str(e)}"
