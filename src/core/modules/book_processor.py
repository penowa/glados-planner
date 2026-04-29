# src/core/modules/book_processor.py (linhas 1-20 corrigidas)
import os
import logging
import json
import hashlib
import re
import shutil
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# CORREÇÃO: Importação mais flexível
try:
    # Namespace padrão da aplicação (evita duplicar módulos via src.core.*)
    from core.config.settings import settings
except ImportError:
    try:
        # Tenta importação relativa
        from ...config.settings import settings
    except ImportError:
        # Configuração padrão para testes
        class Settings:
            class ObsidianConfig:
                vault_structure = [
                    "00-META",
                    "01-LEITURAS",
                    "02-ANOTAÇÕES",
                    "03-REVISÃO",
                    "04-MAPAS MENTAIS",
                    "05-DISCIPLINAS",
                    "06-RECURSOS",
                ]
                brain_regions = ["MEMÓRIA", "ANÁLISE"]
            obsidian = ObsidianConfig()
            vault_path = None
        settings = Settings()

from .obsidian.vault_manager import ObsidianVaultManager
from ui.utils.citation_notes import ensure_citations_note_for_book
from ui.utils.discipline_links import append_book_note_links, ensure_discipline_note

logger = logging.getLogger(__name__)

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"

class ProcessingQuality(Enum):
    DRAFT = "draft"      # Rápido, menos preciso
    STANDARD = "standard" # Equilíbrio velocidade/qualidade
    HIGH = "high"        # Lento, mais preciso
    ACADEMIC = "academic" # Máxima qualidade (OCR + revisão)

@dataclass
class BookMetadata:
    """Metadados extraídos de um livro."""
    title: str = ""
    author: str = ""
    publisher: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None
    total_pages: int = 0
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    language: str = "pt"
    has_images: bool = False
    requires_ocr: bool = False
    estimated_processing_time: int = 0  # em segundos
    file_size_mb: float = 0.0

@dataclass
class ProcessingResult:
    """Resultado do processamento de um livro."""
    status: ProcessingStatus
    metadata: BookMetadata
    output_dir: Optional[Path] = None
    processed_chapters: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class BookProcessor:
    """Processador principal de livros."""
    
    def __init__(self, vault_manager: Optional[ObsidianVaultManager] = None):
        """
        Inicializa o processador de livros.
        
        Args:
            vault_manager: Instância do gerenciador do vault. Se None, cria uma nova.
        """
        self.vault_manager = vault_manager or ObsidianVaultManager()
        self.supported_formats = {
            '.pdf': self._process_pdf,
            '.epub': self._process_epub,
            # Removendo formatos não implementados até que sejam adicionados
            # '.mobi': self._process_mobi,
            # '.djvu': self._process_djvu
        }
        
        # Configurações de processamento
        self.config = {
            'default_quality': ProcessingQuality.STANDARD,
            'max_file_size_mb': 100,
            'output_structure': settings.obsidian.vault_structure,
            'image_quality': 300,  # DPI para extração de imagens
            'preserve_layout': True,
            'extract_metadata': True,
            'detect_chapters': True
        }
        
        logger.info("BookProcessor inicializado")
    
    def analyze_book(self, filepath: str) -> Tuple[BookMetadata, List[str]]:
        """
        Analisa um arquivo de livro para extrair metadados e estimar processamento.
        
        Args:
            filepath: Caminho para o arquivo do livro
            
        Returns:
            Tupla (metadados, recomendações)
        """
        path = Path(filepath).expanduser()
        
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        
        # Verificar formato
        extension = path.suffix.lower()
        if extension not in self.supported_formats:
            raise ValueError(f"Formato não suportado: {extension}. Suportados: {list(self.supported_formats.keys())}")
        
        metadata = BookMetadata()
        recommendations = []
        
        # Informações básicas do arquivo
        metadata.file_size_mb = path.stat().st_size / (1024 * 1024)
        
        if metadata.file_size_mb > self.config['max_file_size_mb']:
            recommendations.append(f"Arquivo grande ({metadata.file_size_mb:.1f}MB). Considere processamento noturno.")
        
        # Extrair metadados baseado no formato
        if extension == '.pdf':
            metadata, recs = self._analyze_pdf(path)
            recommendations.extend(recs)
        elif extension == '.epub':
            metadata, recs = self._analyze_epub(path)
            recommendations.extend(recs)
        else:
            # Para outros formatos, usar metadados básicos
            metadata.title = path.stem
            recommendations.append(f"Formato {extension} não é suportado para processamento completo.")
        
        # Estimativa de tempo de processamento
        metadata.estimated_processing_time = self._estimate_processing_time(metadata)
        
        return metadata, recommendations
    
    def process_book(
        self,
        filepath: str,
        quality: ProcessingQuality = None,
        output_dir: Optional[str] = None,
        schedule_night: bool = False,
        force_immediate: bool = False,
        integrate_with_vault: bool = True,
        discipline: str = "",
    ) -> ProcessingResult:
        """
        Processa um livro completo.
        
        Args:
            filepath: Caminho para o arquivo do livro
            quality: Qualidade do processamento
            output_dir: Diretório de saída (opcional)
            schedule_night: Agendar para processamento noturno
            force_immediate: Se True, não agenda automaticamente por tempo estimado
            integrate_with_vault: Se True, integra resultado no vault automaticamente
            discipline: Nome da disciplina (obrigatório para PDF)
            
        Returns:
            ProcessingResult com o resultado
        """
        start_time = datetime.now()
        
        try:
            # Analisar o livro primeiro
            metadata, recommendations = self.analyze_book(filepath)
            
            # Determinar qualidade
            if quality is None:
                quality = self.config['default_quality']
            
            # Verificar se deve agendar para noite
            if schedule_night or (metadata.estimated_processing_time > 300 and not force_immediate):  # > 5 minutos
                logger.info(f"Agendando processamento noturno para: {metadata.title}")
                return ProcessingResult(
                    status=ProcessingStatus.SCHEDULED,
                    metadata=metadata,
                    start_time=start_time,
                    warnings=recommendations
                )
            
            # Determinar diretório de saída
            if output_dir:
                output_path = Path(output_dir).expanduser()
            else:
                # Usar estrutura padrão do vault: 01-LEITURAS/Autor/Título/
                safe_author = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
                safe_title = self._sanitize_filename(metadata.title)
                output_path = (
                    self.vault_manager.vault_path / 
                    "01-LEITURAS" / 
                    safe_author / 
                    safe_title
                )
            
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Processar baseado no formato
            extension = Path(filepath).suffix.lower()
            normalized_discipline = str(discipline or "").strip()
            if extension == ".pdf" and not normalized_discipline:
                raise ValueError("Processamento de PDF requer o nome da disciplina.")
            processor_func = self.supported_formats.get(extension)
            
            if not processor_func:
                raise ValueError(f"Processador não disponível para formato: {extension}")
            
            # Executar processamento
            logger.info(f"Iniciando processamento de {metadata.title} (qualidade: {quality.value})")
            
            result = processor_func(
                filepath=filepath,
                metadata=metadata,
                output_dir=output_path,
                quality=quality
            )
            
            result.start_time = start_time
            result.end_time = datetime.now()
            
            # Integrar com o vault
            if result.status == ProcessingStatus.COMPLETED and integrate_with_vault:
                self._integrate_with_vault(result, output_path, discipline=normalized_discipline)
            
            if result.status == ProcessingStatus.COMPLETED:
                logger.info(f"Processamento concluído: {metadata.title}")
            else:
                logger.warning(
                    f"Processamento finalizado com status {result.status.value}: {metadata.title} - "
                    f"{result.error or 'sem detalhes'}"
                )
            return result
            
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                metadata=metadata if 'metadata' in locals() else BookMetadata(),
                error=str(e),
                start_time=start_time,
                end_time=datetime.now()
            )
    
    def _analyze_pdf(self, filepath: Path) -> Tuple[BookMetadata, List[str]]:
        """Analisa um arquivo PDF."""
        metadata = BookMetadata()
        recommendations = []
        
        metadata.title = filepath.stem

        try:
            import fitz  # PyMuPDF

            with fitz.open(filepath) as doc:
                pdf_metadata = doc.metadata or {}
                detected_title = str(pdf_metadata.get('title') or '').strip()
                detected_author = str(pdf_metadata.get('author') or '').strip()

                metadata.title = detected_title or filepath.stem
                metadata.author = detected_author
                metadata.total_pages = len(doc)

                sample_pages = self._build_pdf_sample_pages(metadata.total_pages)
                text_lengths: List[int] = []
                image_pages = 0

                for page_index in sample_pages:
                    page = doc.load_page(page_index)
                    text = self._extract_pdf_page_text_sample(page)
                    text_lengths.append(len(text.strip()))
                    if page.get_images():
                        image_pages += 1

                avg_text_length = sum(text_lengths) / max(len(text_lengths), 1)
                low_text_pages = sum(1 for size in text_lengths if size < 80)

                metadata.has_images = image_pages > 0
                metadata.requires_ocr = (
                    metadata.total_pages > 0 and
                    (low_text_pages >= max(2, len(sample_pages) // 2) or avg_text_length < 120)
                )

                if metadata.requires_ocr:
                    recommendations.append(
                        "PDF com pouco texto nativo detectado em várias páginas. OCR provavelmente será necessário."
                    )
                    if shutil.which("tesseract") is None:
                        recommendations.append(
                            "OCR necessário, mas o binário `tesseract` não está instalado no sistema."
                        )
                elif avg_text_length < 300:
                    recommendations.append(
                        "PDF com extração textual fraca/irregular. O processamento pode alternar entre texto nativo e OCR."
                    )

                if metadata.has_images and not metadata.requires_ocr:
                    recommendations.append(
                        "PDF híbrido detectado: há imagens e texto nativo. Algumas páginas podem precisar de OCR."
                    )

                if self.config['detect_chapters']:
                    metadata.chapters = self._detect_pdf_chapters(doc)

        except ImportError:
            fallback_meta = self._analyze_pdf_with_fallback(filepath)
            metadata.title = fallback_meta.get("title") or metadata.title
            metadata.author = fallback_meta.get("author") or metadata.author
            metadata.total_pages = int(fallback_meta.get("total_pages") or metadata.total_pages or 0)
            recommendations.append(
                "PyMuPDF não instalado. A análise foi feita com fallback limitado; a transcrição completa exigirá pymupdf."
            )
        except Exception as e:
            logger.warning(f"Erro na análise do PDF: {e}")
            fallback_meta = self._analyze_pdf_with_fallback(filepath)
            metadata.title = fallback_meta.get("title") or metadata.title
            metadata.author = fallback_meta.get("author") or metadata.author
            metadata.total_pages = int(fallback_meta.get("total_pages") or metadata.total_pages or 0)
        
        return metadata, recommendations

    def _build_pdf_sample_pages(self, total_pages: int) -> List[int]:
        """Seleciona páginas de amostra ao longo do documento."""
        if total_pages <= 0:
            return [0]

        candidates = {
            0,
            min(1, total_pages - 1),
            min(2, total_pages - 1),
            total_pages // 3,
            total_pages // 2,
            max(total_pages - 3, 0),
            max(total_pages - 2, 0),
            total_pages - 1,
        }
        return sorted(page for page in candidates if 0 <= page < total_pages)

    def _extract_pdf_page_text_sample(self, page) -> str:
        """Extrai amostra textual de uma página para diagnóstico."""
        try:
            from .pdf_processor import PDFProcessorOCR

            text, _ = PDFProcessorOCR()._extract_best_page_text(page)
            return text
        except Exception:
            try:
                return (page.get_text("text", sort=True) or "").strip()
            except Exception:
                return ""

    def _analyze_pdf_with_fallback(self, filepath: Path) -> Dict[str, Any]:
        """Obtém metadados mínimos quando PyMuPDF não está disponível."""
        fallback = {
            "title": filepath.stem,
            "author": "",
            "total_pages": 0,
        }

        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(str(filepath))
            info = reader.metadata or {}
            fallback["title"] = str(getattr(info, "title", "") or info.get("/Title") or filepath.stem).strip() or filepath.stem
            fallback["author"] = str(getattr(info, "author", "") or info.get("/Author") or "").strip()
            fallback["total_pages"] = len(reader.pages)
            return fallback
        except Exception:
            return fallback
    
    def _analyze_epub(self, filepath: Path) -> Tuple[BookMetadata, List[str]]:
        """Analisa um arquivo EPUB."""
        metadata = BookMetadata()
        recommendations = []
        
        try:
            import ebooklib
            from ebooklib import epub
            
            book = epub.read_epub(filepath)
            
            # Extrair metadados
            title_data = book.get_metadata('DC', 'title')
            if title_data:
                metadata.title = title_data[0][0] if title_data else filepath.stem
            
            author_data = book.get_metadata('DC', 'creator')
            if author_data:
                metadata.author = author_data[0][0] if author_data else ''
            
            # Contar itens como proxy para "páginas"
            metadata.total_pages = len(list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT)))
            
            # Verificar imagens
            images = list(book.get_items_of_type(ebooklib.ITEM_IMAGE))
            if images:
                metadata.has_images = True
            
            # Extrair capítulos da TOC
            if self.config['detect_chapters']:
                metadata.chapters = self._extract_epub_toc(book)
        
        except ImportError:
            recommendations.append("ebooklib não instalado. Instale com: pip install ebooklib")
        except Exception as e:
            logger.warning(f"Erro na análise do EPUB: {e}")
        
        return metadata, recommendations
    
    def _process_pdf(self, filepath: str, metadata: BookMetadata, 
                    output_dir: Path, quality: ProcessingQuality) -> ProcessingResult:
        """Processa um arquivo PDF."""
        try:
            # Verificação explícita da dependência PyMuPDF para mensagens claras.
            import fitz  # noqa: F401

            # Compatibilidade: alguns ambientes expõem PDFProcessorOCR em vez de PDFProcessor.
            try:
                from .pdf_processor import PDFProcessor
            except ImportError:
                from .pdf_processor import PDFProcessorOCR as PDFProcessor
            
            processor = PDFProcessor(quality=quality)
            result = processor.process(filepath, output_dir, metadata)

            chapters = self._normalize_chapters(result.get('chapters', []))
            warnings = result.get('warnings', [])
            page_cache_dir = result.get('page_cache_dir')

            if not result.get('success', True):
                # Degradação graciosa: mantém processamento quando há conteúdo parcial utilizável.
                missing_text_warning = any(
                    "sem texto extraído após OCR" in str(w).lower()
                    for w in warnings
                )
                if chapters and missing_text_warning:
                    warnings = [
                        *warnings,
                        "Processamento parcial concluído: algumas páginas ficaram sem texto após OCR."
                    ]
                    if page_cache_dir:
                        warnings = [
                            *warnings,
                            f"Cache de OCR salvo em {page_cache_dir}. Uma nova execução continuará do progresso existente."
                        ]
                    chapter_warning = self._build_chapter_detection_warning(metadata, chapters)
                    if chapter_warning:
                        warnings = [*warnings, chapter_warning]
                    return ProcessingResult(
                        status=ProcessingStatus.COMPLETED,
                        metadata=metadata,
                        output_dir=output_dir,
                        processed_chapters=chapters,
                        warnings=warnings
                    )

                warning = "; ".join(warnings) or "Falha no processamento OCR do PDF"
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    metadata=metadata,
                    output_dir=output_dir,
                    processed_chapters=chapters,
                    warnings=warnings,
                    error=warning
                )

            if not chapters:
                return ProcessingResult(
                    status=ProcessingStatus.FAILED,
                    metadata=metadata,
                    output_dir=output_dir,
                    processed_chapters=[],
                    warnings=warnings,
                    error="Nenhum conteúdo foi extraído do PDF"
                )

            chapter_warning = self._build_chapter_detection_warning(metadata, chapters)
            if chapter_warning:
                warnings = [*warnings, chapter_warning]
            if page_cache_dir:
                warnings = [
                    *warnings,
                    f"Cache de OCR salvo em {page_cache_dir}."
                ]

            return ProcessingResult(
                status=ProcessingStatus.COMPLETED,
                metadata=metadata,
                output_dir=output_dir,
                processed_chapters=chapters,
                warnings=warnings
            )
            
        except ImportError as e:
            error_msg = str(e)
            if "fitz" in error_msg.lower() or "pymupdf" in error_msg.lower():
                user_error = "PyMuPDF não instalado. Instale com: pip install pymupdf"
            else:
                user_error = f"Processador PDF indisponível: {error_msg}"
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                metadata=metadata,
                error=user_error
            )
        except Exception as e:
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                metadata=metadata,
                error=f"Erro no processamento PDF: {e}"
            )
    
    def _process_epub(self, filepath: str, metadata: BookMetadata,
                     output_dir: Path, quality: ProcessingQuality) -> ProcessingResult:
        """Processa um arquivo EPUB."""
        try:
            from .epub_processor import EPUBProcessor
            
            processor = EPUBProcessor(quality=quality)
            result = processor.process(filepath, output_dir, metadata)
            
            return ProcessingResult(
                status=ProcessingStatus.COMPLETED,
                metadata=metadata,
                output_dir=output_dir,
                processed_chapters=result['chapters'],
                warnings=result.get('warnings', [])
            )
            
        except ImportError:
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                metadata=metadata,
                error="ebooklib não instalado. Instale com: pip install ebooklib"
            )
        except Exception as e:
            return ProcessingResult(
                status=ProcessingStatus.FAILED,
                metadata=metadata,
                error=f"Erro no processamento EPUB: {e}"
            )
    
    def _integrate_with_vault(
        self,
        result: ProcessingResult,
        output_dir: Path,
        discipline: str = "",
    ) -> None:
        """Integra o livro processado com o vault do Obsidian."""
        try:
            metadata = result.metadata
            safe_author = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
            safe_title = self._sanitize_filename(metadata.title)
            base_path = f"01-LEITURAS/{safe_author}/{safe_title}"

            def create_or_update_note(path: str, content: str, frontmatter: Dict[str, Any]) -> None:
                """Cria a nota; se já existir, atualiza conteúdo e frontmatter."""
                try:
                    self.vault_manager.create_note(
                        path,
                        content=content,
                        frontmatter=frontmatter
                    )
                except ValueError as e:
                    if "already exists" not in str(e).lower():
                        raise
                    self.vault_manager.update_note(
                        path,
                        content=content,
                        frontmatter=frontmatter
                    )
            
            # 1. Criar nota de metadados do livro
            book_note_path = f"{base_path}/📖 {safe_title}.md"
            
            frontmatter = {
                'title': metadata.title,
                'author': metadata.author,
                'type': 'book',
                'status': 'processed',
                'total_pages': metadata.total_pages,
                'language': metadata.language,
                'processed_date': datetime.now().isoformat(),
                'tags': ['book', 'processed', f'author:{metadata.author}']
            }
            
            content = f"""# {metadata.title}

## 📋 Metadados
- **Autor**: {metadata.author}
- **Editora**: {metadata.publisher or 'Desconhecida'}
- **Ano**: {metadata.year or 'Desconhecido'}
- **ISBN**: {metadata.isbn or 'Desconhecido'}
- **Páginas**: {metadata.total_pages}
- **Idioma**: {metadata.language}
- **Processado em**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 📚 Capítulos
{self._format_chapters_list(result.processed_chapters)}

## 📁 Estrutura
- **Diretório**: `{output_dir}`
- **Capítulos**: {len(result.processed_chapters)}
- **Status**: Processado ({result.status.value})

## 📝 Notas
<!-- Adicione suas anotações sobre o livro aqui -->
"""
            
            create_or_update_note(
                book_note_path,
                content=content,
                frontmatter=frontmatter
            )
            
            # 2. Criar notas para cada capítulo
            for chapter in result.processed_chapters:
                chapter_number = chapter.get('chapter_num') or chapter.get('number') or 0
                chapter_title = chapter.get('chapter_title') or chapter.get('title') or f"Capítulo {chapter_number}"
                safe_chapter_title = self._sanitize_filename(chapter_title)
                chapter_filename = f"{int(chapter_number):03d} - {safe_chapter_title}"
                chapter_note_path = f"{base_path}/{chapter_filename}.md"
                
                chapter_frontmatter = {
                    'title': chapter_title,
                    'book': metadata.title,
                    'author': metadata.author,
                    'chapter_number': chapter_number,
                    'pages': chapter.get('pages'),
                    'tags': ['chapter', 'book', f'book:{metadata.title}']
                }

                chapter_content = chapter.get('content', '')
                if not chapter_content.strip().startswith("# "):
                    chapter_content = (
                        f"# {chapter_title}\n\n"
                        f"## 📖 Páginas\n{chapter.get('pages', 'N/A')}\n\n"
                        f"{chapter_content}"
                    )
                
                create_or_update_note(
                    chapter_note_path,
                    content=chapter_content,
                    frontmatter=chapter_frontmatter
                )
            
            # 3. Criar índice de conceitos vazio
            concepts_path = f"{base_path}/🧠 Conceitos-Chave.md"
            
            concepts_content = f"""# Conceitos-Chave - {metadata.title}

## 📚 Livro
[[{metadata.title}]]

## 🧠 Conceitos
<!-- Liste e explique os conceitos principais do livro aqui -->

## 💬 Citações Importantes
<!-- Colete citações importantes do livro -->

## ❓ Questões para Reflexão
<!-- Questões geradas pela LLM ou suas próprias -->
"""
            
            create_or_update_note(
                concepts_path,
                content=concepts_content,
                frontmatter={'title': f'Conceitos-Chave - {metadata.title}', 'type': 'concepts'}
            )

            self._create_discipline_note(metadata, discipline)
            
            logger.info(f"Livro integrado ao vault: {metadata.title}")
            
        except Exception as e:
            logger.error(f"Erro ao integrar livro com vault: {e}")
            raise

    def _create_discipline_note(self, metadata: BookMetadata, discipline: str) -> None:
        """Cria/atualiza nota em 05-DISCIPLINAS para o livro processado."""
        discipline_name = str(discipline or "").strip()
        if not discipline_name:
            return

        safe_author = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
        safe_title = self._sanitize_filename(metadata.title)
        safe_discipline = self._sanitize_filename(discipline_name)
        note_path = f"05-DISCIPLINAS/{safe_discipline}.md"
        vault_root = Path(self.vault_manager.vault_path)
        book_note_abs = vault_root / "01-LEITURAS" / safe_author / safe_title / f"📖 {safe_title}.md"

        discipline_tag = self._discipline_tag(discipline_name)
        tag_line = f"- #{discipline_tag}\n"

        ensure_discipline_note(vault_root, discipline_name)
        append_book_note_links(vault_root, discipline_name, [book_note_abs])
        ensure_citations_note_for_book(
            vault_root,
            book_note_path=book_note_abs,
            discipline=discipline_name,
            discipline_note_path=vault_root / note_path,
        )

        existing_note = self.vault_manager.get_note_by_path(note_path)
        frontmatter = {
            "title": f"Disciplina - {discipline_name}",
            "type": "disciplina",
            "discipline": discipline_name,
            "tags": ["disciplina", discipline_tag],
        }

        if existing_note:
            content = (vault_root / note_path).read_text(encoding="utf-8", errors="ignore")
            if f"#{discipline_tag}" not in content:
                content = content.rstrip() + "\n" + tag_line

            merged_frontmatter = dict(existing_note.frontmatter or {})
            existing_tags = merged_frontmatter.get("tags", [])
            if isinstance(existing_tags, str):
                existing_tags = [existing_tags]
            merged_frontmatter.update(frontmatter)
            merged_frontmatter["tags"] = list(dict.fromkeys([*existing_tags, "disciplina", discipline_tag]))

            self.vault_manager.update_note(
                note_path,
                content=content.rstrip() + "\n",
                frontmatter=merged_frontmatter,
            )
            return

        content = (vault_root / note_path).read_text(encoding="utf-8", errors="ignore")
        if f"#{discipline_tag}" not in content:
            content = content.rstrip() + "\n" + tag_line + "\n"
        self.vault_manager.create_note(
            note_path,
            content=content,
            frontmatter=frontmatter,
        )
    
    def _format_chapters_list(self, chapters: List[Dict]) -> str:
        """Formata lista de capítulos para markdown."""
        if not chapters:
            return "Nenhum capítulo detectado."
        
        formatted = ""
        for chapter in chapters:
            chapter_num = chapter.get('chapter_num') or chapter.get('number') or 0
            title = chapter.get('chapter_title') or chapter.get('title') or 'Capítulo sem título'
            filename = f"{int(chapter_num):03d} - {self._sanitize_filename(title)}"
            formatted += f"- [[{filename}|{title}]]\n"
        
        return formatted
    
    def _detect_pdf_chapters(self, doc) -> List[Dict]:
        """Detecta capítulos em um PDF."""
        try:
            total_pages = len(doc)

            toc_entries = []
            try:
                toc_entries = doc.get_toc(simple=True) or []
            except Exception:
                toc_entries = []

            # Prioriza entradas de primeiro nível do sumário (TOC).
            if toc_entries:
                level_one = [entry for entry in toc_entries if len(entry) >= 3 and entry[0] == 1]
                if not level_one:
                    min_level = min(entry[0] for entry in toc_entries if len(entry) >= 3)
                    level_one = [entry for entry in toc_entries if len(entry) >= 3 and entry[0] == min_level]

                chapter_points = []
                seen_pages = set()
                for entry in level_one:
                    _, title, page = entry[:3]
                    if not title or page in seen_pages or page < 1 or page > total_pages:
                        continue
                    seen_pages.add(page)
                    chapter_points.append({"title": str(title).strip(), "start_page": int(page)})

                if len(chapter_points) >= 2:
                    return self._build_chapter_ranges(chapter_points, total_pages, source="toc", confidence=0.95)

            # Fallback heurístico no topo das páginas.
            heading_pattern = re.compile(
                r"^(cap[ií]tulo|chapter|parte|part|livro|book)\s+([ivxlcdm]+|\d+)",
                re.IGNORECASE
            )
            chapter_points = []
            for page_idx in range(total_pages):
                page = doc.load_page(page_idx)
                text = page.get_text("text") or ""
                lines = [ln.strip() for ln in text.split('\n')[:12] if ln.strip()]
                for line in lines:
                    normalized = re.sub(r"\s+", " ", line)
                    if len(normalized) <= 120 and heading_pattern.search(normalized):
                        chapter_points.append({
                            "title": normalized,
                            "start_page": page_idx + 1
                        })
                        break

            dedup = []
            seen = set()
            for item in chapter_points:
                key = (item["start_page"], item["title"].lower())
                if key in seen:
                    continue
                seen.add(key)
                dedup.append(item)

            if len(dedup) >= 2:
                return self._build_chapter_ranges(dedup, total_pages, source="heuristic", confidence=0.6)

        except Exception as e:
            logger.debug(f"Erro na detecção de capítulos: {e}")

        return []

    def _build_chapter_ranges(self, chapter_points: List[Dict[str, Any]], total_pages: int,
                              source: str, confidence: float) -> List[Dict[str, Any]]:
        """Transforma pontos de início em intervalos completos de capítulos."""
        chapter_points = sorted(chapter_points, key=lambda item: item["start_page"])
        chapters: List[Dict[str, Any]] = []

        for idx, chapter in enumerate(chapter_points):
            start_page = chapter["start_page"]
            if idx + 1 < len(chapter_points):
                end_page = chapter_points[idx + 1]["start_page"] - 1
            else:
                end_page = total_pages

            if end_page < start_page:
                continue

            chapters.append({
                "number": idx + 1,
                "title": chapter["title"] or f"Capítulo {idx + 1}",
                "page": start_page,
                "start_page": start_page,
                "end_page": end_page,
                "source": source,
                "confidence": confidence
            })

        return chapters

    def _normalize_chapters(self, chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normaliza estrutura de capítulos para uso consistente no pipeline/UI."""
        normalized: List[Dict[str, Any]] = []
        for index, chapter in enumerate(chapters, start=1):
            chapter_num = chapter.get("chapter_num") or chapter.get("number") or index
            chapter_title = chapter.get("chapter_title") or chapter.get("title") or f"Capítulo {chapter_num}"
            start_page = chapter.get("start_page")
            end_page = chapter.get("end_page")
            pages = chapter.get("pages")
            if not pages and start_page and end_page:
                pages = f"{start_page}-{end_page}"

            normalized.append({
                **chapter,
                "number": chapter_num,
                "chapter_num": chapter_num,
                "title": chapter_title,
                "chapter_title": chapter_title,
                "pages": pages or ""
            })
        return normalized

    def _build_chapter_detection_warning(self, metadata: BookMetadata,
                                         processed_chapters: List[Dict[str, Any]]) -> Optional[str]:
        """Retorna aviso quando a divisão em capítulos não está clara."""
        detected = metadata.chapters or []
        if len(detected) < 2:
            return (
                "Não foi possível identificar com clareza os capítulos pelo sumário do arquivo. "
                "As notas por capítulo foram criadas por faixas de páginas."
            )

        low_confidence = [chapter for chapter in detected if float(chapter.get("confidence", 0)) < 0.8]
        if low_confidence:
            return (
                "A divisão de capítulos foi identificada com baixa confiança. "
                "Revise os títulos e intervalos das notas de capítulo."
            )

        if len(processed_chapters) < len(detected):
            return (
                "Nem todos os capítulos detectados puderam ser materializados em notas. "
                "Revise a estrutura gerada no vault."
            )

        return None
    
    def _extract_epub_toc(self, book) -> List[Dict]:
        """Extrai TOC de um EPUB."""
        chapters = []
        
        try:
            toc = book.toc
            for item in toc:
                chapters.append({
                    'title': item.title,
                    'href': item.href,
                    'level': getattr(item, 'level', 0)
                })
        except:
            pass
        
        return chapters
    
    def _estimate_processing_time(self, metadata: BookMetadata) -> int:
        """Estima tempo de processamento em segundos."""
        base_time = 10  # segundos base
        
        # Fatores que afetam o tempo
        time_per_page = 2 if metadata.requires_ocr else 0.5
        image_penalty = 5 if metadata.has_images else 0
        
        estimated = base_time + (metadata.total_pages * time_per_page) + image_penalty
        return int(estimated)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitiza um nome de arquivo para ser seguro em sistemas de arquivos."""
        # Substituir caracteres problemáticos
        import re
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        return filename[:100]  # Limitar tamanho

    def _discipline_tag(self, discipline: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(discipline or "").strip())
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
        return normalized or "disciplina"

    def _normalize_path_key(self, value: str) -> str:
        """Normaliza texto para comparação estável de pastas."""
        normalized = unicodedata.normalize("NFKD", value or "")
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized).strip().lower()
        return re.sub(r"\s+", " ", normalized)

    def _primary_author(self, author_name: str) -> str:
        """Extrai autor principal para evitar duplicatas por coautoria/formato."""
        raw = (author_name or "").strip()
        if not raw:
            return "Autor Desconhecido"

        split_patterns = [r"\s*&\s*", r"\s+and\s+", r"\s+e\s+", r"\s*;\s*", r"\s*/\s*", r"\s*\|\s*"]
        for pattern in split_patterns:
            parts = re.split(pattern, raw, maxsplit=1, flags=re.IGNORECASE)
            if parts and parts[0].strip() and len(parts) > 1:
                raw = parts[0].strip()
                break

        if "," in raw:
            fragments = [frag.strip() for frag in raw.split(",") if frag.strip()]
            if len(fragments) >= 2:
                raw = f"{fragments[1]} {fragments[0]}".strip()

        return raw

    def _author_tokens(self, author_name: str) -> set[str]:
        normalized = self._normalize_path_key(self._primary_author(author_name))
        return {tok for tok in normalized.split(" ") if len(tok) > 1}

    def _soft_token_overlap(self, left_tokens: set[str], right_tokens: set[str]) -> float:
        """Sobreposição fuzzy de tokens para variações ortográficas leves."""
        if not left_tokens or not right_tokens:
            return 0.0

        right_list = list(right_tokens)
        used = set()
        matched = 0

        for token in left_tokens:
            best_idx = None
            best_ratio = 0.0
            for idx, candidate in enumerate(right_list):
                if idx in used:
                    continue
                ratio = SequenceMatcher(None, token, candidate).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = idx

            if best_idx is not None and best_ratio >= 0.84:
                used.add(best_idx)
                matched += 1

        return matched / max(len(left_tokens), len(right_tokens))

    def _soft_token_overlap(self, left_tokens: set[str], right_tokens: set[str]) -> float:
        """Sobreposição fuzzy de tokens para variações ortográficas leves."""
        if not left_tokens or not right_tokens:
            return 0.0

        right_list = list(right_tokens)
        used = set()
        matched = 0

        for token in left_tokens:
            best_idx = None
            best_ratio = 0.0
            for idx, candidate in enumerate(right_list):
                if idx in used:
                    continue
                ratio = SequenceMatcher(None, token, candidate).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = idx

            if best_idx is not None and best_ratio >= 0.84:
                used.add(best_idx)
                matched += 1

        return matched / max(len(left_tokens), len(right_tokens))

    def _resolve_author_directory_name(self, author_name: str) -> str:
        """
        Reutiliza pasta de autor já existente em 01-LEITURAS quando o nome bate
        por normalização (acentos/pontuação/caixa ignorados).
        """
        canonical_author = self._primary_author(author_name or "Autor Desconhecido")
        safe_author = self._sanitize_filename(canonical_author)
        authors_root = self.vault_manager.vault_path / "01-LEITURAS"

        if not authors_root.exists():
            return safe_author

        target_key = self._normalize_path_key(canonical_author)
        target_tokens = self._author_tokens(canonical_author)
        if not target_key:
            return safe_author

        best_match_name = None
        best_score = 0.0

        try:
            for child in authors_root.iterdir():
                if not child.is_dir():
                    continue

                child_key = self._normalize_path_key(child.name)
                if child_key == target_key:
                    return child.name

                child_tokens = self._author_tokens(child.name)
                if not target_tokens or not child_tokens:
                    continue

                intersection = len(target_tokens & child_tokens)
                union = len(target_tokens | child_tokens)
                jaccard_score = (intersection / union) if union else 0.0
                fuzzy_score = self._soft_token_overlap(target_tokens, child_tokens)
                score = max(jaccard_score, fuzzy_score)

                if score > best_score:
                    best_score = score
                    best_match_name = child.name
        except Exception:
            return safe_author

        if best_match_name and best_score >= 0.8:
            return best_match_name

        return safe_author

class ChapterProcessor:
    """Processador incremental de capítulos de livros"""
    
    def __init__(self, vault_manager: ObsidianVaultManager):
        self.vault_manager = vault_manager
        self.llm_pdf_processor = None
        self.book_registry = {}
        self._load_registry()
    
    def _load_registry(self):
        """Carrega registro de livros já processados"""
        registry_path = self.vault_manager.vault_path / "06-RECURSOS" / "book_registry.json"
        if registry_path.exists():
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    self.book_registry = json.load(f)
            except:
                self.book_registry = {}
    
    def _save_registry(self):
        """Salva registro de livros"""
        registry_path = self.vault_manager.vault_path / "06-RECURSOS" / "book_registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.book_registry, f, indent=2, ensure_ascii=False)
    
    def register_book(self, metadata: BookMetadata, output_dir: Path) -> str:
        """Registra um novo livro e retorna seu ID"""
        import hashlib
        
        # Gera ID único baseado no título e autor
        book_id = hashlib.md5(f"{metadata.title}_{metadata.author}".encode()).hexdigest()[:12]
        
        self.book_registry[book_id] = {
            'title': metadata.title,
            'author': metadata.author,
            'output_dir': str(output_dir.relative_to(self.vault_manager.vault_path)),
            'total_pages': metadata.total_pages,
            'chapters_processed': [],
            'registered_at': datetime.now().isoformat(),
            'next_chapter': 1
        }
        
        self._save_registry()
        return book_id
    
    def process_chapters(self, pdf_path: str, num_chapters: int = None, 
                        start_chapter: int = 1, book_id: str = None) -> Dict:
        """
        Processa capítulos de um livro PDF
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            num_chapters: Número de capítulos a processar (None = todos)
            start_chapter: Capítulo inicial (1-indexed)
            book_id: ID do livro existente (None para novo)
            
        Returns:
            Dicionário com resultados
        """
        try:
            import fitz
            
            # Analisar o livro
            metadata, _ = self._analyze_pdf(pdf_path)
            
            # Determinar diretório de saída no vault
            safe_author = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
            safe_title = self._sanitize_filename(metadata.title)
            
            output_dir = self.vault_manager.vault_path / "01-LEITURAS" / safe_author / safe_title
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Criar ou recuperar registro do livro
            if book_id and book_id in self.book_registry:
                book_info = self.book_registry[book_id]
                start_chapter = book_info['next_chapter']
            else:
                book_id = self.register_book(metadata, output_dir)
                start_chapter = 1
            
            # Processar capítulos
            results = []
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # Estimar páginas por capítulo (10 por padrão)
            pages_per_chapter = 10
            total_chapters_estimated = max(1, total_pages // pages_per_chapter)
            
            if num_chapters is None:
                num_chapters = total_chapters_estimated - start_chapter + 1
            
            for chapter_num in range(start_chapter, start_chapter + num_chapters):
                if chapter_num > total_chapters_estimated:
                    break
                
                # Calcular páginas do capítulo
                start_page = (chapter_num - 1) * pages_per_chapter
                end_page = min(start_page + pages_per_chapter - 1, total_pages - 1)
                
                # Processar capítulo
                result = self._process_chapter_range(
                    doc, start_page, end_page, chapter_num, 
                    metadata, output_dir, book_id
                )
                
                if result['success']:
                    results.append(result)
                    
                    # Atualizar registro
                    self.book_registry[book_id]['chapters_processed'].append({
                        'chapter': chapter_num,
                        'title': result['chapter_title'],
                        'pages': f"{start_page+1}-{end_page+1}",
                        'processed_at': datetime.now().isoformat()
                    })
                    self.book_registry[book_id]['next_chapter'] = chapter_num + 1
                    self._save_registry()
                    
                    # Criar nota no Obsidian
                    self._create_obsidian_note(result, metadata, output_dir, book_id)
                    
                    # Agendar leitura
                    self._schedule_reading(book_id, metadata, result)
            
            doc.close()
            
            return {
                'success': True,
                'book_id': book_id,
                'book_title': metadata.title,
                'author': metadata.author,
                'chapters_processed': len(results),
                'results': results,
                'next_chapter': self.book_registry[book_id]['next_chapter']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _analyze_pdf(self, pdf_path: str) -> tuple:
        """Analisa PDF básico"""
        import fitz
        
        doc = fitz.open(pdf_path)
        metadata = BookMetadata()
        
        # Extrair metadados
        pdf_metadata = doc.metadata
        metadata.title = pdf_metadata.get('title', Path(pdf_path).stem)
        metadata.author = pdf_metadata.get('author', 'Autor Desconhecido')
        metadata.total_pages = len(doc)
        
        doc.close()
        return metadata, []
    
    def _process_chapter_range(self, doc, start_page: int, end_page: int, 
                              chapter_num: int, metadata: BookMetadata,
                              output_dir: Path, book_id: str) -> Dict:
        """Processa um intervalo de páginas como capítulo"""
        try:
            chapter_text = ""
            
            for page_num in range(start_page, end_page + 1):
                if page_num >= len(doc):
                    break
                
                page = doc.load_page(page_num)
                try:
                    from .pdf_processor import PDFProcessorOCR
                    text = PDFProcessorOCR.extract_page_text_preserving_layout(
                        page,
                        preserve_layout=True,
                    )
                except Exception:
                    text = page.get_text("text", sort=True)
                chapter_text += f"\n\n--- Página {page_num + 1} ---\n\n{text}"
            
            # Detectar título do capítulo
            lines = chapter_text.strip().split('\n')
            chapter_title = f"Capítulo {chapter_num}"
            
            for line in lines[:10]:
                line = line.strip()
                if (len(line) > 20 and len(line) < 100 and 
                    not line.startswith('---') and
                    not re.match(r'^\d+$', line)):
                    # Remover caracteres especiais
                    clean_line = re.sub(r'^[^a-zA-Z0-9]*', '', line)
                    if clean_line:
                        chapter_title = clean_line[:80]
                        break
            
            return {
                'success': True,
                'chapter_num': chapter_num,
                'chapter_title': chapter_title,
                'start_page': start_page + 1,
                'end_page': end_page + 1,
                'num_pages': end_page - start_page + 1,
                'content': chapter_text,
                'content_length': len(chapter_text)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'chapter_num': chapter_num
            }
    
    def _create_obsidian_note(self, chapter_data: Dict, metadata: BookMetadata,
                             output_dir: Path, book_id: str):
        """Cria nota do capítulo no Obsidian"""
        try:
            chapter_num = chapter_data['chapter_num']
            chapter_title = chapter_data['chapter_title']
            safe_title = self._sanitize_filename(chapter_title)
            
            # Nome do arquivo
            filename = f"{chapter_num:03d} - {safe_title}.md"
            author_dir = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
            title_dir = self._sanitize_filename(metadata.title)
            relative_path = f"01-LEITURAS/{author_dir}/{title_dir}/{filename}"
            
            # Frontmatter
            frontmatter = {
                'title': f"{metadata.title} - {chapter_title}",
                'book': metadata.title,
                'author': metadata.author,
                'chapter': chapter_num,
                'pages': f"{chapter_data['start_page']}-{chapter_data['end_page']}",
                'total_pages': metadata.total_pages,
                'book_id': book_id,
                'processed_date': datetime.now().isoformat(),
                'tags': ['livro', 'capitulo', f'livro:{metadata.title}']
            }
            
            # Conteúdo
            content = f"""# {chapter_title}

## 📚 Livro
[[{metadata.title}]]

## 📖 Informações
- **Livro**: {metadata.title}
- **Autor**: {metadata.author}
- **Capítulo**: {chapter_num}
- **Páginas**: {chapter_data['start_page']}-{chapter_data['end_page']}

## 📝 Conteúdo
{chapter_data['content']}

## 💭 Anotações
<!-- Adicione suas anotações aqui -->

## 🔗 Links
[[{metadata.title}]] | [[Índice - {metadata.title}]]
"""
            
            # Criar ou atualizar nota
            existing_note = self.vault_manager.get_note_by_path(relative_path)
            
            if existing_note:
                self.vault_manager.update_note(
                    relative_path,
                    content=content,
                    frontmatter=frontmatter
                )
                print(f"✅ Capítulo {chapter_num} atualizado: {filename}")
            else:
                self.vault_manager.create_note(
                    relative_path,
                    content=content,
                    frontmatter=frontmatter
                )
                print(f"✅ Capítulo {chapter_num} criado: {filename}")
            
            # Criar/atualizar índice do livro
            self._update_book_index(metadata, output_dir, book_id)
            
        except Exception as e:
            print(f"❌ Erro criando nota: {e}")
    
    def _update_book_index(self, metadata: BookMetadata, output_dir: Path, book_id: str):
        """Cria/atualiza índice do livro no vault"""
        try:
            author_dir = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
            title_dir = self._sanitize_filename(metadata.title)
            relative_path = f"01-LEITURAS/{author_dir}/{title_dir}/📖 {metadata.title}.md"
            
            # Buscar capítulos existentes apenas no diretório do livro.
            book_notes = []
            book_prefix = f"01-LEITURAS/{author_dir}/{title_dir}"
            for note in self.vault_manager.get_notes_by_prefix(book_prefix, include_content=False):
                if note.path.name != f"📖 {metadata.title}.md" and 'chapter' in note.frontmatter:
                    book_notes.append({
                        'path': note.path,
                        'chapter': note.frontmatter.get('chapter', 0),
                        'title': note.frontmatter.get('title', '')
                    })
            
            # Ordenar por capítulo
            book_notes.sort(key=lambda x: x['chapter'])
            
            # Conteúdo do índice
            frontmatter = {
                'title': metadata.title,
                'author': metadata.author,
                'type': 'livro',
                'book_id': book_id,
                'total_pages': metadata.total_pages,
                'total_chapters': len(book_notes),
                'tags': ['livro', 'indice', f'autor:{metadata.author}']
            }
            
            content = f"""# {metadata.title}

## 👤 Autor
{metadata.author}

## 📊 Informações
- **Total de páginas**: {metadata.total_pages}
- **Capítulos processados**: {len(book_notes)}
- **ID do livro**: {book_id}

## 📑 Capítulos
"""
            
            # Lista de capítulos
            for note in book_notes:
                note_name = note['path'].stem
                content += f"- [[{note_name}|Capítulo {note['chapter']}]]\n"
            
            content += f"""

## 📝 Notas Gerais
<!-- Adicione suas notas sobre o livro aqui -->

## 🎯 Objetivos de Leitura
<!-- Defina seus objetivos de leitura -->

## 📅 Progresso
<!-- Acompanhe seu progresso -->
"""
            
            # Criar ou atualizar índice
            existing_note = self.vault_manager.get_note_by_path(relative_path)
            
            if existing_note:
                self.vault_manager.update_note(
                    relative_path,
                    content=content,
                    frontmatter=frontmatter
                )
            else:
                self.vault_manager.create_note(
                    relative_path,
                    content=content,
                    frontmatter=frontmatter
                )
                
        except Exception as e:
            print(f"❌ Erro atualizando índice: {e}")
    
    def _schedule_reading(self, book_id: str, metadata: BookMetadata, chapter_data: Dict):
        """Agenda leitura do capítulo"""
        try:
            # Importar aqui para evitar dependência circular
            from .reading_manager import ReadingManager
            from .agenda_manager import AgendaManager
            
            reading_manager = ReadingManager(str(self.vault_manager.vault_path))
            agenda_manager = AgendaManager(str(self.vault_manager.vault_path))
            
            # Adicionar livro ao reading manager se não existir
            if book_id not in reading_manager.readings:
                reading_manager.add_book(
                    title=metadata.title,
                    author=metadata.author,
                    total_pages=metadata.total_pages,
                    book_id=book_id
                )
            
            # Calcular tempo estimado (2 minutos por página)
            estimated_minutes = chapter_data['num_pages'] * 2
            
            # Encontrar slot livre
            from datetime import datetime, timedelta
            
            for day_offset in range(1, 8):  # Próximos 7 dias
                target_date = datetime.now() + timedelta(days=day_offset)
                date_str = target_date.strftime("%Y-%m-%d")
                
                free_slots = agenda_manager.find_free_slots(
                    date_str,
                    duration_minutes=estimated_minutes,
                    start_hour=9,
                    end_hour=22
                )
                
                if free_slots:
                    # Usar o primeiro slot livre
                    slot = free_slots[0]
                    
                    # Perguntar ao usuário (simulação - na prática seria input)
                    print(f"\n📚 Capítulo {chapter_data['chapter_num']} de '{metadata.title}'")
                    print(f"📖 Páginas: {chapter_data['num_pages']}")
                    print(f"⏱️ Tempo estimado: {estimated_minutes} minutos")
                    print(f"📅 Slot disponível: {slot['start']}")
                    
                    # Em uma implementação real, aqui perguntaríamos ao usuário
                    # Para agora, vamos aceitar automaticamente
                    event_id = agenda_manager.add_event(
                        title=f"Leitura: {metadata.title} - {chapter_data['chapter_title']}",
                        start=slot['start'],
                        end=slot['end'],
                        event_type="leitura",
                        book_id=book_id,
                        metadata={
                            'chapter': chapter_data['chapter_num'],
                            'pages': chapter_data['num_pages']
                        }
                    )
                    
                    print(f"✅ Leitura agendada: Evento {event_id}")
                    break
                    
        except ImportError:
            print("⚠️ Módulos de agenda não disponíveis")
        except Exception as e:
            print(f"⚠️ Erro agendando leitura: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitiza nome de arquivo"""
        # Substituir caracteres problemáticos
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        return filename[:100]

    def _normalize_path_key(self, value: str) -> str:
        """Normaliza texto para comparação de nomes de pasta."""
        normalized = unicodedata.normalize("NFKD", value or "")
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized).strip().lower()
        return re.sub(r"\s+", " ", normalized)

    def _primary_author(self, author_name: str) -> str:
        """Extrai autor principal para evitar duplicatas por coautoria/formato."""
        raw = (author_name or "").strip()
        if not raw:
            return "Autor Desconhecido"

        split_patterns = [r"\s*&\s*", r"\s+and\s+", r"\s+e\s+", r"\s*;\s*", r"\s*/\s*", r"\s*\|\s*"]
        for pattern in split_patterns:
            parts = re.split(pattern, raw, maxsplit=1, flags=re.IGNORECASE)
            if parts and parts[0].strip() and len(parts) > 1:
                raw = parts[0].strip()
                break

        if "," in raw:
            fragments = [frag.strip() for frag in raw.split(",") if frag.strip()]
            if len(fragments) >= 2:
                raw = f"{fragments[1]} {fragments[0]}".strip()

        return raw

    def _author_tokens(self, author_name: str) -> set[str]:
        normalized = self._normalize_path_key(self._primary_author(author_name))
        return {tok for tok in normalized.split(" ") if len(tok) > 1}

    def _resolve_author_directory_name(self, author_name: str) -> str:
        """Reutiliza diretório de autor existente em 01-LEITURAS."""
        canonical_author = self._primary_author(author_name or "Autor Desconhecido")
        safe_author = self._sanitize_filename(canonical_author)
        authors_root = self.vault_manager.vault_path / "01-LEITURAS"
        if not authors_root.exists():
            return safe_author

        target_key = self._normalize_path_key(canonical_author)
        target_tokens = self._author_tokens(canonical_author)
        if not target_key:
            return safe_author

        best_match_name = None
        best_score = 0.0

        try:
            for child in authors_root.iterdir():
                if not child.is_dir():
                    continue

                child_key = self._normalize_path_key(child.name)
                if child_key == target_key:
                    return child.name

                child_tokens = self._author_tokens(child.name)
                if not target_tokens or not child_tokens:
                    continue

                intersection = len(target_tokens & child_tokens)
                union = len(target_tokens | child_tokens)
                jaccard_score = (intersection / union) if union else 0.0
                fuzzy_score = self._soft_token_overlap(target_tokens, child_tokens)
                score = max(jaccard_score, fuzzy_score)

                if score > best_score:
                    best_score = score
                    best_match_name = child.name
        except Exception:
            return safe_author

        if best_match_name and best_score >= 0.8:
            return best_match_name

        return safe_author
# Adicione ao final do arquivo book_processor.py
chapter_processor = ChapterProcessor(ObsidianVaultManager())
