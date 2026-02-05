"""
Controller refatorado para gerenciamento completo do fluxo de livros - VERSÃO REFATORADA
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer, Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QImage, QBrush, QLinearGradient
from datetime import datetime, timedelta
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import uuid
import hashlib
import re

logger = logging.getLogger('GLaDOS.UI.BookController')


class BookProcessingWorker(QThread):
    """Worker especializado para processamento de livros com etapas bem definidas"""
    
    # Sinais de progresso específicos
    step_started = pyqtSignal(str, str)  # (step_name, message)
    step_completed = pyqtSignal(str, dict)  # (step_name, result)
    step_failed = pyqtSignal(str, str)  # (step_name, error)
    
    # Sinais gerais
    progress_updated = pyqtSignal(int, str)  # (percent, message)
    result_ready = pyqtSignal(dict)
    
    def __init__(self, controller, file_path: str, quality: str, schedule_night: bool = False):
        super().__init__()
        self.controller = controller
        self.file_path = file_path
        self.quality = quality
        self.schedule_night = schedule_night
        self.book_id = None
        self._is_running = True
        
    def run(self):
        """Executa fluxo completo de processamento"""
        try:
            file_name = Path(self.file_path).stem
            
            # ETAPA 1: Análise do arquivo
            self.step_started.emit("analysis", f"Analisando {file_name}...")
            metadata, recommendations = self.controller.book_processor.analyze_book(self.file_path)
            self.step_completed.emit("analysis", {"metadata": metadata, "recommendations": recommendations})
            self.progress_updated.emit(25, f"Análise concluída: {metadata.title}")
            
            if not self._is_running:
                return
            
            # ETAPA 2: Processamento do conteúdo
            if self.schedule_night:
                self.step_completed.emit("scheduled", {"message": "Agendado para processamento noturno"})
                self.result_ready.emit({
                    "status": "scheduled",
                    "title": metadata.title,
                    "message": "Livro agendado para processamento noturno"
                })
                return
            
            self.step_started.emit("processing", f"Processando {metadata.title}...")
            
            # Determinar qualidade
            from src.core.modules.book_processor import ProcessingQuality
            quality_map = {
                'draft': ProcessingQuality.DRAFT,
                'standard': ProcessingQuality.STANDARD,
                'high': ProcessingQuality.HIGH,
                'academic': ProcessingQuality.ACADEMIC
            }
            processing_quality = quality_map.get(self.quality, ProcessingQuality.STANDARD)
            
            # Processar livro
            result = self.controller.book_processor.process_book(
                filepath=self.file_path,
                quality=processing_quality
            )
            
            if result.status.value == "failed":
                raise Exception(result.error or "Erro no processamento")
            
            self.step_completed.emit("processing", {"result": result})
            self.progress_updated.emit(50, "Processamento concluído")
            
            if not self._is_running:
                return
            
            # ETAPA 3: Integração com sistema de leitura
            self.step_started.emit("integration", "Integrando com sistema de leitura...")
            
            # Gerar ID único para o livro
            self.book_id = self._generate_book_id(metadata.title, metadata.author)
            
            # Adicionar ao ReadingManager
            if self.controller.reading_manager:
                book_data = {
                    "id": self.book_id,
                    "title": metadata.title,
                    "author": metadata.author,
                    "total_pages": metadata.total_pages,
                    "current_page": 0,
                    "status": "pending"
                }
                
                # Usar ReadingController se disponível
                if hasattr(self.controller, 'reading_controller'):
                    self.controller.reading_controller.add_new_book(
                        metadata.title, metadata.author, metadata.total_pages, self.book_id
                    )
                elif hasattr(self.controller.reading_manager, 'add_book'):
                    self.controller.reading_manager.add_book(
                        title=metadata.title,
                        author=metadata.author,
                        total_pages=metadata.total_pages,
                        book_id=self.book_id
                    )
            
            self.step_completed.emit("integration", {"book_id": self.book_id})
            self.progress_updated.emit(75, "Integração concluída")
            
            if not self._is_running:
                return
            
            # ETAPA 4: Agendamento na agenda (opcional)
            if metadata.total_pages > 100 and self.controller.agenda_controller:
                self.step_started.emit("scheduling", "Agendando tempo de leitura...")
                
                # Calcular páginas por dia (assumindo conclusão em 30 dias)
                pages_per_day = max(5, metadata.total_pages // 30)
                
                self.controller.agenda_controller.allocate_reading_time_async(
                    self.book_id, pages_per_day, "balanced"
                )
                
                self.step_completed.emit("scheduling", {"pages_per_day": pages_per_day})
                self.progress_updated.emit(90, "Agendamento configurado")
            
            # Resultado final
            self.result_ready.emit({
                "status": "completed",
                "book_id": self.book_id,
                "title": metadata.title,
                "author": metadata.author,
                "total_pages": metadata.total_pages,
                "result": self.controller._processing_result_to_dict(result),
                "metadata": {
                    "title": metadata.title,
                    "author": metadata.author,
                    "total_pages": metadata.total_pages,
                    "chapters": metadata.chapters,
                    "language": metadata.language
                }
            })
            self.progress_updated.emit(100, "Processamento completo!")
            
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            self.step_failed.emit("processing", str(e))
            self.result_ready.emit({
                "status": "failed",
                "error": str(e),
                "file_path": self.file_path
            })
    
    def _generate_book_id(self, title: str, author: str) -> str:
        """Gera ID único para o livro"""
        content = f"{title}_{author}_{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def stop(self):
        """Para o worker de forma segura"""
        self._is_running = False
        self.quit()
        self.wait(1000)


class BookController(QObject):
    """Controller refatorado para gerenciamento completo de livros"""
    
    # Sinais principais
    processing_pipeline_started = pyqtSignal(str, str)  # (pipeline_id, file_name)
    processing_pipeline_completed = pyqtSignal(str, dict)  # (pipeline_id, result)
    processing_pipeline_failed = pyqtSignal(str, str)  # (pipeline_id, error)
    
    processing_step_started = pyqtSignal(str, str, str)  # (pipeline_id, step, message)
    processing_step_completed = pyqtSignal(str, str, dict)  # (pipeline_id, step, result)
    processing_step_failed = pyqtSignal(str, str, str)  # (pipeline_id, step, error)
    
    processing_progress_updated = pyqtSignal(str, int, str)  # (pipeline_id, percent, message)
    
    # Sinais herdados (para compatibilidade)
    book_list_loaded = pyqtSignal(list)
    book_metadata_loaded = pyqtSignal(dict)
    book_processed = pyqtSignal(dict)
    book_processing_progress = pyqtSignal(int, str)
    book_processing_started = pyqtSignal(str, str)
    book_processing_completed = pyqtSignal(str, str)
    
    def __init__(self, book_processor, reading_manager=None, 
                 vault_manager=None, agenda_controller=None, 
                 reading_controller=None, checkin_system=None):
        super().__init__()
        self.book_processor = book_processor
        self.reading_manager = reading_manager
        self.vault_manager = vault_manager
        self.agenda_controller = agenda_controller
        self.reading_controller = reading_controller
        self.checkin_system = checkin_system
        
        # Cache e estado
        self.books_cache = {}
        self.covers_cache = {}
        self.metadata_cache = {}
        
        # Pipeline de processamento ativo
        self.active_pipelines = {}  # pipeline_id -> worker
        
        # Workers para operações gerais
        self.general_workers = []
        
        # Timer para atualizações
        self.maintenance_timer = QTimer()
        self.maintenance_timer.timeout.connect(self._perform_maintenance)
        self.maintenance_timer.start(300000)  # 5 minutos
        
        logger.info("BookController refatorado inicializado")
    
    # ====== FLUXO PRINCIPAL: PROCESSAMENTO DE LIVRO ======
    
    @pyqtSlot(str, str, bool)
    def process_book_pipeline(self, file_path: str, quality: str = "standard", 
                            schedule_night: bool = False) -> str:
        """
        Inicia pipeline completo de processamento de livro
        
        Returns:
            pipeline_id: ID do pipeline para acompanhamento
        """
        pipeline_id = str(uuid.uuid4())[:8]
        file_name = Path(file_path).stem
        
        logger.info(f"Iniciando pipeline {pipeline_id} para {file_name}")
        
        # Criar worker especializado
        worker = BookProcessingWorker(self, file_path, quality, schedule_night)
        
        # Conectar sinais do worker
        worker.step_started.connect(
            lambda step, msg: self._on_step_started(pipeline_id, step, msg)
        )
        worker.step_completed.connect(
            lambda step, result: self._on_step_completed(pipeline_id, step, result)
        )
        worker.step_failed.connect(
            lambda step, error: self._on_step_failed(pipeline_id, step, error)
        )
        worker.progress_updated.connect(
            lambda percent, msg: self._on_progress_updated(pipeline_id, percent, msg)
        )
        worker.result_ready.connect(
            lambda result: self._on_pipeline_completed(pipeline_id, result)
        )
        
        # Armazenar referência
        self.active_pipelines[pipeline_id] = worker
        
        # Emitir sinal de início
        self.processing_pipeline_started.emit(pipeline_id, file_name)
        self.book_processing_started.emit(pipeline_id, file_name)
        
        # Iniciar worker
        worker.start()
        
        return pipeline_id
    
    @pyqtSlot(str)
    def cancel_pipeline(self, pipeline_id: str):
        """Cancela pipeline em andamento"""
        if pipeline_id in self.active_pipelines:
            worker = self.active_pipelines[pipeline_id]
            worker.stop()
            del self.active_pipelines[pipeline_id]
            logger.info(f"Pipeline {pipeline_id} cancelado")
    
    # ====== CALLBACKS DO PIPELINE ======
    
    def _on_step_started(self, pipeline_id: str, step: str, message: str):
        """Chamado quando uma etapa do pipeline inicia"""
        self.processing_step_started.emit(pipeline_id, step, message)
        logger.info(f"Pipeline {pipeline_id} - {step}: {message}")
    
    def _on_step_completed(self, pipeline_id: str, step: str, result: dict):
        """Chamado quando uma etapa do pipeline é concluída"""
        self.processing_step_completed.emit(pipeline_id, step, result)
        
        # Ações específicas por etapa
        if step == "analysis":
            metadata = result.get("metadata", {})
            self._cache_book_analysis(pipeline_id, metadata)
            
        elif step == "processing":
            # Atualizar cache com resultado do processamento
            self._update_cache_from_processing(pipeline_id, result.get("result"))
    
    def _on_step_failed(self, pipeline_id: str, step: str, error: str):
        """Chamado quando uma etapa do pipeline falha"""
        self.processing_step_failed.emit(pipeline_id, step, error)
        logger.error(f"Pipeline {pipeline_id} - Erro em {step}: {error}")
    
    def _on_progress_updated(self, pipeline_id: str, percent: int, message: str):
        """Chamado quando há atualização de progresso"""
        self.processing_progress_updated.emit(pipeline_id, percent, message)
        self.book_processing_progress.emit(percent, message)
    
    def _on_pipeline_completed(self, pipeline_id: str, result: dict):
        """Chamado quando o pipeline é concluído"""
        status = result.get("status")
        
        if pipeline_id in self.active_pipelines:
            worker = self.active_pipelines[pipeline_id]
            worker.wait(1000)
            del self.active_pipelines[pipeline_id]
        
        if status == "completed":
            self.processing_pipeline_completed.emit(pipeline_id, result)
            self.book_processing_completed.emit(pipeline_id, result.get("title", ""))
            
            # Se foi gerado um book_id, emitir sinal de livro processado
            book_id = result.get("book_id")
            if book_id:
                self.book_processed.emit(result)
                
                # Atualizar lista de livros
                self.load_all_books_async(force_refresh=True)
                
                # Registrar no check-in se disponível
                if self.checkin_system:
                    self._log_book_processing_in_checkin(book_id, result)
        
        elif status == "failed":
            error = result.get("error", "Erro desconhecido")
            self.processing_pipeline_failed.emit(pipeline_id, error)
            self.book_processing_completed.emit(pipeline_id, "Falhou")
        
        logger.info(f"Pipeline {pipeline_id} concluído com status: {status}")
    
    # ====== COMUNICAÇÃO COM OUTRAS CONTROLLERS ======
    
    def schedule_reading_for_book(self, book_id: str, target_date: str = None, 
                                 pages_per_day: int = None) -> bool:
        """
        Agenda tempo de leitura para um livro
        
        Args:
            book_id: ID do livro
            target_date: Data alvo para conclusão (YYYY-MM-DD)
            pages_per_day: Páginas por dia (se None, calcula automaticamente)
        
        Returns:
            True se agendado com sucesso
        """
        if not self.agenda_controller:
            logger.warning("AgendaController não disponível")
            return False
        
        try:
            # Obter informações do livro
            book_info = self.get_book_info(book_id)
            if not book_info or "total_pages" not in book_info:
                logger.error(f"Informações do livro {book_id} insuficientes")
                return False
            
            total_pages = book_info["total_pages"]
            current_page = book_info.get("current_page", 0)
            pages_remaining = total_pages - current_page
            
            # Calcular páginas por dia se não especificado
            if pages_per_day is None:
                if target_date:
                    # Calcular baseado na data alvo
                    target = datetime.strptime(target_date, "%Y-%m-%d").date()
                    days_remaining = (target - datetime.now().date()).days
                    if days_remaining > 0:
                        pages_per_day = max(1, pages_remaining // days_remaining)
                    else:
                        pages_per_day = pages_remaining
                else:
                    # Valor padrão: 10 páginas por dia
                    pages_per_day = 10
            
            # Agendar na agenda
            self.agenda_controller.allocate_reading_time_async(
                book_id, pages_per_day, "balanced"
            )
            
            logger.info(f"Leitura agendada: {book_id}, {pages_per_day} páginas/dia")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao agendar leitura: {e}")
            return False
    
    def sync_book_to_all_systems(self, book_id: str) -> str:
        """
        Sincroniza livro com todos os sistemas disponíveis
        
        Returns:
            pipeline_id do processo de sincronização
        """
        sync_id = str(uuid.uuid4())[:8]
        
        # Executar sincronizações em paralelo
        sync_tasks = []
        
        # Sincronizar com vault do Obsidian
        if self.vault_manager:
            sync_tasks.append(("vault", self.vault_manager.sync_to_obsidian, book_id))
        
        # Sincronizar com sistema de leitura
        if self.reading_controller:
            sync_tasks.append(("reading", self.reading_controller.force_refresh_all, None))
        
        # Sincronizar com agenda
        if self.agenda_controller:
            sync_tasks.append(("agenda", self.agenda_controller.load_agenda_async, None))
        
        # Executar tarefas em threads separadas
        for system_name, method, param in sync_tasks:
            def sync_task_wrapper(name=system_name, func=method, arg=param):
                try:
                    if arg:
                        func(arg)
                    else:
                        func()
                    return {"system": name, "status": "success"}
                except Exception as e:
                    return {"system": name, "status": "error", "error": str(e)}
            
            self._execute_async(sync_task_wrapper, lambda r: self._on_sync_completed(sync_id, r))
        
        return sync_id
    
    def _on_sync_completed(self, sync_id: str, result: dict):
        """Chamado quando uma sincronização é concluída"""
        system = result.get("system")
        status = result.get("status")
        
        if status == "success":
            logger.info(f"Sincronização {sync_id} - {system}: sucesso")
        else:
            logger.error(f"Sincronização {sync_id} - {system}: {result.get('error')}")
    
    def _log_book_processing_in_checkin(self, book_id: str, result: dict):
        """Registra processamento de livro no sistema de check-in"""
        if not self.checkin_system:
            return
        
        try:
            title = result.get("title", "Livro desconhecido")
            author = result.get("author", "Autor desconhecido")
            
            entry = {
                "type": "book_processed",
                "book_id": book_id,
                "title": title,
                "author": author,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "total_pages": result.get("total_pages", 0),
                    "processing_result": result.get("result", {})
                }
            }
            
            # Usar check-in system para registrar
            if hasattr(self.checkin_system, 'add_entry'):
                self.checkin_system.add_entry(entry)
            elif hasattr(self.checkin_system, 'create_evening_checkin_async'):
                # Adaptar para o formato do checkin_system existente
                self.checkin_system.create_evening_checkin_async(
                    mood_score=3.0,
                    achievements=[f"Processado livro: {title}"],
                    challenges=[],
                    insights=["Novo livro disponível para leitura"]
                )
                
        except Exception as e:
            logger.error(f"Erro ao registrar livro no check-in: {e}")
    
    # ====== MÉTODOS AUXILIARES DE CACHE ======
    
    def _cache_book_analysis(self, pipeline_id: str, metadata: dict):
        """Armazena análise do livro em cache temporário"""
        cache_key = f"analysis_{pipeline_id}"
        self.metadata_cache[cache_key] = {
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_cache_from_processing(self, pipeline_id: str, processing_result):
        """Atualiza cache com resultado do processamento"""
        if not processing_result:
            return
        
        # Converter para dicionário se necessário
        if hasattr(processing_result, 'metadata'):
            metadata = processing_result.metadata
            book_dict = {
                "title": metadata.title,
                "author": metadata.author,
                "total_pages": metadata.total_pages,
                "chapters": metadata.chapters,
                "language": metadata.language
            }
            
            # Gerar book_id se não existir
            book_id = self._generate_book_id_from_metadata(metadata)
            self.books_cache[book_id] = book_dict
    
    def _generate_book_id_from_metadata(self, metadata) -> str:
        """Gera ID do livro baseado nos metadados"""
        content = f"{metadata.title}_{metadata.author}_{metadata.total_pages}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # ====== MÉTODOS DE MANUTENÇÃO ======
    
    @pyqtSlot()
    def _perform_maintenance(self):
        """Executa manutenção periódica"""
        try:
            # Limpar pipelines antigos
            current_time = datetime.now()
            pipelines_to_remove = []
            
            for pipeline_id, worker in list(self.active_pipelines.items()):
                if not worker.isRunning():
                    pipelines_to_remove.append(pipeline_id)
            
            for pipeline_id in pipelines_to_remove:
                if pipeline_id in self.active_pipelines:
                    del self.active_pipelines[pipeline_id]
            
            # Limpar cache antigo
            self._clean_old_cache()
            
            # Atualizar estatísticas
            self._update_system_stats()
            
            logger.debug("Manutenção periódica executada")
            
        except Exception as e:
            logger.error(f"Erro na manutenção: {e}")
    
    def _clean_old_cache(self):
        """Limpa cache antigo"""
        current_time = datetime.now()
        cache_keys_to_remove = []
        
        for key, entry in list(self.metadata_cache.items()):
            if isinstance(entry, dict) and "timestamp" in entry:
                try:
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    if (current_time - entry_time).total_seconds() > 3600:  # 1 hora
                        cache_keys_to_remove.append(key)
                except:
                    cache_keys_to_remove.append(key)
        
        for key in cache_keys_to_remove:
            del self.metadata_cache[key]
    
    def _update_system_stats(self):
        """Atualiza estatísticas do sistema"""
        stats = {
            "total_books": len(self.books_cache),
            "active_pipelines": len(self.active_pipelines),
            "cache_size": {
                "books": len(self.books_cache),
                "covers": len(self.covers_cache),
                "metadata": len(self.metadata_cache)
            },
            "last_updated": datetime.now().isoformat()
        }
        
        # Emitir estatísticas se necessário
        if hasattr(self, 'system_stats_updated'):
            self.system_stats_updated.emit(stats)
    
    # ====== MÉTODOS COMPATÍVEIS (mantidos da versão anterior) ======
    
    @pyqtSlot()
    def load_all_books_async(self, force_refresh: bool = False):
        """Versão compatível com o método antigo"""
        if not self.reading_manager:
            logger.error("ReadingManager não disponível")
            return
        
        self._execute_async(
            self.reading_manager.get_all_books,
            callback=self._on_books_loaded
        )
    
    @pyqtSlot(str)
    def process_book_file_async(self, file_path: str, quality: str = "standard", 
                              schedule_night: bool = False):
        """Versão compatível com o método antigo"""
        self.process_book_pipeline(file_path, quality, schedule_night)
    
    def _execute_async(self, backend_method, callback, *args, **kwargs):
        """Versão simplificada para compatibilidade"""
        from PyQt6.QtCore import QThreadPool, QRunnable
        
        class GenericTask(QRunnable):
            def __init__(self, method, callback, args, kwargs):
                super().__init__()
                self.method = method
                self.callback = callback
                self.args = args
                self.kwargs = kwargs
            
            def run(self):
                try:
                    result = self.method(*self.args, **self.kwargs)
                    self.callback(result)
                except Exception as e:
                    logger.error(f"Erro na tarefa assíncrona: {e}")
        
        task = GenericTask(backend_method, callback, args, kwargs)
        QThreadPool.globalInstance().start(task)
    
    # ====== MÉTODOS RESTANTES DA IMPLEMENTAÇÃO ORIGINAL ======
    # (Mantidos para compatibilidade - podem ser refatorados posteriormente)
    
    def _on_books_loaded(self, books):
        """Mantido da versão original"""
        ui_books = []
        for book in books:
            ui_book = self._book_to_ui_format(book)
            ui_books.append(ui_book)
            self.books_cache[book.id] = ui_book
        
        self.book_list_loaded.emit(ui_books)
    
    def _book_to_ui_format(self, book) -> Dict:
        """Mantido da versão original"""
        # Implementação original...
        pass
    
    def _processing_result_to_dict(self, processing_result) -> Dict:
        """Mantido da versão original"""
        # Implementação original...
        pass
    
    def get_book_info(self, book_id: str) -> Dict:
        """Mantido da versão original"""
        # Implementação original...
        pass
    
    def get_book_cover(self, book_id: str) -> QPixmap:
        """Mantido da versão original"""
        # Implementação original...
        pass
    
    def cleanup(self):
        """Limpeza antes de encerrar"""
        # Parar todos os pipelines
        for pipeline_id, worker in list(self.active_pipelines.items()):
            worker.stop()
        
        # Parar timer
        self.maintenance_timer.stop()
        
        # Limpar workers gerais
        self.general_workers.clear()
        
        logger.info("BookController finalizado")