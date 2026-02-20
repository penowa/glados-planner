"""
Módulo LocalLLM para gerenciar o TinyLlama com GLaDOS
Versão com busca semântica integrada (Sembrain)
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import hashlib
import pickle
from datetime import datetime
import re

from core.config.settings import settings
from core.llm.glados.models.tinyllama_wrapper import TinyLlamaGlados, LlamaConfig
from core.llm.glados.brain.vault_connector import VaultStructure
from core.llm.glados.personality.glados_voice import GladosVoice
from core.llm.runtime_discovery import (
    detect_nvidia_gpus,
    pick_model_path,
)

class LocalLLM:
    """Gerenciador do LLM local com busca semântica integrada"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalLLM, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model = None
        self.vault_structure = None
        self.sembrain = None
        self.response_cache = {}
        self.query_history = []
        self.runtime_info: Dict[str, Any] = {
            "models": [],
            "gpus": [],
            "selected_gpu": None,
            "device_mode": getattr(settings.llm, "device_mode", "auto"),
            "use_gpu": bool(getattr(settings.llm, "use_gpu", True)),
            "use_cpu": bool(getattr(settings.llm, "use_cpu", True)),
        }
        
        # Obter diretório base do projeto
        base_dir = Path(__file__).parent.parent.parent.parent
        
        model_path_text, discovered_models = pick_model_path(
            explicit_model_path=str(getattr(settings.llm, "model_path", "") or ""),
            models_dir=str(getattr(settings.llm, "models_dir", settings.paths.models_dir)),
            model_name=str(getattr(settings.llm, "model_name", "") or ""),
        )
        self.runtime_info["models"] = discovered_models
        model_path = Path(model_path_text) if model_path_text else None

        if model_path is None or not model_path.exists():
            expected_dir = str(getattr(settings.llm, "models_dir", settings.paths.models_dir))
            print(f"❌ Nenhum modelo GGUF válido encontrado em: {expected_dir}")
            print("   📥 Configure um .gguf em Configurações > LLM.")
            self._initialized = True
            return
        
        try:
            # Configuração de threads por modo:
            # - cpu_only: respeita integralmente o valor configurado pelo usuário.
            # - gpu_only: limita a 2 threads para reduzir uso de CPU auxiliar.
            # - demais modos: mantém teto conservador de 4.
            device_mode = str(getattr(settings.llm, "device_mode", "auto") or "auto").lower()
            requested_threads = max(1, int(getattr(settings.llm.cpu, "threads", 4) or 4))
            if device_mode == "cpu_only":
                cpu_threads = requested_threads
            elif device_mode == "gpu_only":
                cpu_threads = min(requested_threads, 2)
            else:
                cpu_threads = min(requested_threads, 4)
            gpu_devices = detect_nvidia_gpus()
            selected_gpu = None
            selected_gpu_name = ""
            if gpu_devices:
                gpu_index = int(getattr(settings.llm, "gpu_index", 0) or 0)
                for gpu in gpu_devices:
                    if int(gpu.get("index", -1)) == gpu_index:
                        selected_gpu = gpu
                        selected_gpu_name = str(gpu.get("name", ""))
                        break
                if selected_gpu is None:
                    selected_gpu = gpu_devices[0]
                    selected_gpu_name = str(selected_gpu.get("name", ""))
                    try:
                        settings.llm.gpu_index = int(selected_gpu.get("index", 0))
                    except Exception:
                        pass

            self.runtime_info["gpus"] = gpu_devices
            self.runtime_info["selected_gpu"] = selected_gpu

            config = LlamaConfig(
                model_path=str(model_path),
                n_ctx=settings.llm.n_ctx,
                n_gpu_layers=settings.llm.n_gpu_layers,
                use_gpu=bool(getattr(settings.llm, "use_gpu", True)),
                use_cpu=bool(getattr(settings.llm, "use_cpu", True)),
                device_mode=str(getattr(settings.llm, "device_mode", "auto")),
                gpu_index=int(getattr(settings.llm, "gpu_index", 0) or 0),
                vram_soft_limit_mb=int(getattr(settings.llm, "vram_soft_limit_mb", 0) or 0),
                gpu_name=selected_gpu_name,
                temperature=settings.llm.temperature,
                top_p=settings.llm.top_p,
                repeat_penalty=settings.llm.repeat_penalty,
                max_tokens=settings.llm.max_tokens,
                n_threads=cpu_threads,
                n_batch=settings.llm.cpu.batch_size,
                use_mlock=settings.llm.cpu.use_mlock,
                verbose=False
            )
            
            # Vault structure
            vault_path = Path(settings.paths.vault).expanduser()
            if not vault_path.is_absolute():
                vault_path = base_dir / vault_path
            
            print(f"📂 Carregando vault: {vault_path}")
            self.vault_structure = VaultStructure(str(vault_path))
            
            # Inicializar Sembrain se configurado
            # CORREÇÃO: acessar diretamente o atributo, não usar .get()
            if hasattr(settings.llm, 'use_semantic_search') and settings.llm.use_semantic_search:
                self._init_sembrain()
            
            # Glados voice
            glados_voice = GladosVoice()
            
            # Instanciar o TinyLlamaGlados
            self.model = TinyLlamaGlados(config, self.vault_structure, glados_voice)
            if self.model is not None:
                print(
                    f"🧩 Runtime LLM: mode={config.device_mode} | "
                    f"use_gpu={config.use_gpu} | use_cpu={config.use_cpu} | "
                    f"device={self.model.runtime_device}"
                )
            
            # Carregar cache se existir
            self._load_cache()
            
            self._initialized = True
            print("✅ LLM local inicializado com busca semântica")
            
        except Exception as e:
            print(f"❌ Erro inicializando LLM: {e}")
            import traceback
            traceback.print_exc()
            self._initialized = True
    
    def _init_sembrain(self):
        """Inicializa o sistema de busca semântica"""
        try:
            from core.llm.glados.brain.semantic_search import Sembrain
            
            # CORREÇÃO: usar get_all_notes() que agora existe
            notes = self.vault_structure.get_all_notes()
            vault_path = Path(settings.paths.vault).expanduser()
            
            self.sembrain = Sembrain(vault_path, notes)
            print(f"🧠 Sembrain inicializado: {len(notes)} notas indexadas")
            
        except ImportError as e:
            print(f"⚠️  Sembrain não disponível: {e}")
            print("   Usando busca textual básica")
        except Exception as e:
            print(f"⚠️  Erro inicializando Sembrain: {e}")
    
    def _get_cache_key(self, query: str, user_name: str = None) -> str:
        """Gera chave única para cache"""
        key_data = f"{query}_{user_name or 'default'}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _load_cache(self):
        """Carrega cache de respostas do disco"""
        cache_path = Path("./data/cache/llm_responses.pkl")
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    self.response_cache = pickle.load(f)
                print(f"📦 Cache carregado: {len(self.response_cache)} respostas")
            except Exception as e:
                print(f"⚠️  Erro carregando cache: {e}")
                self.response_cache = {}
    
    def _save_cache(self):
        """Salva cache de respostas no disco"""
        try:
            cache_path = Path("./data/cache/llm_responses.pkl")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(self.response_cache, f)
        except Exception as e:
            print(f"⚠️  Erro salvando cache: {e}")

    def _sanitize_response_text(self, text: str) -> str:
        """Limpa vazamentos evidentes de prompt quando vindos do cache/geração."""
        value = (text or "").strip()
        if not value:
            return value

        for marker in (
            "Responda como GLaDOS:",
            "Sinta as notas acima do vault e responda:",
            "Responda no estilo GLaDOS:",
            "[CONSULTA AO CÉREBRO DE GLaDOS",
            "[FIM DA CONSULTA AO CÉREBRO]",
        ):
            if marker in value:
                before, _after = value.split(marker, 1)
                if len(before.strip()) >= 40:
                    value = before.strip()
                break

        lines = []
        for line in value.splitlines():
            if re.match(r"^\s*\d+\.\s*(Seja útil academicamente|Use tom sarcástico.*|Baseie-se no contexto acima|Seja conciso.*|Assine como GLaDOS)\s*$", line, flags=re.IGNORECASE):
                continue
            lines.append(line)

        value = "\n".join(lines).strip()
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value

    def set_generation_params(
        self,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        repeat_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Atualiza parâmetros de geração no modelo ativo."""
        if self.model is None or not hasattr(self.model, "config"):
            return {"updated": False, "reason": "model_not_loaded"}

        cfg = self.model.config
        if temperature is not None:
            cfg.temperature = float(max(0.0, min(temperature, 1.2)))
        if top_p is not None:
            cfg.top_p = float(max(0.1, min(top_p, 1.0)))
        if repeat_penalty is not None:
            cfg.repeat_penalty = float(max(1.0, min(repeat_penalty, 1.3)))
        if max_tokens is not None:
            cfg.max_tokens = int(max(64, min(max_tokens, 700)))

        return {
            "updated": True,
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "repeat_penalty": cfg.repeat_penalty,
            "max_tokens": cfg.max_tokens,
        }
    
    def generate(
        self,
        query: str,
        user_name: str = None,
        use_semantic: bool = True,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Gera resposta para uma consulta com contexto semântico"""
        metadata = request_metadata or {}
        
        # Verificar cache primeiro
        cache_key = self._get_cache_key(query, user_name)
        if cache_key in self.response_cache:
            cached_time, response = self.response_cache[cache_key]
            if (datetime.now().timestamp() - cached_time) < 3600:  # 1 hora
                print("⚡ Resposta do cache")
                response = dict(response)
                response["text"] = self._sanitize_response_text(response.get("text", ""))
                response["request_metadata"] = metadata
                return {
                    **response,
                    "cached": True,
                    "cache_key": cache_key
                }
        
        if self.model is None:
            return {
                "text": "LLM não disponível. Verifique se o modelo está instalado em data/models/",
                "error": "Model not loaded",
                "suggestions": [
                    "Baixe TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf",
                    "Coloque em ./data/models/",
                    "Verifique o caminho em config/settings.yaml"
                ]
            }

        if (
            str(getattr(settings.llm, "device_mode", "auto")).lower() == "gpu_only"
            and getattr(self.model, "llm", None) is None
        ):
            details = str(getattr(self.model, "runtime_init_error", "") or "").strip()
            attempted = getattr(self.model, "runtime_gpu_attempts", []) or []
            attempted_text = ",".join(str(x) for x in attempted) if attempted else "n/d"
            if not details:
                details = "modelo não carregou na GPU (causa não informada pelo backend)."
            return {
                "text": (
                    "LLM indisponível na GPU (modo gpu_only estrito). "
                    f"Diagnóstico: {details} "
                    f"[gpu_index={getattr(settings.llm, 'gpu_index', 0)}, "
                    f"n_gpu_layers={getattr(settings.llm, 'n_gpu_layers', 0)}, "
                    f"tentativas={attempted_text}, "
                    f"vram_soft_limit_mb={getattr(settings.llm, 'vram_soft_limit_mb', 0)}]"
                ),
                "model": "None",
                "status": "error",
                "error": f"gpu_only: model not loaded on GPU ({details})",
            }
        
        if user_name is None:
            user_name = settings.llm.glados.user_name
        
        # Obter contexto semântico se disponível
        semantic_context = ""
        if use_semantic and self.sembrain:
            try:
                semantic_context = self.sembrain.get_context_for_llm(query, max_notes=3)
                print(f"🧠 Contexto semântico: {len(semantic_context)} caracteres")
            except Exception as e:
                print(f"⚠️  Erro obtendo contexto semântico: {e}")
        
        try:
            response = self.model.generate_response(
                query,
                user_name,
                extra_context=semantic_context,
            )
            
            # Registrar no histórico
            self.query_history.append({
                "query": query,
                "response": response[:100] + "..." if len(response) > 100 else response,
                "timestamp": datetime.now().isoformat(),
                "used_semantic": use_semantic and bool(semantic_context),
                "request_metadata": metadata,
            })
            
            # Limitar histórico
            if len(self.query_history) > 100:
                self.query_history = self.query_history[-100:]
            
            # Salvar no cache
            result = {
                "text": self._sanitize_response_text(response),
                "model": "TinyLlama-1.1B",
                "status": "success",
                "semantic_context_used": use_semantic and bool(semantic_context),
                "timestamp": datetime.now().isoformat(),
                "request_metadata": metadata,
            }
            
            self.response_cache[cache_key] = (datetime.now().timestamp(), result)
            
            # Limitar cache
            if len(self.response_cache) > 500:
                # Remove as mais antigas
                sorted_keys = sorted(self.response_cache.keys(), 
                                   key=lambda k: self.response_cache[k][0])
                keys_to_remove = sorted_keys[:100]
                for key in keys_to_remove:
                    del self.response_cache[key]
            
            # Salvar cache periodicamente
            if len(self.response_cache) % 50 == 0:
                self._save_cache()
            
            return result
            
        except Exception as e:
            error_msg = f"Erro gerando resposta: {e}"
            print(f"❌ {error_msg}")

            if str(getattr(settings.llm, "device_mode", "auto")).lower() == "gpu_only":
                return {
                    "text": "Falha na geração em modo gpu_only. Ajuste n_gpu_layers/libere VRAM.",
                    "model": "None",
                    "status": "error",
                    "error": str(e),
                }
            
            # Fallback para resposta sem LLM
            if self.sembrain:
                try:
                    results = self.sembrain.search(query, limit=3)
                    if results:
                        fallback_response = "Com base nas suas notas:\n\n"
                        for i, result in enumerate(results, 1):
                            fallback_response += f"{i}. **{result.note.title}**\n"
                            if result.excerpt:
                                fallback_response += f"   {result.excerpt[:200]}...\n\n"
                        return {
                            "text": fallback_response,
                            "model": "Sembrain-Fallback",
                            "status": "fallback",
                            "error": str(e)
                        }
                except Exception as inner_e:
                    print(f"⚠️  Fallback também falhou: {inner_e}")
            
            return {
                "text": "Desculpe, ocorreu um erro ao processar sua consulta.",
                "model": "None",
                "status": "error",
                "error": str(e)
            }
    
    def get_semantic_context(self, query: str, max_notes: int = 3) -> Optional[str]:
        """Obtém contexto semântico para uma consulta"""
        if self.sembrain is None:
            return None
        
        try:
            return self.sembrain.get_context_for_llm(query, max_notes)
        except Exception as e:
            print(f"Erro obtendo contexto semântico: {e}")
            return None
    
    def search_notes(self, query: str, limit: int = 5, use_semantic: bool = True) -> List[Dict]:
        """Busca notas no vault"""
        if use_semantic and self.sembrain:
            try:
                results = self.sembrain.search(query, limit)
                return [
                    {
                        "title": result.note.title,
                        "path": str(result.note.path),
                        "relevance": result.relevance,
                        "excerpt": result.excerpt[:200] if result.excerpt else None,
                        "tags": getattr(result.note, 'tags', []),
                        "search_type": "semantic"
                    }
                    for result in results
                ]
            except Exception as e:
                print(f"⚠️  Busca semântica falhou: {e}")
        
        # Fallback para busca textual
        if self.vault_structure:
            try:
                notes = self.vault_structure.search_notes(query, limit)
                return [
                    {
                        "title": note.title,
                        "path": str(note.path),
                        "relevance": 0.5,  # Default
                        "excerpt": note.content[:200] if hasattr(note, 'content') else None,
                        "tags": getattr(note, 'tags', []),
                        "search_type": "textual"
                    }
                    for note in notes
                ]
            except Exception as e:
                print(f"⚠️  Busca textual falhou: {e}")
        
        return []
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status detalhado do LLM"""
        if self.model is None:
            return {
                "status": "not_loaded",
                "message": "Modelo não carregado",
                "runtime": self.runtime_info,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            stats = self.model.get_stats()
            
            status = {
                "status": "loaded" if stats.get("model_loaded", False) else "error",
                "model": stats.get("config", {}).get("model", "Unknown"),
                "runtime": {
                    "backend": stats.get("runtime", {}).get("backend", "unknown"),
                    "device": stats.get("runtime", {}).get("device", "unknown"),
                    "device_mode": self.runtime_info.get("device_mode"),
                    "use_gpu": self.runtime_info.get("use_gpu"),
                    "use_cpu": self.runtime_info.get("use_cpu"),
                    "selected_gpu": self.runtime_info.get("selected_gpu"),
                    "available_gpus": self.runtime_info.get("gpus", []),
                    "available_models": self.runtime_info.get("models", []),
                },
                "cache": {
                    "hits": stats.get("cache_hits", 0),
                    "misses": stats.get("cache_misses", 0),
                    "size": stats.get("cache_size", 0)
                },
                "performance": {
                    "total_queries": len(self.query_history),
                    "response_cache_size": len(self.response_cache),
                    "last_queries": self.query_history[-5:] if self.query_history else []
                },
                "sembrain": {
                    "available": self.sembrain is not None,
                    "notes_indexed": self.sembrain.get_stats().get("total_notes", 0) if self.sembrain else 0
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Erro obtendo status: {e}",
                "timestamp": datetime.now().isoformat()
            }
    
    def clear_cache(self, cache_type: str = "all"):
        """Limpa cache do sistema"""
        if cache_type in ["all", "responses"]:
            self.response_cache.clear()
            print("🧹 Cache de respostas limpo")
        
        if cache_type in ["all", "history"]:
            self.query_history.clear()
            print("🧹 Histórico de consultas limpo")
        
        if self.sembrain:
            if cache_type in ["all", "semantic"]:
                # O Sembrain tem seu próprio cache interno
                print("ℹ️  Para limpar cache semântico, use 'glados limpar-cache' na CLI")
        
        self._save_cache()
    
    def save_state(self):
        """Salva estado atual do LLM"""
        try:
            self._save_cache()
            print("💾 Estado do LLM salvo")
        except Exception as e:
            print(f"⚠️  Erro salvando estado: {e}")

# Evita duplicação de módulo por imports mistos (core.* vs src.core.*),
# que podem levar ao carregamento duplicado do modelo em RAM.
if __name__ == "core.llm.local_llm":
    sys.modules.setdefault("src.core.llm.local_llm", sys.modules[__name__])
elif __name__ == "src.core.llm.local_llm":
    sys.modules.setdefault("core.llm.local_llm", sys.modules[__name__])

# Instância global
llm = LocalLLM()
