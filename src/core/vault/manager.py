"""
Gerenciador do Vault do Obsidian para o GLaDOS
"""
import json
from pathlib import Path
from typing import Optional
from rich.console import Console

# Correção da importação
try:
    # Tenta importar de src.core.config.settings
    from src.core.config.settings import settings
except ImportError:
    # Fallback para importação relativa
    from ..config.settings import settings

console = Console()

class VaultManager:
    """Gerencia a estrutura e operações do vault do Obsidian"""
    _instance = None
    _initialized = False
    
    def __new__(cls, vault_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, vault_path: Optional[str] = None):
        """
        Inicializa o gerenciador do vault.
        
        Args:
            vault_path: Caminho para o vault do Obsidian. Se None, usa o das configurações.
        """
        if vault_path is None:
            # Tentar obter do settings do backend
            if hasattr(settings, 'paths') and hasattr(settings.paths, 'vault'):
                vault_path = settings.paths.vault
            else:
                # Fallback para caminho padrão
                vault_path = os.path.expanduser("~/Documentos/Obsidian/Planner")

        
        self.structure = settings.obsidian.vault_structure
        self.brain_regions = settings.obsidian.brain_regions
        
    def is_connected(self) -> bool:
        """Verifica se o vault está acessível"""
        return self.vault_path.exists() and self.vault_path.is_dir()
    
    def create_structure(self) -> bool:
        """Cria a estrutura completa de diretórios do vault"""
        try:
            console.print(f"[cyan]Criando estrutura em: {self.vault_path}[/cyan]")
            
            # Cria diretório raiz se não existir
            self.vault_path.mkdir(parents=True, exist_ok=True)
            
            # Cria diretórios da estrutura
            created_dirs = []
            for directory in self.structure:
                dir_path = self.vault_path / directory
                dir_path.mkdir(exist_ok=True)
                created_dirs.append(str(dir_path))
                console.print(f"[green]✓ Criado: {directory}[/green]")
            
            # Cria READMEs para diretórios principais
            self._create_readmes()
            
            # Cria configurações do Obsidian
            self._create_obsidian_config()
            
            # Cria arquivos principais
            self._create_main_files()
            
            console.print(f"[bold green]✅ Estrutura criada: {len(created_dirs)} diretórios[/bold green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Erro ao criar estrutura: {e}[/red]")
            return False
    
    def _create_readmes(self):
        """Cria arquivos README explicativos"""
        descriptions = {
            "00-META": "Metadados, índices e organização do sistema.",
            "01-LEITURAS": "Obras por autor e progresso de leitura.",
            "02-ANOTAÇÕES": "Anotações do usuário durante estudo/leitura.",
            "03-REVISÃO": "Materiais de revisão gerados com LLM.",
            "04-MAPAS MENTAIS": "Mapas mentais e estruturas visuais (Canva).",
            "05-DISCIPLINAS": "Conteúdos organizados por disciplina.",
            "06-RECURSOS": "Recursos de apoio, caches e registros."
        }
        
        for directory in self.structure:
            if directory in descriptions:
                dir_path = self.vault_path / directory
                readme_path = dir_path / "README.md"
                content = f"# {directory}\n\n{descriptions[directory]}\n\n*Gerenciado por GLaDOS*"
                readme_path.write_text(content, encoding="utf-8")
    
    def _create_obsidian_config(self):
        """Cria configurações básicas do Obsidian"""
        config_dir = self.vault_path / ".obsidian"
        config_dir.mkdir(exist_ok=True)
        
        # Configuração básica
        core_plugins = {
            "corePlugins": {
                "file-explorer": True,
                "global-search": True,
                "graph": True,
                "backlink": True,
                "templates": True
            }
        }
        
        config_file = config_dir / "core-plugins.json"
        config_file.write_text(json.dumps(core_plugins, indent=2), encoding="utf-8")
        
        templates_config = {
            "folder": "06-RECURSOS/templates",
            "dateFormat": "YYYY-MM-DD"
        }
        
        templates_file = config_dir / "templates.json"
        templates_file.write_text(json.dumps(templates_config, indent=2), encoding="utf-8")
    
    def _create_main_files(self):
        """Cria arquivos principais do vault"""
        # Índice principal
        index_content = """# 🧠 Cérebro Digital - Filosofia

Bem-vindo ao seu vault gerenciado pelo **GLaDOS**.

## Estrutura
- **00-META**: Metadados e organização
- **01-LEITURAS**: Obras por autor e sessão de leitura
- **02-ANOTAÇÕES**: Notas do usuário
- **03-REVISÃO**: Resumos, flashcards e perguntas de revisão
- **04-MAPAS MENTAIS**: Materiais visuais (Canva)
- **05-DISCIPLINAS**: Conteúdos organizados por disciplina
- **06-RECURSOS**: Arquivos de suporte e registros

## Como Usar
1. Use `[[links]]` para conectar ideias
2. Adicione tags como `#importante`
3. Use templates para consistência

---
*Sistema GLaDOS v0.4.0*
"""
        
        index_path = self.vault_path / "Índice Principal.md"
        index_path.write_text(index_content, encoding="utf-8")
