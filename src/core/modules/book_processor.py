# src/core/modules/book_processor.py (linhas 1-20 corrigidas)
import os
import logging
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# CORREÇÃO: Importação mais flexível
try:
    # Tenta importação absoluta primeiro
    from src.core.config.settings import settings
except ImportError:
    try:
        # Tenta importação relativa
        from ...config.settings import settings
    except ImportError:
        # Configuração padrão para testes
        class Settings:
            class ObsidianConfig:
                vault_structure = ["01-LEITURAS", "02-CONCEITOS", "06-RECURSOS"]
                brain_regions = ["MEMÓRIA", "ANÁLISE"]
            obsidian = ObsidianConfig()
            vault_path = None
        settings = Settings()

from .obsidian.vault_manager import ObsidianVaultManager

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
        schedule_night: bool = False
    ) -> ProcessingResult:
        """
        Processa um livro completo.
        
        Args:
            filepath: Caminho para o arquivo do livro
            quality: Qualidade do processamento
            output_dir: Diretório de saída (opcional)
            schedule_night: Agendar para processamento noturno
            
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
            if schedule_night or metadata.estimated_processing_time > 300:  # > 5 minutos
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
                safe_author = self._sanitize_filename(metadata.author or "Autor Desconhecido")
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
            if result.status == ProcessingStatus.COMPLETED:
                self._integrate_with_vault(result, output_path)
            
            logger.info(f"Processamento concluído: {metadata.title}")
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
        
        try:
            import fitz  # PyMuPDF
            
            with fitz.open(filepath) as doc:
                # Metadados básicos
                pdf_metadata = doc.metadata
                metadata.title = pdf_metadata.get('title', filepath.stem)
                metadata.author = pdf_metadata.get('author', '')
                metadata.total_pages = len(doc)
                
                # Verificar se é PDF escaneado (requer OCR)
                first_page = doc.load_page(0)
                text = first_page.get_text()
                
                if len(text.strip()) < 50:  # Pouco texto -> provavelmente escaneado
                    metadata.requires_ocr = True
                    metadata.has_images = True
                    recommendations.append("PDF parece ser escaneado. Será necessário OCR.")
                
                # Verificar imagens
                for i in range(min(5, len(doc))):
                    page = doc.load_page(i)
                    if page.get_images():
                        metadata.has_images = True
                        break
                
                # Tentar detectar capítulos (heurística simples)
                if self.config['detect_chapters']:
                    metadata.chapters = self._detect_pdf_chapters(doc)
        
        except ImportError:
            recommendations.append("PyMuPDF não instalado. Instale com: pip install pymupdf")
        except Exception as e:
            logger.warning(f"Erro na análise do PDF: {e}")
        
        return metadata, recommendations
    
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
            import fitz
            from .pdf_processor import PDFProcessor
            
            processor = PDFProcessor(quality=quality)
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
                error="PyMuPDF não instalado. Instale com: pip install pymupdf"
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
    
    def _integrate_with_vault(self, result: ProcessingResult, output_dir: Path) -> None:
        """Integra o livro processado com o vault do Obsidian."""
        try:
            metadata = result.metadata
            
            # 1. Criar nota de metadados do livro
            book_note_path = f"01-LEITURAS/{metadata.author}/{metadata.title}/📖 {metadata.title}.md"
            
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
            
            self.vault_manager.create_note(
                book_note_path,
                content=content,
                frontmatter=frontmatter
            )
            
            # 2. Criar notas para cada capítulo
            for chapter in result.processed_chapters:
                chapter_note_path = f"01-LEITURAS/{metadata.author}/{metadata.title}/{chapter['filename']}.md"
                
                chapter_frontmatter = {
                    'title': chapter['title'],
                    'book': metadata.title,
                    'author': metadata.author,
                    'chapter_number': chapter.get('number'),
                    'tags': ['chapter', 'book', f'book:{metadata.title}']
                }
                
                self.vault_manager.create_note(
                    chapter_note_path,
                    content=chapter['content'],
                    frontmatter=chapter_frontmatter
                )
            
            # 3. Criar índice de conceitos vazio
            concepts_path = f"01-LEITURAS/{metadata.author}/{metadata.title}/🧠 Conceitos-Chave.md"
            
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
            
            self.vault_manager.create_note(
                concepts_path,
                content=concepts_content,
                frontmatter={'title': f'Conceitos-Chave - {metadata.title}', 'type': 'concepts'}
            )
            
            logger.info(f"Livro integrado ao vault: {metadata.title}")
            
        except Exception as e:
            logger.error(f"Erro ao integrar livro com vault: {e}")
            raise
    
    def _format_chapters_list(self, chapters: List[Dict]) -> str:
        """Formata lista de capítulos para markdown."""
        if not chapters:
            return "Nenhum capítulo detectado."
        
        formatted = ""
        for chapter in chapters:
            title = chapter.get('title', 'Capítulo sem título')
            filename = chapter.get('filename', '').replace('.md', '')
            formatted += f"- [[{filename}|{title}]]\n"
        
        return formatted
    
    def _detect_pdf_chapters(self, doc) -> List[Dict]:
        """Detecta capítulos em um PDF."""
        chapters = []
        
        try:
            for i in range(len(doc)):
                page = doc.load_page(i)
                text = page.get_text("text")
                
                # Heurística: linhas que podem ser títulos de capítulo
                lines = text.split('\n')
                for line in lines[:10]:  # Primeiras linhas da página
                    line = line.strip()
                    if (len(line) < 100 and  # Não muito longo
                        any(word in line.lower() for word in ['capítulo', 'chapter', 'parte', 'part', 'livro', 'book']) and
                        any(char.isdigit() for char in line)):
                        
                        chapters.append({
                            'page': i + 1,
                            'title': line,
                            'number': i + 1
                        })
                        break
        
        except Exception as e:
            logger.debug(f"Erro na detecção de capítulos: {e}")
        
        return chapters
    
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
            safe_author = self._sanitize_filename(metadata.author or "Autor Desconhecido")
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
                text = page.get_text()
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
            relative_path = f"01-LEITURAS/{self._sanitize_filename(metadata.author)}/{self._sanitize_filename(metadata.title)}/{filename}"
            
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
            relative_path = f"01-LEITURAS/{self._sanitize_filename(metadata.author)}/{self._sanitize_filename(metadata.title)}/📖 {metadata.title}.md"
            
            # Buscar capítulos existentes
            book_notes = []
            for note in self.vault_manager.get_all_notes():
                if (f"01-LEITURAS/{self._sanitize_filename(metadata.author)}/{self._sanitize_filename(metadata.title)}" in str(note.path) and
                    note.path.name != f"📖 {metadata.title}.md"):
                    if 'chapter' in note.frontmatter:
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
# Adicione ao final do arquivo book_processor.py
chapter_processor = ChapterProcessor(ObsidianVaultManager())