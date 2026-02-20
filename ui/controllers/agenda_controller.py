"""
Controller refatorado para agenda com integração robusta e tratamento de erros
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, QDateTime, Qt, QThread, QMutex
from PyQt6.QtGui import QPixmap, QPainter, QColor
from datetime import datetime, timedelta, date
import json
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
import uuid
from pathlib import Path
from functools import wraps

logger = logging.getLogger('GLaDOS.UI.AgendaController')


class SchedulingWorker(QThread):
    """Worker especializado para operações de agendamento"""
    
    scheduling_result = pyqtSignal(dict)  # Resultado do agendamento
    scheduling_progress = pyqtSignal(int, str)  # (percent, message)
    scheduling_failed = pyqtSignal(str, str)  # (book_id, error)
    
    def __init__(self, agenda_manager, operation: str, **kwargs):
        super().__init__()
        self.agenda_manager = agenda_manager
        self.operation = operation
        self.kwargs = kwargs
        self._is_running = True
        
        # Validação específica por operação
        self.valid_operations = {
            'allocate_reading': self._allocate_reading,
            'emergency_mode': self._emergency_mode,
            'find_slots': self._find_slots,
            'transition_review': self._transition_review
        }
    
    def run(self):
        """Executa operação de agendamento"""
        try:
            if self.operation not in self.valid_operations:
                raise ValueError(f"Operação inválida: {self.operation}")
            
            # Executar operação
            operation_func = self.valid_operations[self.operation]
            result = operation_func()
            
            if self._is_running:
                self.scheduling_result.emit(result)
                
        except Exception as e:
            logger.error(f"Erro no worker de agendamento: {e}")
            if self._is_running:
                error_msg = str(e)
                book_id = self.kwargs.get('book_id', 'unknown')
                self.scheduling_failed.emit(book_id, error_msg)
    
    def _allocate_reading(self) -> Dict:
        """Operação de alocação de leitura"""
        book_id = self.kwargs.get('book_id')
        pages_per_day = self.kwargs.get('pages_per_day', 10.0)
        strategy = self.kwargs.get('strategy', 'balanced')
        
        # Validações
        if not book_id or not book_id.strip():
            return {"error": "ID do livro inválido", "book_id": book_id}
        
        # Verificar existência do livro
        self.scheduling_progress.emit(10, "Verificando livro...")
        book_progress = self.agenda_manager.reading_manager.get_reading_progress(book_id)
        
        if not book_progress:
            return {"error": f"Livro {book_id} não encontrado", "book_id": book_id}
        
        # Validar páginas por dia
        if pages_per_day <= 0:
            pages_per_day = 10.0
        
        # Executar alocação
        self.scheduling_progress.emit(30, "Calculando alocação...")
        try:
            allocation_result = self.agenda_manager.allocate_reading_time(
                book_id=book_id,
                pages_per_day=pages_per_day,
                reading_speed=10.0,  # Padrão
                days_off=[6],  # Domingo
                max_daily_minutes=180,
                strategy=strategy
            )
            
            # Verificar erro no resultado
            if "error" in allocation_result:
                return {"error": allocation_result["error"], "book_id": book_id}
            
            # Adicionar metadados
            allocation_result["book_id"] = book_id
            allocation_result["pages_per_day"] = pages_per_day
            allocation_result["strategy"] = strategy
            allocation_result["timestamp"] = datetime.now().isoformat()
            
            self.scheduling_progress.emit(100, "Alocação concluída")
            return allocation_result
            
        except Exception as e:
            logger.error(f"Erro na alocação de {book_id}: {e}")
            return {"error": str(e), "book_id": book_id}
    
    def _emergency_mode(self) -> Dict:
        """Operação de modo emergência"""
        # Implementação existente...
        pass
    
    def _find_slots(self) -> Dict:
        """Operação de busca de slots"""
        # Implementação existente...
        pass
    
    def _transition_review(self) -> Dict:
        """Operação de transição para revisão"""
        # Implementação existente...
        pass
    
    def stop(self):
        """Para o worker de forma segura"""
        self._is_running = False
        self.quit()
        self.wait(1000)


class AgendaController(QObject):
    """Controller robusto para integração da agenda"""
    
    # === SINAIS PRINCIPAIS ===
    # Agenda
    agenda_loaded = pyqtSignal(list)
    agenda_updated = pyqtSignal(str, list)  # (date_str, events)
    weekly_review_loaded = pyqtSignal(dict)
    
    # Eventos
    event_added = pyqtSignal(dict)
    event_updated = pyqtSignal(str, dict)
    event_deleted = pyqtSignal(str)
    event_completed = pyqtSignal(str, bool)
    
    # Leitura e agendamento
    reading_scheduled = pyqtSignal(str, dict)  # (book_id, result)
    reading_scheduling_failed = pyqtSignal(str, str, dict)  # (book_id, error, context)
    reading_allocation_progress = pyqtSignal(str, int, str)  # (book_id, percent, message)
    review_plan_scheduled = pyqtSignal(str, dict)  # (book_id, result)
    review_plan_failed = pyqtSignal(str, str, dict)  # (book_id, error, context)
    
    # Otimizações e prazos
    deadlines_loaded = pyqtSignal(list)
    optimizations_loaded = pyqtSignal(list)
    free_slots_found = pyqtSignal(str, list)  # (date_str, slots)
    
    # Sistema
    productivity_insights_loaded = pyqtSignal(dict)
    emergency_mode_activated = pyqtSignal(dict)
    review_transitioned = pyqtSignal(dict)
    routine_preferences_updated = pyqtSignal(dict)
    
    # === CONSTANTES ===
    CACHE_TTL_SECONDS = 300
    REFRESH_INTERVAL_MS = 60000
    DEFAULT_WORK_DAY_HOURS = (8, 22)
    MAX_SCHEDULING_ATTEMPTS = 3
    
    def __init__(self, agenda_manager, checkin_system=None):
        super().__init__()
        self.agenda_manager = agenda_manager
        self.checkin_system = checkin_system
        
        # Cache com mutex
        self.event_cache: Dict[str, Dict] = {}
        self.day_cache: Dict[str, List[Dict]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.cache_mutex = QMutex()
        
        # Workers e operações ativas
        self.active_workers: Dict[str, SchedulingWorker] = {}
        self.scheduling_operations: Dict[str, Dict] = {}  # book_id -> operation_info
        self.operations_mutex = QMutex()
        
        # Timer para atualizações
        self._setup_timers()
        
        # Diagnóstico
        self.scheduling_stats = {
            "successful": 0,
            "failed": 0,
            "last_success": None,
            "last_failure": None
        }
        
        logger.info("AgendaController robusto inicializado")
    
    # ====== CONFIGURAÇÃO ======
    
    def _setup_timers(self):
        """Configura timers para atualizações automáticas"""
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self._auto_refresh)
        self.auto_refresh_timer.start(self.REFRESH_INTERVAL_MS)
        
        # Timer para limpeza de cache
        self.cache_cleanup_timer = QTimer()
        self.cache_cleanup_timer.timeout.connect(self._cleanup_old_cache)
        self.cache_cleanup_timer.start(300000)  # 5 minutos

    def _auto_refresh(self):
        """Refresh periódico leve para manter cache/estado da agenda atualizados."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            self.load_agenda(today)
        except Exception as e:
            logger.debug(f"Agenda auto-refresh ignorado por erro não fatal: {e}")
    
    # ====== AGENDAMENTO DE LEITURA (MÉTODO PRINCIPAL) ======
    
    @pyqtSlot(str, float, str)
    def schedule_reading(self, book_id: str, pages_per_day: float = None, 
                        strategy: str = "balanced", retry_on_failure: bool = True) -> str:
        """
        Agenda leitura de forma robusta com retry e validação
        
        Args:
            book_id: ID do livro
            pages_per_day: Páginas por dia (calcula automaticamente se None)
            strategy: Estratégia de alocação
            retry_on_failure: Se True, tenta novamente em caso de falha
            
        Returns:
            operation_id: ID da operação para acompanhamento
        """
        operation_id = str(uuid.uuid4())[:8]
        
        # Validar livro
        validation_result = self._validate_book_for_scheduling(book_id)
        if not validation_result["valid"]:
            error_msg = validation_result["error"]
            logger.error(f"Validação falhou para {book_id}: {error_msg}")
            
            self.reading_scheduling_failed.emit(
                book_id, error_msg, {"operation_id": operation_id}
            )
            return operation_id
        
        # Calcular páginas por dia se necessário
        if pages_per_day is None or pages_per_day <= 0:
            pages_per_day = self._calculate_optimal_pages_per_day(
                validation_result["total_pages"],
                validation_result["current_page"]
            )
        
        # Registrar operação
        self.operations_mutex.lock()
        try:
            self.scheduling_operations[book_id] = {
                "operation_id": operation_id,
                "started_at": datetime.now().isoformat(),
                "attempts": 0,
                "max_attempts": self.MAX_SCHEDULING_ATTEMPTS if retry_on_failure else 1,
                "status": "pending",
                "pages_per_day": pages_per_day,
                "strategy": strategy
            }
        finally:
            self.operations_mutex.unlock()
        
        # Executar agendamento
        self._execute_scheduling_operation(book_id, operation_id, pages_per_day, strategy)
        
        return operation_id

    @pyqtSlot(str, int, float, int, result=dict)
    def schedule_review_plan(
        self,
        book_id: str,
        plan_days: int = 7,
        hours_per_session: float = 1.0,
        sessions_per_day: int = 1,
    ) -> Dict:
        """
        Agenda plano de revisão para um livro concluído (ou em conclusão).
        """
        if not self.agenda_manager or not hasattr(self.agenda_manager, "create_review_plan"):
            error = "AgendaManager não suporta criação de plano de revisão."
            context = {"book_id": book_id, "timestamp": datetime.now().isoformat()}
            self.review_plan_failed.emit(book_id, error, context)
            return {"error": error}

        try:
            result = self.agenda_manager.create_review_plan(
                book_id=book_id,
                plan_days=plan_days,
                hours_per_session=hours_per_session,
                sessions_per_day=sessions_per_day,
            )
        except Exception as exc:
            error = str(exc)
            context = {"book_id": book_id, "timestamp": datetime.now().isoformat()}
            self.review_plan_failed.emit(book_id, error, context)
            logger.error(f"Falha ao criar plano de revisão para {book_id}: {exc}")
            return {"error": error}

        if isinstance(result, dict) and result.get("error"):
            error = str(result.get("error"))
            context = {
                "book_id": book_id,
                "timestamp": datetime.now().isoformat(),
                "result": result,
            }
            self.review_plan_failed.emit(book_id, error, context)
            return result

        self._invalidate_agenda_cache()
        self.review_plan_scheduled.emit(book_id, result)
        self.review_transitioned.emit(result if isinstance(result, dict) else {})
        self.load_agenda_async()
        return result
    
    def _validate_book_for_scheduling(self, book_id: str) -> Dict:
        """Valida livro para agendamento"""
        result = {
            "valid": False,
            "book_id": book_id,
            "error": None,
            "total_pages": 0,
            "current_page": 0
        }
        
        try:
            # Verificar se livro existe no ReadingManager
            book_progress = self.agenda_manager.reading_manager.get_reading_progress(book_id)
            if not book_progress:
                result["error"] = f"Livro {book_id} não encontrado no sistema"
                return result
            
            # Extrair informações
            result["title"] = book_progress.get("title", "Desconhecido")
            result["total_pages"] = book_progress.get("total_pages", 0)
            result["current_page"] = book_progress.get("current_page", 0)
            
            # Validar páginas
            if result["total_pages"] <= 0:
                result["error"] = "Número total de páginas inválido"
                return result
            
            # Verificar se já está concluído
            if result["current_page"] >= result["total_pages"]:
                result["error"] = "Livro já concluído"
                return result
            
            # Verificar slots disponíveis
            today = datetime.now().strftime("%Y-%m-%d")
            free_slots = self.agenda_manager.find_free_slots(
                today, duration_minutes=60, start_hour=8, end_hour=22
            )
            
            if not free_slots:
                result["warning"] = "Nenhum slot disponível hoje"
                # Não falha, apenas avisa
            
            result["valid"] = True
            return result
            
        except Exception as e:
            result["error"] = f"Erro na validação: {str(e)}"
            logger.error(f"Erro na validação de {book_id}: {e}")
            return result
    
    def _calculate_optimal_pages_per_day(self, total_pages: int, current_page: int = 0) -> float:
        """Calcula páginas por dia ótimas baseadas no livro"""
        remaining_pages = total_pages - current_page
        
        if remaining_pages <= 0:
            return 0
        
        # Estratégia: completar em aproximadamente 30 dias
        base_pages = remaining_pages / 30
        
        # Ajustar baseado na complexidade estimada
        if total_pages < 150:
            return max(10, base_pages)  # Livros curtos: mínimo 10 páginas/dia
        elif total_pages < 400:
            return max(8, base_pages)   # Livros médios: mínimo 8 páginas/dia
        else:
            return max(5, base_pages)   # Livros longos: mínimo 5 páginas/dia
    
    def _execute_scheduling_operation(self, book_id: str, operation_id: str, 
                                     pages_per_day: float, strategy: str):
        """Executa operação de agendamento em worker separado"""
        # Criar worker
        worker = SchedulingWorker(
            agenda_manager=self.agenda_manager,
            operation='allocate_reading',
            book_id=book_id,
            pages_per_day=pages_per_day,
            strategy=strategy
        )
        
        # Atualizar status da operação
        self.operations_mutex.lock()
        try:
            if book_id in self.scheduling_operations:
                self.scheduling_operations[book_id]["status"] = "running"
                self.scheduling_operations[book_id]["attempts"] += 1
                self.scheduling_operations[book_id]["worker_id"] = id(worker)
        finally:
            self.operations_mutex.unlock()
        
        # Conectar sinais do worker
        worker.scheduling_result.connect(
            lambda result: self._on_scheduling_result(book_id, operation_id, result)
        )
        worker.scheduling_progress.connect(
            lambda percent, msg: self._on_scheduling_progress(book_id, percent, msg)
        )
        worker.scheduling_failed.connect(
            lambda bid, error: self._on_scheduling_failed(bid, error, operation_id)
        )
        worker.finished.connect(
            lambda: self._remove_worker(book_id, worker)
        )
        
        # Armazenar worker
        self.active_workers[operation_id] = worker
        
        # Iniciar worker
        worker.start()
        
        logger.info(f"Agendamento iniciado para {book_id}: {pages_per_day} páginas/dia")
    
    # ====== CALLBACKS DE AGENDAMENTO ======
    
    def _on_scheduling_result(self, book_id: str, operation_id: str, result: Dict):
        """Processa resultado bem-sucedido do agendamento"""
        # Atualizar estatísticas
        self.scheduling_stats["successful"] += 1
        self.scheduling_stats["last_success"] = datetime.now().isoformat()
        
        # Atualizar status da operação
        self.operations_mutex.lock()
        try:
            if book_id in self.scheduling_operations:
                self.scheduling_operations[book_id].update({
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "result": result
                })
                # Operação concluída: remover para não acumular estado indefinidamente.
                self.scheduling_operations.pop(book_id, None)
        finally:
            self.operations_mutex.unlock()
        
        # Invalidar cache da agenda
        self._invalidate_agenda_cache()
        
        # Emitir sinais
        self.reading_scheduled.emit(book_id, result)
        
        # Se houve criação de eventos, recarregar agenda
        if result.get("total_sessions", 0) > 0:
            self.load_agenda_async()
        
        logger.info(f"Agendamento concluído para {book_id}: {result.get('total_sessions', 0)} sessões")
    
    def _on_scheduling_progress(self, book_id: str, percent: int, message: str):
        """Processa progresso do agendamento"""
        self.reading_allocation_progress.emit(book_id, percent, message)
    
    def _on_scheduling_failed(self, book_id: str, error: str, operation_id: str):
        """Processa falha no agendamento"""
        # Atualizar estatísticas
        self.scheduling_stats["failed"] += 1
        self.scheduling_stats["last_failure"] = datetime.now().isoformat()
        
        self.operations_mutex.lock()
        try:
            if book_id in self.scheduling_operations:
                operation = self.scheduling_operations[book_id]
                operation["status"] = "failed"
                operation["error"] = error
                operation["failed_at"] = datetime.now().isoformat()
                
                # Verificar se deve tentar novamente
                if (operation["attempts"] < operation["max_attempts"] and 
                    "worker_id" in operation):
                    
                    # Tentar novamente após delay
                    QTimer.singleShot(2000, lambda: self._retry_scheduling(book_id))
                    
                    logger.warning(f"Tentando novamente agendamento para {book_id} "
                                 f"(tentativa {operation['attempts'] + 1})")
                    
                    return
        finally:
            self.operations_mutex.unlock()
        
        # Emitir sinal de falha final
        context = {
            "operation_id": operation_id,
            "book_id": book_id,
            "timestamp": datetime.now().isoformat()
        }
        
        self.reading_scheduling_failed.emit(book_id, error, context)
        self.operations_mutex.lock()
        try:
            # Falha final: remover para evitar retenção de contexto de erro antigo.
            self.scheduling_operations.pop(book_id, None)
        finally:
            self.operations_mutex.unlock()
        logger.error(f"Agendamento falhou para {book_id}: {error}")
    
    def _retry_scheduling(self, book_id: str):
        """Tenta novamente o agendamento"""
        self.operations_mutex.lock()
        try:
            if book_id in self.scheduling_operations:
                operation = self.scheduling_operations[book_id]
                
                # Re-executar operação
                self._execute_scheduling_operation(
                    book_id=book_id,
                    operation_id=operation["operation_id"],
                    pages_per_day=operation["pages_per_day"],
                    strategy=operation["strategy"]
                )
        finally:
            self.operations_mutex.unlock()
    
    # ====== MÉTODOS DE GERENCIAMENTO DE WORKERS ======
    
    def _remove_worker(self, book_id: str, worker: SchedulingWorker):
        """Remove worker da lista de ativos"""
        try:
            # Encontrar operation_id pelo worker
            operation_id = None
            for op_id, w in self.active_workers.items():
                if w == worker:
                    operation_id = op_id
                    break
            
            if operation_id:
                del self.active_workers[operation_id]
                worker.deleteLater()
                
        except Exception as e:
            logger.error(f"Erro ao remover worker: {e}")
    
    # ====== MÉTODOS COMPATÍVEIS (para integração com outros controllers) ======
    
    @pyqtSlot(str, float, str)
    def allocate_reading_time_async(self, book_id: str, pages_per_day: float,
                                  strategy: str = "balanced"):
        """Método compatível para integração com BookController"""
        return self.schedule_reading(book_id, pages_per_day, strategy)
    
    @pyqtSlot(str, float, str, result=dict)
    def allocate_reading_time(self, book_id: str, pages_per_day: float,
                            strategy: str = "balanced") -> Dict:
        """Versão síncrona para uso direto"""
        # Usar evento loop para sincronizar
        from PyQt6.QtCore import QEventLoop
        
        result_container = {"result": None}
        event_loop = QEventLoop()
        operation_id = None
        
        def on_scheduled(bid, result):
            if bid == book_id:
                result_container["result"] = result
                event_loop.quit()
        
        def on_failed(bid, error, context):
            if bid == book_id:
                result_container["result"] = {"error": error, "context": context}
                event_loop.quit()
        
        # Conectar sinais temporariamente
        self.reading_scheduled.connect(on_scheduled)
        self.reading_scheduling_failed.connect(on_failed)
        
        # Iniciar agendamento
        operation_id = self.schedule_reading(book_id, pages_per_day, strategy, False)
        
        # Aguardar resultado (timeout de 15 segundos)
        QTimer.singleShot(15000, event_loop.quit)
        event_loop.exec()
        
        # Desconectar sinais
        self.reading_scheduled.disconnect(on_scheduled)
        self.reading_scheduling_failed.disconnect(on_failed)
        
        return result_container.get("result", {"error": "Timeout no agendamento"})
    
    # ====== MÉTODOS DE DIAGNÓSTICO ======
    
    @pyqtSlot(str, result=dict)
    def diagnose_scheduling(self, book_id: str) -> Dict:
        """Diagnóstico completo do fluxo de agendamento"""
        result = {
            "book_id": book_id,
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "errors": [],
            "recommendations": [],
            "can_schedule": False
        }
        
        try:
            # 1. Verificar existência do livro
            book_progress = self.agenda_manager.reading_manager.get_reading_progress(book_id)
            if book_progress:
                result["checks"].append({
                    "check": "livro_existe",
                    "status": "ok",
                    "data": {
                        "title": book_progress.get("title"),
                        "total_pages": book_progress.get("total_pages"),
                        "current_page": book_progress.get("current_page")
                    }
                })
            else:
                result["errors"].append("Livro não encontrado no ReadingManager")
                return result
            
            # 2. Verificar se já está agendado
            if book_id in self.scheduling_operations:
                operation = self.scheduling_operations[book_id]
                result["checks"].append({
                    "check": "ja_agendado",
                    "status": "warning",
                    "data": {
                        "status": operation.get("status"),
                        "attempts": operation.get("attempts"),
                        "started_at": operation.get("started_at")
                    }
                })
            
            # 3. Verificar slots disponíveis
            today = datetime.now().strftime("%Y-%m-%d")
            free_slots = self.agenda_manager.find_free_slots(
                today, duration_minutes=60, start_hour=8, end_hour=22
            )
            
            result["checks"].append({
                "check": "slots_disponiveis",
                "status": "ok" if free_slots else "warning",
                "data": f"{len(free_slots)} slots hoje"
            })
            
            # 4. Verificar agenda atual
            today_events = self.agenda_manager.get_day_events(today)
            result["checks"].append({
                "check": "agenda_atual",
                "status": "ok",
                "data": f"{len(today_events)} eventos hoje"
            })
            
            # 5. Verificar estatísticas do sistema
            result["checks"].append({
                "check": "estatisticas_sistema",
                "status": "ok",
                "data": self.scheduling_stats
            })
            
            # Determinar se pode agendar
            if not result["errors"]:
                result["can_schedule"] = True
                result["recommendations"].append(
                    "Livro pronto para agendamento. Use schedule_reading()."
                )
            
        except Exception as e:
            result["errors"].append(f"Erro no diagnóstico: {str(e)}")
            logger.error(f"Erro no diagnóstico de {book_id}: {e}")
        
        return result
    
    @pyqtSlot(result=dict)
    def get_scheduling_stats(self) -> Dict:
        """Retorna estatísticas de agendamento"""
        return {
            **self.scheduling_stats,
            "active_operations": len(self.active_workers),
            "pending_scheduling": len(self.scheduling_operations),
            "cache_size": len(self.day_cache)
        }
    
    # ====== MÉTODOS DE CACHE ======
    
    def _cleanup_old_cache(self):
        """Limpa cache antigo"""
        self.cache_mutex.lock()
        try:
            current_time = datetime.now()
            keys_to_remove = []
            
            for key, timestamp in self.cache_timestamps.items():
                if (current_time - timestamp).total_seconds() > self.CACHE_TTL_SECONDS:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self.day_cache.pop(key, None)
                self.cache_timestamps.pop(key, None)
            
            if keys_to_remove:
                logger.debug(f"Cache limpo: {len(keys_to_remove)} entradas removidas")
                
        finally:
            self.cache_mutex.unlock()
    
    def _invalidate_agenda_cache(self):
        """Invalida cache completo da agenda"""
        self.cache_mutex.lock()
        try:
            self.day_cache.clear()
            self.cache_timestamps.clear()
        finally:
            self.cache_mutex.unlock()
    
    # ====== MÉTODOS DE AGENDA (mantidos para compatibilidade) ======

    def _serialize_events(self, events: List[Any]) -> List[Dict]:
        """Serializa lista de eventos para dicionário."""
        return [
            event.to_dict() if hasattr(event, "to_dict") else dict(event)
            for event in events
        ]

    def _parse_datetime(self, value: str) -> datetime:
        """Converte string de data/hora para datetime de forma tolerante."""
        if not value:
            raise ValueError("Data/hora inválida")
        raw = str(value).strip()
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        raise ValueError(f"Formato de data/hora não suportado: {value}")

    def _priority_from_value(self, value: Any) -> int:
        """Converte prioridade textual/numérica para inteiro (1-5)."""
        if isinstance(value, int):
            return max(1, min(5, value))
        mapping = {
            "baixa": 1,
            "low": 1,
            "média": 2,
            "media": 2,
            "medium": 2,
            "alta": 3,
            "high": 3,
            "fixo": 4,
            "fixed": 4,
            "bloqueio": 5,
            "critical": 5,
        }
        return mapping.get(str(value).strip().lower(), 2)
    
    @pyqtSlot(str)
    def load_agenda_async(self, date_str: str = None):
        """Carrega agenda para data específica"""
        self.load_agenda(date_str)
    
    @pyqtSlot()
    def load_upcoming_deadlines_async(self, days: int = 7):
        """Carrega prazos próximos"""
        self.load_upcoming_deadlines(days)
    
    @pyqtSlot(dict)
    def add_event_async(self, event_data: Dict):
        """Adiciona evento à agenda"""
        self.add_event(event_data)
    
    @pyqtSlot(str, result=bool)
    def delete_event(self, event_id: str) -> bool:
        """Remove evento da agenda"""
        try:
            if not self.agenda_manager or event_id not in self.agenda_manager.events:
                return False
            event = self.agenda_manager.events[event_id]
            event_day = event.start.date().isoformat()
            del self.agenda_manager.events[event_id]
            self.agenda_manager._save_events()
            self._invalidate_agenda_cache()
            self.event_deleted.emit(event_id)
            self.load_agenda(event_day)
            return True
        except Exception as e:
            logger.error(f"Erro ao remover evento {event_id}: {e}")
            return False
    
    @pyqtSlot(str, result=list)
    def load_agenda(self, date_str: str = None) -> List[Dict]:
        """Versão síncrona para compatibilidade"""
        try:
            if date_str is None:
                date_str = datetime.now().strftime("%Y-%m-%d")

            events = self.agenda_manager.get_day_events(date_str) if self.agenda_manager else []
            serialized = [
                event.to_dict() if hasattr(event, "to_dict") else event
                for event in events
            ]

            self.agenda_loaded.emit(serialized)
            self.agenda_updated.emit(date_str, serialized)
            return serialized
        except Exception as e:
            try:
                logger.error(f"Erro ao carregar agenda ({date_str}): {e}")
            except RecursionError:
                # Fallback extremo para cenários com stack recursiva.
                print(f"[AGENDA] Erro ao carregar agenda ({date_str})")
            self.agenda_loaded.emit([])
            self.agenda_updated.emit(date_str or datetime.now().strftime("%Y-%m-%d"), [])
            return []

    @pyqtSlot(str, result=list)
    def get_day_events(self, date_str: str = None) -> List[Dict]:
        """Retorna eventos serializados de um dia específico."""
        return self.load_agenda(date_str)

    @pyqtSlot(int, int, result=dict)
    def get_month_events(self, year: int, month: int) -> Dict[str, List[Dict]]:
        """Retorna eventos serializados por dia para um mês específico."""
        result: Dict[str, List[Dict]] = {}
        try:
            first_day = date(year, month, 1)
            if month == 12:
                next_month = date(year + 1, 1, 1)
            else:
                next_month = date(year, month + 1, 1)
            total_days = (next_month - first_day).days
            for day in range(total_days):
                current = first_day + timedelta(days=day)
                current_str = current.isoformat()
                events = self.agenda_manager.get_day_events(current_str) if self.agenda_manager else []
                result[current_str] = self._serialize_events(events)
        except Exception as e:
            logger.error(f"Erro ao carregar mês {year}-{month:02d}: {e}")
        return result

    @pyqtSlot(dict, result=str)
    def add_event(self, event_data: Dict) -> str:
        """Adiciona evento e emite sinais de atualização."""
        try:
            title = event_data.get("title", "").strip()
            start = event_data.get("start")
            end = event_data.get("end")
            event_type = event_data.get("event_type") or event_data.get("type") or "casual"
            if not title or not start or not end:
                raise ValueError("Campos obrigatórios: title, start e end")

            metadata = {
                k: v for k, v in event_data.items()
                if k not in {"id", "title", "start", "end", "type", "event_type"}
            }
            event_id = self.agenda_manager.add_event(
                title=title,
                start=start,
                end=end,
                event_type=event_type,
                **metadata,
            )
            self._invalidate_agenda_cache()
            created = self.agenda_manager.events.get(event_id)
            if created and "priority" in event_data:
                try:
                    created.priority = type(created.priority)(self._priority_from_value(event_data["priority"]))
                except Exception:
                    pass
            if created and "discipline" in event_data and hasattr(created, "discipline"):
                created.discipline = event_data.get("discipline")
            if created and "description" in event_data and hasattr(created, "metadata"):
                created.metadata["description"] = event_data.get("description")
            if created:
                self.agenda_manager._save_events()
            created_data = created.to_dict() if created and hasattr(created, "to_dict") else {"id": event_id}
            self.event_added.emit(created_data)

            if created:
                day_str = created.start.date().isoformat()
                self.load_agenda(day_str)
            return event_id
        except Exception as e:
            logger.error(f"Erro ao adicionar evento: {e}")
            return ""

    @pyqtSlot(str, dict, result=bool)
    def update_event(self, event_id: str, updates: Dict) -> bool:
        """Atualiza evento existente de forma compatível com a UI."""
        try:
            event = self.agenda_manager.events.get(event_id) if self.agenda_manager else None
            if not event:
                return False

            old_day = event.start.date().isoformat()

            if updates.get("deleted", False):
                return self.delete_event(event_id)

            if "title" in updates:
                event.title = str(updates["title"]).strip() or event.title

            if "start" in updates:
                event.start = self._parse_datetime(updates["start"])
            if "end" in updates:
                event.end = self._parse_datetime(updates["end"])

            event_type = updates.get("event_type", updates.get("type"))
            if event_type:
                try:
                    event.type = type(event.type)(str(event_type))
                except Exception:
                    logger.warning(f"Tipo de evento inválido para {event_id}: {event_type}")

            if "priority" in updates:
                priority_value = self._priority_from_value(updates["priority"])
                try:
                    event.priority = type(event.priority)(priority_value)
                except Exception:
                    pass

            if "completed" in updates:
                event.completed = bool(updates["completed"])

            if hasattr(event, "discipline") and "discipline" in updates:
                event.discipline = updates.get("discipline")

            if hasattr(event, "metadata"):
                for key in ("description", "notes"):
                    if key in updates:
                        event.metadata[key] = updates[key]

            self.agenda_manager._save_events()
            self._invalidate_agenda_cache()

            event_data = event.to_dict() if hasattr(event, "to_dict") else {"id": event_id}
            self.event_updated.emit(event_id, event_data)

            new_day = event.start.date().isoformat()
            self.load_agenda(old_day)
            if new_day != old_day:
                self.load_agenda(new_day)
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar evento {event_id}: {e}")
            return False

    @pyqtSlot(str, bool, result=bool)
    def toggle_event_completion(self, event_id: str, completed: bool) -> bool:
        """Marca evento como concluído/não concluído."""
        success = self.update_event(event_id, {"completed": completed})
        if success:
            self.event_completed.emit(event_id, completed)
        return success

    @pyqtSlot(str, str, int, result=bool)
    def move_event(self, event_id: str, target_date: str, target_hour: int = -1) -> bool:
        """Move um evento para outro dia e/ou horário, preservando duração."""
        try:
            event = self.agenda_manager.events.get(event_id) if self.agenda_manager else None
            if not event:
                return False
            old_day = event.start.date().isoformat()
            duration = event.end - event.start
            target_day = date.fromisoformat(str(target_date))
            hour = event.start.hour if target_hour is None or target_hour < 0 else int(target_hour)
            hour = max(0, min(23, hour))
            new_start = datetime.combine(target_day, datetime.min.time()).replace(
                hour=hour,
                minute=event.start.minute if target_hour is None or target_hour < 0 else 0,
                second=0,
                microsecond=0,
            )
            event.start = new_start
            event.end = new_start + duration
            self.agenda_manager._save_events()
            self._invalidate_agenda_cache()
            event_data = event.to_dict() if hasattr(event, "to_dict") else {"id": event_id}
            self.event_updated.emit(event_id, event_data)
            self.load_agenda(old_day)
            new_day = event.start.date().isoformat()
            self.load_agenda(new_day)
            return True
        except Exception as e:
            logger.error(f"Erro ao mover evento {event_id}: {e}")
            return False

    @pyqtSlot(int)
    def load_upcoming_deadlines(self, days: int = 7):
        """Carrega prazos próximos e emite sinal."""
        try:
            deadlines = self.agenda_manager.get_upcoming_deadlines(days=days) if self.agenda_manager else []
            self.deadlines_loaded.emit(deadlines)
        except Exception as e:
            logger.error(f"Erro ao carregar prazos: {e}")
            self.deadlines_loaded.emit([])

    @pyqtSlot()
    def load_optimizations(self):
        """Carrega sugestões de otimização e emite sinal."""
        try:
            suggestions = self.agenda_manager.suggest_optimizations() if self.agenda_manager else []
            self.optimizations_loaded.emit(suggestions)
        except Exception as e:
            logger.error(f"Erro ao carregar otimizações: {e}")
            self.optimizations_loaded.emit([])

    @pyqtSlot(str, int, int, int)
    def find_free_slots(self, date_str: str, duration_minutes: int, start_hour: int = 8, end_hour: int = 22):
        """Busca slots livres e emite sinal."""
        try:
            slots = self.agenda_manager.find_free_slots(
                date_str,
                duration_minutes=duration_minutes,
                start_hour=start_hour,
                end_hour=end_hour,
            ) if self.agenda_manager else []
            self.free_slots_found.emit(date_str, slots)
        except Exception as e:
            logger.error(f"Erro ao buscar slots livres: {e}")
            self.free_slots_found.emit(date_str, [])

    @pyqtSlot(str, int, str)
    def activate_emergency_mode(self, objective: str, days: int = 3, focus_area: str = None):
        """Ativa modo emergência se disponível no manager."""
        payload = {
            "objective": objective,
            "days": days,
            "focus_area": focus_area,
            "activated_at": datetime.now().isoformat(),
        }
        try:
            if self.agenda_manager and hasattr(self.agenda_manager, "activate_emergency_mode"):
                result = self.agenda_manager.activate_emergency_mode(objective, days, focus_area)
                if isinstance(result, dict):
                    payload.update(result)
            self.emergency_mode_activated.emit(payload)
        except Exception as e:
            payload["error"] = str(e)
            logger.error(f"Erro ao ativar modo emergência: {e}")
            self.emergency_mode_activated.emit(payload)

    @pyqtSlot(result=dict)
    def get_routine_preferences(self) -> Dict:
        """Obtém preferências de rotina (sono/refeições/revisão dominical)."""
        try:
            if self.agenda_manager and hasattr(self.agenda_manager, "get_routine_preferences"):
                return self.agenda_manager.get_routine_preferences()
        except Exception as e:
            logger.error(f"Erro ao obter preferências de rotina: {e}")
        return {
            "sleep_start": "23:00",
            "sleep_end": "07:00",
            "breakfast_time": "08:00",
            "lunch_time": "12:30",
            "dinner_time": "19:30",
            "weekly_review_time": "18:00",
            "weekly_review_duration_minutes": 90,
            "weekly_review_weekday": 6,
        }

    @pyqtSlot(dict, result=dict)
    def update_routine_preferences(self, updates: Dict) -> Dict:
        """Atualiza preferências de rotina e recarrega agenda visível."""
        try:
            if self.agenda_manager and hasattr(self.agenda_manager, "update_routine_preferences"):
                result = self.agenda_manager.update_routine_preferences(updates or {})
                self._invalidate_agenda_cache()
                today_str = datetime.now().strftime("%Y-%m-%d")
                self.load_agenda(today_str)
                self.routine_preferences_updated.emit(result)
                return result
        except Exception as e:
            logger.error(f"Erro ao atualizar preferências de rotina: {e}")
        return {}
    
    # ====== LIMPEZA ======
    
    def cleanup(self):
        """Limpeza antes de encerrar"""
        # Parar todos os workers
        for worker in list(self.active_workers.values()):
            worker.stop()
        
        # Parar timers
        self.auto_refresh_timer.stop()
        self.cache_cleanup_timer.stop()
        
        # Limpar estruturas
        self.active_workers.clear()
        self.scheduling_operations.clear()
        self._invalidate_agenda_cache()
        
        logger.info("AgendaController finalizado")
