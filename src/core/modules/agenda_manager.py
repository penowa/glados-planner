# [file name]: src/core/modules/agenda_manager.py
"""
AgendaManager - Cérebro do Sistema GLaDOS Planner
Gestor inteligente de agenda acadêmica para estudantes de filosofia
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
import json
from pathlib import Path
import heapq
from collections import defaultdict
import uuid

# Módulos que serão importados (importação real será ajustada)
from .reading_manager import ReadingManager
from .review_system import ReviewSystem
from .pomodoro_timer import PomodoroTimer
from .writing_assistant import WritingAssistant


class AgendaEventType(Enum):
    """Tipos de compromissos no sistema"""
    AULA = "aula"
    LEITURA = "leitura"
    PRODUCAO = "producao"
    REVISAO = "revisao"
    ORIENTACAO = "orientacao"
    GRUPO_ESTUDO = "grupo_estudo"
    REFEICAO = "refeicao"
    SONO = "sono"
    LAZER = "lazer"
    CASUAL = "casual"
    TRANSCRICAO = "transcricao"  # Processamento de livros
    CHECKIN = "checkin"  # Check-in diário
    REVISAO_DOMINICAL = "revisao_dominical"


class EventPriority(Enum):
    """Níveis de prioridade"""
    BLOQUEIO = 5  # Sono, refeições (intransponível)
    FIXO = 4      # Aulas, orientações (pouco flexível)
    ALTA = 3      # Produção, leituras com prazo próximo
    MEDIA = 2     # Leituras, revisão
    BAIXA = 1     # Lazer, casual


@dataclass
class AgendaEvent:
    """Evento na agenda com metadados avançados"""
    id: str
    type: AgendaEventType
    title: str
    start: datetime
    end: datetime
    completed: bool = False
    auto_generated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Metadados específicos
    book_id: Optional[str] = None
    discipline: Optional[str] = None
    priority: EventPriority = EventPriority.MEDIA
    difficulty: int = 3  # 1-5
    estimated_difficulty: float = 0.0
    progress_notes: List[str] = field(default_factory=list)
    
    def duration_minutes(self) -> float:
        """Retorna duração em minutos"""
        return (self.end - self.start).total_seconds() / 60
    
    def is_blocking(self) -> bool:
        """Se é um evento intransponível"""
        return self.type in [AgendaEventType.SONO, AgendaEventType.REFEICAO]
    
    def is_flexible(self) -> bool:
        """Se pode ser movido/reagendado"""
        return not self.is_blocking() and self.priority.value <= 3
    
    def to_dict(self) -> Dict:
        """Converte para dicionário para serialização"""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "completed": self.completed,
            "auto_generated": self.auto_generated,
            "metadata": self.metadata,
            "book_id": self.book_id,
            "discipline": self.discipline,
            "priority": self.priority.value,
            "difficulty": self.difficulty,
            "progress_notes": self.progress_notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AgendaEvent':
        """Cria evento a partir de dicionário"""
        return cls(
            id=data["id"],
            type=AgendaEventType(data["type"]),
            title=data["title"],
            start=datetime.fromisoformat(data["start"]),
            end=datetime.fromisoformat(data["end"]),
            completed=data.get("completed", False),
            auto_generated=data.get("auto_generated", False),
            metadata=data.get("metadata", {}),
            book_id=data.get("book_id"),
            discipline=data.get("discipline"),
            priority=EventPriority(data.get("priority", 2)),
            difficulty=data.get("difficulty", 3),
            progress_notes=data.get("progress_notes", [])
        )


class TimeSlot:
    """Slot de tempo para alocação"""
    def __init__(self, start: datetime, end: datetime, 
                 available: bool = True, quality_score: float = 1.0):
        self.start = start
        self.end = end
        self.available = available
        self.quality_score = quality_score  # 0.0-1.0, baseado em preferências
    
    def duration_minutes(self) -> float:
        return (self.end - self.start).total_seconds() / 60
    
    def __lt__(self, other):
        return self.start < other.start


class AgendaManager:
    """Gestor principal de agenda - Cérebro do sistema"""
    
    def __init__(self, vault_path: str = None, user_id: str = "default_user"):
        """
        Inicializa o gerenciador de leituras
        
        Args:
            vault_path: Caminho para o vault do Obsidian
        """
        from pathlib import Path
        import os
        if vault_path is None:
            try:
                from ...config.settings import settings
                vault_path = settings.paths.vault
            except (ImportError, AttributeError):
                # Fallback para caminho padrão
                vault_path = os.path.expanduser("~/Documentos/Obsidian/Philosophy_Vault")
        self.vault_path = Path(vault_path).expanduser()
        self.user_id = user_id
        
        # Arquivos de dados
        self.agenda_file = self.vault_path / "06-RECURSOS" / "agenda.json"
        self.preferences_file = self.vault_path / "06-RECURSOS" / "preferences.json"
        
        # Inicializa módulos
        self.reading_manager = ReadingManager(vault_path)
        self.review_system = ReviewSystem(vault_path)
        self.writing_assistant = WritingAssistant(vault_path)
        # Pomodoro será inicializado quando necessário
        
        # Carrega dados
        self.events = self._load_events()
        self.user_preferences = self._load_preferences()
        
        # Estatísticas e aprendizado
        self.productivity_history = []
        self.adjustment_history = []
        
        # Configurações padrão
        self._setup_default_preferences()
    
    def _load_events(self) -> Dict[str, AgendaEvent]:
        """Carrega eventos da agenda"""
        events = {}
        
        if self.agenda_file.exists():
            try:
                with open(self.agenda_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for event_id, event_data in data.items():
                    events[event_id] = AgendaEvent.from_dict(event_data)
            except Exception as e:
                print(f"Erro ao carregar agenda: {e}")
                # Criar agenda vazia
                self._create_default_agenda()
        
        return events
    
    def _load_preferences(self) -> Dict:
        """Carrega preferências do usuário"""
        preferences = {}
        
        if self.preferences_file.exists():
            try:
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    preferences = json.load(f)
            except:
                pass
        
        return preferences
    
    def _setup_default_preferences(self):
        """Configura preferências padrão se não existirem"""
        defaults = {
            "sleep_schedule": {
                "start": "23:00",
                "end": "07:00"
            },
            "meal_times": {
                "breakfast": "08:00",
                "lunch": "12:30",
                "dinner": "19:30"
            },
            "work_preferences": {
                "production_time": "night",  # morning, afternoon, night
                "reading_sessions_per_day": 3,
                "pomodoro_duration": 25,
                "max_daily_work_hours": 8
            },
            "learning_style": {
                "review_method": "flashcards",
                "difficulty_adjustment": "auto"
            },
            "time_optimization": {
                "morning_peak": 8,   # 8-12
                "afternoon_peak": 14, # 14-17
                "night_peak": 19,     # 19-22
                "weekend_strategy": "light"
            }
        }
        
        # Mescla padrões com preferências existentes
        for key, value in defaults.items():
            if key not in self.user_preferences:
                self.user_preferences[key] = value
        
        self._save_preferences()
    
    def _create_default_agenda(self):
        """Cria agenda padrão com blocos fixos"""
        today = datetime.now().date()
        
        # Blocos fixos padrão
        default_events = [
            self._create_fixed_event("Sono", AgendaEventType.SONO, 
                                   "23:00", "07:00", EventPriority.BLOQUEIO),
            self._create_fixed_event("Café da Manhã", AgendaEventType.REFEICAO,
                                   "08:00", "08:30", EventPriority.BLOQUEIO),
            self._create_fixed_event("Almoço", AgendaEventType.REFEICAO,
                                   "12:30", "13:30", EventPriority.BLOQUEIO),
            self._create_fixed_event("Jantar", AgendaEventType.REFEICAO,
                                   "19:30", "20:30", EventPriority.BLOQUEIO)
        ]
        
        for event in default_events:
            self.events[event.id] = event
        
        self._save_events()
    
    def _create_fixed_event(self, title: str, event_type: AgendaEventType,
                          start_time: str, end_time: str, 
                          priority: EventPriority) -> AgendaEvent:
        """Cria evento fixo diário"""
        today = datetime.now().date()
        start = datetime.combine(today, datetime.strptime(start_time, "%H:%M").time())
        end = datetime.combine(today, datetime.strptime(end_time, "%H:%M").time())
        
        # Se o horário já passou hoje, agenda para amanhã
        if start < datetime.now():
            start += timedelta(days=1)
            end += timedelta(days=1)
        
        return AgendaEvent(
            id=str(uuid.uuid4()),
            type=event_type,
            title=title,
            start=start,
            end=end,
            priority=priority,
            auto_generated=True
        )
    
    def _save_events(self):
        """Salva eventos no arquivo"""
        try:
            data = {event_id: event.to_dict() 
                   for event_id, event in self.events.items()}
            
            self.agenda_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.agenda_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar agenda: {e}")
    
    def _save_preferences(self):
        """Salva preferências do usuário"""
        try:
            self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar preferências: {e}")
    
    # ====== MÉTODOS PÚBLICOS PRINCIPAIS ======
    
    def add_event(self, title: str, start: str, end: str, 
                 event_type: str = "casual", **kwargs) -> str:
        """
        Adiciona um evento à agenda
        
        Args:
            title: Título do evento
            start: Início (ISO format ou YYYY-MM-DD HH:MM)
            end: Fim (ISO format ou YYYY-MM-DD HH:MM)
            event_type: Tipo do evento
            **kwargs: Metadados adicionais
            
        Returns:
            ID do evento criado
        """
        # Converte strings para datetime
        try:
            start_dt = datetime.fromisoformat(start) if 'T' in start else \
                      datetime.strptime(start, "%Y-%m-%d %H:%M")
            end_dt = datetime.fromisoformat(end) if 'T' in end else \
                    datetime.strptime(end, "%Y-%m-%d %H:%M")
        except ValueError:
            # Tenta formato alternativo
            start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M")
            end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M")
        
        # Cria evento
        event = AgendaEvent(
            id=str(uuid.uuid4()),
            type=AgendaEventType(event_type),
            title=title,
            start=start_dt,
            end=end_dt,
            completed=False,
            auto_generated=False,
            metadata=kwargs
        )
        
        # Define prioridade baseada no tipo
        priority_map = {
            AgendaEventType.AULA: EventPriority.FIXO,
            AgendaEventType.ORIENTACAO: EventPriority.FIXO,
            AgendaEventType.PRODUCAO: EventPriority.ALTA,
            AgendaEventType.LEITURA: EventPriority.MEDIA,
            AgendaEventType.REVISAO: EventPriority.MEDIA,
            AgendaEventType.LAZER: EventPriority.BAIXA,
            AgendaEventType.CASUAL: EventPriority.BAIXA
        }
        
        event.priority = priority_map.get(event.type, EventPriority.MEDIA)
        
        # Adiciona à coleção
        self.events[event.id] = event
        self._save_events()
        
        return event.id
    
    def get_day_events(self, date_str: str = None) -> List[AgendaEvent]:
        """
        Retorna eventos de um dia específico
        
        Args:
            date_str: Data no formato YYYY-MM-DD (hoje se None)
            
        Returns:
            Lista de eventos ordenados por horário
        """
        if date_str is None:
            target_date = datetime.now().date()
        else:
            # Evita dependência de locale/strptime para robustez.
            raw_date = str(date_str).strip()
            if "T" in raw_date:
                raw_date = raw_date.split("T", 1)[0]
            try:
                target_date = date.fromisoformat(raw_date)
            except ValueError:
                # Fallback conservador para não quebrar a UI.
                target_date = datetime.now().date()
        
        day_events = []
        for event in self.events.values():
            if event.start.date() == target_date and not event.completed:
                day_events.append(event)
        
        # Ordena por horário
        day_events.sort(key=lambda x: x.start)
        return day_events
    
    def find_free_slots(self, date: str, duration_minutes: int,
                       start_hour: int = 8, end_hour: int = 22,
                       exclude_types: List[str] = None,
                       consider_preferences: bool = True) -> List[Dict]:
        """
        Encontra horários livres otimizados considerando preferências
        
        Args:
            date: Data no formato YYYY-MM-DD
            duration_minutes: Duração necessária
            start_hour: Hora inicial do dia
            end_hour: Hora final do dia
            exclude_types: Tipos de eventos a excluir
            consider_preferences: Se True, considera picos de produtividade
            
        Returns:
            Lista de slots otimizados
        """
        from datetime import datetime, timedelta
        
        # Eventos do dia
        day_events = self.get_day_events(date)
        
        # Converte para datetime sem depender de locale.
        day_start = datetime.fromisoformat(f"{date}T{start_hour:02d}:00")
        day_end = datetime.fromisoformat(f"{date}T{end_hour:02d}:00")
        
        # Blocos ocupados
        occupied = []
        for event in day_events:
            if exclude_types and event.type.value in exclude_types:
                continue
            occupied.append((event.start, event.end))
        
        # Ordena por horário
        occupied.sort(key=lambda x: x[0])
        
        # Encontra lacunas
        free_slots = []
        current = day_start
        
        for occ_start, occ_end in occupied:
            if occ_start > current:
                gap_minutes = (occ_start - current).total_seconds() / 60
                if gap_minutes >= duration_minutes:
                    free_slots.append({
                        "start": current,
                        "end": occ_start,
                        "duration_minutes": gap_minutes,
                        "quality_score": self._calculate_time_quality(current, gap_minutes)
                    })
            current = max(current, occ_end)
        
        # Slot final do dia
        if current < day_end:
            remaining_minutes = (day_end - current).total_seconds() / 60
            if remaining_minutes >= duration_minutes:
                free_slots.append({
                    "start": current,
                    "end": day_end,
                    "duration_minutes": remaining_minutes,
                    "quality_score": self._calculate_time_quality(current, remaining_minutes)
                })
        
        # Ordena por qualidade (melhor horário primeiro)
        if consider_preferences:
            free_slots.sort(key=lambda x: x["quality_score"], reverse=True)
        
        # Converte para formato de retorno
        result = []
        for slot in free_slots:
            if slot["duration_minutes"] >= duration_minutes:
                result.append({
                    "start": slot["start"].strftime("%Y-%m-%d %H:%M"),
                    "end": slot["end"].strftime("%Y-%m-%d %H:%M"),
                    "duration_minutes": slot["duration_minutes"],
                    "quality_score": slot["quality_score"]
                })
        
        return result
    
    def _calculate_time_quality(self, start_time: datetime, 
                               duration_minutes: float) -> float:
        """
        Calcula qualidade de um horário baseado nas preferências
        
        Args:
            start_time: Horário de início
            duration_minutes: Duração em minutos
            
        Returns:
            Score de qualidade (0.0-1.0)
        """
        hour = start_time.hour
        weekday = start_time.weekday()  # 0=segunda, 6=domingo
        
        # Score baseado no período do dia
        period_score = 0.5  # neutro
        
        if 8 <= hour < 12:
            period_score = 0.8  # manhã boa para leitura densa
        elif 14 <= hour < 18:
            period_score = 0.7  # tarde boa para revisão
        elif 19 <= hour < 22:
            period_score = 0.9  # noite boa para produção
        elif 22 <= hour < 23:
            period_score = 0.3  # tarde demais
        elif 6 <= hour < 8:
            period_score = 0.6  # madrugada pode ser produtiva para alguns
        
        # Ajusta por dia da semana
        day_factor = 1.0
        if weekday == 6:  # domingo
            day_factor = 0.7  # mais leve
        elif weekday >= 4:  # sexta/sábado
            day_factor = 0.9
        
        # Ajusta por duração (sessões muito longas são menos eficientes)
        duration_factor = 1.0
        if duration_minutes > 120:
            duration_factor = 0.7
        elif duration_minutes < 30:
            duration_factor = 0.8
        
        return period_score * day_factor * duration_factor
    
    def allocate_reading_time(self, book_id: str, pages_per_day: float,
                            reading_speed: float = 10.0,
                            days_off: List[int] = None,
                            max_daily_minutes: int = 180,
                            strategy: str = "balanced") -> Dict:
        """
        Aloca tempo de leitura na agenda usando algoritmo otimizado
        
        Args:
            book_id: ID do livro
            pages_per_day: Média de páginas por dia
            reading_speed: Velocidade de leitura (páginas/hora)
            days_off: Dias sem estudo (padrão: [6] - domingo)
            max_daily_minutes: Máximo de minutos por dia
            strategy: Estratégia de alocação (balanced, intensive, spaced)
            
        Returns:
            Dicionário com alocações criadas
        """
        if days_off is None:
            days_off = [6]  # domingo por padrão
        
        # Obtém informações do livro
        book_progress = self.reading_manager.get_reading_progress(book_id)
        if not book_progress:
            return {"error": "Livro não encontrado"}
        
        # Calcula tempo necessário
        pages_per_hour = max(reading_speed, 1)
        minutes_per_page = 60 / pages_per_hour
        required_minutes_per_day = pages_per_day * minutes_per_page
        
        # Limita ao máximo diário
        required_minutes_per_day = min(required_minutes_per_day, max_daily_minutes)
        
        # Define estratégia
        session_settings = {
            "balanced": {"min_session": 30, "max_session": 90, "sessions_per_day": 2},
            "intensive": {"min_session": 45, "max_session": 120, "sessions_per_day": 3},
            "spaced": {"min_session": 25, "max_session": 50, "sessions_per_day": 4}
        }
        
        settings = session_settings.get(strategy, session_settings["balanced"])
        
        # Encontra dias até o prazo
        allocations = {}
        today = datetime.now()
        days_ahead = 60  # planeja até 60 dias à frente
        
        for day_offset in range(days_ahead):
            day = today + timedelta(days=day_offset)
            
            # Pula dias de folga
            if day.weekday() in days_off:
                continue
            
            date_str = day.strftime("%Y-%m-%d")
            
            # Define horários ideais baseado no tipo de atividade
            if strategy == "intensive":
                time_windows = [(9, 12), (14, 17), (19, 21)]  # manhã, tarde, noite
            else:
                time_windows = [(9, 12), (15, 18)]  # manhã e fim da tarde
            
            # Tenta alocar em cada janela de tempo
            for window_start, window_end in time_windows:
                free_slots = self.find_free_slots(
                    date_str,
                    duration_minutes=settings["min_session"],
                    start_hour=window_start,
                    end_hour=window_end,
                    exclude_types=['aula', 'reunião', 'orientação'],
                    consider_preferences=True
                )
                
                if free_slots:
                    # Pega o melhor slot (maior qualidade)
                    best_slot = free_slots[0]
                    
                    # Calcula páginas para este slot
                    slot_minutes = best_slot["duration_minutes"]
                    slot_pages = int(slot_minutes / minutes_per_page)
                    
                    # Cria evento
                    event_id = self.add_event(
                        title=f"Leitura: {book_progress.get('title', book_id)}",
                        start=best_slot["start"],
                        end=best_slot["end"],
                        event_type="leitura",
                        discipline="Filosofia",
                        book_id=book_id,
                        difficulty=3  # padrão, ajustável
                    )
                    
                    allocations[f"{date_str}_{window_start}"] = {
                        "event_id": event_id,
                        "date": date_str,
                        "time_slot": f"{best_slot['start'][11:16]} - {best_slot['end'][11:16]}",
                        "duration_minutes": slot_minutes,
                        "pages_planned": slot_pages,
                        "quality_score": best_slot.get("quality_score", 0.5)
                    }
                    
                    # Atualiza páginas restantes
                    pages_per_day -= slot_pages
                    
                    if pages_per_day <= 0:
                        break
            
            if pages_per_day <= 0:
                break
        
        # Registra estatísticas
        self._record_allocation_statistics(allocations, strategy)
        
        return {
            "book_id": book_id,
            "strategy": strategy,
            "total_sessions": len(allocations),
            "allocations": allocations
        }
    
    def emergency_mode(self, objective: str, days: int = 3,
                      focus_area: str = None) -> Dict:
        """
        Modo emergência - reorganiza agenda para foco intensivo
        
        Args:
            objective: Objetivo (ex: "Prova de Ética")
            days: Número de dias de foco
            focus_area: Área específica (ex: "Filosofia Moral")
            
        Returns:
            Plano de emergência
        """
        today = datetime.now()
        emergency_plan = {
            "objective": objective,
            "days": days,
            "start_date": today.strftime("%Y-%m-%d"),
            "end_date": (today + timedelta(days=days)).strftime("%Y-%m-%d"),
            "original_events_moved": [],
            "new_schedule": [],
            "warnings": []
        }
        
        # 1. Identifica eventos que podem ser movidos
        movable_events = []
        for event_id, event in self.events.items():
            if (event.start.date() >= today.date() and 
                event.start.date() <= today.date() + timedelta(days=days)):
                
                if event.is_flexible() and not event.completed:
                    movable_events.append(event)
        
        # 2. Move eventos para após o período de emergência
        for event in movable_events:
            new_start = event.start + timedelta(days=days + 2)  # +2 dias de buffer
            new_end = event.end + timedelta(days=days + 2)
            
            emergency_plan["original_events_moved"].append({
                "event_id": event.id,
                "original_title": event.title,
                "original_time": event.start.strftime("%Y-%m-%d %H:%M"),
                "new_time": new_start.strftime("%Y-%m-%d %H:%M")
            })
            
            # Atualiza evento
            event.start = new_start
            event.end = new_end
        
        # 3. Cria cronograma intensivo
        intensive_schedule = []
        for day_offset in range(days):
            day_date = today + timedelta(days=day_offset)
            date_str = day_date.strftime("%Y-%m-%d")
            
            # Blocos do dia (8 blocos de 1.5h com pausas)
            daily_blocks = [
                ("08:00", "09:30", "Revisão Intensiva"),
                ("09:45", "11:15", "Leitura Condensada"),
                ("11:30", "13:00", "Prática/Exercícios"),
                ("14:00", "15:30", "Mapas Mentais"),
                ("15:45", "17:15", "Flashcards Focados"),
                ("17:30", "19:00", "Simulado/Prova"),
                ("19:30", "21:00", "Síntese Final")
            ]
            
            for block_start, block_end, activity in daily_blocks:
                start_dt = datetime.strptime(f"{date_str} {block_start}", "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(f"{date_str} {block_end}", "%Y-%m-%d %H:%M")
                
                event_id = self.add_event(
                    title=f"[EMERGÊNCIA] {activity}: {objective}",
                    start=start_dt.isoformat(),
                    end=end_dt.isoformat(),
                    event_type="leitura" if "Leitura" in activity else "revisao",
                    priority=EventPriority.ALTA.value,
                    emergency_mode=True
                )
                
                intensive_schedule.append({
                    "date": date_str,
                    "time": f"{block_start}-{block_end}",
                    "activity": activity,
                    "event_id": event_id
                })
        
        emergency_plan["new_schedule"] = intensive_schedule
        
        # 4. Avisos
        emergency_plan["warnings"].append(
            f"{len(movable_events)} eventos foram reagendados"
        )
        emergency_plan["warnings"].append(
            f"Dormirá aproximadamente 1h menos por dia durante este período"
        )
        emergency_plan["warnings"].append(
            "Considere pausas para alimentação e hidratação"
        )
        
        # Salva mudanças
        self._save_events()
        
        return emergency_plan
    
    def generate_weekly_review(self, week_start: str = None) -> Dict:
        """
        Gera análise da semana (dominical)
        
        Args:
            week_start: Data de início da semana (YYYY-MM-DD)
            
        Returns:
            Análise completa da semana
        """
        if week_start is None:
            # Encontra o último domingo
            today = datetime.now().date()
            week_start_date = today - timedelta(days=today.weekday() + 1)
            week_start = week_start_date.strftime("%Y-%m-%d")
        
        week_start_dt = datetime.strptime(week_start, "%Y-%m-%d")
        week_end_dt = week_start_dt + timedelta(days=6)
        
        # Coleta eventos da semana
        week_events = []
        for event in self.events.values():
            if week_start_dt.date() <= event.start.date() <= week_end_dt.date():
                week_events.append(event)
        
        # Estatísticas
        stats = {
            "total_events": len(week_events),
            "completed_events": sum(1 for e in week_events if e.completed),
            "completion_rate": 0,
            "time_by_category": defaultdict(float),
            "productivity_score": 0
        }
        
        # Calcula tempo por categoria
        for event in week_events:
            duration_hours = event.duration_minutes() / 60
            stats["time_by_category"][event.type.value] += duration_hours
        
        # Taxa de conclusão
        if stats["total_events"] > 0:
            stats["completion_rate"] = (stats["completed_events"] / stats["total_events"]) * 100
        
        # Score de produtividade
        productive_categories = ["leitura", "producao", "revisao", "aula"]
        productive_time = sum(
            stats["time_by_category"].get(cat, 0) 
            for cat in productive_categories
        )
        
        total_awake_time = 16 * 7  # 16 horas/dia × 7 dias
        stats["productivity_score"] = (productive_time / total_awake_time) * 100
        
        # Recomendações
        recommendations = []
        
        if stats["completion_rate"] < 70:
            recommendations.append({
                "type": "completion",
                "message": "Taxa de conclusão baixa. Considere ajustar metas para a próxima semana.",
                "priority": "medium"
            })
        
        if stats["time_by_category"].get("lazer", 0) < 10:
            recommendations.append({
                "type": "balance",
                "message": "Pouco tempo de lazer registrado. Lembre-se do equilíbrio trabalho-descanso.",
                "priority": "low"
            })
        
        if productive_time > 50:
            recommendations.append({
                "type": "intensity",
                "message": "Semana muito intensa. Considere incluir mais pausas na próxima semana.",
                "priority": "high"
            })
        
        # Próximos passos
        next_week_plan = self._generate_next_week_plan(week_end_dt + timedelta(days=1))
        
        review = {
            "period": {
                "start": week_start,
                "end": week_end_dt.strftime("%Y-%m-%d")
            },
            "statistics": stats,
            "event_breakdown": dict(stats["time_by_category"]),
            "recommendations": recommendations,
            "next_week_preview": next_week_plan,
            "generated_at": datetime.now().isoformat()
        }
        
        # Salva review no vault
        self._save_weekly_review(review)
        
        return review
    
    def _generate_next_week_plan(self, start_date: datetime) -> Dict:
        """Gera prévia da próxima semana"""
        # Simples: analisa eventos já agendados
        next_week_events = []
        for event in self.events.values():
            if start_date.date() <= event.start.date() <= start_date.date() + timedelta(days=6):
                next_week_events.append(event)
        
        return {
            "total_events": len(next_week_events),
            "focus_areas": self._extract_focus_areas(next_week_events),
            "estimated_workload": self._calculate_workload(next_week_events)
        }
    
    def _extract_focus_areas(self, events: List[AgendaEvent]) -> List[str]:
        """Extrai áreas de foco dos eventos"""
        focus_areas = set()
        for event in events:
            if event.discipline:
                focus_areas.add(event.discipline)
            elif event.book_id:
                # Tenta obter disciplina do livro
                progress = self.reading_manager.get_reading_progress(event.book_id)
                if progress:
                    focus_areas.add("Leitura")
        
        return list(focus_areas)
    
    def _calculate_workload(self, events: List[AgendaEvent]) -> Dict:
        """Calcula carga de trabalho"""
        productive_minutes = 0
        for event in events:
            if event.type in [AgendaEventType.LEITURA, AgendaEventType.PRODUCAO, 
                            AgendaEventType.REVISAO, AgendaEventType.AULA]:
                productive_minutes += event.duration_minutes()
        
        return {
            "productive_hours": productive_minutes / 60,
            "intensity": "alta" if productive_minutes > 3000 else 
                        "media" if productive_minutes > 2000 else "baixa"
        }
    
    def _save_weekly_review(self, review: Dict):
        """Salva review no vault"""
        review_dir = self.vault_path / "06-RECURSOS" / "reviews"
        review_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"weekly_review_{review['period']['start']}.json"
        filepath = review_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(review, f, indent=2, ensure_ascii=False)
    
    def _record_allocation_statistics(self, allocations: Dict, strategy: str):
        """Registra estatísticas de alocações para aprendizado"""
        stats_entry = {
            "date": datetime.now().isoformat(),
            "strategy": strategy,
            "total_sessions": len(allocations),
            "avg_quality_score": 0
        }
        
        if allocations:
            scores = [a.get("quality_score", 0.5) for a in allocations.values()]
            stats_entry["avg_quality_score"] = sum(scores) / len(scores)
        
        self.productivity_history.append(stats_entry)
        
        # Mantém apenas histórico recente
        if len(self.productivity_history) > 100:
            self.productivity_history = self.productivity_history[-100:]
    
    def get_productivity_insights(self) -> Dict:
        """
        Retorna insights baseados no histórico
        
        Returns:
            Insights de produtividade
        """
        if not self.productivity_history:
            return {"message": "Histórico insuficiente para insights"}
        
        # Análise básica
        total_sessions = sum(entry["total_sessions"] for entry in self.productivity_history)
        avg_quality = sum(entry.get("avg_quality_score", 0) 
                         for entry in self.productivity_history) / len(self.productivity_history)
        
        insights = {
            "total_sessions_allocated": total_sessions,
            "average_quality_score": round(avg_quality, 2),
            "recommended_strategy": self._recommend_strategy(),
            "peak_performance_times": self._identify_peak_times()
        }
        
        return insights
    
    def _recommend_strategy(self) -> str:
        """Recomenda estratégia baseada no histórico"""
        if not self.productivity_history:
            return "balanced"
        
        # Simples: se qualidade média baixa, sugere mudança
        avg_quality = sum(entry.get("avg_quality_score", 0) 
                         for entry in self.productivity_history) / len(self.productivity_history)
        
        if avg_quality < 0.5:
            return "spaced"
        elif avg_quality > 0.7:
            return "intensive"
        else:
            return "balanced"
    
    def _identify_peak_times(self) -> List[Dict]:
        """Identifica horários de pico baseado no histórico"""
        # Implementação simplificada
        return [
            {"period": "manhã", "time": "08:00-12:00", "score": 0.8},
            {"period": "tarde", "time": "14:00-17:00", "score": 0.7},
            {"period": "noite", "time": "19:00-22:00", "score": 0.9}
        ]
    
    def transition_to_review(self, book_id: str, review_type: str = "spaced",
                           deadline: str = None) -> Dict:
        """
        Transição automática de leitura para revisão
        
        Args:
            book_id: ID do livro concluído
            review_type: Tipo de revisão (spaced, intensive, summary)
            deadline: Prazo para revisão (padrão: 7 dias)
            
        Returns:
            Plano de revisão
        """
        # Marca livro como concluído no ReadingManager
        book_progress = self.reading_manager.get_reading_progress(book_id)
        if not book_progress:
            return {"error": "Livro não encontrado"}
        
        # Define prazo padrão
        if deadline is None:
            deadline_date = datetime.now() + timedelta(days=7)
        else:
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
        
        # Cria plano de revisão
        review_plan = {
            "book_id": book_id,
            "book_title": book_progress.get("title", "Desconhecido"),
            "review_type": review_type,
            "deadline": deadline_date.strftime("%Y-%m-%d"),
            "sessions_created": [],
            "flashcards_generated": 0
        }
        
        # Substitui blocos de leitura por revisão
        for event_id, event in self.events.items():
            if (event.book_id == book_id and event.type == AgendaEventType.LEITURA and
                not event.completed and event.start > datetime.now()):
                
                # Atualiza evento para revisão
                event.type = AgendaEventType.REVISAO
                event.title = f"Revisão: {book_progress.get('title', book_id)}"
                event.metadata["review_type"] = review_type
                
                review_plan["sessions_created"].append({
                    "event_id": event_id,
                    "date": event.start.strftime("%Y-%m-%d"),
                    "time": event.start.strftime("%H:%M")
                })
        
        # Gera flashcards no ReviewSystem
        flashcards = self.review_system.generate_flashcards(
            source="book",
            tags=[book_id],
            limit=20
        )
        
        review_plan["flashcards_generated"] = len(flashcards)
        
        # Agenda revisão espaçada
        if review_type == "spaced":
            spaced_dates = [
                datetime.now() + timedelta(days=1),
                datetime.now() + timedelta(days=3),
                datetime.now() + timedelta(days=7),
                datetime.now() + timedelta(days=14)
            ]
            
            for i, review_date in enumerate(spaced_dates):
                event_id = self.add_event(
                    title=f"Revisão Espaçada {i+1}: {book_progress.get('title', book_id)}",
                    start=review_date.strftime("%Y-%m-%d 09:00"),
                    end=review_date.strftime("%Y-%m-%d 09:45"),
                    event_type="revisao",
                    book_id=book_id,
                    metadata={"spaced_repetition": True, "interval": i+1}
                )
        
        self._save_events()
        
        return review_plan
    
    def get_upcoming_deadlines(self, days: int = 7) -> List[Dict]:
        """
        Retorna prazos próximos
        
        Args:
            days: Número de dias à frente para verificar
            
        Returns:
            Lista de prazos próximos
        """
        today = datetime.now()
        cutoff = today + timedelta(days=days)
        
        deadlines = []
        
        # Verifica eventos com alta prioridade
        for event in self.events.values():
            if (event.start.date() <= cutoff.date() and 
                not event.completed and
                event.priority in [EventPriority.ALTA, EventPriority.FIXO]):
                
                days_until = (event.start.date() - today.date()).days
                
                deadlines.append({
                    "event_id": event.id,
                    "title": event.title,
                    "date": event.start.strftime("%Y-%m-%d"),
                    "time": event.start.strftime("%H:%M"),
                    "days_until": days_until,
                    "priority": event.priority.name,
                    "type": event.type.value
                })
        
        # Ordena por data e prioridade
        deadlines.sort(key=lambda x: (x["days_until"], -EventPriority[x["priority"]].value))
        
        return deadlines
    
    def suggest_optimizations(self) -> List[Dict]:
        """
        Sugere otimizações na agenda
        
        Returns:
            Lista de sugestões
        """
        suggestions = []
        today = datetime.now()
        
        # Analisa próximos 7 dias
        for day_offset in range(7):
            day_date = today + timedelta(days=day_offset)
            date_str = day_date.strftime("%Y-%m-%d")
            day_events = self.get_day_events(date_str)
            
            # Verifica sobrecarga
            productive_minutes = 0
            for event in day_events:
                if event.type in [AgendaEventType.LEITURA, AgendaEventType.PRODUCAO, 
                                AgendaEventType.REVISAO, AgendaEventType.AULA]:
                    productive_minutes += event.duration_minutes()
            
            if productive_minutes > 480:  # > 8 horas
                suggestions.append({
                    "type": "overload",
                    "date": date_str,
                    "message": f"Sobrecarga detectada: {productive_minutes/60:.1f}h de trabalho",
                    "suggestion": "Considere redistribuir algumas atividades"
                })
            
            # Verifica blocos muito longos sem pausa
            events_sorted = sorted(day_events, key=lambda x: x.start)
            for i in range(len(events_sorted) - 1):
                current = events_sorted[i]
                next_event = events_sorted[i + 1]
                
                gap = (next_event.start - current.end).total_seconds() / 60
                
                if (current.type in [AgendaEventType.LEITURA, AgendaEventType.PRODUCAO] and
                    next_event.type in [AgendaEventType.LEITURA, AgendaEventType.PRODUCAO] and
                    gap < 15):
                    
                    suggestions.append({
                        "type": "back_to_back",
                        "date": date_str,
                        "message": f"Blocos intensivos consecutivos: {current.title} → {next_event.title}",
                        "suggestion": "Adicione uma pausa de 15-20 minutos entre sessões intensivas"
                    })
        
        # Verifica equilíbrio trabalho-descanso
        leisure_events = [e for e in self.events.values() 
                         if e.type == AgendaEventType.LAZER and not e.completed]
        
        if len(leisure_events) < 3:  # Menos de 3 eventos de lazer na semana
            suggestions.append({
                "type": "balance",
                "message": "Poucas atividades de lazer agendadas",
                "suggestion": "Considere agendar pelo menos 3 períodos de lazer por semana"
            })
        
        return suggestions
