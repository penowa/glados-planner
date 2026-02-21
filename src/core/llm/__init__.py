"""
Módulo LLM - Exporta a instância do LLM local
"""

def __getattr__(name):
    if name == "llm":
        from .local_llm import llm as _llm
        return _llm
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["llm"]
