"""
Wrapper do TinyLlama 1.1B para integração com GLaDOS
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import time
import re
import os
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
    temperature: float = 0.35
    top_p: float = 0.9
    repeat_penalty: float = 1.12
    max_tokens: int = 384
    n_threads: int = 4
    n_batch: int = 128
    use_mlock: bool = True
    verbose: bool = False

class TinyLlamaGlados:
    """Wrapper do TinyLlama com personalidade GLaDOS"""
    
    def __init__(self, config: LlamaConfig, vault_structure: Any, glados_voice: Any):
        # Limite rígido de threads para evitar saturação de CPU por bibliotecas nativas.
        safe_threads = max(1, min(int(config.n_threads or 4), 4))
        config.n_threads = safe_threads
        config.n_batch = max(32, min(int(config.n_batch or 128), 256))
        os.environ["OMP_NUM_THREADS"] = str(safe_threads)
        os.environ["OPENBLAS_NUM_THREADS"] = str(safe_threads)
        os.environ["MKL_NUM_THREADS"] = str(safe_threads)
        os.environ["NUMEXPR_NUM_THREADS"] = str(safe_threads)

        self.config = config
        self.vault = vault_structure
        self.glados_voice = glados_voice
        
        # Inicializa o modelo se disponível
        self.llm = None
        if LLAMA_AVAILABLE:
            try:
                llama_kwargs = {
                    "model_path": config.model_path,
                    "n_ctx": config.n_ctx,
                    "n_gpu_layers": config.n_gpu_layers,
                    "n_threads": config.n_threads,
                    "n_threads_batch": config.n_threads,
                    "n_batch": config.n_batch,
                    "use_mlock": config.use_mlock,
                    "verbose": config.verbose,
                }
                try:
                    self.llm = Llama(**llama_kwargs)
                except TypeError:
                    # Fallback para versões antigas do llama-cpp com assinatura menor.
                    self.llm = Llama(
                        model_path=config.model_path,
                        n_ctx=config.n_ctx,
                        n_gpu_layers=config.n_gpu_layers,
                        n_threads=config.n_threads,
                        n_threads_batch=config.n_threads,
                        verbose=config.verbose,
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
        
        # Prompt minimalista para modelo pequeno: só identidade, usuário e contexto útil.
        minimal_template = """Sistema: Você é GLaDOS.
Usuário: {user_name}

Contexto do vault (use apenas se relevante):
{context}

Pergunta do usuário:
{query}

Instruções:
- Responda em português claro e objetivo.
- Priorize precisão e utilidade.
- Não repita o contexto literalmente.
- Faça síntese/paráfrase em vez de copiar trechos longos.
- Se citar, use no máximo uma frase curta.
- Se o contexto for insuficiente, diga explicitamente.

Resposta:
"""
        self.prompt_templates = {
            "concept_explanation": minimal_template,
            "vault_search": minimal_template,
            "philosophical_question": minimal_template,
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

    def _sanitize_model_output(self, output: str) -> str:
        """
        Remove vazamentos comuns de prompt/instruções quando o modelo ecoa o template.
        Mantém o conteúdo útil e reduz a chance de mostrar instruções internas ao usuário.
        """
        text = (output or "").strip()
        if not text:
            return text

        # Se o modelo ecoar delimitadores de resposta, prioriza o trecho após eles.
        for marker in ("[RESPOSTA GLaDOS]", "[RESPOSTA]"):
            if marker in text:
                candidate = text.rsplit(marker, 1)[-1].strip()
                if candidate:
                    text = candidate

        # Remove blocos de instrução quando aparecem após uma resposta válida.
        leak_markers = (
            "Responda como GLaDOS:",
            "Sinta as notas acima do vault e responda:",
            "Responda no estilo GLaDOS:",
        )
        for marker in leak_markers:
            if marker in text:
                before, after = text.split(marker, 1)
                # Se já há conteúdo substancial antes do marcador, descarta o resto.
                if len(before.strip()) >= 40:
                    text = before.strip()
                else:
                    text = after.strip()
                break

        # Remove linhas de prompt que às vezes vazam no corpo da resposta.
        drop_line_patterns = (
            r"^\s*\[CONTEXTO.*\]\s*$",
            r"^\s*\[INSTRUÇÕES.*\]\s*$",
            r"^\s*Usuário:\s*.*$",
            r"^\s*Pergunta( filosófica)?:\s*.*$",
            r"^\s*Consulta:\s*.*$",
            r"^\s*\d+\.\s*(Seja útil academicamente|Use tom sarcástico.*|Baseie-se no contexto acima|Seja conciso.*|Assine como GLaDOS)\s*$",
        )
        cleaned_lines = []
        for line in text.splitlines():
            if any(re.match(pattern, line, flags=re.IGNORECASE) for pattern in drop_line_patterns):
                continue
            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines).strip()

        # Compacta quebras exageradas.
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _extract_manual_context(self, query: str) -> tuple[str, str]:
        """
        Extrai contexto/manual e pergunta quando a UI envia payload delimitado.
        Retorna (user_query, inline_context).
        """
        text = (query or "").strip()
        if not text:
            return "", ""

        ctx_start = "### INICIO_CONTEXTO_NOTAS ###"
        ctx_end = "### FIM_CONTEXTO_NOTAS ###"
        q_marker = "### PERGUNTA_USUARIO ###"

        if ctx_start not in text or ctx_end not in text or q_marker not in text:
            return text, ""

        try:
            context_part = text.split(ctx_start, 1)[1].split(ctx_end, 1)[0].strip()
            question_part = text.split(q_marker, 1)[1].strip()
            return question_part or text, context_part
        except Exception:
            return text, ""

    def _fit_prompt_budget(self, query: str, context: str) -> tuple[str, int]:
        """
        Ajusta o contexto para caber na janela de contexto do modelo.
        Retorna (contexto_ajustado, max_tokens_geracao).
        """
        # Estimativa simples: ~4 chars por token em PT.
        safety_tokens = 64
        base_limit = max(256, int(self.config.n_ctx) - safety_tokens)
        target_max_tokens = int(self.config.max_tokens)
        context_work = context or ""

        def estimate_tokens(text: str) -> int:
            return max(1, len(text) // 4)

        # Reserva tokens para instruções + pergunta + resposta.
        while True:
            prompt_estimate = estimate_tokens(query) + estimate_tokens(context_work) + 180
            available_for_generation = base_limit - prompt_estimate
            generation_tokens = min(target_max_tokens, max(64, available_for_generation))

            # Se ainda não há espaço mínimo, reduz o contexto gradualmente.
            if available_for_generation < 64 and len(context_work) > 1200:
                keep = int(len(context_work) * 0.75)
                context_work = context_work[:keep]
                continue

            return context_work, generation_tokens
    
    def prepare_context(self, query: str) -> str:
        """Prepara contexto do vault para a consulta"""
        # Busca notas relevantes no vault
        relevant_notes = self.vault.search_notes(query, limit=3)
        
        if not relevant_notes:
            return "Sem contexto relevante no vault."
        
        return self.vault.format_as_brain_context(relevant_notes)
    
    def generate_response(
        self,
        query: str,
        user_name: str,
        mode: str = "concept_explanation",
        extra_context: str = "",
    ) -> str:
        """Gera resposta usando TinyLlama"""
        clean_query, inline_context = self._extract_manual_context(query)
        extra = (extra_context or "").strip()

        # Se a UI já enviou contexto explícito das notas, não buscar novamente no vault
        # para evitar prompt gigante e respostas coladas.
        if inline_context:
            context_parts = [part for part in (inline_context, extra) if part]
            context = "\n\n".join(context_parts) if context_parts else "Sem contexto relevante no vault."
        else:
            base_context = self.prepare_context(clean_query)
            context = f"{extra}\n\n{base_context}" if extra else base_context
        
        # Verifica cache
        cache_key = self._create_cache_key(clean_query, context)
        cached_response = self._get_from_cache(cache_key)
        
        if cached_response:
            print(f"[GLaDOS] Cache hit: {self.cache_hits}/{self.cache_hits + self.cache_misses}")
            sanitized_cached = self._sanitize_model_output(cached_response)
            return self.glados_voice.format_response(
                clean_query,
                sanitized_cached,
                include_intro=False,
                include_signature=False,
            )
        
        # Ajustar tamanho do contexto para evitar estouro da janela do modelo.
        context, generation_max_tokens = self._fit_prompt_budget(clean_query, context)

        # Prepara prompt
        template = self.prompt_templates.get(mode, self.prompt_templates["concept_explanation"])
        prompt = template.format(
            context=context,
            user_name=user_name,
            query=clean_query,
            max_tokens=self.config.max_tokens
        )
        
        # Gera resposta
        if self.llm is not None:
            # Usa modelo real
            try:
                output = self.llm(
                    prompt,
                    max_tokens=generation_max_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    repeat_penalty=self.config.repeat_penalty,
                    echo=False
                )
                
                raw_response = output["choices"][0]["text"].strip()
            except Exception as e:
                print(f"[GLaDOS] Erro na geração: {e}")
                raw_response = self._fallback_response(clean_query, context)
        else:
            # Modo simulado
            raw_response = self._simulated_response(query, context)

        raw_response = self._sanitize_model_output(raw_response)
        
        # Formata no modo mínimo para preservar tokens para o conteúdo.
        final_response = self.glados_voice.format_response(
            clean_query,
            raw_response,
            include_intro=False,
            include_signature=False,
        )
        
        # Adiciona ao cache
        self._add_to_cache(cache_key, raw_response)
        
        return final_response
    
    def _fallback_response(self, query: str, context: str) -> str:
        """Resposta de fallback quando o modelo falha"""
        return (
            f"Não consegui processar totalmente a pergunta '{query}' desta vez. "
            "Reformule em uma frase mais direta ou peça um resumo objetivo do texto."
        )
    
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
