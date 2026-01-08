"""
Conector do vault do Obsidian como cérebro da GLaDOS
Atualizado para a estrutura real do vault
"""
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import frontmatter
import json
from dataclasses import dataclass
from datetime import datetime

@dataclass
class VaultNote:
    """Representa uma nota do vault"""
    path: Path
    title: str
    content: str
    frontmatter: Dict[str, Any]
    tags: List[str]
    links: List[str]
    created: Optional[datetime] = None
    modified: Optional[datetime] = None

class VaultStructure:
    """Mapeia a estrutura REAL do vault"""
    
    # Estrutura REAL baseada na sua pasta
    STRUCTURE = {
        "00 - Meta": "Sistema e metadados",
        "01 - Leituras": "Gestão de leituras por autor",
        "02 - Conceitos": "Conceitos filosóficos organizados",
        "03 - Disciplinas": "Organização por áreas da filosofia",
        "04 - Projetos": "Produção acadêmica do usuário",
        "05 - Pessoal": "Conteúdo pessoal e reflexões",
        "06 - Templates": "Templates de notas",
        "07 - Arquivos": "Arquivos diversos",
        "08 - Referências": "Referências bibliográficas",
        "09 - Excalidraw": "Desenhos e diagramas",
        "10 - Mapas Mentais": "Mapas conceituais"
    }
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).expanduser()
        self.notes_cache = {}
        self._validate_structure()
        self._index_vault()
    
    def _validate_structure(self) -> bool:
        """Valida se o vault existe (modo flexível)"""
        if not self.vault_path.exists():
            print(f"[GLaDOS] ❌ Vault não encontrado: {self.vault_path}")
            print(f"[GLaDOS] Criando estrutura básica...")
            self._create_basic_structure()
            return True
        
        # Verifica estrutura existente
        print(f"[GLaDOS] ✅ Vault encontrado: {self.vault_path}")
        
        # Lista diretórios existentes
        existing_dirs = [d.name for d in self.vault_path.iterdir() if d.is_dir()]
        print(f"[GLaDOS] Diretórios encontrados: {existing_dirs}")
        
        return True
    
    def _create_basic_structure(self):
        """Cria estrutura básica do vault se não existir"""
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        for folder_name, description in self.STRUCTURE.items():
            folder_path = self.vault_path / folder_name
            folder_path.mkdir(exist_ok=True)
            
            # Cria README em cada pasta
            readme_path = folder_path / "README.md"
            if not readme_path.exists():
                readme_content = f"""# {folder_name}

{description}

*Esta pasta é gerenciada automaticamente pelo sistema GLaDOS.*

## Conteúdo Esperado:
- {description.lower()}
- Notas relacionadas
- Metadados do sistema

---
*Criado por GLaDOS v0.4.0*
"""
                readme_path.write_text(readme_content, encoding="utf-8")
        
        print(f"[GLaDOS] ✅ Estrutura criada em: {self.vault_path}")
    
    def _index_vault(self):
        """Indexa todas as notas do vault"""
        print(f"[GLaDOS] 🔍 Indexando vault...")
        
        # Lista de extensões de arquivos de nota
        note_extensions = ['.md', '.txt', '.markdown']
        
        note_count = 0
        for ext in note_extensions:
            for md_file in self.vault_path.glob(f"**/*{ext}"):
                try:
                    note = self._parse_note(md_file)
                    if note:
                        relative_path = md_file.relative_to(self.vault_path)
                        self.notes_cache[str(relative_path)] = note
                        note_count += 1
                except Exception as e:
                    print(f"[GLaDOS] ⚠️  Erro ao parsear {md_file}: {e}")
        
        print(f"[GLaDOS] ✅ {note_count} notas indexadas")
    
    def _parse_note(self, file_path: Path) -> Optional[VaultNote]:
        """Parseia uma nota Markdown com frontmatter"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Tenta extrair frontmatter
            frontmatter_data = {}
            if content.startswith('---'):
                try:
                    # Usa frontmatter se disponível
                    parsed = frontmatter.loads(content)
                    content = parsed.content
                    frontmatter_data = parsed.metadata
                except:
                    # Fallback para parsing simples
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter_str = parts[1]
                        content = parts[2].lstrip('\n')
                        try:
                            frontmatter_data = yaml.safe_load(frontmatter_str) or {}
                        except:
                            frontmatter_data = {}
            
            # Extrai título do frontmatter ou do nome do arquivo
            title = frontmatter_data.get('title', file_path.stem)
            
            # Extrai tags
            tags = frontmatter_data.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]
            
            # Extrai links [[link]]
            import re
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            
            return VaultNote(
                path=file_path,
                title=title,
                content=content.strip(),
                frontmatter=frontmatter_data,
                tags=tags,
                links=links,
                created=datetime.fromtimestamp(file_path.stat().st_ctime),
                modified=datetime.fromtimestamp(file_path.stat().st_mtime)
            )
        except Exception as e:
            print(f"[GLaDOS] ⚠️  Erro ao parsear {file_path}: {e}")
            return None
    
    def get_notes_by_folder(self, folder_name: str) -> List[VaultNote]:
        """Retorna todas as notas de uma pasta específica"""
        folder_path = self.vault_path / folder_name
        notes = []
        
        for note_path, note in self.notes_cache.items():
            if note_path.startswith(folder_name):
                notes.append(note)
        
        return notes
    
    def get_concept_notes(self) -> List[VaultNote]:
        """Retorna notas de conceitos da pasta 02 - Conceitos"""
        return self.get_notes_by_folder("02 - Conceitos")
    
    def get_reading_notes(self) -> List[VaultNote]:
        """Retorna notas de leituras da pasta 01 - Leituras"""
        return self.get_notes_by_folder("01 - Leituras")
    
    def get_discipline_notes(self) -> List[VaultNote]:
        """Retorna notas de disciplinas da pasta 03 - Disciplinas"""
        return self.get_notes_by_folder("03 - Disciplinas")
    
    def search_notes(self, query: str, limit: int = 3) -> List[VaultNote]:
        """Busca por texto nas notas"""
        if not self.notes_cache:
            return []
        
        results = []
        query_lower = query.lower()
        
        for note in self.notes_cache.values():
            # Busca no título
            if query_lower in note.title.lower():
                results.append((note, 1.0))  # Alta relevância
                continue
            
            # Busca no conteúdo
            if query_lower in note.content.lower():
                results.append((note, 0.7))  # Relevância média
                continue
            
            # Busca em tags
            for tag in note.tags:
                if query_lower in tag.lower():
                    results.append((note, 0.5))  # Relevância baixa
                    break
        
        # Ordena por relevância e limite
        results.sort(key=lambda x: x[1], reverse=True)
        return [note for note, _ in results[:limit]]
    
    def get_note_by_path(self, path: str) -> Optional[VaultNote]:
        """Obtém uma nota específica pelo caminho relativo"""
        return self.notes_cache.get(path)
    
    def get_vault_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do vault"""
        total_notes = len(self.notes_cache)
        notes_by_folder = {}
        
        for folder in self.STRUCTURE.keys():
            notes = self.get_notes_by_folder(folder)
            notes_by_folder[folder] = len(notes)
        
        return {
            "total_notes": total_notes,
            "notes_by_folder": notes_by_folder,
            "structure": self.STRUCTURE,
            "vault_path": str(self.vault_path)
        }
    
    def format_as_brain_context(self, notes: List[VaultNote]) -> str:
        """Formata notas como contexto cerebral para a LLM"""
        if not notes:
            return "[MEMÓRIA VAZIA] Nenhuma informação relevante encontrada no meu cérebro."
        
        context = "[CONSULTA AO CÉREBRO DE GLaDOS]\n"
        context += f"Consulta retornou {len(notes)} nota(s) relevantes:\n\n"
        
        for i, note in enumerate(notes):
            relative_path = note.path.relative_to(self.vault_path)
            context += f"--- NOTA {i+1}: {relative_path} ---\n"
            context += f"Título: {note.title}\n"
            
            # Resumo do conteúdo (primeiros 300 caracteres)
            if len(note.content) > 300:
                summary = note.content[:300] + "..."
            else:
                summary = note.content
            
            context += f"Conteúdo: {summary}\n"
            
            if note.tags:
                context += f"Tags: {', '.join(note.tags)}\n"
            
            context += "\n"
        
        return context
