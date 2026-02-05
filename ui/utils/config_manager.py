"""
Gerenciador de configurações da aplicação
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from PyQt6.QtCore import QSettings

class ConfigManager:
    """Gerenciador de configurações que combina YAML e QSettings"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.default_config = self._load_default_config()
            self.user_settings = QSettings("GLaDOS Project", "Philosophy Planner")
            
    def _load_default_config(self) -> Dict[str, Any]:
        """Carrega configurações padrão do arquivo YAML"""
        config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
        
        if not config_path.exists():
            print(f"⚠️  Arquivo de configuração não encontrado: {config_path}")
            return self._get_fallback_config()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️  Erro ao carregar configuração YAML: {e}")
            return self._get_fallback_config()
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Configuração de fallback se o arquivo YAML não existir"""
        return {
            'app': {
                'name': 'Philosophy Planner',
                'version': '0.1.0',
                'debug': True,
                'log_level': 'INFO'
            },
            'paths': {
                'vault': '~/Documents/Obsidian/Philosophy_Vault',
                'data_dir': './data',
                'models_dir': './data/models',
                'exports_dir': './data/exports'
            },
            'database': {
                'url': 'sqlite:///data/database/philosophy.db',
                'echo': False
            },
            'llm': {
                'model_path': './data/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf',
                'n_ctx': 2048,
                'n_gpu_layers': 0,
                'temperature': 0.7,
                'top_p': 0.95
            },
            'obsidian': {
                'templates_dir': './config/templates',
                'auto_sync': True,
                'sync_interval': 300
            },
            'pomodoro': {
                'work_duration': 25,
                'short_break': 5,
                'long_break': 15,
                'sessions_before_long_break': 4
            },
            'features': {
                'enable_llm': True,
                'enable_obsidian_sync': True,
                'enable_pomodoro': True,
                'enable_translation': False
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtém um valor de configuração.
        
        A chave pode ser em formato de ponto, ex: 'app.name'
        ou pode ser uma lista de chaves, ex: ['app', 'name']
        """
        # Primeiro, tenta obter do usuário (QSettings)
        user_value = self.user_settings.value(key)
        if user_value is not None:
            return user_value
        
        # Se não encontrou no usuário, busca no YAML
        keys = key.split('.') if isinstance(key, str) else key
        value = self.default_config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Define um valor de configuração (salva no QSettings)"""
        self.user_settings.setValue(key, value)
        self.user_settings.sync()
    
    @property
    def vault_path(self) -> str:
        """Retorna o caminho do vault Obsidian"""
        path = self.get('paths.vault', '~/Documents/Obsidian/Philosophy_Vault')
        return os.path.expanduser(path)
    
    @vault_path.setter
    def vault_path(self, path: str) -> None:
        """Define o caminho do vault Obsidian"""
        self.set('paths.vault', path)
    
    @property
    def theme(self) -> str:
        """Retorna o tema atual"""
        return self.get('ui.theme', 'philosophy_dark')
    
    @theme.setter
    def theme(self, theme_name: str) -> None:
        """Define o tema"""
        self.set('ui.theme', theme_name)
    
    def get_window_geometry(self) -> Optional[bytes]:
        """Obtém geometria da janela"""
        return self.user_settings.value('window/geometry')
    
    def set_window_geometry(self, geometry: bytes) -> None:
        """Define geometria da janela"""
        self.user_settings.setValue('window/geometry', geometry)
    
    def get_window_state(self) -> Optional[bytes]:
        """Obtém estado da janela"""
        return self.user_settings.value('window/state')
    
    def set_window_state(self, state: bytes) -> None:
        """Define estado da janela"""
        self.user_settings.setValue('window/state', state)
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Retorna todas as configurações (padrão + usuário)"""
        all_settings = {}
        
        # Adiciona configurações padrão
        all_settings.update(self.default_config)
        
        # Sobrescreve com configurações do usuário
        for key in self.user_settings.allKeys():
            # Converte chaves do QSettings para formato de dicionário aninhado
            keys = key.split('/')
            current = all_settings
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = self.user_settings.value(key)
        
        return all_settings
    
    def reset_to_defaults(self) -> None:
        """Reseta todas as configurações do usuário para padrão"""
        self.user_settings.clear()
        self.user_settings.sync()
    
    def export_settings(self, file_path: str) -> bool:
        """Exporta configurações do usuário para arquivo JSON"""
        try:
            import json
            user_settings = {}
            for key in self.user_settings.allKeys():
                user_settings[key] = self.user_settings.value(key)
            
            with open(file_path, 'w') as f:
                json.dump(user_settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Erro ao exportar configurações: {e}")
            return False
    
    def import_settings(self, file_path: str) -> bool:
        """Importa configurações de arquivo JSON"""
        try:
            import json
            with open(file_path, 'r') as f:
                user_settings = json.load(f)
            
            for key, value in user_settings.items():
                self.user_settings.setValue(key, value)
            
            self.user_settings.sync()
            return True
        except Exception as e:
            print(f"Erro ao importar configurações: {e}")
            return False
    
    @classmethod
    def instance(cls):
        """Retorna a instância singleton"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance