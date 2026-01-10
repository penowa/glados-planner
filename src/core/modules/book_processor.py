# src/core/modules/book_processor.py (linhas 1-20 corrigidas)
import os
import logging
import json
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
