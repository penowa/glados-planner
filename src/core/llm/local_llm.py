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

# Adiciona o diretório raiz do projeto ao path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.config.settings import settings
from src.core.llm.glados.models.tinyllama_wrapper import TinyLlamaGlados, LlamaConfig
from src.core.llm.glados.brain.vault_connector import VaultStructure
from src.core.llm.glados.personality.glados_voice import GladosVoice

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
        
        # Obter diretório base do projeto
        base_dir = Path(__file__).parent.parent.parent.parent
        
        # Verificar e expandir caminho do modelo
        model_path = Path(settings.llm.model_path)
        if not model_path.is_absolute():
            model_path = base_dir / model_path
        
        if not model_path.exists():
            print(f"❌ Modelo não encontrado: {model_path}")
            print(f"   📥 Baixe o modelo GGUF e coloque em: {model_path.parent}")
            self._initialized = True
            return
        
        try:
            # Configuração do modelo
            config = LlamaConfig(
                model_path=str(model_path),
                n_ctx=settings.llm.n_ctx,
                n_gpu_layers=settings.llm.n_gpu_layers,
                temperature=settings.llm.temperature,
                top_p=settings.llm.top_p,
                repeat_penalty=settings.llm.repeat_penalty,
                max_tokens=settings.llm.max_tokens,
                n_threads=settings.llm.cpu.threads,
                verbose=False
            )
            
            # Vault structure
            vault_path = Path(settings.paths.vault).expanduser()
            if not vault_path.is_absolute():
                vault_path = base_dir / vault_path
            
            print(f"📂 Carregando vault: {vault_path}")
            self.vault_structure = VaultStructure(str(vault_path))
            
            # Inicializar Sembrain se configurado
            if settings.llm.get('use_semantic_search', True):
                self._init_sembrain()
            
            # Glados voice
            glados_voice = GladosVoice()
            
            # Instanciar o TinyLlamaGlados
            self.model = TinyLlamaGlados(config, self.vault_structure, glados_voice)
            
            # Carregar cache se existir
            self._load_cache()
            
            self._initialized = True
            print("✅ LLM local inicializado com busca semântica")
            
        except Exception as e:
            print(f"❌ Erro inicializando LLM: {e}")
            self._initialized = True
    
    def _init_sembrain(self):
        """Inicializa o sistema de busca semântica"""
        try:
            from src.core.llm.glados.brain.sembrain import Sembrain
            
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
    
    def generate(self, query: str, user_name: str = None, use_semantic: bool = True) -> Dict[str, Any]:
        """Gera resposta para uma consulta com contexto semântico"""
        
        # Verificar cache primeiro
        cache_key = self._get_cache_key(query, user_name)
        if cache_key in self.response_cache:
            cached_time, response = self.response_cache[cache_key]
            if (datetime.now().timestamp() - cached_time) < 3600:  # 1 hora
                print("⚡ Resposta do cache")
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
        
        # Adicionar contexto ao prompt se disponível
        enhanced_query = query
        if semantic_context:
            enhanced_query = f"""
CONTEXTO DO VAULT:
{semantic_context}

PERGUNTA: {query}

Por favor, use o contexto acima para responder. Se não houver informações suficientes no contexto, indique isso.
"""
        
        try:
            response = self.model.generate_response(enhanced_query, user_name)
            
            # Registrar no histórico
            self.query_history.append({
                "query": query,
                "response": response[:100] + "..." if len(response) > 100 else response,
                "timestamp": datetime.now().isoformat(),
                "used_semantic": use_semantic and bool(semantic_context)
            })
            
            # Limitar histórico
            if len(self.query_history) > 100:
                self.query_history = self.query_history[-100:]
            
            # Salvar no cache
            result = {
                "text": response,
                "model": "TinyLlama-1.1B",
                "status": "success",
                "semantic_context_used": use_semantic and bool(semantic_context),
                "timestamp": datetime.now().isoformat()
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
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            stats = self.model.get_stats()
            
            status = {
                "status": "loaded" if stats.get("model_loaded", False) else "error",
                "model": stats.get("config", {}).get("model", "Unknown"),
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
                    "notes_indexed": self.sembrain.get_stats()["total_notes"] if self.sembrain else 0
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

# Instância global
llm = LocalLLM()
