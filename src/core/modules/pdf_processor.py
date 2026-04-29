# src/core/modules/pdf_processor_ocr.py
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
import io
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - dependência opcional em runtime
    fitz = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - dependência opcional em runtime
    Image = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - dependência opcional em runtime
    pytesseract = None

try:
    import numpy as np
except ImportError:  # pragma: no cover - dependência opcional em runtime
    np = None

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
        self.state_file: Optional[Path] = None
        self.page_cache_dir: Optional[Path] = None
        self.runtime_state: Dict[str, Any] = {}

    @staticmethod
    def extract_page_text_preserving_layout(page, preserve_layout: bool = True) -> str:
        """
        Extrai texto mantendo a ordem de leitura e, quando possível,
        as quebras de linha do PDF original.
        """
        try:
            if not preserve_layout:
                return (page.get_text("text", sort=True) or "").strip()

            page_dict = page.get_text("dict", sort=True) or {}
            blocks = page_dict.get("blocks", []) or []
            if not blocks:
                return (page.get_text("text", sort=True) or "").strip()

            block_entries: List[Dict[str, Any]] = []
            for block in blocks:
                if int(block.get("type", -1)) != 0:
                    continue
                bbox = block.get("bbox") or [0, 0, 0, 0]
                lines = block.get("lines", []) or []
                block_lines: List[Dict[str, Any]] = []
                for line in lines:
                    line_bbox = line.get("bbox") or bbox
                    spans = line.get("spans", []) or []
                    line_text = "".join(str(span.get("text") or "") for span in spans)
                    line_text = line_text.rstrip()
                    if not line_text.strip():
                        continue
                    block_lines.append(
                        {
                            "text": line_text,
                            "y0": float(line_bbox[1]),
                            "x0": float(line_bbox[0]),
                            "height": max(1.0, float(line_bbox[3]) - float(line_bbox[1])),
                        }
                    )

                if not block_lines:
                    continue

                avg_line_height = sum(item["height"] for item in block_lines) / max(1, len(block_lines))
                block_entries.append(
                    {
                        "x0": float(bbox[0]),
                        "y0": float(bbox[1]),
                        "lines": sorted(block_lines, key=lambda item: (item["y0"], item["x0"])),
                        "avg_line_height": avg_line_height,
                    }
                )

            if not block_entries:
                return (page.get_text("text", sort=True) or "").strip()

            block_entries.sort(key=lambda item: (item["y0"], item["x0"]))
            assembled_lines: List[str] = []
            previous_block_bottom: Optional[float] = None

            for block in block_entries:
                lines = block["lines"]
                if previous_block_bottom is not None:
                    block_gap = float(block["y0"]) - previous_block_bottom
                    if block_gap > block["avg_line_height"] * 0.8:
                        assembled_lines.append("")

                previous_line_y: Optional[float] = None
                previous_line_height: Optional[float] = None
                for line in lines:
                    if previous_line_y is not None and previous_line_height is not None:
                        gap = float(line["y0"]) - previous_line_y
                        if gap > previous_line_height * 1.35:
                            assembled_lines.append("")
                    assembled_lines.append(str(line["text"]))
                    previous_line_y = float(line["y0"])
                    previous_line_height = float(line["height"])

                if lines:
                    last_line = lines[-1]
                    previous_block_bottom = float(last_line["y0"]) + float(last_line["height"])

            text = "\n".join(assembled_lines)
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = text.strip("\n")
            if text.strip():
                return text
        except Exception as exc:
            logger.debug("Falha ao preservar layout da página %s: %s", getattr(page, "number", "?"), exc)

        return (page.get_text("text", sort=True) or "").strip()
    
    def _get_quality_config(self, quality: ProcessingQuality) -> Dict[str, Any]:
        """Configurações baseadas na qualidade."""
        return {
            ProcessingQuality.DRAFT: {
                'ocr_enabled': False,
                'image_dpi': 150,
                'preserve_layout': False,
                # Mesmo no modo rascunho, processar o livro inteiro.
                'max_pages': None,
                'parallel_processing': False,
                'pages_per_chunk': 10,
            },
            ProcessingQuality.STANDARD: {
                'ocr_enabled': True,
                'image_dpi': 120,
                'preserve_layout': True,
                'max_pages': None,
                'parallel_processing': True,
                'ocr_configs': ["--psm 6"],
                'ocr_timeout_seconds': 20,
                'pages_per_chunk': 10,
            },
            ProcessingQuality.HIGH: {
                'ocr_enabled': True,
                'image_dpi': 180,
                'preserve_layout': True,
                'max_pages': None,
                'parallel_processing': True,
                'preprocess_image': True,
                'ocr_configs': ["--psm 6", "--psm 4"],
                'ocr_timeout_seconds': 30,
                'pages_per_chunk': 8,
            },
            ProcessingQuality.ACADEMIC: {
                'ocr_enabled': True,
                'image_dpi': 220,
                'preserve_layout': True,
                'max_pages': None,
                'parallel_processing': True,
                'preprocess_image': True,
                'language_model': 'por+eng',
                'ocr_configs': ["--psm 6", "--psm 4", "--psm 3"],
                'ocr_timeout_seconds': 45,
                'pages_per_chunk': 6,
            }
        }.get(quality, {
            'ocr_enabled': True,
            'image_dpi': 120,
            'preserve_layout': True,
            'max_pages': None,
            'parallel_processing': True,
            'ocr_configs': ["--psm 6"],
            'ocr_timeout_seconds': 20,
            'pages_per_chunk': 10,
        })
    
    def process(self, filepath: str, output_dir: Path, 
                metadata: Any) -> Dict[str, Any]:
        """Processa PDF com OCR."""
        logger.info(f"Processando PDF com OCR: {filepath}")
        
        try:
            if fitz is None:
                raise ImportError("PyMuPDF não está instalado")

            warnings: List[str] = []

            # Abre PDF
            doc = fitz.open(filepath)
            total_pages = len(doc)
            requires_ocr = bool(getattr(metadata, "requires_ocr", False))
            self._prepare_processing_runtime(metadata, output_dir, total_pages)
            if self.runtime_state.get("scan_heavy_mode"):
                warnings.append(
                    "PDF escaneado pesado detectado. OCR será feito de forma sequencial com cache e retomada."
                )
                if self.runtime_state.get("completed_pages"):
                    warnings.append(
                        f"Retomando OCR a partir do progresso salvo ({len(self.runtime_state.get('completed_pages', []))} página(s) já processadas)."
                    )

            if requires_ocr and not self._ocr_is_available():
                reason = self._ocr_unavailable_reason()
                doc.close()
                logger.warning(reason)
                return {
                    'chapters': [],
                    'warnings': [reason],
                    'success': False,
                    'pages_processed': 0,
                    'total_pages': total_pages
                }
            
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
                if self.page_cache_dir:
                    warnings.append(
                        f"O progresso do OCR foi salvo em {self.page_cache_dir} para retomada posterior."
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
                'total_pages': total_pages,
                'page_cache_dir': str(self.page_cache_dir) if self.page_cache_dir else None,
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento OCR: {e}")
            return {
                'chapters': [],
                'warnings': [f"Erro OCR: {str(e)}"],
                'success': False
            }

    def _prepare_processing_runtime(self, metadata: Any, output_dir: Path, total_pages: int) -> None:
        """Configura estratégia de execução e persistência para o documento atual."""
        self.state_file = output_dir / ".ocr_state.json"
        self.page_cache_dir = output_dir / ".ocr_pages"
        self.page_cache_dir.mkdir(parents=True, exist_ok=True)

        self.runtime_state = self._load_state()
        self.runtime_state.setdefault("total_pages", total_pages)
        self.runtime_state.setdefault("quality", self.quality.value)
        self.runtime_state.setdefault("completed_pages", [])
        self.runtime_state.setdefault("failed_pages", {})
        self.runtime_state.setdefault("page_sources", {})

        requires_ocr = bool(getattr(metadata, "requires_ocr", False))
        is_scan_heavy = requires_ocr or self._document_looks_scan_heavy(total_pages)

        if is_scan_heavy:
            self.config["parallel_processing"] = False
            self.max_workers = 1
            self.config["pages_per_chunk"] = min(int(self.config.get("pages_per_chunk", 6)), 4)

            if self.quality == ProcessingQuality.STANDARD:
                self.config["image_dpi"] = 96
                self.config["ocr_timeout_seconds"] = 90
                self.config["ocr_configs"] = ["--psm 6"]
            elif self.quality == ProcessingQuality.HIGH:
                self.config["image_dpi"] = 120
                self.config["ocr_timeout_seconds"] = 120
                self.config["ocr_configs"] = ["--psm 6", "--psm 4"]
            elif self.quality == ProcessingQuality.ACADEMIC:
                self.config["image_dpi"] = 144
                self.config["ocr_timeout_seconds"] = 180
                self.config["ocr_configs"] = ["--psm 6", "--psm 4", "--psm 3"]

            self.runtime_state["scan_heavy_mode"] = True
        else:
            self.runtime_state["scan_heavy_mode"] = False

        self._save_state()

    def _document_looks_scan_heavy(self, total_pages: int) -> bool:
        """Usa estado anterior para reconhecer documentos problemáticos."""
        completed = set(int(page) for page in self.runtime_state.get("completed_pages", []))
        failed = self.runtime_state.get("failed_pages", {}) or {}
        return bool(failed) and len(completed) < max(3, total_pages // 10)

    def _load_state(self) -> Dict[str, Any]:
        """Carrega estado persistido do OCR."""
        if self.state_file and self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_state(self) -> None:
        """Persiste estado incremental do OCR."""
        if not self.state_file:
            return
        self.state_file.write_text(
            json.dumps(self.runtime_state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _page_cache_path(self, page_num: int) -> Optional[Path]:
        """Retorna caminho do cache da página."""
        if not self.page_cache_dir:
            return None
        return self.page_cache_dir / f"page-{page_num + 1:04d}.txt"

    def _load_cached_page_text(self, page_num: int) -> str:
        """Lê texto já OCRizado para evitar retrabalho."""
        cache_path = self._page_cache_path(page_num)
        if cache_path and cache_path.exists():
            try:
                return cache_path.read_text(encoding="utf-8")
            except Exception:
                return ""
        return ""

    def _save_cached_page_text(self, page_num: int, text: str, source: str) -> None:
        """Persiste texto da página e atualiza estado."""
        cache_path = self._page_cache_path(page_num)
        if cache_path:
            cache_path.write_text(text, encoding="utf-8")

        completed = {
            int(item) for item in self.runtime_state.get("completed_pages", [])
            if isinstance(item, int) or str(item).isdigit()
        }
        completed.add(page_num + 1)
        self.runtime_state["completed_pages"] = sorted(completed)

        page_sources = self.runtime_state.setdefault("page_sources", {})
        page_sources[str(page_num + 1)] = source

        failed = self.runtime_state.setdefault("failed_pages", {})
        failed.pop(str(page_num + 1), None)
        self._save_state()

    def _mark_page_failure(self, page_num: int, reason: str) -> None:
        """Registra falha da página para facilitar retomada/diagnóstico."""
        failed = self.runtime_state.setdefault("failed_pages", {})
        failed[str(page_num + 1)] = reason
        self._save_state()

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
        pages_per_chapter = int(self.config.get("pages_per_chunk", 10))
        
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
        pages_per_chapter = int(self.config.get("pages_per_chunk", 10))
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
                text, extraction_meta = self._extract_page_with_resume(doc, page_num)

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

    def _extract_page_with_resume(self, doc, page_num: int) -> tuple[str, Dict[str, Any]]:
        """Extrai página reutilizando cache persistido quando houver."""
        cached_text = self._load_cached_page_text(page_num)
        if cached_text.strip():
            cached_source = (self.runtime_state.get("page_sources", {}) or {}).get(str(page_num + 1), "cache")
            return cached_text, {"method": cached_source, "score": self._score_extracted_text(cached_text), "cached": True}

        page = doc.load_page(page_num)
        text, extraction_meta = self._extract_best_page_text(page)

        if self._should_try_ocr(text, extraction_meta):
            ocr_text = self._ocr_page(page)
            if self._is_better_candidate(ocr_text, text):
                text = ocr_text
                extraction_meta["method"] = "ocr"
            if text:
                text = f"[OCR] {text}"

        cleaned = self._clean_page_text(text)
        if cleaned.strip():
            source = str(extraction_meta.get("method") or "text")
            self._save_cached_page_text(page_num, cleaned, source)
        else:
            self._mark_page_failure(page_num, "Sem texto extraído")

        return cleaned, extraction_meta

    def _extract_best_page_text(self, page) -> tuple[str, Dict[str, Any]]:
        """Seleciona a melhor extração textual disponível para uma página."""
        candidates: List[tuple[str, str]] = []
        preserve_layout = bool(self.config.get('preserve_layout', True))

        try:
            text = self.extract_page_text_preserving_layout(page, preserve_layout=preserve_layout)
            candidates.append(("layout", text))
        except Exception as exc:
            logger.debug("Extração com layout falhou na página %s: %s", getattr(page, "number", "?"), exc)

        extraction_attempts = [
            ("text", lambda: page.get_text("text", sort=True)),
            ("blocks", lambda: self._extract_text_from_blocks(page)),
            ("words", lambda: self._extract_text_from_words(page)),
        ]

        for method, extractor in extraction_attempts:
            try:
                candidates.append((method, extractor() or ""))
            except Exception as exc:
                logger.debug("Extração %s falhou na página %s: %s", method, getattr(page, "number", "?"), exc)

        best_method = "empty"
        best_text = ""
        best_score = -1.0
        for method, candidate in candidates:
            cleaned = self._clean_page_text(candidate)
            score = self._score_extracted_text(cleaned)
            if score > best_score:
                best_score = score
                best_text = cleaned
                best_method = method

        return best_text, {"method": best_method, "score": best_score}

    def _extract_text_from_blocks(self, page) -> str:
        """Reagrupa blocos para PDFs cujo texto sai embaralhado no modo padrão."""
        page_dict = page.get_text("dict", sort=True) or {}
        blocks = page_dict.get("blocks", []) or []
        lines: List[str] = []

        for block in sorted(blocks, key=lambda item: tuple(item.get("bbox", [0, 0, 0, 0]))):
            if int(block.get("type", -1)) != 0:
                continue
            for line in block.get("lines", []) or []:
                spans = line.get("spans", []) or []
                text = "".join(str(span.get("text") or "") for span in spans).strip()
                if text:
                    lines.append(text)

        return "\n".join(lines).strip()

    def _extract_text_from_words(self, page) -> str:
        """Monta texto ordenando palavras por posição, útil em PDFs antigos/digitalizados."""
        words = page.get_text("words", sort=True) or []
        if not words:
            return ""

        grouped_lines: List[List[tuple[float, float, str]]] = []
        current_line: List[tuple[float, float, str]] = []
        current_y: Optional[float] = None

        for word in words:
            x0, y0, _x1, _y1, text, *_rest = word
            if current_y is None or abs(float(y0) - current_y) <= 3.0:
                current_line.append((float(x0), float(y0), str(text)))
                current_y = float(y0) if current_y is None else current_y
                continue

            grouped_lines.append(current_line)
            current_line = [(float(x0), float(y0), str(text))]
            current_y = float(y0)

        if current_line:
            grouped_lines.append(current_line)

        return "\n".join(
            " ".join(text for _x0, _y0, text in sorted(line, key=lambda item: item[0])).strip()
            for line in grouped_lines
            if line
        ).strip()

    def _clean_page_text(self, text: str) -> str:
        """Normaliza artefatos comuns de extração sem destruir o conteúdo."""
        if not text:
            return ""

        text = str(text).replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        return text.strip()

    def _score_extracted_text(self, text: str) -> float:
        """Pontua candidatos para preferir extrações com mais sinal útil."""
        if not text or not text.strip():
            return 0.0

        stripped = text.strip()
        alnum = sum(1 for char in stripped if char.isalnum())
        words = re.findall(r"\b[\wÀ-ÿ]+\b", stripped, flags=re.UNICODE)
        long_words = sum(1 for word in words if len(word) >= 4)
        weird_ratio = sum(1 for char in stripped if not (char.isalnum() or char.isspace() or char in ".,;:!?()[]\"'/-")) / max(len(stripped), 1)
        line_count = max(1, stripped.count("\n") + 1)

        return (
            min(len(stripped), 3000) * 0.01
            + alnum * 0.02
            + len(words) * 0.5
            + long_words * 0.25
            - weird_ratio * 50
            - max(0, line_count - len(words)) * 0.05
        )

    def _should_try_ocr(self, text: str, extraction_meta: Dict[str, Any]) -> bool:
        """Decide quando vale acionar OCR após a extração nativa."""
        if not self.config.get("ocr_enabled"):
            return False
        if not self._ocr_is_available():
            return False

        stripped = (text or "").strip()
        score = float(extraction_meta.get("score", 0.0) or 0.0)
        return len(stripped) < 120 or score < 25

    def _is_better_candidate(self, candidate: str, current: str) -> bool:
        """Compara dois textos e mantém o mais útil."""
        candidate_score = self._score_extracted_text(self._clean_page_text(candidate))
        current_score = self._score_extracted_text(self._clean_page_text(current))
        return candidate_score > current_score + 5
    
    def _ocr_page(self, page) -> str:
        """Aplica OCR em uma página."""
        try:
            if not self._ocr_is_available():
                return ""

            # Aplica OCR
            lang = self.config.get('language_model', self.language)
            ocr_configs = self.config.get('ocr_configs') or ["--psm 6"]
            timeout_seconds = float(self.config.get('ocr_timeout_seconds') or 20)
            dpi_candidates = self._ocr_dpi_candidates()
            best_text = ""
            best_score = -1.0

            for dpi in dpi_candidates:
                image = self._render_page_image(page, dpi)

                if self.config.get('preprocess_image'):
                    image = self._preprocess_image(image)
                elif image.mode != 'L':
                    image = image.convert('L')

                try:
                    for config in ocr_configs:
                        text = pytesseract.image_to_string(
                            image,
                            lang=lang,
                            config=config,
                            timeout=timeout_seconds,
                        )
                        cleaned = self._clean_page_text(text)
                        score = self._score_extracted_text(cleaned)
                        if score > best_score:
                            best_text = cleaned
                            best_score = score

                    if best_text.strip():
                        return best_text.strip()
                except RuntimeError as exc:
                    logger.warning(
                        "OCR timeout/falha na página %s com dpi=%s: %s",
                        page.number,
                        dpi,
                        exc,
                    )
                    continue

            return best_text.strip()
            
        except Exception as e:
            logger.warning(f"OCR falhou na página {page.number}: {e}")
            return ""

    def _ocr_dpi_candidates(self) -> List[int]:
        """Lista DPIs candidatos para OCR com fallback progressivo."""
        base_dpi = int(self.config.get("image_dpi") or 120)
        fallback_dpis = [base_dpi]
        if base_dpi > 110:
            fallback_dpis.append(max(96, int(base_dpi * 0.8)))
        fallback_dpis.append(72)

        unique: List[int] = []
        for dpi in fallback_dpis:
            if dpi not in unique:
                unique.append(dpi)
        return unique

    def _render_page_image(self, page, dpi: int) -> Image.Image:
        """Renderiza a página em imagem PIL para OCR."""
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_data = pix.tobytes("png")
        return Image.open(io.BytesIO(img_data))

    def _ocr_is_available(self) -> bool:
        """Valida dependências Python e o binário do Tesseract."""
        return (
            fitz is not None
            and Image is not None
            and pytesseract is not None
            and shutil.which("tesseract") is not None
        )

    def _ocr_unavailable_reason(self) -> str:
        """Explica por que o OCR não pode ser usado no ambiente atual."""
        missing = []
        if fitz is None:
            missing.append("PyMuPDF")
        if Image is None:
            missing.append("Pillow")
        if pytesseract is None:
            missing.append("pytesseract")
        if shutil.which("tesseract") is None:
            missing.append("binário tesseract")

        return "OCR indisponível: faltando " + ", ".join(missing) + "."
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Pré-processa imagem para melhor OCR."""
        if np is None:
            return image

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


PDFProcessor = PDFProcessorOCR
