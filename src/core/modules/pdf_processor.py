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
                # Mesmo no modo rascunho, processar o livro inteiro.
                'max_pages': None,
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
            warnings: List[str] = []

            # Abre PDF
            doc = fitz.open(filepath)
            total_pages = len(doc)
            
            # Limita páginas se configurado
            max_pages = self.config.get('max_pages')
            if max_pages and total_pages > max_pages:
                pages_to_process = max_pages
                logger.warning(f"Limitado a {pages_to_process} páginas (modo {self.quality.value})")
                warnings.append(
                    f"Processamento limitado a {pages_to_process} de {total_pages} páginas."
                )
            else:
                pages_to_process = total_pages
            
            # Usa plano de capítulos detectado (TOC/heurística) quando disponível.
            chapter_plan = self._build_chapter_plan(metadata, pages_to_process)
            if chapter_plan:
                chapters = self._process_chapter_plan(doc, chapter_plan, output_dir)
            elif self.config.get('parallel_processing'):
                chapters = self._process_parallel(doc, pages_to_process, output_dir)
            else:
                chapters = self._process_sequential(doc, pages_to_process, output_dir)

            # Garantia de completude: detectar e recuperar páginas não cobertas.
            missing_ranges = self._find_missing_ranges(chapters, pages_to_process)
            if missing_ranges:
                warnings.append(
                    f"Foram detectadas lacunas na cobertura de páginas: {missing_ranges}. Tentando recuperar..."
                )
                next_chapter_num = max((c.get("number", 0) for c in chapters), default=0) + 1
                for range_idx, (start_page, end_page) in enumerate(missing_ranges, start=1):
                    recovered = self._process_page_range(
                        doc=doc,
                        start_page=start_page - 1,   # 0-index
                        end_page=end_page,           # exclusivo no loop interno
                        chapter_num=next_chapter_num,
                        output_dir=output_dir,
                        chapter_title=f"Trecho complementar {range_idx}"
                    )
                    next_chapter_num += 1
                    if recovered:
                        chapters.append(recovered)

                chapters = sorted(chapters, key=lambda item: item.get("number", 0))
                missing_after_recovery = self._find_missing_ranges(chapters, pages_to_process)
            else:
                missing_after_recovery = []
            
            doc.close()

            if missing_after_recovery:
                warnings.append(
                    f"Não foi possível cobrir todas as páginas. Faixas faltantes: {missing_after_recovery}"
                )
                return {
                    'chapters': chapters,
                    'warnings': warnings,
                    'success': False,
                    'pages_processed': pages_to_process,
                    'total_pages': total_pages
                }

            total_pages_without_text = sum(int(ch.get("missing_text_pages", 0) or 0) for ch in chapters)
            if total_pages_without_text > 0:
                warnings.append(
                    f"{total_pages_without_text} página(s) sem texto extraído após OCR."
                )
                return {
                    'chapters': chapters,
                    'warnings': warnings,
                    'success': False,
                    'pages_processed': pages_to_process,
                    'total_pages': total_pages
                }
            
            return {
                'chapters': chapters,
                'warnings': warnings,
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

    def _find_missing_ranges(self, chapters: List[Dict[str, Any]], total_pages: int) -> List[tuple[int, int]]:
        """
        Retorna faixas (1-indexadas, inclusivas) de páginas não cobertas pelos capítulos.
        """
        if total_pages <= 0:
            return []

        covered = [False] * (total_pages + 1)  # índice 1..total_pages
        for chapter in chapters:
            start_page = chapter.get("start_page")
            end_page = chapter.get("end_page")
            pages_str = chapter.get("pages", "")

            if (start_page is None or end_page is None) and isinstance(pages_str, str) and "-" in pages_str:
                try:
                    left, right = pages_str.split("-", 1)
                    start_page = int(left.strip())
                    end_page = int(right.strip())
                except Exception:
                    start_page, end_page = None, None

            if start_page is None or end_page is None:
                continue

            start_page = max(1, int(start_page))
            end_page = min(total_pages, int(end_page))
            if end_page < start_page:
                continue

            for page in range(start_page, end_page + 1):
                covered[page] = True

        missing_ranges: List[tuple[int, int]] = []
        current_start = None

        for page in range(1, total_pages + 1):
            if not covered[page]:
                if current_start is None:
                    current_start = page
            else:
                if current_start is not None:
                    missing_ranges.append((current_start, page - 1))
                    current_start = None

        if current_start is not None:
            missing_ranges.append((current_start, total_pages))

        return missing_ranges

    def _build_chapter_plan(self, metadata: Any, pages_to_process: int) -> List[Dict[str, Any]]:
        """Monta plano de capítulos a partir dos metadados detectados."""
        raw_chapters = getattr(metadata, "chapters", None) or []
        plan: List[Dict[str, Any]] = []

        for idx, chapter in enumerate(raw_chapters, start=1):
            start_page = chapter.get("start_page")
            end_page = chapter.get("end_page")

            if start_page is None or end_page is None:
                continue

            start_page = max(1, int(start_page))
            end_page = min(int(end_page), pages_to_process)
            if end_page < start_page:
                continue

            title = chapter.get("title") or f"Capítulo {idx}"
            plan.append({
                "number": int(chapter.get("number", idx)),
                "title": str(title).strip(),
                "start_page": start_page,
                "end_page": end_page
            })

        if len(plan) < 2:
            return []

        # Remove sobreposição eventual mantendo ordem.
        plan.sort(key=lambda item: item["start_page"])
        clean_plan: List[Dict[str, Any]] = []
        last_end = 0
        for chapter in plan:
            start_page = max(chapter["start_page"], last_end + 1)
            end_page = chapter["end_page"]
            if end_page < start_page:
                continue
            chapter["start_page"] = start_page
            clean_plan.append(chapter)
            last_end = end_page

        # Se o primeiro capítulo detectado começa após a página 1,
        # preserva o conteúdo inicial (prefácio/apresentação/sumário).
        if clean_plan and clean_plan[0]["start_page"] > 1:
            intro_end = clean_plan[0]["start_page"] - 1
            clean_plan.insert(0, {
                "number": 0,
                "title": "Pré-texto / Introdução",
                "start_page": 1,
                "end_page": intro_end
            })

        return clean_plan

    def _process_chapter_plan(self, doc, chapter_plan: List[Dict[str, Any]],
                              output_dir: Path) -> List[Dict[str, Any]]:
        """Processa capítulos com base em intervalos explícitos."""
        chapters: List[Dict[str, Any]] = []
        next_fallback_number = 1
        for idx, chapter in enumerate(chapter_plan, start=1):
            chapter_num = chapter.get("number")
            if isinstance(chapter_num, int):
                chapter_num = chapter_num
                if chapter_num >= next_fallback_number:
                    next_fallback_number = chapter_num + 1
            else:
                chapter_num = next_fallback_number
                next_fallback_number += 1
            chapter_data = self._process_page_range(
                doc,
                start_page=chapter["start_page"] - 1,
                end_page=chapter["end_page"],
                chapter_num=chapter_num,
                output_dir=output_dir,
                chapter_title=chapter["title"]
            )
            if chapter_data:
                chapters.append(chapter_data)
        return chapters
    
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
                           chapter_num: int, output_dir: Path,
                           chapter_title: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Processa um intervalo de páginas."""
        try:
            chapter_text = ""
            missing_text_pages = 0
            
            for page_num in range(start_page, end_page):
                page = doc.load_page(page_num)
                
                # Tenta extrair texto primeiro
                text = page.get_text()
                
                # Se pouco texto, usa OCR
                if len(text.strip()) < 100 and self.config['ocr_enabled']:
                    text = self._ocr_page(page)
                    if text:
                        text = f"[OCR] {text}"

                if not text or not text.strip():
                    missing_text_pages += 1
                    text = "[Sem texto extraído nesta página]"

                # Sempre materializa a página no conteúdo para garantir completude estrutural.
                chapter_text += f"\n\n--- Página {page_num + 1} ---\n\n{text}"
            
            if not chapter_text.strip():
                return None
            
            # Salva capítulo
            display_title = chapter_title or f"Capítulo {chapter_num}"
            filename = f"capitulo-{chapter_num:03d}"
            filepath = output_dir / f"{filename}.md"
            filepath.write_text(chapter_text, encoding='utf-8')
            
            return {
                'title': display_title,
                'chapter_title': display_title,
                'filename': filename,
                'number': chapter_num,
                'chapter_num': chapter_num,
                'content': chapter_text,
                'pages': f"{start_page+1}-{end_page}",
                'start_page': start_page + 1,
                'end_page': end_page,
                'missing_text_pages': missing_text_pages,
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
