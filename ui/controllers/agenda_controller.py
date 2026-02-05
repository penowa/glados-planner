"""
Controller para módulo de Agenda - VERSÃO REFATORADA COM INTEGRAÇÃO COMPLETA
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, QDateTime, Qt, QThread
from PyQt6.QtGui import QPixmap, QPainter, QColor
from datetime import datetime, timedelta, date
import json
import logging
from typing import Dict, List, Optional, Any, Callable
import uuid
from pathlib import Path
from functools import wraps

logger = logging.getLogger('GLaDOS.UI.AgendaController')


class AgendaWorker(QThread):
    """Thread worker para operações pesadas da agenda"""
    
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, method: Callable, *args, **kwargs):
        super().__init__()
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self._is_running = True
        
    def run(self):
        """Executa operação em thread separada"""
        try:
            if not self._is_running:
                return
                
            result = self.method(*self.args, **self.kwargs)
            if self._is_running:
                self.result_ready.emit(result)
                
        except Exception as e:
            logger.error(f"Erro no worker: {e}")
            if self._is_running:
                self.error_occurred.emit(str(e))
    
    def stop(self):
        """Para a thread de forma segura"""
        self._is_running = False
        self.quit()
        self.wait(1000)


class AgendaController(QObject):
    """Controller completo para integração da agenda"""
    
    # === SINAIS DE EVENTOS ===
    agenda_loaded = pyqtSignal(list)  # Lista de eventos para um dia
    weekly_review_loaded = pyqtSignal(dict)
    event_added = pyqtSignal(dict)
    event_updated = pyqtSignal(str, dict)
    event_deleted = pyqtSignal(str)
    event_completed = pyqtSignal(str, bool)  # IMPORTANTE: Adicionado para o card
    deadlines_loaded = pyqtSignal(list)
    optimizations_loaded = pyqtSignal(list)
    emergency_mode_activated = pyqtSignal(dict)
    free_slots_found = pyqtSignal(list)
    reading_allocated = pyqtSignal(dict)
    review_transitioned = pyqtSignal(dict)
    productivity_insights_loaded = pyqtSignal(dict)
    checkin_created = pyqtSignal(dict)
    checkins_loaded = pyqtSignal(list)
    trends_loaded = pyqtSignal(dict)
    
    # === CONSTANTES ===
    CACHE_TTL_SECONDS = 300  # 5 minutos
    REFRESH_INTERVAL_MS = 60000  # 1 minuto
    DEFAULT_WORK_DAY_HOURS = (8, 22)
    
    def __init__(self, agenda_manager, checkin_system=None):
        super().__init__()
        self.agenda_manager = agenda_manager
        self.checkin_system = checkin_system
        
        # Cache com timestamp
        self.event_cache: Dict[str, Dict] = {}
        self.day_cache: Dict[str, Dict] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Workers ativos
        self.active_workers: List[AgendaWorker] = []
        
        self._setup_timers()
        logger.info("AgendaController inicializado")
    
    # === CONFIGURAÇÃO INICIAL ===
    
    def _setup_timers(self):
        """Configura timers para atualizações automáticas"""
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self._auto_refresh)
        self.auto_refresh_timer.start(self.REFRESH_INTERVAL_MS)
    
    # === MÉTODOS ASSÍNCRONOS PRINCIPAIS ===
    
    @pyqtSlot(str)
    def load_agenda_async(self, date_str: str = None):
        """Carrega agenda para data específica de forma assíncrona"""
        date_str = date_str or datetime.now().strftime("%Y-%m-%d")
        
        if self._is_cached_and_valid(date_str):
            logger.debug(f"Usando cache para {date_str}")
            self.agenda_loaded.emit(self.day_cache[date_str])
            return
        
        self._execute_async(
            self.agenda_manager.get_day_events,
            lambda events: self._on_agenda_loaded(events, date_str),
            date_str=date_str
        )
    
    @pyqtSlot()
    def load_weekly_review_async(self, week_start: str = None):
        """Carrega revisão semanal de forma assíncrona"""
        self._execute_async(
            self.agenda_manager.generate_weekly_review,
            self._on_weekly_review_loaded,
            week_start=week_start
        )
    
    @pyqtSlot(int)
    def load_upcoming_deadlines_async(self, days: int = 7):
        """Carrega prazos próximos de forma assíncrona"""
        self._execute_async(
            self.agenda_manager.get_upcoming_deadlines,
            self._on_deadlines_loaded,
            days=days
        )
    
    @pyqtSlot()
    def load_optimizations_async(self):
        """Carrega sugestões de otimização de forma assíncrona"""
        self._execute_async(
            self.agenda_manager.suggest_optimizations,
            self._on_optimizations_loaded
        )
    
    @pyqtSlot(dict)
    def add_event_async(self, event_data: Dict):
        """Adiciona novo evento de forma assíncrona"""
        logger.info(f"Adicionando evento: {event_data.get('title')}")
        formatted_data = self._format_event_data(event_data)
        
        self._execute_async(
            self.agenda_manager.add_event,
            lambda event_id: self._on_event_added(event_id, formatted_data),
            **formatted_data
        )
    
    @pyqtSlot(str, dict)
    def update_event_async(self, event_id: str, updates: Dict):
        """Atualiza evento existente de forma assíncrona"""
        logger.info(f"Atualizando evento {event_id}")
        self._update_local_event(event_id, updates)
        
        self._execute_async(
            self._update_event_backend,
            lambda success: self._on_event_updated(success, event_id, updates),
            event_id=event_id,
            updates=updates
        )
    
    @pyqtSlot(str, float, str)
    def allocate_reading_time_async(self, book_id: str, pages_per_day: float,
                                  strategy: str = "balanced"):
        """Aloca tempo de leitura de forma assíncrona"""
        self._execute_async(
            self.agenda_manager.allocate_reading_time,
            self._on_reading_allocated,
            book_id=book_id,
            pages_per_day=pages_per_day,
            strategy=strategy
        )
    
    @pyqtSlot(str, int, str)
    def activate_emergency_mode_async(self, objective: str, days: int,
                                     focus_area: str = None):
        """Ativa modo emergência de forma assíncrona"""
        self._execute_async(
            self.agenda_manager.emergency_mode,
            self._on_emergency_mode_activated,
            objective=objective,
            days=days,
            focus_area=focus_area
        )
    
    @pyqtSlot(str, int, int, int)
    def find_free_slots_async(self, date_str: str, duration_minutes: int,
                             start_hour: int = None, end_hour: int = None):
        """Encontra slots livres de forma assíncrona"""
        start_hour = start_hour or self.DEFAULT_WORK_DAY_HOURS[0]
        end_hour = end_hour or self.DEFAULT_WORK_DAY_HOURS[1]
        
        self._execute_async(
            self.agenda_manager.find_free_slots,
            self._on_free_slots_found,
            date=date_str,
            duration_minutes=duration_minutes,
            start_hour=start_hour,
            end_hour=end_hour
        )
    
    # === MÉTODOS DE CHECK-IN ===
    
    @pyqtSlot(float, float, list)
    def create_morning_checkin_async(self, energy_level: float = 3.0,
                                    focus_score: float = 3.0,
                                    goals_today: List[str] = None):
        """Cria check-in matinal de forma assíncrona"""
        self._execute_checkin_operation(
            self.checkin_system.morning_routine,
            energy_level=energy_level,
            focus_score=focus_score,
            goals_today=goals_today or []
        )
    
    @pyqtSlot(float, list, list, list)
    def create_evening_checkin_async(self, mood_score: float = 3.0,
                                    achievements: List[str] = None,
                                    challenges: List[str] = None,
                                    insights: List[str] = None):
        """Cria check-in noturno de forma assíncrona"""
        self._execute_checkin_operation(
            self.checkin_system.evening_checkin,
            mood_score=mood_score,
            achievements=achievements or [],
            challenges=challenges or [],
            insights=insights or []
        )
    
    @pyqtSlot(int)
    def load_recent_checkins_async(self, days: int = 7):
        """Carrega check-ins recentes de forma assíncrona"""
        self._execute_checkin_operation(
            self.checkin_system.get_recent_checkins,
            days=days
        )
    
    @pyqtSlot(int)
    def load_trends_async(self, days: int = 30):
        """Carrega tendências de forma assíncrona"""
        self._execute_checkin_operation(
            self.checkin_system.get_trends,
            days=days
        )
    
    # === MÉTODOS SÍNCRONOS ===
    
    @pyqtSlot(str, result=list)
    def load_agenda(self, date_str: str = None) -> List[Dict]:
        """Versão síncrona para compatibilidade com AgendaCard"""
        try:
            date_str = date_str or datetime.now().strftime("%Y-%m-%d")
            
            if self._is_cached_and_valid(date_str):
                return self.day_cache[date_str]
            
            events = self.agenda_manager.get_day_events(date_str=date_str)
            ui_events = [self._event_to_ui_format(event) for event in events]
            ui_events.sort(key=lambda x: x['start'])
            
            self._update_cache(date_str, ui_events)
            
            # Emitir sinal para notificar atualização
            self.agenda_loaded.emit(ui_events)
            
            return ui_events
            
        except Exception as e:
            logger.error(f"Erro ao carregar agenda: {e}")
            return []
    
    @pyqtSlot(result=list)
    def load_upcoming_deadlines(self) -> List[Dict]:
        """Versão síncrona para compatibilidade"""
        try:
            return self.agenda_manager.get_upcoming_deadlines(days=7)
        except Exception as e:
            logger.error(f"Erro ao carregar prazos: {e}")
            return []
    
    @pyqtSlot(result=list)
    def load_optimizations(self) -> List[Dict]:
        """Versão síncrona para compatibilidade"""
        try:
            return self.agenda_manager.suggest_optimizations()
        except Exception as e:
            logger.error(f"Erro ao carregar otimizações: {e}")
            return []
    
    @pyqtSlot(dict, result=str)
    def add_event(self, event_data: Dict) -> str:
        """Versão síncrona para compatibilidade"""
        try:
            formatted_data = self._format_event_data(event_data)
            event_id = self.agenda_manager.add_event(**formatted_data)
            
            if event_id and 'start' in formatted_data:
                try:
                    event_date = datetime.fromisoformat(
                        formatted_data['start']
                    ).strftime("%Y-%m-%d")
                    self._invalidate_cache(event_date)
                except:
                    pass
            
            # Emitir sinal para notificar adição
            if event_id:
                self.event_added.emit({**formatted_data, 'id': event_id})
            
            return event_id or ""
        except Exception as e:
            logger.error(f"Erro ao adicionar evento: {e}")
            return ""
    
    @pyqtSlot(str, dict, result=bool)
    def update_event(self, event_id: str, updates: Dict) -> bool:
        """Versão síncrona para compatibilidade"""
        try:
            self._update_local_event(event_id, updates)
            success = self._update_event_backend(event_id, updates)
            if success:
                self.event_updated.emit(event_id, updates)
                # Emitir sinal específico para conclusão
                if 'completed' in updates:
                    self.event_completed.emit(event_id, updates['completed'])
            return success
        except Exception as e:
            logger.error(f"Erro ao atualizar evento: {e}")
            return False
    
    @pyqtSlot(str, bool, result=bool)
    def toggle_event_completion(self, event_id: str, completed: bool) -> bool:
        """Alterna estado de conclusão do evento (compatível com AgendaCard)"""
        return self.update_event(event_id, {"completed": completed})
    
    @pyqtSlot(str, result=bool)
    def complete_event(self, event_id: str) -> bool:
        """Marca evento como concluído (síncrono)"""
        return self.toggle_event_completion(event_id, True)
    
    @pyqtSlot(str, result=bool)
    def delete_event(self, event_id: str) -> bool:
        """Remove evento da agenda (síncrono)"""
        try:
            # Remove do cache
            self.event_cache.pop(event_id, None)
            for date_str in list(self.day_cache.keys()):
                self.day_cache[date_str] = [
                    e for e in self.day_cache[date_str]
                    if e['id'] != event_id
                ]
            
            # Remove do backend
            success = self._delete_event_backend(event_id)
            if success:
                self.event_deleted.emit(event_id)
            
            return success
        except Exception as e:
            logger.error(f"Erro ao deletar evento: {e}")
            return False
    
    @pyqtSlot(str, result=dict)
    def get_event_details(self, event_id: str) -> Dict:
        """Retorna detalhes de um evento (síncrono com cache)"""
        return self.event_cache.get(event_id, {"id": event_id, "error": "Evento não encontrado"})
    
    # === CALLBACKS ===
    
    def _on_agenda_loaded(self, events, date_str: str):
        """Processa agenda carregada"""
        ui_events = [self._event_to_ui_format(event) for event in events]
        ui_events.sort(key=lambda x: x['start'])
        
        # Atualiza caches
        for event in events:
            ui_event = self._event_to_ui_format(event)
            self.event_cache[event.id] = ui_event
        
        self._update_cache(date_str, ui_events)
        self.agenda_loaded.emit(ui_events)
        logger.debug(f"Agenda carregada: {len(ui_events)} eventos")
    
    def _on_weekly_review_loaded(self, weekly_data):
        self.weekly_review_loaded.emit(weekly_data)
    
    def _on_deadlines_loaded(self, deadlines):
        self.deadlines_loaded.emit(deadlines)
    
    def _on_optimizations_loaded(self, optimizations):
        self.optimizations_loaded.emit(optimizations)
    
    def _on_event_added(self, event_id, event_data):
        result = {
            "event_id": event_id,
            **event_data,
            "timestamp": datetime.now().isoformat()
        }
        self.event_added.emit(result)
        self._invalidate_date_cache(event_data.get('start'))
        self.load_agenda_async()
    
    def _on_event_updated(self, success, event_id, updates):
        if success:
            self.event_updated.emit(event_id, updates)
            # Emitir sinal específico para conclusão
            if 'completed' in updates:
                self.event_completed.emit(event_id, updates['completed'])
            
            if event_id in self.event_cache:
                self.event_cache[event_id].update(updates)
            self.load_agenda_async()
    
    def _on_event_deleted(self, success, event_id):
        if success:
            self.event_deleted.emit(event_id)
            self.event_cache.pop(event_id, None)
            self.load_agenda_async()
    
    def _on_reading_allocated(self, allocation_result):
        self.reading_allocated.emit(allocation_result)
        self.load_agenda_async()
    
    def _on_emergency_mode_activated(self, emergency_plan):
        self.emergency_mode_activated.emit(emergency_plan)
        self.load_agenda_async()
    
    def _on_free_slots_found(self, free_slots):
        self.free_slots_found.emit(free_slots)
    
    def _on_checkin_created(self, checkin_result):
        self.checkin_created.emit(checkin_result)
    
    def _on_checkins_loaded(self, checkins):
        self.checkins_loaded.emit(checkins)
    
    def _on_trends_loaded(self, trends):
        self.trends_loaded.emit(trends)
    
    # === UTILITÁRIOS ===
    
    def _execute_async(self, method: Callable, callback: Callable, *args, **kwargs):
        """Executa método em thread separada"""
        worker = AgendaWorker(method, *args, **kwargs)
        worker.result_ready.connect(callback)
        worker.error_occurred.connect(
            lambda error: logger.error(f"Erro no worker: {error}")
        )
        worker.finished.connect(lambda: self._remove_worker(worker))
        
        self.active_workers.append(worker)
        worker.start()
    
    def _execute_checkin_operation(self, method: Callable, **kwargs):
        """Executa operação de check-in com validação"""
        if not self.checkin_system:
            logger.error("Sistema de check-in não inicializado")
            return
        
        self._execute_async(method, self._on_checkin_created, **kwargs)
    
    def _remove_worker(self, worker: AgendaWorker):
        """Remove worker da lista de ativos"""
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        worker.deleteLater()
    
    def _is_cached_and_valid(self, cache_key: str) -> bool:
        """Verifica se cache é válido"""
        if cache_key not in self.cache_timestamps:
            return False
        
        age = (datetime.now() - self.cache_timestamps[cache_key]).total_seconds()
        return age < self.CACHE_TTL_SECONDS and cache_key in self.day_cache
    
    def _update_cache(self, key: str, data: Any):
        """Atualiza cache com timestamp"""
        self.day_cache[key] = data
        self.cache_timestamps[key] = datetime.now()
    
    def _invalidate_cache(self, key: str):
        """Remove item do cache"""
        self.day_cache.pop(key, None)
        self.cache_timestamps.pop(key, None)
    
    def _invalidate_date_cache(self, date_str: str):
        """Invalida cache de uma data específica"""
        if not date_str:
            return
        
        try:
            event_date = datetime.fromisoformat(date_str).strftime("%Y-%m-%d")
            self._invalidate_cache(event_date)
        except:
            pass
    
    def _update_local_event(self, event_id: str, updates: Dict):
        """Atualiza evento no cache local"""
        if event_id in self.event_cache:
            self.event_cache[event_id].update(updates)
            for date_events in self.day_cache.values():
                for event in date_events:
                    if event['id'] == event_id:
                        event.update(updates)
                        break
    
    def _update_event_backend(self, event_id: str, updates: Dict) -> bool:
        """Atualiza evento no backend"""
        try:
            event = self.agenda_manager.events.get(event_id)
            if not event:
                return False
            
            for key, value in updates.items():
                if hasattr(event, key):
                    if key in ('start', 'end') and isinstance(value, str):
                        value = self._parse_datetime(value)
                    setattr(event, key, value)
            
            self.agenda_manager._save_events()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar evento no backend: {e}")
            return False
    
    def _delete_event_backend(self, event_id: str) -> bool:
        """Remove evento do backend"""
        try:
            if event_id in self.agenda_manager.events:
                del self.agenda_manager.events[event_id]
                self.agenda_manager._save_events()
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao deletar evento no backend: {e}")
            return False
    
    def _event_to_ui_format(self, event) -> Dict:
        """Converte evento do backend para formato UI (compatível com AgendaCard)"""
        event_dict = event.to_dict() if hasattr(event, 'to_dict') else event
        
        start_dt = self._parse_datetime(event_dict.get('start'))
        end_dt = self._parse_datetime(event_dict.get('end'))
        metadata = event_dict.get('metadata', {})
        
        # Calcular duração em minutos
        duration_minutes = 60
        if start_dt and end_dt:
            duration_minutes = (end_dt - start_dt).seconds // 60
        
        # Extrair tipo do evento
        event_type = self._extract_event_type(event_dict)
        
        # Criar formato UI compatível com AgendaCard
        ui_event = {
            'id': event_dict.get('id', str(uuid.uuid4())),
            'title': event_dict.get('title', 'Sem título'),
            'description': metadata.get('description', event_dict.get('description', '')),
            'start': start_dt.isoformat() if start_dt else '',
            'end': end_dt.isoformat() if end_dt else '',
            'start_time': start_dt.strftime('%H:%M') if start_dt else '',
            'end_time': end_dt.strftime('%H:%M') if end_dt else '',
            'date': start_dt.strftime('%Y-%m-%d') if start_dt else '',
            'day_of_week': start_dt.strftime('%A') if start_dt else '',
            'type': event_type,
            'priority': event_dict.get('priority', 2),
            'completed': event_dict.get('completed', False),
            'auto_generated': event_dict.get('auto_generated', False),
            'book_id': event_dict.get('book_id'),
            'discipline': event_dict.get('discipline', 'Geral'),
            'difficulty': event_dict.get('difficulty', 3),
            'color': self._get_event_color(event_type),
            'icon': self._get_event_icon(event_type),
            'duration_minutes': event_dict.get('duration_minutes', duration_minutes),
            'is_blocking': event_dict.get('is_blocking', False),
            'is_flexible': event_dict.get('is_flexible', True),
            'progress_notes': event_dict.get('progress_notes', []),
            'metadata': metadata
        }
        
        return ui_event
    
    def _extract_event_type(self, event_dict):
        """Extrai tipo do evento em formato string"""
        event_type = event_dict.get('type', 'casual')
        if isinstance(event_type, dict):
            return event_type.get('value', 'casual')
        elif hasattr(event_type, 'value'):
            return event_type.value
        return event_type
    
    def _parse_datetime(self, dt_str):
        """Converte string para datetime"""
        if not dt_str or isinstance(dt_str, datetime):
            return dt_str
        
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        
        logger.error(f"Formato de data inválido: {dt_str}")
        return None
    
    def _get_event_color(self, event_type):
        """Retorna cor baseada no tipo do evento (compatível com AgendaCard)"""
        color_map = {
            'leitura': '#4A90E2',    # Azul
            'revisao': '#50E3C2',    # Turquesa
            'producao': '#B8E986',   # Verde claro
            'aula': '#9013FE',       # Roxo
            'orientacao': '#F5A623', # Laranja
            'grupo_estudo': '#FF6B6B', # Vermelho claro
            'lazer': '#FFD166',      # Amarelo
            'refeicao': '#7ED321',   # Verde
            'sono': '#417505',       # Verde escuro
            'transcricao': '#9C27B0', # Violeta
            'checkin': '#00BCD4',    # Ciano
            'casual': '#9B9B9B'      # Cinza
        }
        
        return color_map.get(event_type, '#9B9B9B')
    
    def _get_event_icon(self, event_type):
        """Retorna nome do ícone baseado no tipo de evento"""
        icon_map = {
            'leitura': 'book-open',
            'revisao': 'refresh-cw',
            'producao': 'edit-3',
            'aula': 'graduation-cap',
            'orientacao': 'users',
            'grupo_estudo': 'users',
            'lazer': 'coffee',
            'refeicao': 'utensils',
            'sono': 'moon',
            'transcricao': 'file-text',
            'checkin': 'check-circle',
            'casual': 'calendar'
        }
        
        return icon_map.get(event_type, 'calendar')
    
    def _format_event_data(self, event_data: Dict) -> Dict:
        """Formata dados do evento para o backend"""
        formatted = event_data.copy()
        
        # Converte QDateTime para string
        if isinstance(formatted.get('start'), QDateTime):
            formatted['start'] = formatted['start'].toString(Qt.DateFormat.ISODate)
        if isinstance(formatted.get('end'), QDateTime):
            formatted['end'] = formatted['end'].toString(Qt.DateFormat.ISODate)
        
        # Converte prioridade string para numérica
        priority = formatted.get('priority')
        if isinstance(priority, str):
            priority_map = {
                'low': 1, 'baixa': 1,
                'medium': 2, 'media': 2,
                'high': 3, 'alta': 3,
                'fixed': 4, 'fixo': 4,
                'blocking': 5, 'bloqueio': 5
            }
            formatted['priority'] = priority_map.get(priority.lower(), 2)
        
        return formatted
    
    def _auto_refresh(self):
        """Atualização automática da agenda"""
        now = datetime.now()
        
        # Meia-noite: recarrega tudo
        if now.hour == 0 and now.minute == 0:
            self.day_cache.clear()
            self.cache_timestamps.clear()
            self.load_agenda_async()
            self.load_upcoming_deadlines_async(7)
            self.load_optimizations_async()
        
        # A cada 15 minutos: verifica agenda atual
        elif now.minute % 15 == 0:
            self.load_agenda_async()
    
    def cleanup(self):
        """Limpeza antes de encerrar"""
        # Para todos os workers
        for worker in self.active_workers[:]:
            worker.stop()
        
        # Para o timer
        self.auto_refresh_timer.stop()
        logger.info("AgendaController finalizado")