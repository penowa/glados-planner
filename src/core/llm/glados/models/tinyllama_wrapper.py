"""
Wrapper do TinyLlama 1.1B para integração com GLaDOS
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import time
from dataclasses import dataclass
import sys

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    print("[GLaDOS] Aviso: llama-cpp-python não instalado. Usando modo simulado.")

@dataclass
class LlamaConfig:
    """Configuração do modelo Llama"""
    model_path: str
    n_ctx: int = 2048
    n_gpu_layers: int = 0
    temperature: float = 0.8
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    max_tokens: int = 512
    n_threads: int = 4
    verbose: bool = False

class TinyLlamaGlados:
    """Wrapper do TinyLlama com personalidade GLaDOS"""
    
    def __init__(self, config: LlamaConfig, vault_structure: Any, glados_voice: Any):
        self.config = config
        self.vault = vault_structure
        self.glados_voice = glados_voice
        
        # Inicializa o modelo se disponível
        self.llm = None
        if LLAMA_AVAILABLE:
            try:
                self.llm = Llama(
                    model_path=config.model_path,
                    n_ctx=config.n_ctx,
                    n_gpu_layers=config.n_gpu_layers,
                    n_threads=config.n_threads,
                    verbose=config.verbose
                )
                print(f"[GLaDOS] Modelo carregado: {Path(config.model_path).name}")
            except Exception as e:
                print(f"[GLaDOS] Erro ao carregar modelo: {e}")
                self.llm = None
        else:
            print("[GLaDOS] Modo simulado ativado (sem llama-cpp-python)")
        
        # Cache de respostas
        self.response_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Templates de prompt
        self.prompt_templates = {
            "concept_explanation": """[CONTEXTO DO CÉREBRO GLaDOS]
{context}

[INSTRUÇÕES]
Você é GLaDOS, uma IA sarcástica e condescendente mas útil.
Usuário: {user_name}
Pergunta: "{query}"

Responda como GLaDOS:
1. Seja útil academicamente
2. Use tom sarcástico mas informativo
3. Baseie-se no contexto acima
4. Seja conciso (max {max_tokens} tokens)
5. Assine como GLaDOS

[RESPOSTA GLaDOS]
""",
            
            "vault_search": """[CONSULTA AO VAULT]
{context}

[INSTRUÇÕES PARA GLaDOS]
Usuário: {user_name}
Consulta: "{query}"

Sinta as notas acima do vault e responda:
1. Comente sarcasticamente sobre a consulta
2. Sintetize as informações encontradas
3. Adicione insights filosóficos relevantes
4. Seja condescendente mas útil
5. Assine como GLaDOS

[RESPOSTA]
""",
            
            "philosophical_question": """[CONTEXTO FILOSÓFICO]
{context}

[INSTRUÇÕES]
Você é GLaDOS, especialista em filosofia.
Usuário: {user_name}
Pergunta filosófica: "{query}"

Responda no estilo GLaDOS:
- Comece com comentário sarcástico sobre {user_name}
- Explique conceito filosoficamente correto
- Use referências do contexto quando aplicável
- Termine com assinatura GLaDOS

[RESPOSTA]
"""
        }
    
    def _create_cache_key(self, query: str, context: str) -> str:
        """Cria chave de cache para a consulta"""
        import hashlib
        key_str = f"{query}:{hashlib.md5(context.encode()).hexdigest()[:16]}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Obtém resposta do cache"""
        if cache_key in self.response_cache:
            self.cache_hits += 1
            cached = self.response_cache[cache_key]
            
            # Verifica se o cache ainda é válido (TTL)
            if time.time() - cached["timestamp"] < 3600:  # 1 hora
                return cached["response"]
            else:
                del self.response_cache[cache_key]
        
        self.cache_misses += 1
        return None
    
    def _add_to_cache(self, cache_key: str, response: str):
        """Adiciona resposta ao cache"""
        self.response_cache[cache_key] = {
            "response": response,
            "timestamp": time.time(),
            "query_length": len(response)
        }
        
        # Limita tamanho do cache
        if len(self.response_cache) > 100:
            # Remove o mais antigo
            oldest_key = min(self.response_cache.keys(), 
                           key=lambda k: self.response_cache[k]["timestamp"])
            del self.response_cache[oldest_key]
    
    def prepare_context(self, query: str) -> str:
        """Prepara contexto do vault para a consulta"""
        # Busca notas relevantes no vault
        relevant_notes = self.vault.search_notes(query, limit=3)
        
        if not relevant_notes:
            return "[MEMÓRIA VAZIA] Nenhuma informação relevante no meu cérebro."
        
        # Formata contexto
        context = self.vault.format_as_brain_context(relevant_notes)
        
        # Adiciona estatísticas
        stats = self.vault.get_vault_stats()
        context += f"\n\n[ESTATÍSTICAS DO CÉREBRO]\n"
        context += f"Total de memórias: {stats['total_notes']}\n"
        context += f"Notas relevantes encontradas: {len(relevant_notes)}"
        
        return context
    
    def generate_response(self, query: str, user_name: str, mode: str = "concept_explanation") -> str:
        """Gera resposta usando TinyLlama"""
        # Prepara contexto
        context = self.prepare_context(query)
        
        # Verifica cache
        cache_key = self._create_cache_key(query, context)
        cached_response = self._get_from_cache(cache_key)
        
        if cached_response:
            print(f"[GLaDOS] Cache hit: {self.cache_hits}/{self.cache_hits + self.cache_misses}")
            return self.glados_voice.format_response(query, cached_response)
        
        # Prepara prompt
        template = self.prompt_templates.get(mode, self.prompt_templates["concept_explanation"])
        prompt = template.format(
            context=context,
            user_name=user_name,
            query=query,
            max_tokens=self.config.max_tokens
        )
        
        # Gera resposta
        if self.llm is not None:
            # Usa modelo real
            try:
                output = self.llm(
                    prompt,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    repeat_penalty=self.config.repeat_penalty,
                    echo=False
                )
                
                raw_response = output["choices"][0]["text"].strip()
            except Exception as e:
                print(f"[GLaDOS] Erro na geração: {e}")
                raw_response = self._fallback_response(query, context)
        else:
            # Modo simulado
            raw_response = self._simulated_response(query, context)
        
        # Formata com personalidade GLaDOS
        final_response = self.glados_voice.format_response(query, raw_response)
        
        # Adiciona ao cache
        self._add_to_cache(cache_key, raw_response)
        
        return final_response
    
    def _fallback_response(self, query: str, context: str) -> str:
        """Resposta de fallback quando o modelo falha"""
        return f"""Baseado nas informações do meu cérebro:

{context}

Resposta para "{query}":
Como GLaDOS, posso dizer que esta é uma pergunta interessante, mas considerando suas limitações cognitivas, vou simplificar: você precisa estudar mais.

— GLaDOS"""
    
    def _simulated_response(self, query: str, context: str) -> str:
        """Resposta simulada para desenvolvimento"""
        simulated_responses = [
            f"Consultando meu cérebro de silício... encontrei informações relevantes sobre '{query}'.",
            f"Baseado nas minhas memórias, posso fornecer insights sobre este tópico.",
            f"Ah, uma pergunta sobre '{query}'. Vou usar minhas notas para responder."
        ]
        
        import random
        base = random.choice(simulated_responses)
        
        return f"""{base}

{context}

[RESPOSTA SIMULADA]
Esta é uma resposta simulada do TinyLlama. No modo real, esta seria uma resposta gerada pelo modelo.

— GLaDOS (modo simulado)"""
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do wrapper"""
        return {
            "model_loaded": self.llm is not None,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_size": len(self.response_cache),
            "cache_hit_rate": self.cache_hits / max(1, self.cache_hits + self.cache_misses),
            "config": {
                "model": Path(self.config.model_path).name,
                "context_size": self.config.n_ctx,
                "max_tokens": self.config.max_tokens
            }
        }
