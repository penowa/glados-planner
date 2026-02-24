"""
Runtime LLM backend selector (local or cloud).
"""
from __future__ import annotations

import sys
from typing import Any, Dict, Optional

from core.config.settings import settings


class LLMBackendProxy:
    """Lazy proxy that routes calls to the backend selected in settings.llm.backend."""

    def __init__(self):
        self._backend: Any = None
        self._backend_kind: str = ""

    def _desired_backend_kind(self) -> str:
        value = str(getattr(settings.llm, "backend", "local") or "local").strip().lower()
        return value if value in {"local", "cloud"} else "local"

    def _build_backend(self, kind: str):
        if kind == "cloud":
            from core.llm.cloud_llm import CloudLLM

            return CloudLLM()

        from core.llm.local_llm import LocalLLM

        return LocalLLM()

    def _ensure_backend(self):
        kind = self._desired_backend_kind()
        if self._backend is None or self._backend_kind != kind:
            self._backend = self._build_backend(kind)
            self._backend_kind = kind
            print(f"🧠 Backend LLM ativo: {kind}")
        return self._backend

    def reload(self):
        self._backend = None
        self._backend_kind = ""
        return self._ensure_backend()

    @staticmethod
    def _build_manual_context_query(query: str, context: Optional[str]) -> str:
        clean_query = str(query or "").strip()
        clean_context = str(context or "").strip()
        if not clean_context:
            return clean_query
        return (
            "### INICIO_CONTEXTO_NOTAS ###\n"
            f"{clean_context}\n"
            "### FIM_CONTEXTO_NOTAS ###\n"
            "### PERGUNTA_USUARIO ###\n"
            f"Pergunta do usuário: {clean_query}"
        )

    def is_available(self) -> bool:
        backend = self._ensure_backend()
        if hasattr(backend, "get_status"):
            try:
                status = backend.get_status()
                state = str(status.get("status", "")).lower()
                if state in {"loaded", "ready", "success"}:
                    return True
                if state in {"error", "not_loaded"}:
                    return False
            except Exception:
                pass
        return backend is not None

    def generate(
        self,
        query: str,
        user_name: Optional[str] = None,
        use_semantic: bool = True,
        request_metadata: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **_kwargs,
    ) -> Dict[str, Any]:
        backend = self._ensure_backend()
        composed_query = self._build_manual_context_query(query, context)
        effective_user = user_name or getattr(settings.llm.glados, "user_name", "Usuario")

        metadata: Dict[str, Any] = dict(request_metadata or {})
        previous_max_tokens: Optional[int] = None
        requested_tokens: Optional[int] = None
        if context:
            metadata.setdefault("manual_context_chars", len(str(context)))
        if max_tokens is not None:
            requested_tokens = int(max_tokens)
            metadata.setdefault("requested_max_tokens", requested_tokens)
            previous_max_tokens = int(getattr(settings.llm, "max_tokens", requested_tokens) or requested_tokens)
            if hasattr(backend, "set_generation_params"):
                try:
                    backend.set_generation_params(max_tokens=requested_tokens)
                except Exception:
                    pass

        try:
            try:
                result = backend.generate(
                    query=composed_query,
                    user_name=effective_user,
                    use_semantic=use_semantic,
                    request_metadata=metadata,
                )
            except TypeError:
                # Compatibilidade com assinaturas antigas que não aceitam request_metadata.
                result = backend.generate(
                    query=composed_query,
                    user_name=effective_user,
                    use_semantic=use_semantic,
                )
        finally:
            if (
                requested_tokens is not None
                and previous_max_tokens is not None
                and previous_max_tokens != requested_tokens
                and hasattr(backend, "set_generation_params")
            ):
                try:
                    backend.set_generation_params(max_tokens=previous_max_tokens)
                except Exception:
                    pass

        if isinstance(result, dict):
            return result
        return {
            "text": str(result),
            "status": "success",
            "model": str(getattr(settings.llm, "model_name", "llm")),
        }

    def query(self, prompt: str, context: str = None, user_name: str = None):
        result = self.generate(
            query=str(prompt or ""),
            context=context,
            user_name=user_name,
            use_semantic=True,
            request_metadata={"source": "query_api"},
        )
        if isinstance(result, dict):
            return result.get("text", "")
        return str(result)

    def __getattr__(self, name: str):
        backend = self._ensure_backend()
        return getattr(backend, name)


def get_llm_backend():
    return llm._ensure_backend()


llm = LLMBackendProxy()


if __name__ == "core.llm.backend_router":
    sys.modules.setdefault("src.core.llm.backend_router", sys.modules[__name__])
elif __name__ == "src.core.llm.backend_router":
    sys.modules.setdefault("core.llm.backend_router", sys.modules[__name__])
