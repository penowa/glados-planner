# src/core/modules/pdf_processor_ocr.py
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import fitz  # PyMuPDF
from PIL import Image
import io
import pytesseract
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

from .book_processor import ProcessingQuality

logger = logging.getLogger(__name__)

class PDFProcessorOCR:
    """Processador de PDF com OCR avançado."""
    
    def __init__(self, quality: ProcessingQuality = ProcessingQuality.STANDARD, 
                 language: str = 'por', max_workers: int = 4):
        self.quality = quality
        self.language = language
        self.max_workers = max_workers
        self.config = self._get_quality_config(quality)
    
    def _get_quality_config(self, quality: ProcessingQuality) -> Dict[str, Any]:
        """Configurações baseadas na qualidade."""
        return {
            ProcessingQuality.DRAFT: {
                'ocr_enabled': False,
                'image_dpi': 150,
                'preserve_layout': False,
                'max_pages': 50,
                'parallel_processing': False
            },
            ProcessingQuality.STANDARD: {
                'ocr_enabled': True,
                'image_dpi': 200,
                'preserve_layout': True,
                'max_pages': None,
                'parallel_processing': True
            },
            ProcessingQuality.HIGH: {
                'ocr_enabled': True,
                'image_dpi': 300,
                'preserve_layout': True,
                'max_pages': None,
                'parallel_processing': True,
                'preprocess_image': True
            },
            ProcessingQuality.ACADEMIC: {
                'ocr_enabled': True,
                'image_dpi': 400,
                'preserve_layout': True,
                'max_pages': None,
                'parallel_processing': True,
                'preprocess_image': True,
                'language_model': 'por+eng'
            }
        }.get(quality, {
            'ocr_enabled': True,
            'image_dpi': 200,
            'preserve_layout': True,
            'max_pages': None,
            'parallel_processing': True
        })
    
    def process(self, filepath: str, output_dir: Path, 
                metadata: Any) -> Dict[str, Any]:
        """Processa PDF com OCR."""
        logger.info(f"Processando PDF com OCR: {filepath}")
        
        try:
            # Abre PDF
            doc = fitz.open(filepath)
            total_pages = len(doc)
            
            # Limita páginas se configurado
            max_pages = self.config.get('max_pages')
            if max_pages and total_pages > max_pages:
                pages_to_process = max_pages
                logger.warning(f"Limitado a {pages_to_process} páginas (modo {self.quality.value})")
            else:
                pages_to_process = total_pages
            
            # Processa páginas
            if self.config.get('parallel_processing'):
                chapters = self._process_parallel(doc, pages_to_process, output_dir)
            else:
                chapters = self._process_sequential(doc, pages_to_process, output_dir)
            
            doc.close()
            
            return {
                'chapters': chapters,
                'warnings': [],
                'success': True,
                'pages_processed': pages_to_process,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento OCR: {e}")
            return {
                'chapters': [],
                'warnings': [f"Erro OCR: {str(e)}"],
                'success': False
            }
    
    def _process_parallel(self, doc, pages_to_process: int, 
                         output_dir: Path) -> List[Dict[str, Any]]:
        """Processa páginas em paralelo."""
        chapters = []
        pages_per_chapter = 10
        
        # Divide em grupos para processamento paralelo
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for chapter_num, start_page in enumerate(range(0, pages_to_process, pages_per_chapter), start=1):
                end_page = min(start_page + pages_per_chapter, pages_to_process)
                future = executor.submit(
                    self._process_page_range,
                    doc, start_page, end_page, 
                    chapter_num, output_dir
                )
                futures.append(future)
            
            for future in as_completed(futures):
                chapter = future.result()
                if chapter:
                    chapters.append(chapter)
        
        return sorted(chapters, key=lambda x: x['number'])
    
    def _process_sequential(self, doc, pages_to_process: int, 
                           output_dir: Path) -> List[Dict[str, Any]]:
        """Processa páginas sequencialmente."""
        chapters = []
        pages_per_chapter = 10
        chapter_num = 1
        
        for start_page in range(0, pages_to_process, pages_per_chapter):
            end_page = min(start_page + pages_per_chapter, pages_to_process)
            
            chapter = self._process_page_range(
                doc, start_page, end_page, chapter_num, output_dir
            )
            
            if chapter:
                chapters.append(chapter)
                chapter_num += 1
        
        return chapters
    
    def _process_page_range(self, doc, start_page: int, end_page: int,
                           chapter_num: int, output_dir: Path) -> Optional[Dict[str, Any]]:
        """Processa um intervalo de páginas."""
        try:
            chapter_text = ""
            
            for page_num in range(start_page, end_page):
                page = doc.load_page(page_num)
                
                # Tenta extrair texto primeiro
                text = page.get_text()
                
                # Se pouco texto, usa OCR
                if len(text.strip()) < 100 and self.config['ocr_enabled']:
                    text = self._ocr_page(page)
                    if text:
                        text = f"[OCR] {text}"
                
                if text:
                    chapter_text += f"\n\n--- Página {page_num + 1} ---\n\n{text}"
            
            if not chapter_text.strip():
                return None
            
            # Salva capítulo
            filename = f"capitulo-{chapter_num:03d}"
            filepath = output_dir / f"{filename}.md"
            filepath.write_text(chapter_text, encoding='utf-8')
            
            return {
                'title': f"Capítulo {chapter_num} (Páginas {start_page+1}-{end_page})",
                'filename': filename,
                'number': chapter_num,
                'content': chapter_text,
                'pages': f"{start_page+1}-{end_page}",
                'filepath': str(filepath)
            }
            
        except Exception as e:
            logger.error(f"Erro processando páginas {start_page}-{end_page}: {e}")
            return None
    
    def _ocr_page(self, page) -> str:
        """Aplica OCR em uma página."""
        try:
            # Converte página para imagem
            zoom = self.config['image_dpi'] / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Converte para PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Pré-processamento (para qualidade HIGH/ACADEMIC)
            if self.config.get('preprocess_image'):
                image = self._preprocess_image(image)
            
            # Aplica OCR
            lang = self.config.get('language_model', self.language)
            text = pytesseract.image_to_string(image, lang=lang)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"OCR falhou na página {page.number}: {e}")
            return ""
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Pré-processa imagem para melhor OCR."""
        # Converte para escala de cinza
        if image.mode != 'L':
            image = image.convert('L')
        
        # Aumenta contraste
        import numpy as np
        img_array = np.array(image)
        
        # Normaliza
        img_array = (img_array - img_array.min()) / (img_array.max() - img_array.min() + 1e-7) * 255
        
        # Remove ruído (simples threshold)
        threshold = np.mean(img_array)
        img_array = np.where(img_array > threshold * 0.7, 255, 0)
        
        return Image.fromarray(img_array.astype('uint8'))
