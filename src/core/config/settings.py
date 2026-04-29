"""
Configurações do sistema com suporte a GLaDOS
Atualizado para incluir todas as novas configurações
"""
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional, Any, Literal
import shutil
import yaml
from pathlib import Path
import sys

class AppConfig(BaseModel):
    name: str = "Glados Planner"
    version: str = "1.0.0"
    debug: bool = True
    log_level: str = "INFO"

class PathsConfig(BaseModel):
    vault: str = "~/Documentos/Obsidian/Planner/"
    data_dir: str = "data"
    models_dir: str = "data/models"
    exports_dir: str = "data/exports"
    cache_dir: str = "data/cache"

class DatabaseConfig(BaseModel):
    url: str = "sqlite:///data/database/philosophy.db"
    echo: bool = False

class CpuConfig(BaseModel):
    threads: int = 4
    batch_size: int = 128
    use_mlock: bool = True

class LlmCloudConfig(BaseModel):
    model: str = "ollama/qwen2.5:1.5b"
    api_key: str = ""
    api_base: str = "http://127.0.0.1:11434"
    api_version: str = ""
    organization: str = ""
    timeout_seconds: int = 120
    max_retries: int = 1

class GladosAreaBehavior(BaseModel):
    sarcasm_level: float = 0.5
    formality: float = 0.8

class GladosResponseConfig(BaseModel):
    include_intro_comment: bool = True
    include_signature: bool = True
    max_response_length: int = 1000

class GladosPersonalityConfig(BaseModel):
    user_name: str = "Pindarolas"
    glados_name: str = "GLaDOS"
    personality_profile: Literal["auto", "glados", "marvin"] = "auto"
    gender: str = "feminino"
    personality_intensity: float = 0.7
    enable_sarcasm: bool = True
    enable_brain_metaphor: bool = True
    area_behavior: Dict[str, GladosAreaBehavior] = Field(default_factory=dict)
    response: GladosResponseConfig = GladosResponseConfig()

class LlmConfig(BaseModel):
    backend: Literal["local", "cloud"] = "local"
    model_name: str = "Mistral-7B-GGUF-Q4K"
    model_path: str = "data/models/mistral-7b-GGUF-Q4K.gguf"
    models_dir: str = "data/models"
    n_ctx: int = 2048
    n_gpu_layers: int = 0
    use_gpu: bool = True
    use_cpu: bool = True
    device_mode: Literal["auto", "cpu_only", "gpu_prefer", "gpu_only"] = "auto"
    gpu_index: int = 0
    vram_soft_limit_mb: int = 0
    temperature: float = 0.35
    top_p: float = 0.9
    repeat_penalty: float = 1.12
    max_tokens: int = 384
    use_semantic_search: bool = True
    cpu: CpuConfig = CpuConfig()
    cloud: LlmCloudConfig = LlmCloudConfig()
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


class ReviewViewConfig(BaseModel):
    question_prompt_enabled: bool = True
    question_interval_minutes: int = 10
    arrow_pan_step: int = 130

class ZathuraConfig(BaseModel):
    enabled: bool = True
    preset: str = ""
    binary: str = "zathura"
    config_dir: str = "~/.config/zathura"
    config_file: str = "~/.config/zathura/zathurarc"
    data_dir: str = "~/.local/share/zathura"
    cache_dir: str = "~/.cache/zathura"
    plugin_path: str = ""
    sync_to_zathurarc: bool = True
    theme_mode: Literal["plain", "pywal_internal", "pywal_generator", "custom_include"] = "plain"
    pywal_generator: str = "genzathurarc"
    pywal_colors_file: str = "~/.cache/wal/colors.sh"
    generated_theme_file: str = "~/.config/zathura/glados-theme.zathurarc"
    custom_theme_include_file: str = ""
    selection_clipboard: Literal["clipboard", "primary"] = "clipboard"
    statusbar_basename: bool = True
    window_title_home_tilde: bool = True
    recolor: bool = False
    session_open_mode: Literal["normal", "fullscreen", "presentation"] = "fullscreen"
    session_use_fork: bool = True
    extra_options: Dict[str, Any] = Field(default_factory=dict)
    include_files: List[str] = Field(default_factory=list)
    keymaps: List[str] = Field(default_factory=list)
    extra_config: str = ""

class CacheConfig(BaseModel):
    enabled: bool = True
    max_size: int = 100
    ttl: int = 3600
    preload_vault: bool = False

class DevelopmentConfig(BaseModel):
    log_llm_prompts: bool = False
    log_vault_access: bool = False
    simulate_llm: bool = False

def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]

def _user_app_dir() -> Path:
    return (Path.home() / ".glados").resolve()

def _runtime_storage_root() -> Path:
    if getattr(sys, "frozen", False):
        return _user_app_dir()
    return _runtime_base_dir()

def _bundled_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[3]

def _seed_runtime_config_from_bundle(target_path: Path) -> None:
    """No modo frozen, copia config padrão do bundle para área gravável do usuário."""
    if not getattr(sys, "frozen", False):
        return
    if target_path.exists():
        return

    candidate_names = [target_path.name]
    if target_path.name == "settings.yaml":
        candidate_names = ["settings.release.yaml", "settings.yaml"]

    search_roots: list[Path] = []
    for root in (_bundled_base_dir(), _runtime_base_dir()):
        if root not in search_roots:
            search_roots.append(root)

    bundled_candidate = None
    for candidate_name in candidate_names:
        for root in search_roots:
            probe = root / "config" / candidate_name
            if probe.exists():
                bundled_candidate = probe
                break
        if bundled_candidate is not None:
            break

    if bundled_candidate is None:
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bundled_candidate, target_path)

def _resolve_config_path(yaml_path: str) -> Path:
    target = Path(str(yaml_path or "config/settings.yaml")).expanduser()
    if target.is_absolute():
        return target
    if getattr(sys, "frozen", False):
        runtime_target = _user_app_dir() / target.name
    else:
        runtime_target = _runtime_base_dir() / target
    _seed_runtime_config_from_bundle(runtime_target)
    return runtime_target

def _resolve_runtime_path(raw_path: str, base_dir: Path) -> Path:
    value = str(raw_path or "").strip()
    if not value:
        return base_dir
    target = Path(value).expanduser()
    if not target.is_absolute():
        target = base_dir / target
    return target.resolve()

def _sqlite_url_for_file(file_path: Path) -> str:
    return f"sqlite:///{file_path.as_posix()}"

def _normalize_and_prepare_data_paths(data: Dict[str, Any]) -> Dict[str, Any]:
    storage_root = _runtime_storage_root()
    app_data_root = storage_root / "data"
    legacy_aliases = {"./data", "data", ".data"}

    paths = data.setdefault("paths", {})
    llm_cfg = data.setdefault("llm", {})
    database_cfg = data.setdefault("database", {})

    raw_data_dir = str(paths.get("data_dir", "") or "").strip()
    if not raw_data_dir or raw_data_dir in legacy_aliases:
        data_dir = app_data_root
    else:
        data_dir = _resolve_runtime_path(raw_data_dir, storage_root)

    raw_models_dir = str(paths.get("models_dir", "") or "").strip()
    if not raw_models_dir or raw_models_dir in {"./data/models", "data/models", ".data/models"}:
        models_dir = data_dir / "models"
    else:
        models_dir = _resolve_runtime_path(raw_models_dir, storage_root)

    raw_exports_dir = str(paths.get("exports_dir", "") or "").strip()
    if not raw_exports_dir or raw_exports_dir in {"./data/exports", "data/exports", ".data/exports"}:
        exports_dir = data_dir / "exports"
    else:
        exports_dir = _resolve_runtime_path(raw_exports_dir, storage_root)

    raw_cache_dir = str(paths.get("cache_dir", "") or "").strip()
    if not raw_cache_dir or raw_cache_dir in {"./data/cache", "data/cache", ".data/cache"}:
        cache_dir = data_dir / "cache"
    else:
        cache_dir = _resolve_runtime_path(raw_cache_dir, storage_root)

    for required in (data_dir, models_dir, exports_dir, cache_dir, data_dir / "database", data_dir / "history"):
        required.mkdir(parents=True, exist_ok=True)

    paths["data_dir"] = str(data_dir)
    paths["models_dir"] = str(models_dir)
    paths["exports_dir"] = str(exports_dir)
    paths["cache_dir"] = str(cache_dir)

    llm_models_dir = str(llm_cfg.get("models_dir", "") or "").strip()
    if not llm_models_dir or llm_models_dir in {"./data/models", "data/models", ".data/models"}:
        llm_cfg["models_dir"] = str(models_dir)
    else:
        llm_cfg["models_dir"] = str(_resolve_runtime_path(llm_models_dir, storage_root))

    llm_model_path = str(llm_cfg.get("model_path", "") or "").strip()
    if llm_model_path in {"./data/models/mistral-7b-GGUF-Q4K.gguf", "data/models/mistral-7b-GGUF-Q4K.gguf", ".data/models/mistral-7b-GGUF-Q4K.gguf"}:
        llm_cfg["model_path"] = str(models_dir / "mistral-7b-GGUF-Q4K.gguf")
    elif llm_model_path:
        llm_cfg["model_path"] = str(_resolve_runtime_path(llm_model_path, storage_root))
    else:
        llm_cfg["model_path"] = ""

    db_url = str(database_cfg.get("url", "") or "").strip()
    if (not db_url) or db_url == "sqlite:///data/database/philosophy.db" or db_url == "sqlite:///.data/database/philosophy.db":
        database_cfg["url"] = _sqlite_url_for_file(data_dir / "database" / "philosophy.db")

    return data

class Settings(BaseSettings):
    app: AppConfig = AppConfig()
    paths: PathsConfig = PathsConfig()
    database: DatabaseConfig = DatabaseConfig()
    llm: LlmConfig = LlmConfig()
    obsidian: ObsidianConfig = ObsidianConfig()
    pomodoro: PomodoroConfig = PomodoroConfig()
    features: FeaturesConfig = FeaturesConfig()
    review_view: ReviewViewConfig = ReviewViewConfig()
    zathura: ZathuraConfig = ZathuraConfig()
    cache: CacheConfig = CacheConfig()
    development: DevelopmentConfig = DevelopmentConfig()
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

    @classmethod
    def from_yaml(cls, yaml_path: str = "config/settings.yaml"):
        """Carrega configurações do arquivo YAML"""
        yaml_path = _resolve_config_path(yaml_path)
        if not yaml_path.exists():
            print(f"[WARNING] Arquivo de configuração não encontrado: {yaml_path}")
            default_settings = cls()
            default_settings.save_yaml(str(yaml_path))
            return cls.from_yaml(str(yaml_path))
        
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
        
        normalized = _normalize_and_prepare_data_paths(data or {})
        return cls(**normalized) if normalized else cls()

    def save_yaml(self, yaml_path: str = "config/settings.yaml"):
        """Salva configurações atuais no arquivo YAML."""
        yaml_path_obj = _resolve_config_path(yaml_path)
        yaml_path_obj.parent.mkdir(parents=True, exist_ok=True)

        data = _normalize_and_prepare_data_paths(self.model_dump())
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
