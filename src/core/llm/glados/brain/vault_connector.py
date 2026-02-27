"""
Conector do vault do Obsidian como cérebro da GLaDOS
Atualizado com busca semântica integrada
"""
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import yaml
import frontmatter
from dataclasses import dataclass
from datetime import datetime
import json

from .semantic_search import Sembrain, SearchResult
try:
    from core.vault.bootstrap import bootstrap_vault
except Exception:
    bootstrap_vault = None

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'path': str(self.path),
            'title': self.title,
            'content_preview': self.content[:200] + '...' if len(self.content) > 200 else self.content,
            'tags': self.tags,
            'links': self.links,
            'created': self.created.isoformat() if self.created else None,
            'modified': self.modified.isoformat() if self.modified else None
        }

class VaultStructure:
    """Mapeia a estrutura REAL do vault com busca semântica integrada"""
    
    # Estrutura REAL baseada na sua pasta
    STRUCTURE = {
        "00-META": "Sistema e metadados",
        "01-LEITURAS": "Gestão de leituras por autor/obra",
        "02-ANOTAÇÕES": "Anotações do usuário",
        "03-REVISÃO": "Materiais de revisão gerados",
        "04-MAPAS MENTAIS": "Mapas mentais (ex: Canva)",
        "05-DISCIPLINAS": "Conteúdos organizados por disciplina",
        "06-RECURSOS": "Recursos, registros e dados auxiliares"
    }
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).expanduser()
        self.notes_cache = {}
        self.semantic_search = None
        self._validate_structure()
        self._index_vault()
        self._init_semantic_search()
    
    def _init_semantic_search(self):
        """Inicializa o sistema de busca semântica"""
        try:
            # Converte cache para lista de notas
            notes_list = list(self.notes_cache.values())
            self.semantic_search = Sembrain(self.vault_path, notes_list)
            print(f"[GLaDOS] ✅ Busca semântica inicializada: {len(notes_list)} notas indexadas")
            
            # Mostra estatísticas CORRIGIDO: Sembrain não tem 'model_loaded'
            if self.semantic_search:
                stats = self.semantic_search.get_stats()
                print(f"[GLaDOS] 📊 Estatísticas busca: notas={stats['total_notes']}, vocabulário={stats['vocabulary_size']}")
        except Exception as e:
            print(f"[GLaDOS] ⚠️  Erro ao inicializar busca semântica: {e}")
            self.semantic_search = None
    
    def _validate_structure(self) -> bool:
        """Valida se o vault existe (modo flexível)"""
        vault_exists = self.vault_path.exists()
        if not vault_exists:
            print(f"[GLaDOS] ❌ Vault não encontrado: {self.vault_path}")
            print(f"[GLaDOS] Criando estrutura básica...")
        else:
            print(f"[GLaDOS] ✅ Vault encontrado: {self.vault_path}")

        if bootstrap_vault is not None:
            try:
                self.vault_path = bootstrap_vault(
                    vault_path=str(self.vault_path),
                    vault_structure=self.STRUCTURE.keys(),
                )
            except Exception as exc:
                print(f"[GLaDOS] ⚠️  Falha no bootstrap do vault: {exc}")
                if not self.vault_path.exists():
                    self._create_basic_structure()
        elif not self.vault_path.exists():
            self._create_basic_structure()
        
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
        """Retorna notas de estudo/conceitos."""
        notes = self.get_notes_by_folder("02-ANOTAÇÕES")
        if notes:
            return notes
        return self.get_notes_by_folder("02 - Conceitos")
    
    def get_reading_notes(self) -> List[VaultNote]:
        """Retorna notas de leituras."""
        notes = self.get_notes_by_folder("01-LEITURAS")
        if notes:
            return notes
        return self.get_notes_by_folder("01 - Leituras")
    
    def get_discipline_notes(self) -> List[VaultNote]:
        """Retorna materiais de revisão estruturados."""
        notes = self.get_notes_by_folder("03-REVISÃO")
        if notes:
            return notes
        return self.get_notes_by_folder("03 - Disciplinas")
    
    # ADICIONADO: Método para compatibilidade com local_llm.py
    def get_all_notes(self) -> List[VaultNote]:
        """Retorna todas as notas do vault (para compatibilidade)"""
        return list(self.notes_cache.values())
    
    def search_notes(self, query: str, limit: int = 5, semantic: bool = True) -> List[Union[VaultNote, Dict]]:
        """
        Busca por texto nas notas usando busca semântica ou textual
        
        Args:
            query: Texto da consulta
            limit: Número máximo de resultados
            semantic: Se True, usa busca semântica; senão, só busca textual
        
        Returns:
            Lista de notas ou resultados detalhados
        """
        if not query.strip():
            return []
        
        # Usa busca semântica se disponível
        if semantic and self.semantic_search:
            try:
                results = self.semantic_search.search(query, limit=limit)
                
                # Retorna apenas as notas (backward compatibility)
                notes = [result.note for result in results]
                return notes[:limit]
            except Exception as e:
                print(f"[GLaDOS] ⚠️  Erro na busca semântica: {e}. Usando busca textual.")
                return self._textual_search(query, limit)
        else:
            # Fallback para busca textual
            return self._textual_search(query, limit)
    
    def search_detailed(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Busca detalhada com metadados de relevância
        """
        if not self.semantic_search:
            return []
        
        results = self.semantic_search.search(query, limit=limit)
        
        detailed_results = []
        for result in results:
            detailed_results.append({
                'note': result.note.to_dict(),
                'relevance': result.relevance,
                'search_type': result.search_type,
                'matched_fields': result.matched_fields,
                'excerpt': result.excerpt
            })
        
        return detailed_results
    
    def _textual_search(self, query: str, limit: int) -> List[VaultNote]:
        """Busca textual (fallback quando semântica não disponível)"""
        query_lower = query.lower()
        scored_notes = []
        
        for note in self.notes_cache.values():
            score = 0.0
            
            # Busca no título (maior peso)
            if query_lower in note.title.lower():
                score += 0.6
            
            # Busca em tags
            for tag in note.tags:
                if query_lower in tag.lower():
                    score += 0.3
                    break
            
            # Busca no conteúdo
            if query_lower in note.content.lower():
                score += 0.1
            
            if score > 0:
                scored_notes.append((note, score))
        
        # Ordena por pontuação
        scored_notes.sort(key=lambda x: x[1], reverse=True)
        return [note for note, _ in scored_notes[:limit]]
    
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
        
        # Estatísticas de busca semântica CORRIGIDAS
        semantic_stats = {}
        if self.semantic_search:
            try:
                semantic_stats = self.semantic_search.get_stats()
            except:
                semantic_stats = {}
        
        return {
            "total_notes": total_notes,
            "notes_by_folder": notes_by_folder,
            "structure": self.STRUCTURE,
            "vault_path": str(self.vault_path),
            "semantic_search": {
                "available": self.semantic_search is not None,
                "total_notes": semantic_stats.get('total_notes', 0),
                "vocabulary_size": semantic_stats.get('vocabulary_size', 0),
                "cache_size": semantic_stats.get('cache_size', 0)
            }
        }
    
    def format_as_brain_context(self, notes: List[VaultNote], query: str = "") -> str:
        """
        Formata notas como contexto cerebral para a LLM
        Melhorado para incluir informações de relevância
        """
        if not notes:
            return "[MEMÓRIA VAZIA] Nenhuma informação relevante encontrada no meu cérebro."
        
        context = f"[CONSULTA AO CÉREBRO DE GLaDOS - '{query}']\n"
        context += f"Consulta retornou {len(notes)} nota(s) relevantes do meu conhecimento:\n\n"
        
        # Se temos busca semântica, tenta obter detalhes de relevância
        detailed_results = []
        if self.semantic_search and query:
            try:
                detailed_results = self.search_detailed(query, limit=len(notes))
            except:
                detailed_results = []
        
        for i, note in enumerate(notes):
            relative_path = note.path.relative_to(self.vault_path)
            folder = str(relative_path).split('/')[0] if '/' in str(relative_path) else "raiz"
            
            # Tenta obter relevância da busca detalhada
            relevance_info = ""
            if i < len(detailed_results):
                detail = detailed_results[i]
                relevance_info = f" (Relevância: {detail['relevance']:.2f}, Método: {detail['search_type']})"
            
            context += f"--- NOTA {i+1}: {folder}/{relative_path.name}{relevance_info} ---\n"
            context += f"Título: {note.title}\n"
            
            if note.tags:
                context += f"Tags: {', '.join(note.tags)}\n"
            
            # Resumo inteligente do conteúdo
            if len(note.content) > 500:
                # Tenta encontrar sentenças mais relevantes
                sentences = note.content.split('. ')
                if len(sentences) > 3:
                    # Pega primeira, última e algumas do meio
                    summary = '. '.join([sentences[0]] + sentences[1:3] + ["..."]) + "."
                else:
                    summary = note.content[:500] + "..."
            else:
                summary = note.content
            
            context += f"Conteúdo: {summary}\n"
            
            if note.links:
                context += f"Links relacionados: {', '.join(note.links[:3])}"
                if len(note.links) > 3:
                    context += f" ... (+{len(note.links)-3} mais)"
                context += "\n"
            
            context += "\n"
        
        context += "[FIM DA CONSULTA AO CÉREBRO]\n"
        context += "Instrução: Use essas informações como base principal para sua resposta. "
        context += "Se necessário, complemente com seu conhecimento geral, mas priorize o conteúdo acima."
        
        return context
    
    def add_note_to_index(self, note_path: Path):
        """Adiciona uma nova nota ao índice"""
        try:
            note = self._parse_note(note_path)
            if note:
                relative_path = note_path.relative_to(self.vault_path)
                self.notes_cache[str(relative_path)] = note
                
                # Atualiza índice semântico se disponível
                if self.semantic_search:
                    self.semantic_search.add_note(note)
                
                return note
        except Exception as e:
            print(f"[GLaDOS] ⚠️  Erro ao adicionar nota ao índice: {e}")
        return None
