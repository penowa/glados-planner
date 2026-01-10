# src/core/modules/pdf_processor.py
import logging
from pathlib import Path
from typing import Dict, List, Any
import fitz  # PyMuPDF
from .book_processor import ProcessingQuality

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Processador especializado para arquivos PDF."""
    
    def __init__(self, quality: ProcessingQuality = ProcessingQuality.STANDARD):
        self.quality = quality
        self.config = self._get_quality_config(quality)
    
    def _get_quality_config(self, quality: ProcessingQuality) -> Dict[str, Any]:
        """Retorna configurações baseadas na qualidade."""
        configs = {
            ProcessingQuality.DRAFT: {
                'extract_images': False,
                'ocr_fallback': False,
                'preserve_formatting': False,
                'chapter_detection': False
            },
            ProcessingQuality.STANDARD: {
                'extract_images': True,
                'ocr_fallback': True,
                'preserve_formatting': True,
                'chapter_detection': True
            },
            ProcessingQuality.HIGH: {
                'extract_images': True,
                'ocr_fallback': True,
                'preserve_formatting': True,
                'chapter_detection': True,
                'extract_footnotes': True
            },
            ProcessingQuality.ACADEMIC: {
                'extract_images': True,
                'ocr_fallback': True,
                'preserve_formatting': True,
                'chapter_detection': True,
                'extract_footnotes': True,
                'detect_citations': True,
                'extract_bibliography': True
            }
        }
        return configs.get(quality, configs[ProcessingQuality.STANDARD])
    
    def process(self, filepath: str, output_dir: Path, metadata: Any) -> Dict[str, Any]:
        """Processa um arquivo PDF."""
        logger.info(f"Processando PDF: {filepath}")
        
        chapters = []
        warnings = []
        
        try:
            doc = fitz.open(filepath)
            
            # Estratégia: dividir por páginas ou capítulos detectados
            if metadata.chapters and len(metadata.chapters) > 0:
                chapters = self._process_by_chapters(doc, metadata.chapters, output_dir)
            else:
                chapters = self._process_by_pages(doc, output_dir)
            
            doc.close()
            
            return {
                'chapters': chapters,
                'warnings': warnings,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento PDF: {e}")
            return {
                'chapters': [],
                'warnings': [f"Erro: {str(e)}"],
                'success': False
            }
    
    def _process_by_pages(self, doc, output_dir: Path) -> List[Dict[str, Any]]:
        """Processa dividindo por páginas."""
        chapters = []
        
        # Configurar tamanho do bloco baseado na qualidade
        pages_per_chapter = 20 if self.quality == ProcessingQuality.DRAFT else 10
        
        for i in range(0, len(doc), pages_per_chapter):
            end_idx = min(i + pages_per_chapter, len(doc))
            chapter_text = ""
            
            for page_num in range(i, end_idx):
                page = doc.load_page(page_num)
                text = page.get_text()
                chapter_text += f"\n\n--- Página {page_num + 1} ---\n\n{text}"
            
            chapter_num = (i // pages_per_chapter) + 1
            chapter_title = f"Capítulo {chapter_num} (Páginas {i+1}-{end_idx})"
            
            filename = f"capitulo-{chapter_num:03d}"
            filepath = output_dir / f"{filename}.md"
            
            # Salvar arquivo
            filepath.write_text(chapter_text, encoding='utf-8')
            
            chapters.append({
                'title': chapter_title,
                'filename': filename,
                'number': chapter_num,
                'content': chapter_text,
                'pages': f"{i+1}-{end_idx}",
                'filepath': str(filepath)
            })
        
        return chapters
    
    def _process_by_chapters(self, doc, detected_chapters, output_dir: Path) -> List[Dict[str, Any]]:
        """Processa usando capítulos detectados."""
        chapters = []
        
        # Implementação básica - pode ser expandida
        for i, chapter_info in enumerate(detected_chapters):
            start_page = chapter_info.get('page', 1)
            
            # Determinar página final (próximo capítulo ou final do documento)
            end_page = (
                detected_chapters[i + 1]['page'] - 1 
                if i + 1 < len(detected_chapters) 
                else len(doc)
            )
            
            chapter_text = ""
            for page_num in range(start_page - 1, end_page):
                page = doc.load_page(page_num)
                text = page.get_text()
                chapter_text += f"\n\n--- Página {page_num + 1} ---\n\n{text}"
            
            chapter_title = chapter_info.get('title', f"Capítulo {i+1}")
            filename = f"capitulo-{i+1:03d}-{self._slugify(chapter_title)}"
            
            filepath = output_dir / f"{filename}.md"
            filepath.write_text(chapter_text, encoding='utf-8')
            
            chapters.append({
                'title': chapter_title,
                'filename': filename,
                'number': i + 1,
                'content': chapter_text,
                'pages': f"{start_page}-{end_page}",
                'filepath': str(filepath)
            })
        
        return chapters
    
    def _slugify(self, text: str) -> str:
        """Converte texto para formato de slug."""
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        text = text.strip('-')
        return text[:50]
