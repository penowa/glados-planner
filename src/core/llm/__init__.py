"""
Modulo LLM - Exporta o backend selecionado (local/cloud)
"""

def __getattr__(name):
    if name == "llm":
        from .backend_router import llm as _llm
        return _llm
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["llm"]
