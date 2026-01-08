"""
Módulo LocalLLM para gerenciar o TinyLlama com GLaDOS
"""
import sys
from pathlib import Path
from typing import Dict, Any

# Adiciona o diretório raiz do projeto ao path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.config.settings import settings
from src.core.llm.glados.models.tinyllama_wrapper import TinyLlamaGlados, LlamaConfig
from src.core.llm.glados.brain.vault_connector import VaultStructure
from src.core.llm.glados.personality.glados_voice import GladosVoice

class LocalLLM:
    """Gerenciador do LLM local"""
    
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
        
        # Obter diretório base do projeto
        base_dir = Path(__file__).parent.parent.parent.parent
        
        # Verificar e expandir caminho do modelo
        model_path = Path(settings.llm.model_path)
        if not model_path.is_absolute():
            model_path = base_dir / model_path
        
        if not model_path.exists():
            print(f"❌ Modelo não encontrado: {model_path}")
            self._initialized = True
            return
        
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
        
        vault_structure = VaultStructure(str(vault_path))
        
        # Glados voice
        glados_voice = GladosVoice()
        
        # Instanciar o TinyLlamaGlados
        self.model = TinyLlamaGlados(config, vault_structure, glados_voice)
        
        self._initialized = True
        print("✅ LLM local inicializado")
    
    def generate(self, query: str, user_name: str = None) -> Dict[str, Any]:
        """Gera resposta para uma consulta"""
        if self.model is None:
            return {
                "text": "LLM não disponível. Verifique se o modelo está instalado em data/models/",
                "error": "Model not loaded"
            }
        
        if user_name is None:
            user_name = settings.llm.glados.user_name
        
        response = self.model.generate_response(query, user_name)
        
        return {
            "text": response,
            "model": "TinyLlama-1.1B",
            "status": "success"
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do LLM"""
        if self.model is None:
            return {
                "status": "not_loaded",
                "message": "Modelo não carregado"
            }
        
        stats = self.model.get_stats()
        return {
            "status": "loaded" if stats["model_loaded"] else "error",
            "model": stats["config"]["model"],
            "cache": {
                "hits": stats["cache_hits"],
                "misses": stats["cache_misses"],
                "size": stats["cache_size"]
            }
        }

# Instância global
llm = LocalLLM()
