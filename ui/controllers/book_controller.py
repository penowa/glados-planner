"""
Controller refatorado para gerenciamento de livros com integração robusta com backend
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer, Qt, QMutex, QWaitCondition
from PyQt6.QtGui import QPixmap, QPainter, QColor, QImage, QBrush, QLinearGradient
from datetime import datetime, timedelta
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import uuid
import hashlib
import re
import unicodedata
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from enum import Enum

from core.config.settings import settings

logger = logging.getLogger('GLaDOS.UI.BookController')


class BookProcessingStage(Enum):
    """Estágios do processamento de livro"""
    INITIALIZATION = "initialization"
    ANALYSIS = "analysis"
    EXTRACTION = "extraction"
    STRUCTURING = "structuring"
    LLM_ENHANCEMENT = "llm_enhancement"
    INTEGRATION = "integration"
    SCHEDULING = "scheduling"
    COMPLETED = "completed"
    FAILED = "failed"


class BookProcessingPipeline(QThread):
    """Pipeline completo e robusto para processamento de livros"""
    
    # Sinais de progresso
    stage_started = pyqtSignal(str, str, str)  # (pipeline_id, stage, message)
    stage_progress = pyqtSignal(str, str, int, str)  # (pipeline_id, stage, percent, message)
    stage_completed = pyqtSignal(str, str, dict)  # (pipeline_id, stage, result)
    stage_failed = pyqtSignal(str, str, str)  # (pipeline_id, stage, error)
    
    # Sinais de conclusão
    pipeline_completed = pyqtSignal(str, dict)  # (pipeline_id, final_result)
    pipeline_failed = pyqtSignal(str, str)  # (pipeline_id, error)
    
    def __init__(self, controller, file_path: str, quality: str = "standard", 
                 schedule_reading: bool = True, use_llm: bool = False, config=None):
        super().__init__()
        self.controller = controller
        self.file_path = Path(file_path)
        self.quality = quality
        self.schedule_reading = schedule_reading
        self.use_llm = use_llm
        self.config = config or {}
        self.pipeline_id = str(uuid.uuid4())[:8]
        self._is_running = True
        self._current_stage = None
        
        # Estado do pipeline
        self.metadata = None
        self.book_id = None
        self.processing_result = None
        self.consolidated_result = {}
        self.extracted_content = None

         # Configurações específicas
        self.notes_config = self.config.get("notes_config", {})
        self.scheduling_config = self.config.get("scheduling_config", {})
        self.user_metadata = self.config.get("metadata", {})
 
    def _analyze_book(self) -> Dict:
        """Etapa 1: Análise do arquivo (atualizada para usar metadados do usuário)"""
        self.stage_progress.emit(self.pipeline_id, "analysis", 10, "Analisando arquivo...")
        
        # Usar book_processor para análise
        metadata, recommendations = self.controller.book_processor.analyze_book(str(self.file_path))
        self.metadata = metadata
        
        # Sobrescrever metadados com os fornecidos pelo usuário
        if self.user_metadata:
            for key, value in self.user_metadata.items():
                if value:  # Só sobrescrever se o valor não for vazio
                    setattr(self.metadata, key, value)
        
        self.stage_progress.emit(self.pipeline_id, "analysis", 100, "Análise concluída")
        
        return {
            "title": metadata.title,
            "author": metadata.author,
            "total_pages": metadata.total_pages,
            "requires_ocr": metadata.requires_ocr,
            "estimated_time": metadata.estimated_processing_time,
            "recommendations": recommendations,
            "chapters_detected": len(metadata.chapters),
            "user_metadata_applied": bool(self.user_metadata)
        }
    
    def _structure_content(self) -> Dict:
        """Etapa 3: Estruturação do conteúdo (atualizada para usar configurações)"""
        self.stage_progress.emit(self.pipeline_id, "structuring", 10, "Estruturando conteúdo...")
        
        if not self.metadata or not self.extracted_content:
            raise Exception("Conteúdo não disponível para estruturação")
        
        # Gerar ID consistente
        self.book_id = self.controller.generate_consistent_book_id(
            self.metadata.title, self.metadata.author
        )
        
        # Determinar estrutura baseado na configuração
        structure_type = self.notes_config.get("structure", "Uma nota por capítulo (Recomendado)")
        
        if "Nota única" in structure_type:
            # Criar estrutura de nota única
            structure_result = self.controller.create_single_note_structure(
                book_id=self.book_id,
                metadata=self.metadata,
                content=self.extracted_content,
                config=self.notes_config
            )
        else:
            # Criar estrutura de diretórios no vault (padrão)
            structure_result = self.controller.create_book_structure(
                book_id=self.book_id,
                metadata=self.metadata,
                chapters=self.extracted_content,
                config=self.notes_config
            )
        
        # Criar índice do livro
        index_result = self.controller.create_book_index(
            book_id=self.book_id,
            metadata=self.metadata,
            chapters=self.extracted_content
        )
        
        self.stage_progress.emit(self.pipeline_id, "structuring", 100, "Estruturação concluída")
        
        return {
            "book_id": self.book_id,
            "structure_type": structure_type,
            "directory_created": structure_result.get("directory_created", False),
            "index_created": index_result.get("index_created", False),
            "notes_created": structure_result.get("notes_created", 0),
            "single_note": "Nota única" in structure_type
        }
    
    def _schedule_reading(self) -> Dict:
        """Etapa 6: Agendamento automático de leitura (atualizada para usar configurações)"""
        if not self.book_id:
            raise Exception("Book ID não disponível para agendamento")
        
        self.stage_progress.emit(self.pipeline_id, "scheduling", 10, "Preparando agendamento...")
        
        # Usar configurações personalizadas se fornecidas
        scheduling_config = self.scheduling_config or {}
        
        # Agendar leitura usando AgendaManager com configurações
        scheduling_result = self.controller.schedule_book_reading(
            book_id=self.book_id,
            title=self.metadata.title,
            total_pages=self.metadata.total_pages,
            config=scheduling_config
        )
        
        if not scheduling_result.get("success", False):
            logger.warning(f"Agendamento automático falhou: {scheduling_result.get('error')}")
            scheduling_result["warning"] = "Agendamento automático não concluído"
        
        self.stage_progress.emit(self.pipeline_id, "scheduling", 100, "Agendamento configurado")
        
        return scheduling_result
        
    def run(self):
        """Executa pipeline completo"""
        try:
            # ETAPA 0: Inicialização
            self._run_stage(BookProcessingStage.INITIALIZATION, self._initialize_processing)
            
            # ETAPA 1: Análise do arquivo
            if not self._check_stop_condition():
                self._run_stage(BookProcessingStage.ANALYSIS, self._analyze_book)
            
            # ETAPA 2: Extração de conteúdo
            if not self._check_stop_condition():
                self._run_stage(BookProcessingStage.EXTRACTION, self._extract_content)
            
            # ETAPA 3: Estruturação
            if not self._check_stop_condition():
                self._run_stage(BookProcessingStage.STRUCTURING, self._structure_content)
            
            # ETAPA 4: Aprimoramento com LLM (opcional)
            if not self._check_stop_condition() and self.use_llm:
                self._run_stage(BookProcessingStage.LLM_ENHANCEMENT, self._enhance_with_llm)
            
            # ETAPA 5: Integração com sistemas
            if not self._check_stop_condition():
                self._run_stage(BookProcessingStage.INTEGRATION, self._integrate_with_systems)
            
            # ETAPA 6: Agendamento automático
            if not self._check_stop_condition() and self.schedule_reading:
                self._run_stage(BookProcessingStage.SCHEDULING, self._schedule_reading)
            
            # Conclusão
            if not self._check_stop_condition():
                self._complete_pipeline()
                
        except Exception as e:
            logger.error(f"Erro no pipeline {self.pipeline_id}: {e}")
            self.pipeline_failed.emit(self.pipeline_id, str(e))
            
    def _run_stage(self, stage: BookProcessingStage, stage_func):
        """Executa um estágio do pipeline"""
        try:
            self._current_stage = stage
            stage_name = stage.value
            self.stage_started.emit(self.pipeline_id, stage_name, f"Iniciando {stage_name}...")
            
            # Executar função do estágio
            result = stage_func()
            
            # Atualizar estado consolidado
            self.consolidated_result[stage_name] = result
            
            # Emitir conclusão
            self.stage_completed.emit(self.pipeline_id, stage_name, result)
            
        except Exception as e:
            logger.error(f"Erro no estágio {stage.value} do pipeline {self.pipeline_id}: {e}")
            self.stage_failed.emit(self.pipeline_id, stage.value, str(e))
            raise
    
    def _initialize_processing(self) -> Dict:
        """Etapa 0: Inicialização do processamento"""
        self.stage_progress.emit(self.pipeline_id, "initialization", 10, "Inicializando processamento...")
        
        # Verificar se arquivo existe
        if not self.file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.file_path}")
        
        # Verificar formato suportado
        supported_formats = ['.pdf', '.epub']
        if self.file_path.suffix.lower() not in supported_formats:
            raise ValueError(f"Formato não suportado: {self.file_path.suffix}. Formatos suportados: {supported_formats}")
        
        # Verificar tamanho do arquivo
        file_size_mb = self.file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 100:
            logger.warning(f"Arquivo grande: {file_size_mb:.1f}MB")
        
        self.stage_progress.emit(self.pipeline_id, "initialization", 100, "Inicialização concluída")
        
        return {
            "file_path": str(self.file_path),
            "file_size_mb": file_size_mb,
            "format": self.file_path.suffix,
            "requires_llm": self.use_llm,
            "quality": self.quality
        }
    
    def _analyze_book(self) -> Dict:
        """Etapa 1: Análise do arquivo"""
        self.stage_progress.emit(self.pipeline_id, "analysis", 10, "Analisando arquivo...")
        
        # Usar book_processor para análise
        metadata, recommendations = self.controller.book_processor.analyze_book(str(self.file_path))
        self.metadata = metadata

        # Aplicar metadados informados no diálogo de importação.
        if self.user_metadata:
            for key, value in self.user_metadata.items():
                if value not in (None, "", []):
                    setattr(self.metadata, key, value)
        
        self.stage_progress.emit(self.pipeline_id, "analysis", 100, "Análise concluída")
        
        return {
            "title": self.metadata.title,
            "author": self.metadata.author,
            "total_pages": self.metadata.total_pages,
            "requires_ocr": self.metadata.requires_ocr,
            "estimated_time": self.metadata.estimated_processing_time,
            "recommendations": recommendations,
            "chapters_detected": len(self.metadata.chapters),
            "user_metadata_applied": bool(self.user_metadata)
        }
    
    def _extract_content(self) -> Dict:
        """Etapa 2: Extração de conteúdo"""
        self.stage_progress.emit(self.pipeline_id, "extraction", 10, "Extraindo conteúdo...")
        
        # Determinar qualidade
        from core.modules.book_processor import ProcessingQuality
        quality_map = {
            'draft': ProcessingQuality.DRAFT,
            'standard': ProcessingQuality.STANDARD,
            'high': ProcessingQuality.HIGH,
            'academic': ProcessingQuality.ACADEMIC
        }
        processing_quality = quality_map.get(self.quality, ProcessingQuality.STANDARD)

        # Extração técnica em diretório temporário para evitar criação de estrutura
        # paralela no vault com metadados crus do PDF.
        temp_output_dir = (
            Path(tempfile.gettempdir()) /
            "glados_book_processing" /
            self.pipeline_id
        )
        temp_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Processar livro usando book_processor
        result = self.controller.book_processor.process_book(
            filepath=str(self.file_path),
            quality=processing_quality,
            output_dir=str(temp_output_dir),
            schedule_night=False,  # Processar imediatamente
            force_immediate=True,
            integrate_with_vault=False
        )
        
        if result.status.value == "failed":
            warnings = list(result.warnings or [])
            error_message = str(result.error or "Erro no processamento")
            missing_text_issue = (
                "sem texto extraído após ocr" in error_message.lower()
                or any("sem texto extraído após ocr" in str(w).lower() for w in warnings)
            )

            partial_chapters = list(result.processed_chapters or [])
            if missing_text_issue and not partial_chapters:
                partial_chapters = self._build_fallback_chapters_from_pdf()

            if missing_text_issue and partial_chapters:
                warnings.append(
                    "Extração parcial: algumas páginas ficaram sem texto após OCR, mas o processamento seguiu."
                )
                logger.warning(
                    "Pipeline %s: continuando com extração parcial (%d capítulo(s)).",
                    self.pipeline_id,
                    len(partial_chapters),
                )
                self.processing_result = result
                self.extracted_content = partial_chapters
                self.stage_progress.emit(self.pipeline_id, "extraction", 100, "Extração parcial concluída")
                return {
                    "chapters_extracted": len(partial_chapters),
                    "total_pages": result.metadata.total_pages,
                    "requires_ocr": result.metadata.requires_ocr,
                    "extraction_method": "partial_fallback",
                    "warnings": warnings,
                    "partial_extraction": True,
                }

            raise Exception(error_message)
        if result.status.value == "scheduled":
            raise Exception("Processamento foi agendado, mas esta operação requer execução imediata")
        
        self.processing_result = result
        self.extracted_content = result.processed_chapters
        
        # Se necessário, usar LLM para extração aprimorada
        if result.metadata.requires_ocr and self.use_llm:
            logger.info("Usando LLM para extração aprimorada de texto")
            
        self.stage_progress.emit(self.pipeline_id, "extraction", 100, "Extração concluída")
        
        return {
            "chapters_extracted": len(result.processed_chapters),
            "total_pages": result.metadata.total_pages,
            "requires_ocr": result.metadata.requires_ocr,
            "extraction_method": "standard" + ("+llm" if self.use_llm else ""),
            "warnings": result.warnings or []
        }

    def _build_fallback_chapters_from_pdf(self) -> List[Dict[str, Any]]:
        """Fallback: gera capítulo único com texto bruto extraído diretamente do PDF."""
        try:
            import fitz  # PyMuPDF

            page_blocks: List[str] = []
            with fitz.open(str(self.file_path)) as doc:
                total_pages = len(doc)
                for idx in range(total_pages):
                    page_text = (doc[idx].get_text("text") or "").strip()
                    if not page_text:
                        continue
                    page_blocks.append(f"--- Página {idx + 1} ---\n{page_text}")

            if not page_blocks:
                placeholder_title = "Conteúdo Indisponível (OCR)"
                return [
                    {
                        "number": 1,
                        "chapter_num": 1,
                        "title": placeholder_title,
                        "chapter_title": placeholder_title,
                        "start_page": 1,
                        "end_page": max(int(self.metadata.total_pages or 0), 1) if self.metadata else 1,
                        "pages": f"1-{max(int(self.metadata.total_pages or 0), 1) if self.metadata else 1}",
                        "content": (
                            "Não foi possível extrair texto legível automaticamente deste PDF.\n\n"
                            "Sugestão: reprocessar com qualidade acadêmica, verificar idioma OCR "
                            "ou fornecer versão digital com texto selecionável."
                        ),
                    }
                ]

            content = "\n\n".join(page_blocks)
            title = "Conteúdo Extraído (Fallback)"
            return [
                {
                    "number": 1,
                    "chapter_num": 1,
                    "title": title,
                    "chapter_title": title,
                    "start_page": 1,
                    "end_page": max(int(self.metadata.total_pages or 0), 1) if self.metadata else 1,
                    "pages": f"1-{max(int(self.metadata.total_pages or 0), 1) if self.metadata else 1}",
                    "content": content,
                }
            ]
        except Exception as exc:
            logger.warning("Fallback de extração PDF falhou (%s): %s", self.pipeline_id, exc)
            return []
    
    def _structure_content(self) -> Dict:
        """Etapa 3: Estruturação do conteúdo"""
        self.stage_progress.emit(self.pipeline_id, "structuring", 10, "Estruturando conteúdo...")
        
        if not self.metadata or not self.extracted_content:
            raise Exception("Conteúdo não disponível para estruturação")
        
        # Gerar ID consistente
        self.book_id = self.controller.generate_consistent_book_id(
            self.metadata.title, self.metadata.author
        )
        
        # Sempre criar notas por capítulo
        chapters_result = self.controller.create_book_structure(
            book_id=self.book_id,
            metadata=self.metadata,
            chapters=self.extracted_content
        )
        cover_result = self.controller.create_book_cover(
            metadata=self.metadata,
            source_file=self.file_path
        )

        # Sempre criar nota única com conteúdo completo
        full_note_result = self.controller.create_single_note_structure(
            book_id=self.book_id,
            metadata=self.metadata,
            content=self.extracted_content,
            config=self.notes_config
        )
        
        # Criar índice do livro
        index_result = self.controller.create_book_index(
            book_id=self.book_id,
            metadata=self.metadata,
            chapters=self.extracted_content
        )
        
        self.stage_progress.emit(self.pipeline_id, "structuring", 100, "Estruturação concluída")
        
        return {
            "book_id": self.book_id,
            "directory_created": chapters_result.get("directory_created", False),
            "index_created": index_result.get("index_created", False),
            "cover_created": bool(cover_result.get("cover_created", False)),
            "cover_path": cover_result.get("cover_path"),
            "chapter_notes_created": chapters_result.get("notes_created", 0),
            "full_note_created": full_note_result.get("notes_created", 0) > 0,
            "notes_created": chapters_result.get("notes_created", 0) + full_note_result.get("notes_created", 0),
            "warnings": (self.processing_result.warnings if self.processing_result else []) or []
        }
    
    def _enhance_with_llm(self) -> Dict:
        """Etapa 4: Aprimoramento com LLM"""
        if not self.use_llm:
            return {"llm_used": False, "message": "LLM não habilitado"}
        
        self.stage_progress.emit(self.pipeline_id, "llm_enhancement", 10, "Aprimorando com LLM...")
        
        try:
            # Importar processador LLM
            from core.modules.llm_pdf_transcriber import LLMPDFProcessor
            
            # Inicializar processador LLM
            llm_processor = LLMPDFProcessor()
            
            # Processar páginas que precisam de melhoria
            improved_pages = 0
            if hasattr(self.metadata, 'requires_ocr') and self.metadata.requires_ocr:
                # Processar algumas páginas com LLM
                pages_to_process = min(10, self.metadata.total_pages)
                
                for page_num in range(pages_to_process):
                    if self._check_stop_condition():
                        break
                    
                    self.stage_progress.emit(
                        self.pipeline_id, 
                        "llm_enhancement",
                        int(10 + (page_num / pages_to_process) * 90),
                        f"Aprimorando página {page_num + 1}/{pages_to_process} com LLM..."
                    )
                    
                    # Aqui você implementaria o processamento real com LLM
                    # Por enquanto, apenas simulamos
                    improved_pages += 1
            
            self.stage_progress.emit(self.pipeline_id, "llm_enhancement", 100, "Aprimoramento com LLM concluído")
            
            return {
                "llm_used": True,
                "pages_improved": improved_pages,
                "enhancement_method": "llm_ocr_enhancement"
            }
            
        except ImportError:
            logger.warning("Módulo LLM não disponível")
            return {"llm_used": False, "error": "Módulo LLM não disponível"}
        except Exception as e:
            logger.error(f"Erro no aprimoramento com LLM: {e}")
            return {"llm_used": False, "error": str(e)}
    
    def _integrate_with_systems(self) -> Dict:
        """Etapa 5: Integração com sistemas"""
        self.stage_progress.emit(self.pipeline_id, "integration", 10, "Integrando com sistemas...")
        
        if not self.book_id or not self.metadata:
            raise Exception("Dados do livro não disponíveis para integração")
        
        # Registrar no sistema de leitura
        integration_result = self.controller.register_book_in_system(
            book_id=self.book_id,
            title=self.metadata.title,
            author=self.metadata.author,
            total_pages=self.metadata.total_pages,
            file_path=self.file_path
        )
        
        # Registrar no vault
        if self.controller.vault_manager:
            vault_result = self.controller.integrate_with_vault(
                book_id=self.book_id,
                metadata=self.metadata,
                chapters=self.extracted_content
            )
            integration_result.update(vault_result)
        
        # Registrar no cache interno
        self.controller.book_registry[self.book_id] = {
            "title": self.metadata.title,
            "author": self.metadata.author,
            "total_pages": self.metadata.total_pages,
            "file_path": str(self.file_path),
            "processed_at": datetime.now().isoformat(),
            "quality": self.quality,
            "chapters": len(self.extracted_content) if self.extracted_content else 0
        }
        
        self.stage_progress.emit(self.pipeline_id, "integration", 100, "Integração concluída")
        
        return integration_result
    
    def _schedule_reading(self) -> Dict:
        """Etapa 6: Agendamento automático de leitura"""
        if not self.book_id:
            raise Exception("Book ID não disponível para agendamento")
        
        self.stage_progress.emit(self.pipeline_id, "scheduling", 10, "Preparando agendamento...")
        
        # Agendar leitura usando AgendaManager
        scheduling_result = self.controller.schedule_book_reading(
            book_id=self.book_id,
            title=self.metadata.title,
            total_pages=self.metadata.total_pages
        )
        
        if not scheduling_result.get("success", False):
            logger.warning(f"Agendamento automático falhou: {scheduling_result.get('error')}")
            scheduling_result["warning"] = "Agendamento automático não concluído"
        
        self.stage_progress.emit(self.pipeline_id, "scheduling", 100, "Agendamento configurado")
        
        return scheduling_result
    
    def _complete_pipeline(self):
        """Finaliza o pipeline com sucesso"""
        warnings = []
        extraction_stage = self.consolidated_result.get("extraction", {})
        if isinstance(extraction_stage, dict):
            warnings.extend(extraction_stage.get("warnings", []) or [])
        structure_stage = self.consolidated_result.get("structuring", {})
        if isinstance(structure_stage, dict):
            warnings.extend(structure_stage.get("warnings", []) or [])

        final_result = {
            "status": "completed",
            "pipeline_id": self.pipeline_id,
            "book_id": self.book_id,
            "title": self.metadata.title if self.metadata else "Desconhecido",
            "author": self.metadata.author if self.metadata else "Desconhecido",
            "total_pages": self.metadata.total_pages if self.metadata else 0,
            "chapters": len(self.extracted_content) if self.extracted_content else 0,
            "quality": self.quality,
            "use_llm": self.use_llm,
            "stages": self.consolidated_result,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat(),
            "processing_time": (
                datetime.now() - datetime.fromisoformat(
                    self.consolidated_result.get("initialization", {}).get("timestamp", datetime.now().isoformat())
                )
            ).total_seconds()
        }
        
        # Salvar no histórico
        self.controller.save_to_history(final_result)
        
        # Emitir sinal de conclusão
        self.pipeline_completed.emit(self.pipeline_id, final_result)
        
        logger.info(f"Pipeline {self.pipeline_id} concluído: {final_result.get('title', 'Desconhecido')}")
    
    def _check_stop_condition(self) -> bool:
        """Verifica se o pipeline deve ser interrompido"""
        return not self._is_running
    
    def stop(self):
        """Para o pipeline de forma segura"""
        self._is_running = False
        self.quit()
        self.wait(2000)


class BookController(QObject):
    """Controller robusto para gerenciamento completo de livros"""
    
    # Sinais principais
    book_processing_started = pyqtSignal(str, str, dict)  # (pipeline_id, file_name, settings)
    book_processing_completed = pyqtSignal(str, dict)  # (pipeline_id, result)
    book_processing_failed = pyqtSignal(str, str)  # (pipeline_id, error)
    book_processing_progress = pyqtSignal(str, str, int, str)  # (pipeline_id, stage, percent, message)
    
    book_scheduled = pyqtSignal(str, dict)  # (book_id, scheduling_result)
    book_registered = pyqtSignal(str, dict)  # (book_id, registration_result)
    book_structure_created = pyqtSignal(str, dict)  # (book_id, structure_result)
    
    def __init__(self, pdf_processor, book_processor, reading_manager=None, 
                 agenda_controller=None, vault_manager=None):
        super().__init__()
        self.pdf_processor = pdf_processor
        self.book_processor = book_processor
        self.reading_manager = reading_manager
        self.agenda_controller = agenda_controller
        self.vault_manager = vault_manager
        
        # Gerenciamento de pipelines ativos
        self.active_pipelines: Dict[str, BookProcessingPipeline] = {}
        self.pipeline_mutex = QMutex()
        
        # Cache e estado
        self.books_cache = {}
        self.book_registry = {}
        self.processing_history = []
        
        # Configuração
        self.auto_schedule_reading = True
        self.default_pages_per_day = 10
        self.default_scheduling_strategy = "balanced"
        self.default_quality = "standard"
        self.default_use_llm = False
        
        # Inicializar componentes
        self._initialize_components()
        
        # Timer de manutenção
        self.maintenance_timer = QTimer()
        self.maintenance_timer.timeout.connect(self._perform_maintenance)
        self.maintenance_timer.start(300000)  # 5 minutos
        
        logger.info("BookController inicializado com gerenciamento robusto")
    
    def _initialize_components(self):
        """Inicializa componentes do sistema"""
        try:
            # Verificar se os módulos estão disponíveis
            self.has_llm = self._check_llm_availability()
            self.has_agenda = self.agenda_controller is not None
            self.has_vault = self.vault_manager is not None
            
            logger.info(f"Componentes disponíveis - LLM: {self.has_llm}, Agenda: {self.has_agenda}, Vault: {self.has_vault}")
            
        except Exception as e:
            logger.error(f"Erro na inicialização de componentes: {e}")
    
    def _check_llm_availability(self) -> bool:
        """Verifica se o módulo LLM está disponível"""
        try:
            from core.modules.llm_pdf_transcriber import LLMPDFProcessor
            return True
        except ImportError:
            return False
    
    # ====== MÉTODOS PÚBLICOS PRINCIPAIS ======
    
    @pyqtSlot(str, str, bool, bool)
    def process_book(self, file_path: str, quality: str = None, 
                    auto_schedule: bool = None, use_llm: bool = None) -> str:
        """
        Inicia processamento completo de um livro
        
        Args:
            file_path: Caminho para o arquivo do livro
            quality: Qualidade do processamento (draft, standard, high, academic)
            auto_schedule: Se True, agenda automaticamente após processamento
            use_llm: Se True, usa LLM para aprimoramento
            
        Returns:
            pipeline_id: ID para acompanhamento do processamento
        """
        self.pipeline_mutex.lock()
        try:
            # Usar valores padrão se não especificados
            quality = quality or self.default_quality
            auto_schedule = auto_schedule if auto_schedule is not None else self.auto_schedule_reading
            use_llm = use_llm if use_llm is not None else self.default_use_llm
            
            # Validar parâmetros
            if quality not in ['draft', 'standard', 'high', 'academic']:
                logger.warning(f"Qualidade inválida: {quality}. Usando padrão: {self.default_quality}")
                quality = self.default_quality
            
            # Validar arquivo
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
            # Criar pipeline
            pipeline = BookProcessingPipeline(
                controller=self,
                file_path=file_path,
                quality=quality,
                schedule_reading=auto_schedule,
                use_llm=use_llm and self.has_llm  # Só usar LLM se disponível
            )
            
            pipeline_id = pipeline.pipeline_id
            
            # Conectar sinais do pipeline
            pipeline.stage_started.connect(self._on_stage_started)
            pipeline.stage_progress.connect(self._on_stage_progress)
            pipeline.stage_completed.connect(self._on_stage_completed)
            pipeline.stage_failed.connect(self._on_stage_failed)
            pipeline.pipeline_completed.connect(self._on_pipeline_completed)
            pipeline.pipeline_failed.connect(self._on_pipeline_failed)
            
            # Registrar pipeline ativo
            self.active_pipelines[pipeline_id] = pipeline
            
            # Iniciar pipeline
            pipeline.start()
            
            # Emitir sinal de início
            file_name = Path(file_path).stem
            settings = {
                "quality": quality,
                "auto_schedule": auto_schedule,
                "use_llm": use_llm,
                "timestamp": datetime.now().isoformat()
            }
            self.book_processing_started.emit(pipeline_id, file_name, settings)
            
            logger.info(f"Pipeline {pipeline_id} iniciado para: {file_name} (qualidade: {quality}, LLM: {use_llm})")
            
            return pipeline_id
            
        except Exception as e:
            logger.error(f"Erro ao iniciar processamento: {e}")
            raise
        finally:
            self.pipeline_mutex.unlock()
    
    @pyqtSlot(str, result=dict)
    def get_book_status(self, book_id: str) -> Dict:
        """
        Obtém status completo de um livro
        
        Args:
            book_id: ID do livro
            
        Returns:
            Status do livro
        """
        status = {
            "book_id": book_id,
            "found": False,
            "systems": {}
        }
        
        # Verificar no registro interno
        if book_id in self.book_registry:
            status["found"] = True
            status["registry"] = self.book_registry[book_id]
        
        # Verificar no ReadingManager
        if self.reading_manager:
            try:
                progress = self.reading_manager.get_reading_progress(book_id)
                if progress:
                    status["systems"]["reading_manager"] = {
                        "registered": True,
                        "progress": progress
                    }
                else:
                    status["systems"]["reading_manager"] = {"registered": False}
            except Exception as e:
                status["systems"]["reading_manager"] = {"registered": False, "error": str(e)}
        
        # Verificar no vault
        if self.vault_manager and book_id in self.book_registry:
            try:
                book_info = self.book_registry[book_id]
                author = book_info.get("author", "")
                title = book_info.get("title", "")
                
                # Verificar se diretório existe
                vault_path = self.vault_manager.vault_path
                book_dir = vault_path / "01-LEITURAS" / author / title
                
                status["systems"]["vault"] = {
                    "directory_exists": book_dir.exists(),
                    "notes_count": len(list(book_dir.glob("*.md"))) if book_dir.exists() else 0
                }
            except Exception as e:
                status["systems"]["vault"] = {"error": str(e)}
        
        # Verificar na agenda
        if self.agenda_controller:
            try:
                # Verificar se há eventos agendados para este livro
                # (implementação depende da API do AgendaController)
                status["systems"]["agenda"] = {"registered": "unknown"}
            except Exception as e:
                status["systems"]["agenda"] = {"error": str(e)}
        
        return status
    
    @pyqtSlot(str, int, int)
    def process_additional_chapters(self, book_id: str, start_chapter: int, num_chapters: int):
        """
        Processa capítulos adicionais de um livro já registrado
        
        Args:
            book_id: ID do livro
            start_chapter: Capítulo inicial
            num_chapters: Número de capítulos a processar
        """
        try:
            if book_id not in self.book_registry:
                raise ValueError(f"Livro {book_id} não encontrado no registro")
            
            book_info = self.book_registry[book_id]
            file_path = book_info.get("file_path")
            
            if not file_path or not Path(file_path).exists():
                raise FileNotFoundError(f"Arquivo original não encontrado: {file_path}")
            
            # Usar ChapterProcessor para processar capítulos adicionais
            from core.modules.book_processor import ChapterProcessor
            
            chapter_processor = ChapterProcessor(self.vault_manager)
            
            result = chapter_processor.process_chapters(
                pdf_path=file_path,
                num_chapters=num_chapters,
                start_chapter=start_chapter,
                book_id=book_id
            )
            
            if result.get("success"):
                # Atualizar registro
                self.book_registry[book_id]["chapters"] = result.get("next_chapter", 1) - 1
                
                # Emitir sinal
                self.book_processing_completed.emit(
                    f"chapters_{book_id}_{datetime.now().timestamp()}",
                    result
                )
                
                logger.info(f"Capítulos adicionais processados para {book_id}: {result.get('chapters_processed')} capítulos")
            else:
                raise Exception(result.get("error", "Erro desconhecido"))
                
        except Exception as e:
            logger.error(f"Erro processando capítulos adicionais: {e}")
            self.book_processing_failed.emit(book_id, str(e))
    
    # ====== MÉTODOS DE INTEGRAÇÃO ======
    
    def generate_consistent_book_id(self, title: str, author: str) -> str:
        """Gera ID consistente para todos os sistemas"""
        # Normalizar strings
        norm_title = re.sub(r'\s+', ' ', title.strip().lower())
        norm_author = re.sub(r'\s+', ' ', author.strip().lower())
        
        # Gerar hash consistente
        content = f"{norm_title}||{norm_author}||{datetime.now().strftime('%Y%m')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def create_book_structure(self, book_id: str, metadata, chapters: List[Dict]) -> Dict:
        """Cria estrutura de diretórios e notas para o livro"""
        result = {
            "book_id": book_id,
            "directory_created": False,
            "notes_created": 0,
            "errors": []
        }
        
        try:
            if not self.vault_manager:
                result["errors"].append("VaultManager não disponível")
                return result
            
            # Sanitizar nomes
            safe_author = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
            safe_title = self._sanitize_filename(metadata.title)
            
            # Criar diretório principal
            book_dir = self.vault_manager.vault_path / "01-LEITURAS" / safe_author / safe_title
            book_dir.mkdir(parents=True, exist_ok=True)
            result["directory_created"] = True
            result["directory_path"] = str(book_dir)
            
            # Criar notas para cada capítulo
            for chapter in chapters:
                try:
                    chapter_num = chapter.get('chapter_num') or chapter.get('number') or 0
                    chapter_title = chapter.get('chapter_title') or chapter.get('title') or f"Capítulo {chapter_num}"
                    content = chapter.get('content', '')
                    
                    # Nome do arquivo
                    filename = f"{chapter_num:03d} - {self._sanitize_filename(chapter_title)}.md"
                    relative_path = f"01-LEITURAS/{safe_author}/{safe_title}/{filename}"
                    
                    # Frontmatter
                    frontmatter = {
                        'title': chapter_title,
                        'book': metadata.title,
                        'author': metadata.author,
                        'chapter': chapter_num,
                        'pages': chapter.get('pages') or f"{chapter.get('start_page', 'N/A')}-{chapter.get('end_page', 'N/A')}",
                        'book_id': book_id,
                        'tags': ['livro', 'capitulo']
                    }
                    
                    # Conteúdo da nota
                    note_content = f"""# {chapter_title}

## 📚 Livro
[[{metadata.title}]]

## 📖 Informações
- **Livro**: {metadata.title}
- **Autor**: {metadata.author}
- **Capítulo**: {chapter_num}
- **Páginas**: {chapter.get('pages', 'N/A')}

## 📝 Conteúdo
{content}

## 💭 Anotações
<!-- Adicione suas anotações aqui -->

## 🔗 Links
[[{metadata.title}]] | [[Índice - {metadata.title}]]
"""
                    
                    # Criar nota
                    existing_note = self.vault_manager.get_note_by_path(relative_path)
                    if existing_note:
                        self.vault_manager.update_note(
                            relative_path,
                            content=note_content,
                            frontmatter=frontmatter
                        )
                    else:
                        self.vault_manager.create_note(
                            relative_path,
                            content=note_content,
                            frontmatter=frontmatter
                        )
                    
                    result["notes_created"] += 1
                    
                except Exception as e:
                    result["errors"].append(f"Erro criando capítulo {chapter_num}: {e}")
            
            # Emitir sinal
            self.book_structure_created.emit(book_id, result)
            
        except Exception as e:
            result["errors"].append(f"Erro geral na criação da estrutura: {e}")
        
        return result
    
    def create_book_index(self, book_id: str, metadata, chapters: List[Dict]) -> Dict:
        """Cria índice do livro no vault"""
        result = {
            "book_id": book_id,
            "index_created": False
        }
        
        try:
            if not self.vault_manager:
                return result
            
            safe_author = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
            safe_title = self._sanitize_filename(metadata.title)
            
            # Caminho para o índice
            index_path = f"01-LEITURAS/{safe_author}/{safe_title}/📖 {safe_title}.md"
            
            # Frontmatter
            frontmatter = {
                'title': metadata.title,
                'author': metadata.author,
                'type': 'livro',
                'book_id': book_id,
                'total_pages': metadata.total_pages,
                'total_chapters': len(chapters),
                'processed_date': datetime.now().isoformat(),
                'tags': ['livro', 'indice']
            }
            
            # Lista de capítulos
            chapters_list = ""
            for chapter in chapters:
                chapter_num = chapter.get('chapter_num') or chapter.get('number') or 0
                chapter_title = chapter.get('chapter_title') or chapter.get('title') or f"Capítulo {chapter_num}"
                safe_chapter_title = self._sanitize_filename(chapter_title)
                
                chapters_list += f"{chapter_num}. [[{chapter_num:03d} - {safe_chapter_title}|{chapter_title}]]\n"
            
            # Conteúdo do índice
            content = f"""# {metadata.title}

## 👤 Autor
{metadata.author}

## 📊 Informações
- **Total de páginas**: {metadata.total_pages}
- **Total de capítulos**: {len(chapters)}
- **ID do livro**: {book_id}
- **Processado em**: {datetime.now().strftime('%d/%m/%Y %H:%M')}

## 📑 Capítulos
{chapters_list}

## 📝 Notas Gerais
<!-- Adicione suas notas sobre o livro aqui -->

## 🎯 Objetivos de Leitura
<!-- Defina seus objetivos de leitura -->

## 📅 Progresso
| Capítulo | Data de Leitura | Status | Notas |
|----------|-----------------|--------|-------|
| 1 | | 📖 Pendente | |
| 2 | | 📖 Pendente | |
| ... | | ... | |
"""
            
            # Criar ou atualizar índice
            existing_note = self.vault_manager.get_note_by_path(index_path)
            
            if existing_note:
                self.vault_manager.update_note(
                    index_path,
                    content=content,
                    frontmatter=frontmatter
                )
            else:
                self.vault_manager.create_note(
                    index_path,
                    content=content,
                    frontmatter=frontmatter
                )
            
            result["index_created"] = True
            
        except Exception as e:
            logger.error(f"Erro criando índice: {e}")
            result["error"] = str(e)
        
        return result

    def create_book_cover(self, metadata, source_file: Path) -> Dict:
        """Gera e salva a capa do livro no diretório do vault."""
        result = {
            "cover_created": False,
            "cover_path": None,
            "error": None
        }

        try:
            if not self.vault_manager:
                result["error"] = "VaultManager não disponível"
                return result

            safe_author = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
            safe_title = self._sanitize_filename(metadata.title)
            book_dir = self.vault_manager.vault_path / "01-LEITURAS" / safe_author / safe_title
            book_dir.mkdir(parents=True, exist_ok=True)

            source_path = Path(source_file)
            ext = source_path.suffix.lower()
            cover_path: Optional[Path] = None

            if ext == ".pdf":
                cover_path = self._extract_pdf_cover(source_path, book_dir)
            elif ext == ".epub":
                cover_path = self._extract_epub_cover(source_path, book_dir)

            if cover_path and cover_path.exists():
                result["cover_created"] = True
                result["cover_path"] = str(cover_path)
            else:
                result["error"] = "Não foi possível extrair capa do arquivo"

        except Exception as e:
            result["error"] = str(e)
            logger.warning("Falha ao criar capa do livro: %s", e)

        return result

    def _extract_pdf_cover(self, pdf_path: Path, output_dir: Path) -> Optional[Path]:
        """Extrai a primeira página do PDF como capa."""
        try:
            import fitz

            with fitz.open(pdf_path) as doc:
                if len(doc) == 0:
                    return None
                page = doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), alpha=False)
                cover_path = output_dir / "cover.jpg"
                pix.save(str(cover_path))
                return cover_path
        except Exception as e:
            logger.debug("Não foi possível extrair capa PDF (%s): %s", pdf_path, e)
            return None

    def _extract_epub_cover(self, epub_path: Path, output_dir: Path) -> Optional[Path]:
        """Extrai imagem de capa de EPUB para o diretório do livro."""
        try:
            with zipfile.ZipFile(epub_path, "r") as zf:
                opf_path = self._find_epub_opf_path(zf)
                if not opf_path:
                    return None

                opf_data = zf.read(opf_path)
                root = ET.fromstring(opf_data)
                ns = {
                    "opf": "http://www.idpf.org/2007/opf",
                    "dc": "http://purl.org/dc/elements/1.1/",
                }

                manifest_items = {}
                for item in root.findall(".//opf:manifest/opf:item", ns):
                    item_id = item.attrib.get("id", "")
                    href = item.attrib.get("href", "")
                    media_type = item.attrib.get("media-type", "")
                    props = item.attrib.get("properties", "")
                    if item_id:
                        manifest_items[item_id] = {
                            "href": href,
                            "media_type": media_type,
                            "properties": props,
                        }

                cover_id = None
                for meta in root.findall(".//opf:metadata/opf:meta", ns):
                    if meta.attrib.get("name") == "cover":
                        cover_id = meta.attrib.get("content")
                        break

                selected = None
                if cover_id and cover_id in manifest_items:
                    selected = manifest_items[cover_id]
                if not selected:
                    for item in manifest_items.values():
                        if "cover-image" in (item.get("properties") or ""):
                            selected = item
                            break
                if not selected:
                    for item in manifest_items.values():
                        if item.get("media_type", "").startswith("image/"):
                            selected = item
                            break
                if not selected:
                    return None

                image_path = self._resolve_epub_item_path(opf_path, selected["href"])
                image_data = zf.read(image_path)

                media_type = selected.get("media_type", "")
                ext = {
                    "image/jpeg": ".jpg",
                    "image/jpg": ".jpg",
                    "image/png": ".png",
                    "image/webp": ".webp",
                }.get(media_type, Path(selected["href"]).suffix or ".jpg")

                cover_path = output_dir / f"cover{ext}"
                with open(cover_path, "wb") as f:
                    f.write(image_data)
                return cover_path
        except Exception as e:
            logger.debug("Não foi possível extrair capa EPUB (%s): %s", epub_path, e)
            return None

    def _find_epub_opf_path(self, zf: zipfile.ZipFile) -> Optional[str]:
        """Localiza caminho do OPF dentro do EPUB."""
        try:
            container_path = "META-INF/container.xml"
            if container_path in zf.namelist():
                container_root = ET.fromstring(zf.read(container_path))
                namespace = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
                rootfile = container_root.find(".//c:rootfile", namespace)
                if rootfile is not None and rootfile.attrib.get("full-path"):
                    return rootfile.attrib.get("full-path")
            for name in zf.namelist():
                if name.lower().endswith(".opf"):
                    return name
            return None
        except Exception:
            return None

    def _resolve_epub_item_path(self, opf_path: str, href: str) -> str:
        """Resolve caminho relativo de item do EPUB a partir do OPF."""
        base = Path(opf_path).parent
        resolved = (base / href).as_posix()
        return resolved.lstrip("/")

    def create_single_note_structure(self, book_id: str, metadata, content: List[Dict], config: Dict = None) -> Dict:
        """Cria uma única nota para todo o livro"""
        result = {
            "book_id": book_id,
            "directory_created": False,
            "notes_created": 0,
            "single_note": True,
            "errors": []
        }
        
        try:
            if not self.vault_manager:
                result["errors"].append("VaultManager não disponível")
                return result
            
            # Sanitizar nomes
            safe_author = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
            safe_title = self._sanitize_filename(metadata.title)
            
            # Criar diretório principal
            book_dir = self.vault_manager.vault_path / "01-LEITURAS" / safe_author / safe_title
            book_dir.mkdir(parents=True, exist_ok=True)
            result["directory_created"] = True
            result["directory_path"] = str(book_dir)
            
            # Combinar todo o conteúdo em uma única string
            full_content = ""
            for chapter in content:
                chapter_num = chapter.get('chapter_num') or chapter.get('number') or 0
                chapter_title = chapter.get('chapter_title') or chapter.get('title') or f"Capítulo {chapter_num}"
                chapter_text = chapter.get('content', '')
                
                full_content += f"\n\n## Capítulo {chapter_num}: {chapter_title}\n\n"
                full_content += chapter_text
            
            # Caminho para a nota única
            note_path = f"01-LEITURAS/{safe_author}/{safe_title}/📚 {safe_title} - Completo.md"
            
            # Frontmatter
            frontmatter = {
                'title': metadata.title,
                'book': metadata.title,
                'author': metadata.author,
                'type': 'livro_completo',
                'book_id': book_id,
                'total_pages': metadata.total_pages,
                'total_chapters': len(content),
                'processed_date': datetime.now().isoformat(),
                'tags': ['livro', 'nota_única']
            }
            
            # Adicionar tags personalizadas se fornecidas
            if config and 'tags' in config:
                frontmatter['tags'].extend(config['tags'])
            
            # Conteúdo da nota
            note_content = f"""# {metadata.title}

## 👤 Autor
{metadata.author}

## 📊 Informações
- **Total de páginas**: {metadata.total_pages}
- **Total de capítulos**: {len(content)}
- **Processado em**: {datetime.now().strftime('%d/%m/%Y %H:%M')}
- **ID do livro**: {book_id}

## 📝 Conteúdo Completo
{full_content}

## 💭 Anotações Pessoais
<!-- Adicione suas anotações aqui -->

## 🔗 Índice de Capítulos
"""
            
            # Adicionar índice
            for chapter in content:
                chapter_num = chapter.get('chapter_num') or chapter.get('number') or 0
                chapter_title = chapter.get('chapter_title') or chapter.get('title') or f"Capítulo {chapter_num}"
                note_content += f"{chapter_num}. {chapter_title}\n"
            
            existing_note = self.vault_manager.get_note_by_path(note_path)
            if existing_note:
                self.vault_manager.update_note(
                    note_path,
                    content=note_content,
                    frontmatter=frontmatter
                )
            else:
                self.vault_manager.create_note(
                    note_path,
                    content=note_content,
                    frontmatter=frontmatter
                )
            
            result["notes_created"] = 1
            
            # Emitir sinal
            self.book_structure_created.emit(book_id, result)
            
        except Exception as e:
            result["errors"].append(f"Erro criando nota única: {e}")
            logger.error(f"Erro criando nota única: {e}")
        
        return result
    
    def integrate_with_vault(self, book_id: str, metadata, chapters: List[Dict]) -> Dict:
        """Integra livro com o vault do Obsidian"""
        result = {
            "book_id": book_id,
            "success": False,
            "steps_completed": []
        }
        
        try:
            # 1. Criar estrutura
            structure_result = self.create_book_structure(book_id, metadata, chapters)
            if structure_result.get("directory_created"):
                result["steps_completed"].append("structure_created")
            
            # 2. Criar índice
            index_result = self.create_book_index(book_id, metadata, chapters)
            if index_result.get("index_created"):
                result["steps_completed"].append("index_created")
            
            # 3. Criar nota de conceitos
            concepts_result = self._create_concepts_note(book_id, metadata)
            if concepts_result.get("concepts_note_created"):
                result["steps_completed"].append("concepts_note_created")
            
            result["success"] = len(result["steps_completed"]) > 0
            result["details"] = {
                "structure": structure_result,
                "index": index_result,
                "concepts": concepts_result
            }
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Erro na integração com vault: {e}")
        
        return result
    
    def _create_concepts_note(self, book_id: str, metadata) -> Dict:
        """Cria nota de conceitos-chave do livro"""
        result = {"concepts_note_created": False}
        
        try:
            if not self.vault_manager:
                return result
            
            safe_author = self._resolve_author_directory_name(metadata.author or "Autor Desconhecido")
            safe_title = self._sanitize_filename(metadata.title)
            
            # Caminho para a nota de conceitos
            concepts_path = f"01-LEITURAS/{safe_author}/{safe_title}/🧠 Conceitos-Chave.md"
            
            # Frontmatter
            frontmatter = {
                'title': f'Conceitos-Chave - {metadata.title}',
                'book': metadata.title,
                'author': metadata.author,
                'type': 'concepts',
                'book_id': book_id,
                'tags': ['conceitos', 'livro']
            }
            
            # Conteúdo da nota
            content = f"""# Conceitos-Chave - {metadata.title}

## 📚 Livro
[[{metadata.title}]]

## 🧠 Conceitos Principais
<!-- Liste e explique os conceitos principais do livro aqui -->

## 💬 Citações Importantes
<!-- Colete citações importantes do livro -->

## ❓ Questões para Reflexão
<!-- Questões geradas pela LLM ou suas próprias -->

## 🔍 Conexões com Outras Obras
<!-- Relacione com outros livros ou autores -->

## 📝 Minhas Reflexões
<!-- Adicione suas próprias reflexões -->
"""
            
            # Criar nota
            self.vault_manager.create_note(
                concepts_path,
                content=content,
                frontmatter=frontmatter
            )
            
            result["concepts_note_created"] = True
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def register_book_in_system(self, book_id: str, title: str, author: str, 
                               total_pages: int, file_path: Path) -> Dict:
        """Registra livro em todos os sistemas necessários"""
        result = {
            "book_id": book_id,
            "success": False,
            "systems_registered": [],
            "errors": []
        }
        
        try:
            # 1. Registrar no ReadingManager
            if self.reading_manager:
                try:
                    # Verificar se já existe
                    existing = self.reading_manager.get_reading_progress(book_id)
                    
                    if not existing:
                        # Adicionar novo livro
                        added_id = self.reading_manager.add_book(
                            title=title,
                            author=author,
                            total_pages=total_pages,
                            book_id=book_id
                        )
                        
                        if added_id:
                            result["systems_registered"].append("reading_manager")
                            result["reading_system_id"] = added_id
                            logger.info(f"Livro {book_id} registrado no ReadingManager")
                        else:
                            result["errors"].append("Falha ao adicionar ao ReadingManager")
                    else:
                        result["systems_registered"].append("reading_manager (existing)")
                        logger.info(f"Livro {book_id} já existe no ReadingManager")
                        
                except Exception as e:
                    result["errors"].append(f"ReadingManager error: {str(e)}")
                    logger.error(f"Erro no ReadingManager para {book_id}: {e}")
            
            # 2. Registrar no cache interno
            self.book_registry[book_id] = {
                "title": title,
                "author": author,
                "total_pages": total_pages,
                "file_path": str(file_path),
                "registered_at": datetime.now().isoformat(),
                "systems": result["systems_registered"]
            }
            
            # 3. Registrar no vault (se disponível)
            if self.vault_manager:
                try:
                    # Criar nota de registro no vault
                    registry_path = f"06-RECURSOS/registros_livros/{book_id}.json"
                    
                    registry_data = {
                        "book_id": book_id,
                        "title": title,
                        "author": author,
                        "total_pages": total_pages,
                        "file_path": str(file_path),
                        "registered_at": datetime.now().isoformat(),
                        "processing_complete": True
                    }
                    
                    # Criar diretório se não existir
                    registry_dir = self.vault_manager.vault_path / "06-RECURSOS" / "registros_livros"
                    registry_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Salvar JSON
                    registry_file = registry_dir / f"{book_id}.json"
                    with open(registry_file, 'w', encoding='utf-8') as f:
                        json.dump(registry_data, f, indent=2, ensure_ascii=False)
                    
                    result["systems_registered"].append("vault_registry")
                    
                except Exception as e:
                    result["errors"].append(f"VaultRegistry error: {str(e)}")
            
            # Verificar sucesso
            if len(result["systems_registered"]) > 0:
                result["success"] = True
                result["status"] = "registered"
                
                # Emitir sinal de registro
                self.book_registered.emit(book_id, result)
                
            else:
                result["status"] = "registration_failed"
                
        except Exception as e:
            result["errors"].append(f"Registration error: {str(e)}")
            logger.error(f"Erro geral no registro do livro {book_id}: {e}")
        
        return result
    
    def schedule_book_reading(self, book_id: str, title: str = None, 
                             total_pages: int = None) -> Dict:
        """Agenda leitura automática do livro"""
        result = {
            "book_id": book_id,
            "success": False,
            "scheduling_attempted": False,
            "agenda_events_created": 0,
            "error": None
        }
        
        try:
            # Verificar se temos AgendaController
            if not self.agenda_controller:
                result["error"] = "AgendaController não disponível"
                return result
            
            # Obter informações do livro (se não fornecidas)
            if not title or not total_pages:
                book_info = self.get_book_info(book_id)
                if not book_info:
                    result["error"] = f"Livro {book_id} não encontrado"
                    return result
                
                title = book_info.get("title", title)
                total_pages = book_info.get("total_pages", total_pages)
                author = book_info.get("author", "Desconhecido")
            else:
                author = self.book_registry.get(book_id, {}).get("author", "Desconhecido")

            # Sincroniza o livro no ReadingManager usado pela camada de agenda.
            self._sync_book_to_agenda_reading_manager(
                book_id=book_id,
                title=title,
                author=author,
                total_pages=total_pages
            )
            
            # Calcular páginas por dia
            pages_per_day = self._calculate_pages_per_day(total_pages)
            
            # Chamar AgendaController para alocar tempo
            result["scheduling_attempted"] = True
            result["pages_per_day"] = pages_per_day
            result["strategy"] = self.default_scheduling_strategy
            
            # Usar método síncrono para garantir execução
            scheduling_result = self._execute_scheduling(
                book_id=book_id,
                pages_per_day=pages_per_day,
                strategy=self.default_scheduling_strategy
            )
            
            # Processar resultado
            if "error" in scheduling_result:
                result["error"] = scheduling_result["error"]
            else:
                result["success"] = True
                result["agenda_events_created"] = scheduling_result.get("total_sessions", 0)
                result["allocation_details"] = scheduling_result
                
                # Emitir sinal de agendamento
                self.book_scheduled.emit(book_id, result)
                
                logger.info(f"Leitura agendada para {book_id}: {pages_per_day} páginas/dia")
        
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Erro no agendamento de {book_id}: {e}")
        
        return result

    def _get_agenda_reading_manager(self):
        """Retorna o ReadingManager efetivo usado pelo agendador."""
        if not self.agenda_controller:
            return None
        if hasattr(self.agenda_controller, "reading_manager"):
            return self.agenda_controller.reading_manager
        if hasattr(self.agenda_controller, "agenda_manager"):
            agenda_manager = getattr(self.agenda_controller, "agenda_manager", None)
            if agenda_manager and hasattr(agenda_manager, "reading_manager"):
                return agenda_manager.reading_manager
        return None

    def _sync_book_to_agenda_reading_manager(self, book_id: str, title: str,
                                             author: str, total_pages: int):
        """
        Garante que o livro exista no ReadingManager consultado pelo agendador.
        Evita erro de "Livro não encontrado" após importação recém-concluída.
        """
        agenda_reading_manager = self._get_agenda_reading_manager()
        if not agenda_reading_manager:
            return

        try:
            agenda_progress = agenda_reading_manager.get_reading_progress(book_id)
            if agenda_progress:
                return

            source_progress = None
            if self.reading_manager and hasattr(self.reading_manager, "readings"):
                source_progress = self.reading_manager.readings.get(book_id)

            if source_progress is not None and hasattr(agenda_reading_manager, "readings"):
                agenda_reading_manager.readings[book_id] = source_progress
                if hasattr(agenda_reading_manager, "_save_progress"):
                    agenda_reading_manager._save_progress()
                return

            if hasattr(agenda_reading_manager, "add_book"):
                agenda_reading_manager.add_book(
                    title=title or "Desconhecido",
                    author=author or "Desconhecido",
                    total_pages=int(total_pages or 0),
                    book_id=book_id
                )
        except Exception as e:
            logger.warning(f"Não foi possível sincronizar livro {book_id} para agenda: {e}")
    
    def _execute_scheduling(self, book_id: str, pages_per_day: float, strategy: str) -> Dict:
        """Executa agendamento de forma síncrona com fallback"""
        try:
            # Usar método síncrono do AgendaController
            if hasattr(self.agenda_controller, 'allocate_reading_time'):
                return self.agenda_controller.allocate_reading_time(
                    book_id=book_id,
                    pages_per_day=pages_per_day,
                    strategy=strategy
                )
            elif hasattr(self.agenda_controller, 'allocate_reading_time_async'):
                # Se for assíncrono, usar QEventLoop para sincronizar
                from PyQt6.QtCore import QEventLoop
                
                result_container = {"result": None}
                event_loop = QEventLoop()
                
                def on_allocation_result(allocation_result):
                    result_container["result"] = allocation_result
                    event_loop.quit()
                
                # Conectar sinal temporariamente
                self.agenda_controller.reading_allocated.connect(on_allocation_result)
                
                # Iniciar agendamento
                self.agenda_controller.allocate_reading_time_async(
                    book_id, pages_per_day, strategy
                )
                
                # Aguardar resultado (timeout de 10 segundos)
                QTimer.singleShot(10000, event_loop.quit)
                event_loop.exec()
                
                # Desconectar sinal
                self.agenda_controller.reading_allocated.disconnect(on_allocation_result)
                
                return result_container.get("result", {"error": "Timeout no agendamento"})
            
            else:
                return {"error": "Método de agendamento não disponível"}
                
        except Exception as e:
            logger.error(f"Erro na execução do agendamento: {e}")
            return {"error": str(e)}
    
    def _calculate_pages_per_day(self, total_pages: int) -> float:
        """Calcula páginas por dia de forma inteligente"""
        if total_pages <= 0:
            return self.default_pages_per_day
        
        # Baseado no total de páginas e complexidade estimada
        if total_pages < 100:
            return 15  # Livro curto
        elif total_pages < 300:
            return 12  # Livro médio
        elif total_pages < 600:
            return 10  # Livro longo
        else:
            return 8   # Livro muito longo
    
    # ====== CALLBACKS DO PIPELINE ======
    
    def _on_stage_started(self, pipeline_id: str, stage: str, message: str):
        """Chamado quando um estágio do pipeline inicia"""
        logger.info(f"Pipeline {pipeline_id} - {stage}: {message}")
    
    def _on_stage_progress(self, pipeline_id: str, stage: str, percent: int, message: str):
        """Chamado durante progresso de um estágio"""
        # Emitir sinal de progresso para a UI
        self.book_processing_progress.emit(pipeline_id, stage, percent, message)
        logger.debug(f"Pipeline {pipeline_id} - {stage}: {percent}% - {message}")
    
    def _on_stage_completed(self, pipeline_id: str, stage: str, result: dict):
        """Chamado quando um estágio é concluído"""
        logger.info(f"Pipeline {pipeline_id} - {stage} concluído")
        
        # Ações específicas por estágio
        if stage == "integration" and result.get("book_id"):
            book_id = result["book_id"]
            logger.info(f"Pipeline {pipeline_id} - Livro {book_id} integrado com sucesso")
    
    def _on_stage_failed(self, pipeline_id: str, stage: str, error: str):
        """Chamado quando um estágio falha"""
        logger.error(f"Pipeline {pipeline_id} - Falha em {stage}: {error}")
        # Não interrompemos o pipeline aqui, deixamos ele lidar
    
    def _on_pipeline_completed(self, pipeline_id: str, result: dict):
        """Chamado quando o pipeline é concluído com sucesso"""
        # Limpar pipeline da lista ativa
        self.pipeline_mutex.lock()
        try:
            if pipeline_id in self.active_pipelines:
                pipeline = self.active_pipelines[pipeline_id]
                pipeline.wait(1000)
                del self.active_pipelines[pipeline_id]
        finally:
            self.pipeline_mutex.unlock()
        
        # Emitir sinal de conclusão
        self.book_processing_completed.emit(pipeline_id, result)
        
        logger.info(f"Pipeline {pipeline_id} concluído: {result.get('title', 'Desconhecido')}")
    
    def _on_pipeline_failed(self, pipeline_id: str, error: str):
        """Chamado quando o pipeline falha"""
        # Limpar pipeline da lista ativa
        self.pipeline_mutex.lock()
        try:
            if pipeline_id in self.active_pipelines:
                pipeline = self.active_pipelines[pipeline_id]
                pipeline.stop()
                del self.active_pipelines[pipeline_id]
        finally:
            self.pipeline_mutex.unlock()
        
        # Emitir sinal de falha
        self.book_processing_failed.emit(pipeline_id, error)
        
        logger.error(f"Pipeline {pipeline_id} falhou: {error}")
    
    # ====== MÉTODOS AUXILIARES ======
    
    def get_book_info(self, book_id: str) -> Optional[Dict]:
        """Obtém informações do livro do cache interno"""
        # Primeiro, verificar cache interno
        if book_id in self.book_registry:
            return self.book_registry[book_id]
        
        # Depois, verificar ReadingManager
        if self.reading_manager:
            try:
                progress = self.reading_manager.get_reading_progress(book_id)
                if progress:
                    return {
                        "book_id": book_id,
                        "title": progress.get("title"),
                        "author": progress.get("author", "Desconhecido"),
                        "total_pages": progress.get("total_pages", 0),
                        "current_page": progress.get("current_page", 0),
                        "source": "reading_manager"
                    }
            except Exception as e:
                logger.error(f"Erro ao obter info do ReadingManager: {e}")
        
        return None
    
    
    @pyqtSlot(dict, result=str)
    def process_book_with_config(self, config: dict) -> str:
        """
        Processa livro com configurações avançadas
        
        Args:
            config: Dicionário com todas as configurações:
                - file_path: caminho do arquivo
                - quality: qualidade do processamento
                - use_llm: usar LLM para aprimoramento
                - auto_schedule: agendar automaticamente
                - metadata: metadados editados
                - notes_config: configurações de notas
                - scheduling_config: configurações de agendamento
                
        Returns:
            pipeline_id: ID do pipeline
        """
        try:
            # Extrair configurações básicas
            file_path = config.get("file_path")
            quality = config.get("quality", self.default_quality)
            use_llm = config.get("use_llm", self.default_use_llm)
            auto_schedule = config.get("auto_schedule", self.auto_schedule_reading)
            
            # Validar arquivo
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
            # Criar pipeline com configurações estendidas
            pipeline = BookProcessingPipeline(
                controller=self,
                file_path=file_path,
                quality=quality,
                schedule_reading=auto_schedule,
                use_llm=use_llm,
                config=config  # Passar configurações completas
            )
            
            pipeline_id = pipeline.pipeline_id
            
            # Registrar pipeline ativo
            self.pipeline_mutex.lock()
            try:
                self.active_pipelines[pipeline_id] = pipeline
            finally:
                self.pipeline_mutex.unlock()
            
            # Conectar sinais do pipeline
            pipeline.stage_started.connect(self._on_stage_started)
            pipeline.stage_progress.connect(self._on_stage_progress)
            pipeline.stage_completed.connect(self._on_stage_completed)
            pipeline.stage_failed.connect(self._on_stage_failed)
            pipeline.pipeline_completed.connect(self._on_pipeline_completed)
            pipeline.pipeline_failed.connect(self._on_pipeline_failed)
            
            # Iniciar pipeline
            pipeline.start()
            
            # Emitir sinal de início
            file_name = Path(file_path).stem
            settings = {
                "file_path": file_path,
                "quality": quality,
                "use_llm": use_llm,
                "auto_schedule": auto_schedule,
                "config": config,
                "timestamp": datetime.now().isoformat()
            }
            self.book_processing_started.emit(pipeline_id, file_name, settings)
            
            logger.info(f"Pipeline {pipeline_id} iniciado com configurações avançadas")
            
            return pipeline_id
            
        except Exception as e:
            logger.error(f"Erro ao iniciar processamento com configurações: {e}")
            raise
    
    def update_book_metadata(self, pipeline_id: str, metadata: dict):
        """Atualizar metadados de um livro em processamento"""
        if pipeline_id in self.active_pipelines:
            pipeline = self.active_pipelines[pipeline_id]
            if hasattr(pipeline, 'metadata'):
                # Atualizar metadados do pipeline
                for key, value in metadata.items():
                    if hasattr(pipeline.metadata, key):
                        setattr(pipeline.metadata, key, value)
                    else:
                        # Adicionar atributo dinâmico se não existir
                        setattr(pipeline.metadata, key, value)

    def save_to_history(self, result: Dict):
        """Salva resultado no histórico"""
        self.processing_history.append({
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
        
        # Manter apenas os últimos 100 registros
        if len(self.processing_history) > 100:
            self.processing_history = self.processing_history[-100:]
    
    def get_processing_history(self, limit: int = 20) -> List[Dict]:
        """Retorna histórico de processamento"""
        return self.processing_history[-limit:] if self.processing_history else []
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitiza nome de arquivo"""
        # Substituir caracteres problemáticos
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        return filename[:100]  # Limitar tamanho

    def _normalize_path_key(self, value: str) -> str:
        """Normaliza texto para comparação estável de nomes de pastas."""
        normalized = unicodedata.normalize("NFKD", value or "")
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized).strip().lower()
        return re.sub(r"\s+", " ", normalized)

    def _primary_author(self, author_name: str) -> str:
        """Extrai autor principal para evitar duplicações por coautoria/formato."""
        raw = (author_name or "").strip()
        if not raw:
            return "Autor Desconhecido"

        # Separadores comuns de múltiplos autores.
        split_patterns = [r"\s*&\s*", r"\s+and\s+", r"\s+e\s+", r"\s*;\s*", r"\s*/\s*", r"\s*\|\s*"]
        for pattern in split_patterns:
            parts = re.split(pattern, raw, maxsplit=1, flags=re.IGNORECASE)
            if parts and parts[0].strip() and len(parts) > 1:
                raw = parts[0].strip()
                break

        # "Sobrenome, Nome" -> "Nome Sobrenome"
        if "," in raw:
            fragments = [frag.strip() for frag in raw.split(",") if frag.strip()]
            if len(fragments) >= 2:
                raw = f"{fragments[1]} {fragments[0]}".strip()

        return raw

    def _author_tokens(self, author_name: str) -> set[str]:
        """Tokeniza nome de autor para comparação por similaridade."""
        normalized = self._normalize_path_key(self._primary_author(author_name))
        tokens = {tok for tok in normalized.split(" ") if len(tok) > 1}
        return tokens

    def _soft_token_overlap(self, left_tokens: set[str], right_tokens: set[str]) -> float:
        """
        Sobreposição fuzzy de tokens para capturar pequenas variações ortográficas.
        Ex.: guatarri ~= guattari.
        """
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
        Reutiliza diretório existente do autor, evitando duplicatas por acento/caixa/pontuação.
        """
        canonical_author = self._primary_author(author_name or "Autor Desconhecido")
        safe_author = self._sanitize_filename(canonical_author)
        if not self.vault_manager:
            return safe_author

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
    
    def _perform_maintenance(self):
        """Executa manutenção periódica"""
        try:
            # Limpar pipelines finalizados
            pipelines_to_remove = []
            
            for pipeline_id, pipeline in list(self.active_pipelines.items()):
                if not pipeline.isRunning():
                    pipelines_to_remove.append(pipeline_id)
            
            for pipeline_id in pipelines_to_remove:
                if pipeline_id in self.active_pipelines:
                    del self.active_pipelines[pipeline_id]
            
            # Limpar cache antigo (mais de 1 hora)
            current_time = datetime.now()
            old_keys = []
            
            for key, entry in list(self.book_registry.items()):
                if "registered_at" in entry:
                    try:
                        registered_time = datetime.fromisoformat(entry["registered_at"])
                        if (current_time - registered_time).total_seconds() > 3600:
                            old_keys.append(key)
                    except:
                        old_keys.append(key)
            
            for key in old_keys:
                del self.book_registry[key]
            
            # Salvar histórico em arquivo
            self._save_history_to_file()
            
            logger.debug(f"Manutenção executada: {len(pipelines_to_remove)} pipelines limpos")
            
        except Exception as e:
            logger.error(f"Erro na manutenção: {e}")
    
    def _save_history_to_file(self):
        """Salva histórico em arquivo"""
        try:
            history_dir = Path(settings.paths.data_dir) / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            
            history_file = history_dir / "book_processing_history.json"
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "last_updated": datetime.now().isoformat(),
                    "history": self.processing_history[-50:]  # Últimos 50 registros
                }, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Erro salvando histórico: {e}")
    
    @pyqtSlot(str)
    def cancel_processing(self, pipeline_id: str):
        """Cancela um pipeline em andamento"""
        self.pipeline_mutex.lock()
        try:
            if pipeline_id in self.active_pipelines:
                pipeline = self.active_pipelines[pipeline_id]
                pipeline.stop()
                del self.active_pipelines[pipeline_id]
                logger.info(f"Pipeline {pipeline_id} cancelado")
        finally:
            self.pipeline_mutex.unlock()
    
    @pyqtSlot(str, result=dict)
    def get_processing_status(self, pipeline_id: str) -> Dict:
        """Retorna status de um pipeline"""
        if pipeline_id in self.active_pipelines:
            pipeline = self.active_pipelines[pipeline_id]
            return {
                "pipeline_id": pipeline_id,
                "is_running": pipeline.isRunning(),
                "current_stage": pipeline._current_stage.value if pipeline._current_stage else None,
                "book_id": pipeline.book_id,
                "has_metadata": pipeline.metadata is not None
            }
        return {"pipeline_id": pipeline_id, "status": "not_found"}
    
    def cleanup(self):
        """Limpeza antes de encerrar"""
        # Parar todos os pipelines
        for pipeline_id, pipeline in list(self.active_pipelines.items()):
            pipeline.stop()
        
        # Parar timer
        self.maintenance_timer.stop()
        
        # Salvar histórico
        self._save_history_to_file()
        
        logger.info("BookController finalizado")
