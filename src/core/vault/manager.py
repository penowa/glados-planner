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
    
    def __init__(self, vault_path: Optional[str] = None):
        """Inicializa o gerenciador do vault"""
        if vault_path:
            self.vault_path = Path(vault_path).expanduser()
        else:
            self.vault_path = Path(settings.paths.vault).expanduser()
        
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
            "Meta": "Metacognição - Pensar sobre pensar.",
            "Leituras": "Anotações de leitura e resumos.",
            "Conceitos": "Conceitos filosóficos fundamentais.",
            "Disciplinas": "Notas por disciplina/cursos.",
            "Projetos": "Projetos acadêmicos e de pesquisa.",
            "Pessoal": "Reflexões pessoais e diário."
        }
        
        for directory in self.structure:
            base_name = directory.split(" - ")[-1] if " - " in directory else directory
            if base_name in descriptions:
                dir_path = self.vault_path / directory
                readme_path = dir_path / "README.md"
                content = f"# {base_name}\n\n{descriptions[base_name]}\n\n*Gerenciado por GLaDOS*"
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
            "folder": "06 - Templates",
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
- **00 - Meta**: Metacognição e reflexões sobre aprendizado
- **01 - Leituras**: Anotações de leitura
- **02 - Conceitos**: Conceitos filosóficos
- **03 - Disciplinas**: Organizado por matéria
- **04 - Projetos**: Projetos acadêmicos
- **05 - Pessoal**: Reflexões pessoais
- **06 - Templates**: Templates de notas
- **07 - Arquivos**: Arquivos diversos
- **08 - Referências**: Referências bibliográficas
- **09 - Excalidraw**: Desenhos e diagramas
- **10 - Mapas Mentais**: Mapas conceituais

## Como Usar
1. Use `[[links]]` para conectar ideias
2. Adicione tags como `#importante`
3. Use templates para consistência

---
*Sistema GLaDOS v0.4.0*
"""
        
        index_path = self.vault_path / "Índice Principal.md"
        index_path.write_text(index_content, encoding="utf-8")
