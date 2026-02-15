"""
Configurações do sistema com suporte a GLaDOS
Atualizado para incluir todas as novas configurações
"""
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path

class AppConfig(BaseModel):
    name: str = "Glados Planner"
    version: str = "0.4.0"
    debug: bool = True
    log_level: str = "INFO"

class PathsConfig(BaseModel):
    vault: str = "~/Documentos/Obsidian/Philosophy_Vault"
    data_dir: str = "./data"
    models_dir: str = "./data/models"
    exports_dir: str = "./data/exports"
    cache_dir: str = "./data/cache"

class DatabaseConfig(BaseModel):
    url: str = "sqlite:///data/database/philosophy.db"
    echo: bool = False

class CpuConfig(BaseModel):
    threads: int = 4
    batch_size: int = 128
    use_mlock: bool = True

class GladosAreaBehavior(BaseModel):
    sarcasm_level: float = 0.5
    formality: float = 0.8

class GladosResponseConfig(BaseModel):
    include_intro_comment: bool = True
    include_signature: bool = True
    max_response_length: int = 1000

class GladosPersonalityConfig(BaseModel):
    user_name: str = "Helio"
    glados_name: str = "GLaDOS"
    gender: str = "feminino"
    personality_intensity: float = 0.7
    enable_sarcasm: bool = True
    enable_brain_metaphor: bool = True
    area_behavior: Dict[str, GladosAreaBehavior] = Field(default_factory=dict)
    response: GladosResponseConfig = GladosResponseConfig()

class LlmConfig(BaseModel):
    model_name: str = "Mistral-7B-GGUF-Q4K"
    model_path: str = "./data/models/mistral-7b-GGUF-Q4K.gguf"
    n_ctx: int = 2048
    n_gpu_layers: int = 0
    temperature: float = 0.35
    top_p: float = 0.9
    repeat_penalty: float = 1.12
    max_tokens: int = 384
    cpu: CpuConfig = CpuConfig()
    glados: GladosPersonalityConfig = GladosPersonalityConfig()

class ObsidianConfig(BaseModel):
    templates_dir: str = "./config/templates"
    auto_sync: bool = True
    sync_interval: int = 300
    vault_structure: List[str] = Field(default_factory=list)
    brain_regions: Dict[str, str] = Field(default_factory=dict)

class PomodoroConfig(BaseModel):
    work_duration: int = 25
    short_break: int = 5
    long_break: int = 15
    sessions_before_long_break: int = 4

class FeaturesConfig(BaseModel):
    enable_llm: bool = True
    enable_obsidian_sync: bool = True
    enable_pomodoro: bool = True
    enable_translation: bool = False
    enable_glados_personality: bool = True
    enable_vault_as_brain: bool = True

class CacheConfig(BaseModel):
    enabled: bool = True
    max_size: int = 100
    ttl: int = 3600
    preload_vault: bool = False

class DevelopmentConfig(BaseModel):
    log_llm_prompts: bool = False
    log_vault_access: bool = False
    simulate_llm: bool = False

class Settings(BaseSettings):
    app: AppConfig = AppConfig()
    paths: PathsConfig = PathsConfig()
    database: DatabaseConfig = DatabaseConfig()
    llm: LlmConfig = LlmConfig()
    obsidian: ObsidianConfig = ObsidianConfig()
    pomodoro: PomodoroConfig = PomodoroConfig()
    features: FeaturesConfig = FeaturesConfig()
    cache: CacheConfig = CacheConfig()
    development: DevelopmentConfig = DevelopmentConfig()
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

    @classmethod
    def from_yaml(cls, yaml_path: str = "config/settings.yaml"):
        """Carrega configurações do arquivo YAML"""
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            print(f"[WARNING] Arquivo de configuração não encontrado: {yaml_path}")
            return cls()
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Preenche valores padrão para estruturas aninhadas
        if data and 'llm' in data and 'glados' in data['llm']:
            glados_config = data['llm']['glados']
            
            # Garante que area_behavior tenha todas as áreas
            default_areas = ['meta', 'leituras', 'conceitos', 'disciplinas', 'pessoal', 'geral']
            if 'area_behavior' not in glados_config:
                glados_config['area_behavior'] = {}
            
            for area in default_areas:
                if area not in glados_config['area_behavior']:
                    glados_config['area_behavior'][area] = {
                        'sarcasm_level': 0.5,
                        'formality': 0.8
                    }
        
        return cls(**data) if data else cls()

    def save_yaml(self, yaml_path: str = "config/settings.yaml"):
        """Salva configurações atuais no arquivo YAML."""
        yaml_path_obj = Path(yaml_path)
        yaml_path_obj.parent.mkdir(parents=True, exist_ok=True)

        data = self.model_dump()
        with open(yaml_path_obj, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                data,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False
            )


def reload_settings(yaml_path: str = "config/settings.yaml") -> Settings:
    """Recarrega a instância global de configurações a partir do YAML."""
    global settings
    settings = Settings.from_yaml(yaml_path)
    return settings

# Instância global
settings = Settings.from_yaml()
