"""
Conector do vault do Obsidian como cérebro da GLaDOS
Respeita a estrutura definida na documentação
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
    """Mapeia a estrutura exata do vault definido na documentação"""
    
    # Estrutura baseada no documento original
    STRUCTURE = {
        "00-META": "Sistema e metadados",
        "01-LEITURAS": "Gestão de leituras por autor",
        "02-DISCIPLINAS": "Organização por áreas da filosofia",
        "03-PRODUÇÃO": "Produção acadêmica do usuário",
        "04-AGENDA": "Gestão acadêmica e prazos",
        "05-CONCEITOS": "Conceitos filosóficos organizados",
        "06-RECURSOS": "Recursos e métodos de estudo",
        "07-PESSOAL": "Conteúdo pessoal e reflexões",
        "08-ARCHIVE": "Conteúdo arquivado"
    }
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).expanduser()
        self.notes_cache = {}
        self._validate_structure()
        self._index_vault()
    
    def _validate_structure(self) -> bool:
        """Valida se o vault segue a estrutura esperada"""
        valid = True
        
        for folder in self.STRUCTURE.keys():
            folder_path = self.vault_path / folder
            if not folder_path.exists():
                print(f"[GLaDOS] Aviso: Pasta '{folder}' não encontrada no vault")
                valid = False
        
        return valid
    
    def _index_vault(self):
        """Indexa todas as notas do vault"""
        for md_file in self.vault_path.glob("**/*.md"):
            try:
                note = self._parse_note(md_file)
                if note:
                    relative_path = md_file.relative_to(self.vault_path)
                    self.notes_cache[str(relative_path)] = note
            except Exception as e:
                print(f"[GLaDOS] Erro ao parsear {md_file}: {e}")
    
    def _parse_note(self, file_path: Path) -> Optional[VaultNote]:
        """Parseia uma nota Markdown com frontmatter"""
        try:
            content = file_path.read_text(encoding='utf-8')
            parsed = frontmatter.loads(content)
            
            # Extrai título do frontmatter ou do nome do arquivo
            title = parsed.get('title', file_path.stem)
            
            # Extrai tags
            tags = parsed.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]
            
            # Extrai links [[link]]
            import re
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            
            return VaultNote(
                path=file_path,
                title=title,
                content=parsed.content,
                frontmatter=parsed.metadata,
                tags=tags,
                links=links,
                created=file_path.stat().st_ctime,
                modified=file_path.stat().st_mtime
            )
        except Exception as e:
            print(f"[GLaDOS] Erro ao parsear {file_path}: {e}")
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
        """Retorna notas de conceitos da pasta 05-CONCEITOS"""
        return self.get_notes_by_folder("05-CONCEITOS")
    
    def get_reading_notes(self) -> List[VaultNote]:
        """Retorna notas de leituras da pasta 01-LEITURAS"""
        return self.get_notes_by_folder("01-LEITURAS")
    
    def get_discipline_notes(self) -> List[VaultNote]:
        """Retorna notas de disciplinas da pasta 02-DISCIPLINAS"""
        return self.get_notes_by_folder("02-DISCIPLINAS")
    
    def search_notes(self, query: str, limit: int = 10) -> List[VaultNote]:
        """Busca por texto nas notas"""
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
            "structure": self.STRUCTURE
        }
    
    def format_as_brain_context(self, notes: List[VaultNote]) -> str:
        """Formata notas como contexto cerebral para a LLM"""
        if not notes:
            return "[MEMÓRIA VAZIA] Nenhuma informação relevante encontrada no cérebro."
        
        context = "[CONSULTA AO CÉREBRO DE GLaDOS]\n"
        for i, note in enumerate(notes[:5]):  # Limita a 5 notas
            relative_path = note.path.relative_to(self.vault_path)
            context += f"\n--- NOTA {i+1}: {relative_path} ---\n"
            context += f"Título: {note.title}\n"
            
            # Resumo do conteúdo (primeiras 200 caracteres)
            summary = note.content[:200] + "..." if len(note.content) > 200 else note.content
            context += f"Conteúdo: {summary}\n"
            
            if note.tags:
                context += f"Tags: {', '.join(note.tags)}\n"
        
        return context
