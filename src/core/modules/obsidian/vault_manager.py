# src/core/modules/obsidian/vault_manager.py
import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Iterator
from datetime import datetime, date
import logging
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict
import re

from ...config.settings import settings
from ...models.book import Book, BookStatus
from ...models.note import Note, NoteType
from ...models.task import Task, TaskType

logger = logging.getLogger(__name__)

class ObsidianNoteType(Enum):
    """Tipos de notas no Obsidian correspondentes aos nossos tipos."""
    BOOK_SUMMARY = "📚 Resumo Estruturado"
    CLASS_NOTE = "🎓 Nota de Aula"
    CONCEPT = "🧠 Conceito"
    QUOTE = "💬 Citação"
    IDEA = "💡 Ideia"
    AUTHOR = "👤 Autor"
    BOOK_METADATA = "📖 Metadados do Livro"

@dataclass
class ObsidianNote:
    """Representa uma nota do Obsidian."""
    path: Path
    content: str = ""
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    links: List[str] = field(default_factory=list)
    created: Optional[datetime] = None
    modified: Optional[datetime] = None

class ObsidianVaultManager:
    """Gerenciador de vault do Obsidian."""
    # Adicionando padrão singleton
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
                vault_path = os.path.expanduser("~/Documentos/Obsidian/Philosophy_Vault")

        resolved_vault_path = Path(vault_path).expanduser().resolve()
        if getattr(self, "_initialized", False):
            if resolved_vault_path != self.vault_path:
                self.vault_path = resolved_vault_path
                self._notes_cache.clear()
                self._note_paths = []
                self._note_paths_set = set()
                self._scan_vault()
            return

        # Definir o caminho do vault normalizando "~" e caminho absoluto.
        self.vault_path = resolved_vault_path

        # Cache LRU de notas completas carregadas em memória.
        self._max_cached_notes = 200
        self._notes_cache: "OrderedDict[Path, ObsidianNote]" = OrderedDict()
        # Índice leve de caminhos; evita ler conteúdo no boot.
        self._note_paths: List[Path] = []
        self._note_paths_set: Set[Path] = set()

        self._scan_vault()
        self._initialized = True
        ObsidianVaultManager._initialized = True
    
    @classmethod
    def instance(cls, vault_path: Optional[str] = None) -> 'ObsidianVaultManager':
        """
        Retorna a instância singleton do gerenciador de vault.
        
        Args:
            vault_path: Caminho para o vault (opcional, apenas na primeira chamada)
            
        Returns:
            Instância singleton do ObsidianVaultManager
        """
        if cls._instance is None:
            cls._instance = cls(vault_path)
        return cls._instance
    
    def _scan_vault(self) -> None:
        """Escaneia o vault e mantém apenas índice de caminhos em memória."""
        logger.info(f"Scanning vault: {self.vault_path}")
        self._notes_cache.clear()
        if not self.is_connected():
            self._note_paths = []
            self._note_paths_set = set()
            return

        markdown_files = [p.relative_to(self.vault_path) for p in self.vault_path.rglob("*.md")]
        markdown_files.sort()
        self._note_paths = markdown_files
        self._note_paths_set = set(markdown_files)
        logger.info(f"Found {len(markdown_files)} markdown files")

    def _touch_cache(self, path: Path, note: ObsidianNote) -> None:
        """Atualiza LRU e limita RAM usada por notas em memória."""
        self._notes_cache[path] = note
        self._notes_cache.move_to_end(path, last=True)
        while len(self._notes_cache) > self._max_cached_notes:
            self._notes_cache.popitem(last=False)

    def _read_note(self, filepath: Path, include_content: bool = True) -> ObsidianNote:
        """Lê uma nota do Obsidian e extrai metadados; conteúdo é opcional."""
        raw_content = filepath.read_text(encoding='utf-8')

        # Extrair frontmatter (se existir)
        frontmatter = {}
        body_content = raw_content
        if raw_content.startswith('---'):
            parts = raw_content.split('---', 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1]
                body_content = parts[2].lstrip('\n')
                try:
                    frontmatter = yaml.safe_load(frontmatter_str) or {}
                except yaml.YAMLError as e:
                    logger.warning(f"Error parsing frontmatter in {filepath}: {e}")

        # Extrair tags (formato #tag ou tags: [tag1, tag2] no frontmatter)
        tags = set()

        # Tags do frontmatter
        if 'tags' in frontmatter:
            if isinstance(frontmatter['tags'], list):
                tags.update(frontmatter['tags'])
            elif isinstance(frontmatter['tags'], str):
                tags.add(frontmatter['tags'])

        # Tags no corpo (#tag)
        inline_tags = re.findall(r'#([\w\-]+)', body_content)
        tags.update(inline_tags)

        # Extrair links ([[link]])
        links = re.findall(r'\[\[([^\[\]]+)\]\]', body_content)

        # Obter datas de criação e modificação
        stats = filepath.stat()
        created = datetime.fromtimestamp(stats.st_ctime)
        modified = datetime.fromtimestamp(stats.st_mtime)

        return ObsidianNote(
            path=filepath.relative_to(self.vault_path),
            content=body_content.strip() if include_content else "",
            frontmatter=frontmatter,
            tags=tags,
            links=links,
            created=created,
            modified=modified
        )

    def _get_note(self, relative_path: Path, include_content: bool = True) -> Optional[ObsidianNote]:
        """Carrega nota sob demanda com cache LRU."""
        path = Path(relative_path)
        if path not in self._note_paths_set:
            return None

        if include_content and path in self._notes_cache:
            note = self._notes_cache[path]
            self._notes_cache.move_to_end(path, last=True)
            return note

        full_path = self.vault_path / path
        if not full_path.exists():
            if path in self._note_paths_set:
                self._note_paths.remove(path)
                self._note_paths_set.remove(path)
            self._notes_cache.pop(path, None)
            return None

        note = self._read_note(full_path, include_content=include_content)
        if include_content:
            self._touch_cache(path, note)
        return note
    
    def _write_note(self, note: ObsidianNote) -> None:
        """Escreve uma nota no vault."""
        full_path = self.vault_path / note.path
        
        # Garantir que o diretório existe
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Construir conteúdo com frontmatter
        content_lines = []
        
        if note.frontmatter:
            content_lines.append('---')
            content_lines.append(yaml.dump(note.frontmatter, allow_unicode=True).strip())
            content_lines.append('---')
            content_lines.append('')  # Linha em branco após frontmatter
        
        content_lines.append(note.content)
        
        full_path.write_text('\n'.join(content_lines), encoding='utf-8')

        # Atualizar índice e cache
        if note.path not in self._note_paths:
            self._note_paths.append(note.path)
            self._note_paths.sort()
            self._note_paths_set.add(note.path)
        self._touch_cache(note.path, note)
        logger.debug(f"Written note: {note.path}")

    def iter_notes(
        self,
        include_content: bool = False,
        path_prefix: Optional[str] = None
    ) -> Iterator[ObsidianNote]:
        """Itera notas sob demanda, com filtro por prefixo opcional."""
        normalized_prefix = None
        if path_prefix:
            normalized_prefix = path_prefix.strip("/").replace("\\", "/")

        for relative_path in self._note_paths:
            if normalized_prefix and not str(relative_path).replace("\\", "/").startswith(normalized_prefix):
                continue
            note = self._get_note(relative_path, include_content=include_content)
            if note is not None:
                yield note

    def get_notes_by_prefix(self, path_prefix: str, include_content: bool = False) -> List[ObsidianNote]:
        """Retorna notas de uma subárvore específica do vault."""
        return list(self.iter_notes(include_content=include_content, path_prefix=path_prefix))

    def get_all_notes(self, include_content: bool = True) -> List[ObsidianNote]:
        """
        Retorna todas as notas do vault.

        `include_content=False` evita carregar corpos completos em RAM.
        """
        return list(self.iter_notes(include_content=include_content))

    def get_note_by_path(self, relative_path: str) -> Optional[ObsidianNote]:
        """Busca uma nota pelo caminho relativo."""
        return self._get_note(Path(relative_path), include_content=True)

    def find_notes_by_tag(self, tag: str) -> List[ObsidianNote]:
        """Encontra notas com uma tag específica."""
        normalized = str(tag or "").strip()
        if not normalized:
            return []
        return [
            note for note in self.iter_notes(include_content=False)
            if normalized in note.tags
        ]

    def find_notes_by_content(self, search_text: str) -> List[ObsidianNote]:
        """Encontra notas que contenham o texto especificado."""
        search_text_lower = str(search_text or "").lower().strip()
        if not search_text_lower:
            return []
        return [
            note for note in self.iter_notes(include_content=True)
            if search_text_lower in note.content.lower()
        ]
    
    def create_note(
        self,
        relative_path: str,
        content: str = "",
        frontmatter: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> ObsidianNote:
        """Cria uma nova nota no vault."""
        path = Path(relative_path)

        if path in self._note_paths_set:
            raise ValueError(f"Note already exists: {path}")

        note = ObsidianNote(
            path=path,
            content=content,
            frontmatter=frontmatter or {},
            tags=set(tags or [])
        )
        
        self._write_note(note)
        logger.info(f"Created note: {path}")
        return note
    
    def update_note(
        self,
        relative_path: str,
        content: Optional[str] = None,
        frontmatter: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> ObsidianNote:
        """Atualiza uma nota existente."""
        path = Path(relative_path)

        note = self.get_note_by_path(relative_path)
        if note is None:
            raise ValueError(f"Note not found: {path}")

        if content is not None:
            note.content = content

        if frontmatter is not None:
            note.frontmatter.update(frontmatter)

        if tags is not None:
            note.tags.update(tags)

        self._write_note(note)
        logger.info(f"Updated note: {path}")
        return note
    
    def delete_note(self, relative_path: str) -> None:
        """Exclui uma nota do vault."""
        path = Path(relative_path)

        if path not in self._note_paths_set:
            raise ValueError(f"Note not found: {path}")

        full_path = self.vault_path / path
        full_path.unlink()

        self._notes_cache.pop(path, None)
        self._note_paths = [p for p in self._note_paths if p != path]
        self._note_paths_set.discard(path)
        logger.info(f"Deleted note: {path}")

    def cleanup(self):
        """Libera estruturas em memória usadas pelo manager."""
        try:
            self._notes_cache.clear()
            self._note_paths = []
            self._note_paths_set = set()
        except Exception as e:
            logger.debug(f"Falha ao limpar cache do vault: {e}")

    def clear_note_cache(self):
        """Limpa somente cache de notas carregadas, preservando índice de paths."""
        try:
            self._notes_cache.clear()
        except Exception as e:
            logger.debug(f"Falha ao limpar cache de notas: {e}")
    
    def sync_from_obsidian(self) -> Dict[str, Any]:
        """
        Sincroniza dados do Obsidian para o nosso banco de dados.
        Retorna estatísticas da sincronização.
        """
        from ...repositories import BookRepository, NoteRepository
        from sqlalchemy.orm import Session
        from ...database.base import SessionLocal
        
        db = SessionLocal()
        stats = {
            'books_found': 0,
            'books_created': 0,
            'books_updated': 0,
            'notes_found': 0,
            'notes_created': 0,
            'notes_updated': 0
        }
        
        try:
            book_repo = BookRepository(db)
            note_repo = NoteRepository(db)
            
            # 1. Processar notas de livros
            book_notes = self.find_notes_by_tag('book')
            book_note_paths = {note.path for note in book_notes}
            for obs_note in book_notes:
                stats['books_found'] += 1
                
                # Extrair metadados do livro do frontmatter
                frontmatter = obs_note.frontmatter
                
                if 'title' in frontmatter and 'author' in frontmatter:
                    # Buscar livro existente ou criar novo
                    existing_book = book_repo.find_one(
                        title=frontmatter['title'],
                        author=frontmatter['author']
                    )
                    
                    book_data = {
                        'title': frontmatter['title'],
                        'author': frontmatter['author'],
                        'obsidian_path': str(obs_note.path),
                        'tags': json.dumps(list(obs_note.tags)) if obs_note.tags else None
                    }
                    
                    # Mapear campos adicionais
                    field_mapping = {
                        'total_pages': 'pages',
                        'current_page': 'current_page',
                        'status': 'status',
                        'discipline': 'discipline',
                        'year': 'year',
                        'publisher': 'publisher'
                    }
                    
                    for our_field, obs_field in field_mapping.items():
                        if obs_field in frontmatter:
                            book_data[our_field] = frontmatter[obs_field]
                    
                    if existing_book:
                        # Atualizar livro existente
                        book_repo.update(existing_book.id, **book_data)
                        stats['books_updated'] += 1
                    else:
                        # Criar novo livro
                        book_data.update({
                            'total_pages': book_data.get('total_pages', 0),
                            'current_page': book_data.get('current_page', 0),
                            'status': BookStatus.NOT_STARTED
                        })
                        book_repo.create(**book_data)
                        stats['books_created'] += 1
            
            # 2. Processar anotações gerais
            for obs_note in self.iter_notes(include_content=True):
                # Pular notas que já são de livros
                if obs_note.path in book_note_paths:
                    continue
                
                stats['notes_found'] += 1
                
                # Determinar tipo da nota
                note_type = NoteType.IDEA  # padrão
                for tag in obs_note.tags:
                    if tag in ['concept', 'definition']:
                        note_type = NoteType.CONCEPT
                    elif tag in ['quote', 'citation']:
                        note_type = NoteType.QUOTE
                    elif tag in ['summary', 'book-summary']:
                        note_type = NoteType.BOOK_SUMMARY
                    elif tag in ['class', 'lecture']:
                        note_type = NoteType.CLASS_NOTE
                
                # Extrair título (do frontmatter ou primeira linha)
                title = obs_note.frontmatter.get('title', '')
                if not title and obs_note.content:
                    # Usar primeira linha como título
                    first_line = obs_note.content.split('\n')[0].strip('# ')
                    title = first_line[:100]  # Limitar tamanho
                
                note_data = {
                    'title': title or f"Note {obs_note.path.stem}",
                    'content': obs_note.content,
                    'note_type': note_type,
                    'obsidian_path': str(obs_note.path),
                    'note_tags': json.dumps(list(obs_note.tags)) if obs_note.tags else None
                }
                
                # Buscar nota existente pelo caminho do Obsidian
                existing_note = note_repo.find_one(obsidian_path=str(obs_note.path))
                
                if existing_note:
                    note_repo.update(existing_note.id, **note_data)
                    stats['notes_updated'] += 1
                else:
                    note_repo.create(**note_data)
                    stats['notes_created'] += 1
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error syncing from Obsidian: {e}")
            raise
        finally:
            db.close()
        
        return stats
    
    def sync_to_obsidian(self, book_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Sincroniza dados do nosso banco para o Obsidian.
        Se book_id for fornecido, sincroniza apenas esse livro.
        """
        from ...repositories import BookRepository, NoteRepository
        from sqlalchemy.orm import Session
        from ...database.base import SessionLocal
        
        db = SessionLocal()
        stats = {
            'books_synced': 0,
            'notes_synced': 0,
            'files_created': 0,
            'files_updated': 0
        }
        
        try:
            book_repo = BookRepository(db)
            note_repo = NoteRepository(db)
            
            if book_id:
                books = [book_repo.get(book_id)]
                if not books[0]:
                    raise ValueError(f"Book with ID {book_id} not found")
            else:
                books = book_repo.get_all()
            
            for book in books:
                stats['books_synced'] += 1
                
                # Criar/atualizar nota do livro no Obsidian
                book_note_path = f"01-LEITURAS/{book.author}/{book.title}/📖 Metadados.md"
                
                frontmatter = {
                    'title': book.title,
                    'author': book.author,
                    'status': book.status.value,
                    'progress': f"{book.progress_percentage():.1f}%",
                    'current_page': book.current_page,
                    'total_pages': book.total_pages,
                    'discipline': book.discipline,
                    'tags': ['book', book.discipline.lower() if book.discipline else None]
                }
                
                # Filtrar valores None
                frontmatter = {k: v for k, v in frontmatter.items() if v is not None}
                
                content = f"""
# {book.title}

## 📋 Informações Básicas
- **Autor**: {book.author}
- **Status**: {book.status.value.replace('_', ' ').title()}
- **Progresso**: {book.current_page}/{book.total_pages} páginas ({book.progress_percentage():.1f}%)

## 📅 Datas
- **Início**: {book.start_date if book.start_date else 'Não iniciado'}
- **Prazo**: {book.deadline if book.deadline else 'Sem prazo'}
- **Conclusão**: {book.finish_date if book.finish_date else 'Não concluído'}

## 📝 Notas Relacionadas
<!-- Links para notas relacionadas a este livro -->
"""
                
                try:
                    existing_note = self.get_note_by_path(book_note_path)
                    if existing_note:
                        self.update_note(
                            book_note_path,
                            content=content,
                            frontmatter=frontmatter
                        )
                        stats['files_updated'] += 1
                    else:
                        self.create_note(
                            book_note_path,
                            content=content,
                            frontmatter=frontmatter
                        )
                        stats['files_created'] += 1
                except Exception as e:
                    logger.warning(f"Error syncing book {book.id} to Obsidian: {e}")
                
                # Sincronizar anotações relacionadas ao livro
                book_notes = note_repo.find_by_book(book.id)
                for note in book_notes:
                    stats['notes_synced'] += 1
                    
                    note_path = f"01-LEITURAS/{book.author}/{book.title}/🗒️ {note.title}.md"
                    
                    note_frontmatter = {
                        'title': note.title,
                        'type': note.note_type.value,
                        'book': book.title,
                        'author': book.author,
                        'tags': [note.note_type.value.replace('_', '-')]
                    }
                    
                    # Adicionar tags da nota
                    if note.note_tags:
                        try:
                            tags = json.loads(note.note_tags)
                            note_frontmatter['tags'].extend(tags)
                        except:
                            pass
                    
                    note_content = f"""# {note.title}

## 📚 Livro
[[{book.title}]]

## 📝 Conteúdo
{note.content}

## 🔗 Links Relacionados
<!-- Adicione links para conceitos relacionados -->
"""
                    
                    try:
                        existing_note = self.get_note_by_path(note_path)
                        if existing_note:
                            self.update_note(
                                note_path,
                                content=note_content,
                                frontmatter=note_frontmatter
                            )
                            stats['files_updated'] += 1
                        else:
                            self.create_note(
                                note_path,
                                content=note_content,
                                frontmatter=note_frontmatter
                            )
                            stats['files_created'] += 1
                    except Exception as e:
                        logger.warning(f"Error syncing note {note.id} to Obsidian: {e}")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error syncing to Obsidian: {e}")
            raise
        finally:
            db.close()
        
        return stats
    
    def get_vault_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do vault."""
        # Contar por tipo baseado em tags sem carregar conteúdo completo.
        type_counts = {}
        tag_counts = {}
        total_links = 0
        total_size_bytes = 0
        total_notes = 0

        for note in self.iter_notes(include_content=False):
            total_notes += 1
            # Contar tags
            for tag in note.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Determinar tipo principal
            if note.tags:
                primary_tag = next(iter(note.tags))
                type_counts[primary_tag] = type_counts.get(primary_tag, 0) + 1
            total_links += len(note.links)
            try:
                total_size_bytes += (self.vault_path / note.path).stat().st_size
            except FileNotFoundError:
                continue

        return {
            'total_notes': total_notes,
            'type_counts': type_counts,
            'tag_counts': dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]),  # Top 10 tags
            'total_links': total_links,
            'vault_size_mb': total_size_bytes / (1024 * 1024)
        }
    
    def is_connected(self) -> bool:
        """Verifica se o vault está conectado e acessível."""
        return self.vault_path.exists() and self.vault_path.is_dir()
