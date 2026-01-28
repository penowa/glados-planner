"""
Ponte para o sistema de LLM.
"""
import logging
import hashlib
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class LLMBridge:
    def __init__(self, backend_integration):
        self.backend = backend_integration
        self._llm = None
        self._cache = {}
        self._cache_ttl = 3600  # 1 hora
        
    @property
    def llm(self):
        if self._llm is None:
            try:
                from src.core.llm.local_llm import LocalLLM
                self._llm = LocalLLM()
            except ImportError as e:
                logger.error(f"LocalLLM não disponível: {e}")
                self._llm = None
        return self._llm
    
    def is_available(self) -> bool:
        """Verifica se o módulo está disponível."""
        return self.llm is not None
    
    # API pública para a interface CLI
    
    def query(self, question: str, context: str = None, user_name: str = "Usuário"):
        """Faz uma consulta ao LLM."""
        if not self.is_available():
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
    
    def query_with_context(self, question: str, use_semantic: bool = True, 
                          max_tokens: int = 512, user_name: str = "Usuário",
                          context: str = None) -> Dict[str, Any]:
        """
        Faz uma consulta ao LLM com contexto do vault.
        
        Retorna um dicionário com:
        - response: resposta do LLM
        - sources: lista de fontes utilizadas
        - concepts: conceitos identificados
        - is_fallback: se é uma resposta de fallback
        """
        # Verificar cache primeiro
        cache_key = self._get_cache_key(question, use_semantic, max_tokens, user_name)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit para: {question[:50]}...")
            return cached
        
        if not self.is_available():
            return self._get_fallback_response(question)
        
        try:
            # Chamada real para o backend
            response = self.llm.generate(
                query=question,
                user_name=user_name,
                use_semantic=use_semantic,
                context=context,
                max_tokens=max_tokens
            )
            
            # Formatar resposta
            result = self._format_response(response, question)
            
            # Armazenar em cache
            self._store_in_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao consultar LLM: {e}")
            return self._get_fallback_response(question)
    
    def query_simple(self, question: str, user_name: str = "Usuário") -> str:
        """Consulta simples sem contexto semântico (para comandos rápidos)."""
        if not self.is_available():
            return "Sistema de LLM não disponível."
        
        try:
            return self.llm.generate(
                query=question,
                user_name=user_name,
                use_semantic=False,
                max_tokens=256
            )
        except Exception as e:
            return f"Erro ao consultar LLM: {str(e)}"
    
    def get_llm_status(self) -> Dict[str, Any]:
        """Obtém status do sistema LLM."""
        if not self.is_available():
            return {
                "available": False,
                "model": "Nenhum",
                "context_tokens": 0,
                "cache_size": 0,
                "is_fallback": True
            }
        
        try:
            return {
                "available": True,
                "model": getattr(self.llm, 'model_name', 'TinyLlama'),
                "context_tokens": 2048,
                "cache_size": len(self._cache),
                "is_fallback": False
            }
        except Exception as e:
            logger.error(f"Erro ao obter status: {e}")
            return {
                "available": False,
                "model": "Erro",
                "context_tokens": 0,
                "cache_size": 0,
                "is_fallback": True
            }
    
    # Métodos auxiliares
    
    def _get_cache_key(self, question: str, use_semantic: bool, 
                      max_tokens: int, user_name: str) -> str:
        """Gera chave de cache baseada nos parâmetros."""
        key_str = f"{question}:{use_semantic}:{max_tokens}:{user_name}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Obtém resposta do cache se ainda for válida."""
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if time.time() - cached_data['timestamp'] < self._cache_ttl:
                return cached_data['data']
        return None
    
    def _store_in_cache(self, cache_key: str, data: Dict[str, Any]):
        """Armazena resposta no cache."""
        self._cache[cache_key] = {
            'timestamp': time.time(),
            'data': data
        }
        
        # Limitar tamanho do cache
        if len(self._cache) > 100:
            # Remove o mais antigo
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k]['timestamp'])
            del self._cache[oldest_key]
    
    def _get_fallback_response(self, question: str) -> Dict[str, Any]:
        """Resposta de fallback quando o LLM não está disponível."""
        return {
            "response": "Desculpe, meu cérebro não está disponível no momento. "
                       "Por favor, verifique se o sistema de LLM está inicializado.",
            "sources": [],
            "concepts": [],
            "is_fallback": True
        }
    
    # Atualização do método _format_response no llm_bridge.py
    def _format_response(self, response: Any, question: str) -> Dict[str, Any]:
 
    # Se a resposta já tiver estrutura esperada
        if isinstance(response, dict):
            return {
                "response": response.get("response", str(response)),
                "sources": response.get("sources", []),
                "concepts": response.get("concepts", []),
                "is_fallback": False
            }
    
    # Se for string, tentar extrair fontes do backend Obsidian
        response_text = str(response)
        sources = []
        concepts = []
    
        try:
            # Tentar buscar fontes relacionadas da pergunta
            if self.backend.obsidian.is_available():
                search_results = self.backend.obsidian.search_notes(question, limit=3)
                if not search_results.get("is_fallback", True):
                    for note in search_results.get("notes", [])[:3]:
                        sources.append({
                            "path": note.get("path", ""),
                            "score": 0.7,  # Score padrão para busca textual
                            "title": note.get("title", "")
                        })
        except:
            pass
    
        # Extrair conceitos (palavras-chave da pergunta)
        import re
        keywords = re.findall(r'\b\w{4,}\b', question.lower())
        common_words = ['para', 'como', 'sobre', 'isso', 'este', 'essa', 'qual', 'quando']
        concepts = [kw for kw in keywords if kw not in common_words][:5]
    
        return {
            "response": response_text,
            "sources": sources,
            "concepts": concepts,
            "is_fallback": False
        }