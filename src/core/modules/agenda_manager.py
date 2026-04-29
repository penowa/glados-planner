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
from .smart_allocator import SmartAllocator
from .pomodoro_timer import PomodoroTimer
from .writing_assistant import WritingAssistant


class AgendaEventType(Enum):
    """Tipos de compromissos no sistema"""
    AULA = "aula"
    LEITURA = "leitura"
    PRODUCAO = "producao"
    REVISAO = "revisao"
    ORIENTACAO = "orientacao"
    REUNIAO = "reuniao"
    GRUPO_ESTUDO = "grupo_estudo"
    REFEICAO = "refeicao"
    SONO = "sono"
    LAZER = "lazer"
    CASUAL = "casual"
    PROVA = "prova"
    SEMINARIO = "seminario"
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
                vault_path = os.path.expanduser("~/Documentos/Obsidian/Planner")
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
        self._sync_weekly_review_events()
    
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
            "protected_time_blocks": [
                {
                    "title": "Café da manhã",
                    "type": "refeicao",
                    "start": "08:00",
                    "end": "08:30",
                    "weekdays": [0, 1, 2, 3, 4, 5, 6],
                },
                {
                    "title": "Janela de almoço",
                    "type": "refeicao",
                    "start": "11:00",
                    "end": "14:00",
                    "weekdays": [0, 1, 2, 3, 4, 5, 6],
                },
                {
                    "title": "Janela de jantar",
                    "type": "refeicao",
                    "start": "18:00",
                    "end": "20:00",
                    "weekdays": [0, 1, 2, 3, 4, 5, 6],
                },
            ],
            "weekly_review": {
                "weekday": 6,  # domingo
                "time": "18:00",
                "duration_minutes": 90
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

    def _normalize_hhmm(self, value: str, fallback: str) -> str:
        """Normaliza string HH:MM para formato estável."""
        raw = str(value or "").strip()
        try:
            dt = datetime.strptime(raw, "%H:%M")
            return dt.strftime("%H:%M")
        except Exception:
            return fallback

    def _parse_hhmm(self, value: str) -> Optional[Tuple[int, int]]:
        """Converte HH:MM em (hora, minuto)."""
        raw = str(value or "").strip()
        try:
            parsed = datetime.strptime(raw, "%H:%M")
            return parsed.hour, parsed.minute
        except Exception:
            return None

    def _normalized_protected_time_blocks(self) -> List[Dict[str, Any]]:
        """Retorna blocos protegidos recorrentes em formato estável."""
        raw_blocks = self.user_preferences.get("protected_time_blocks", [])
        if not isinstance(raw_blocks, list) or not raw_blocks:
            raw_blocks = [
                {
                    "title": "Café da manhã",
                    "type": "refeicao",
                    "start": "08:00",
                    "end": "08:30",
                    "weekdays": [0, 1, 2, 3, 4, 5, 6],
                },
                {
                    "title": "Janela de almoço",
                    "type": "refeicao",
                    "start": "11:00",
                    "end": "14:00",
                    "weekdays": [0, 1, 2, 3, 4, 5, 6],
                },
                {
                    "title": "Janela de jantar",
                    "type": "refeicao",
                    "start": "18:00",
                    "end": "20:00",
                    "weekdays": [0, 1, 2, 3, 4, 5, 6],
                },
            ]

        normalized: List[Dict[str, Any]] = []
        valid_types = {item.value for item in AgendaEventType}

        for index, block in enumerate(raw_blocks):
            if not isinstance(block, dict):
                continue

            start_hhmm = self._normalize_hhmm(block.get("start"), "")
            end_hhmm = self._normalize_hhmm(block.get("end"), "")
            if not start_hhmm or not end_hhmm:
                continue

            raw_weekdays = block.get("weekdays", [0, 1, 2, 3, 4, 5, 6])
            weekdays: List[int] = []
            if isinstance(raw_weekdays, (list, tuple, set)):
                for item in raw_weekdays:
                    try:
                        weekday = int(item)
                    except Exception:
                        continue
                    if 0 <= weekday <= 6 and weekday not in weekdays:
                        weekdays.append(weekday)
            elif raw_weekdays is None:
                weekdays = [0, 1, 2, 3, 4, 5, 6]
            else:
                try:
                    weekday = int(raw_weekdays)
                    if 0 <= weekday <= 6:
                        weekdays = [weekday]
                except Exception:
                    weekdays = [0, 1, 2, 3, 4, 5, 6]

            if not weekdays:
                continue

            block_type = str(block.get("type") or "refeicao").strip().lower()
            if block_type not in valid_types:
                block_type = AgendaEventType.REFEICAO.value

            try:
                priority = EventPriority(int(block.get("priority", EventPriority.BLOQUEIO.value)))
            except Exception:
                priority = EventPriority.BLOQUEIO

            normalized.append(
                {
                    "title": str(block.get("title") or f"Bloco protegido {index + 1}").strip() or f"Bloco protegido {index + 1}",
                    "type": block_type,
                    "start": start_hhmm,
                    "end": end_hhmm,
                    "weekdays": weekdays,
                    "priority": priority,
                }
            )

        return normalized

    def _build_virtual_routine_events(self, target_day: date) -> List[AgendaEvent]:
        """Gera eventos virtuais recorrentes de rotina para um dia."""
        events: List[AgendaEvent] = []
        day_anchor = datetime.combine(target_day, datetime.min.time())

        sleep_cfg = self.user_preferences.get("sleep_schedule", {"start": "23:00", "end": "07:00"})
        sleep_end = self._parse_hhmm(sleep_cfg.get("end", "07:00"))
        sleep_start = self._parse_hhmm(sleep_cfg.get("start", "23:00"))

        if sleep_end:
            end_dt = day_anchor.replace(hour=sleep_end[0], minute=sleep_end[1], second=0, microsecond=0)
            if end_dt > day_anchor:
                events.append(
                    AgendaEvent(
                        id=f"virtual-sleep-morning-{target_day.isoformat()}",
                        type=AgendaEventType.SONO,
                        title="Sono",
                        start=day_anchor,
                        end=end_dt,
                        auto_generated=True,
                        priority=EventPriority.BLOQUEIO,
                        metadata={"virtual": True, "routine_block": True},
                    )
                )

        if sleep_start:
            start_dt = day_anchor.replace(hour=sleep_start[0], minute=sleep_start[1], second=0, microsecond=0)
            end_dt = day_anchor.replace(hour=23, minute=59, second=0, microsecond=0)
            if end_dt > start_dt:
                events.append(
                    AgendaEvent(
                        id=f"virtual-sleep-night-{target_day.isoformat()}",
                        type=AgendaEventType.SONO,
                        title="Sono",
                        start=start_dt,
                        end=end_dt,
                        auto_generated=True,
                        priority=EventPriority.BLOQUEIO,
                        metadata={"virtual": True, "routine_block": True},
                    )
                )

        for index, block in enumerate(self._normalized_protected_time_blocks()):
            if target_day.weekday() not in block["weekdays"]:
                continue

            start_parts = self._parse_hhmm(block["start"])
            end_parts = self._parse_hhmm(block["end"])
            if not start_parts or not end_parts:
                continue

            start_dt = day_anchor.replace(hour=start_parts[0], minute=start_parts[1], second=0, microsecond=0)
            end_dt = day_anchor.replace(hour=end_parts[0], minute=end_parts[1], second=0, microsecond=0)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

            events.append(
                AgendaEvent(
                    id=f"virtual-block-{index}-{target_day.isoformat()}",
                    type=AgendaEventType(block["type"]),
                    title=block["title"],
                    start=start_dt,
                    end=end_dt,
                    auto_generated=True,
                    priority=block["priority"],
                    metadata={"virtual": True, "routine_block": True},
                )
            )

        return events

    def get_virtual_fixed_events(self, date_str: str = None) -> List[Dict[str, Any]]:
        """Expõe eventos virtuais recorrentes para a UI."""
        if date_str is None:
            target_day = datetime.now().date()
        else:
            raw_date = str(date_str).strip()
            if "T" in raw_date:
                raw_date = raw_date.split("T", 1)[0]
            try:
                target_day = date.fromisoformat(raw_date)
            except ValueError:
                target_day = datetime.now().date()
        return [event.to_dict() for event in self._build_virtual_routine_events(target_day)]

    def _occupied_ranges_for_day(
        self,
        target_day: date,
        exclude_types: Optional[List[str]] = None,
        include_virtual_blocks: bool = True,
    ) -> List[Tuple[datetime, datetime]]:
        """Lista intervalos ocupados por eventos reais e blocos recorrentes."""
        ignored_types = {
            str(item or "").strip().lower()
            for item in (exclude_types or [])
            if str(item or "").strip()
        }

        occupied: List[Tuple[datetime, datetime]] = []
        for event in self.get_day_events(target_day.isoformat()):
            if event.type.value in ignored_types:
                continue
            occupied.append((event.start, event.end))

        if include_virtual_blocks:
            for event in self._build_virtual_routine_events(target_day):
                if event.type.value in ignored_types:
                    continue
                occupied.append((event.start, event.end))

        occupied.sort(key=lambda item: item[0])
        return occupied

    def get_routine_preferences(self) -> Dict[str, Any]:
        """Retorna preferências de rotina em formato simplificado para UI."""
        sleep_cfg = self.user_preferences.get("sleep_schedule", {})
        meal_cfg = self.user_preferences.get("meal_times", {})
        review_cfg = self.user_preferences.get("weekly_review", {})
        return {
            "sleep_start": self._normalize_hhmm(sleep_cfg.get("start", "23:00"), "23:00"),
            "sleep_end": self._normalize_hhmm(sleep_cfg.get("end", "07:00"), "07:00"),
            "breakfast_time": self._normalize_hhmm(meal_cfg.get("breakfast", "08:00"), "08:00"),
            "lunch_time": self._normalize_hhmm(meal_cfg.get("lunch", "12:30"), "12:30"),
            "dinner_time": self._normalize_hhmm(meal_cfg.get("dinner", "19:30"), "19:30"),
            "weekly_review_time": self._normalize_hhmm(review_cfg.get("time", "18:00"), "18:00"),
            "weekly_review_duration_minutes": int(review_cfg.get("duration_minutes", 90) or 90),
            "weekly_review_weekday": int(review_cfg.get("weekday", 6) or 6),
        }

    def update_routine_preferences(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza preferências de rotina e sincroniza revisão semanal.

        Args:
            updates: dicionário de preferências vindas da UI

        Returns:
            Preferências já normalizadas
        """
        current = self.get_routine_preferences()
        merged = {**current, **(updates or {})}

        sleep_start = self._normalize_hhmm(merged.get("sleep_start"), current["sleep_start"])
        sleep_end = self._normalize_hhmm(merged.get("sleep_end"), current["sleep_end"])
        breakfast = self._normalize_hhmm(merged.get("breakfast_time"), current["breakfast_time"])
        lunch = self._normalize_hhmm(merged.get("lunch_time"), current["lunch_time"])
        dinner = self._normalize_hhmm(merged.get("dinner_time"), current["dinner_time"])
        review_time = self._normalize_hhmm(merged.get("weekly_review_time"), current["weekly_review_time"])

        try:
            review_duration = int(merged.get("weekly_review_duration_minutes", current["weekly_review_duration_minutes"]))
        except Exception:
            review_duration = current["weekly_review_duration_minutes"]
        review_duration = max(30, min(240, review_duration))

        self.user_preferences.setdefault("sleep_schedule", {})
        self.user_preferences["sleep_schedule"]["start"] = sleep_start
        self.user_preferences["sleep_schedule"]["end"] = sleep_end

        self.user_preferences.setdefault("meal_times", {})
        self.user_preferences["meal_times"]["breakfast"] = breakfast
        self.user_preferences["meal_times"]["lunch"] = lunch
        self.user_preferences["meal_times"]["dinner"] = dinner

        self.user_preferences.setdefault("weekly_review", {})
        self.user_preferences["weekly_review"]["weekday"] = 6
        self.user_preferences["weekly_review"]["time"] = review_time
        self.user_preferences["weekly_review"]["duration_minutes"] = review_duration

        self._save_preferences()
        self._sync_weekly_review_events()
        return self.get_routine_preferences()

    def _sync_weekly_review_events(self, weeks_ahead: int = 12):
        """Mantém eventos de revisão dominical alinhados com as preferências."""
        review_cfg = self.user_preferences.get("weekly_review", {})
        review_time = self._normalize_hhmm(review_cfg.get("time", "18:00"), "18:00")
        try:
            review_duration = int(review_cfg.get("duration_minutes", 90) or 90)
        except Exception:
            review_duration = 90
        review_duration = max(30, min(240, review_duration))

        now = datetime.now()
        today = now.date()

        # Remove revisões dominicais auto-geradas futuras para recriar com novo horário.
        to_remove = []
        for event_id, event in self.events.items():
            if (
                event.type == AgendaEventType.REVISAO_DOMINICAL
                and event.auto_generated
                and event.start.date() >= today
            ):
                to_remove.append(event_id)
        for event_id in to_remove:
            self.events.pop(event_id, None)

        # Agenda revisões nos próximos domingos.
        first_sunday = today + timedelta(days=(6 - today.weekday()) % 7)
        review_hour, review_minute = [int(p) for p in review_time.split(":", 1)]

        for offset in range(weeks_ahead):
            day_date = first_sunday + timedelta(days=7 * offset)
            start_dt = datetime.combine(day_date, datetime.min.time()).replace(
                hour=review_hour, minute=review_minute, second=0, microsecond=0
            )
            if start_dt < now:
                continue
            end_dt = start_dt + timedelta(minutes=review_duration)
            event = AgendaEvent(
                id=str(uuid.uuid4()),
                type=AgendaEventType.REVISAO_DOMINICAL,
                title="Revisão Semanal",
                start=start_dt,
                end=end_dt,
                completed=False,
                auto_generated=True,
                metadata={"routine_anchor": True},
                priority=EventPriority.FIXO,
            )
            self.events[event.id] = event

        self._save_events()
    
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

    def _to_local_naive_datetime(self, value: Optional[datetime]) -> Optional[datetime]:
        """Normaliza datetime para comparação local, sem timezone."""
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            return value
        try:
            return value.astimezone().replace(tzinfo=None)
        except Exception:
            try:
                return value.replace(tzinfo=None)
            except Exception:
                return None

    def auto_complete_past_events(self, reference_time: Optional[datetime] = None) -> List[str]:
        """
        Marca automaticamente como concluídos os eventos cujo horário final já passou.

        Returns:
            Lista com IDs dos eventos atualizados nesta execução.
        """
        current_time = self._to_local_naive_datetime(reference_time or datetime.now())
        if current_time is None:
            return []

        completed_ids: List[str] = []
        changed = False

        for event in self.events.values():
            if bool(getattr(event, "completed", False)):
                continue

            event_end = self._to_local_naive_datetime(getattr(event, "end", None))
            if event_end is None:
                continue

            if event_end <= current_time:
                event.completed = True
                completed_ids.append(event.id)
                changed = True

        if changed:
            self._save_events()

        return completed_ids
    
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
        
        auto_generated = bool(kwargs.pop("auto_generated", False))
        metadata = dict(kwargs)
        raw_priority = metadata.pop("priority", None)
        discipline = metadata.pop("discipline", None)
        book_id = metadata.pop("book_id", None)
        difficulty = int(metadata.pop("difficulty", 3) or 3)
        progress_notes = metadata.pop("progress_notes", []) or []

        # Cria evento
        event = AgendaEvent(
            id=str(uuid.uuid4()),
            type=AgendaEventType(event_type),
            title=title,
            start=start_dt,
            end=end_dt,
            completed=False,
            auto_generated=auto_generated,
            metadata=metadata,
            book_id=book_id,
            discipline=discipline,
            difficulty=difficulty,
            progress_notes=progress_notes if isinstance(progress_notes, list) else [str(progress_notes)],
        )
        
        # Define prioridade baseada no tipo
        priority_map = {
            AgendaEventType.AULA: EventPriority.FIXO,
            AgendaEventType.ORIENTACAO: EventPriority.FIXO,
            AgendaEventType.REUNIAO: EventPriority.FIXO,
            AgendaEventType.SEMINARIO: EventPriority.FIXO,
            AgendaEventType.PROVA: EventPriority.ALTA,
            AgendaEventType.PRODUCAO: EventPriority.ALTA,
            AgendaEventType.LEITURA: EventPriority.MEDIA,
            AgendaEventType.REVISAO: EventPriority.MEDIA,
            AgendaEventType.LAZER: EventPriority.BAIXA,
            AgendaEventType.CASUAL: EventPriority.BAIXA
        }
        
        event.priority = priority_map.get(event.type, EventPriority.MEDIA)
        if raw_priority is not None:
            try:
                event.priority = EventPriority(int(raw_priority))
            except Exception:
                pass
        
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
        self.auto_complete_past_events()

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
        
        raw_date = str(date).strip()
        if "T" in raw_date:
            raw_date = raw_date.split("T", 1)[0]
        try:
            target_day = datetime.fromisoformat(f"{raw_date}T00:00").date()
        except Exception:
            target_day = datetime.now().date()
            raw_date = target_day.isoformat()

        # Converte para datetime sem depender de locale.
        day_start = datetime.fromisoformat(f"{raw_date}T{start_hour:02d}:00")
        day_end = datetime.fromisoformat(f"{raw_date}T{end_hour:02d}:00")
        
        # Blocos ocupados
        occupied = self._occupied_ranges_for_day(target_day, exclude_types=exclude_types, include_virtual_blocks=True)
        
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

    def _reading_day_load_factor(self, target_day: date, strategy: str = "") -> float:
        """
        Retorna um fator de carga para leitura no dia.

        Dias úteis recebem carga normal. Em fins de semana, a estratégia padrão
        é manter leituras mais leves, sem zerar completamente o agendamento.
        """
        weekday = target_day.weekday()
        if weekday < 5:
            return 1.0

        weekend_strategy = str(
            self.user_preferences.get("time_optimization", {}).get("weekend_strategy", "light")
            or "light"
        ).strip().lower()
        normalized_strategy = str(strategy or "").strip().lower()

        if weekend_strategy == "off":
            return 0.0
        if weekend_strategy == "normal" or normalized_strategy == "intensive":
            return 1.0
        if weekday == 5:  # sábado
            return 0.6
        return 0.45  # domingo
    
    def allocate_reading_time(self, book_id: str, pages_per_day: float,
                            reading_speed: float = 10.0,
                            days_off: List[int] = None,
                            max_daily_minutes: int = 180,
                            strategy: str = "balanced",
                            start_date: str = None,
                            deadline: str = None,
                            preferred_time: str = "") -> Dict:
        """
        Aloca tempo de leitura na agenda usando algoritmo otimizado
        
        Args:
            book_id: ID do livro
            pages_per_day: Média de páginas por dia
            reading_speed: Velocidade de leitura (páginas/hora)
            days_off: Dias explicitamente excluídos do agendamento
            max_daily_minutes: Máximo de minutos por dia
            strategy: Estratégia de alocação (balanced, intensive, spaced)
            
        Returns:
            Dicionário com alocações criadas
        """
        if days_off is None:
            days_off = []
        
        # Obtém informações do livro
        book_progress = self.reading_manager.get_reading_progress(book_id)
        if not book_progress:
            return {"error": "Livro não encontrado"}
        
        total_pages = int(book_progress.get("total_pages", 0) or 0)
        current_page = int(book_progress.get("current_page", 0) or 0)
        pages_remaining_total = max(0, total_pages - current_page)
        if pages_remaining_total <= 0:
            return {"error": "Livro já concluído"}

        # Calcula tempo necessário
        pages_per_hour = max(reading_speed, 1)
        minutes_per_page = 60 / pages_per_hour
        requested_pages_per_day = max(1.0, float(pages_per_day or 1.0))

        # Define estratégia
        session_settings = {
            "balanced": {"min_session": 30, "max_session": 90, "sessions_per_day": 2},
            "intensive": {"min_session": 45, "max_session": 120, "sessions_per_day": 3},
            "spaced": {"min_session": 25, "max_session": 50, "sessions_per_day": 4}
        }
        settings = session_settings.get(strategy, session_settings["balanced"])
        
        try:
            first_day = date.fromisoformat(str(start_date).strip()) if start_date else datetime.now().date()
        except Exception:
            first_day = datetime.now().date()

        if deadline:
            try:
                deadline_day = date.fromisoformat(str(deadline).strip())
            except Exception:
                deadline_day = first_day + timedelta(days=59)
        else:
            deadline_day = first_day + timedelta(days=59)

        if deadline_day < first_day:
            deadline_day = first_day

        all_candidate_days: List[date] = []
        cursor_day = first_day
        while cursor_day <= deadline_day:
            if cursor_day.weekday() not in days_off:
                all_candidate_days.append(cursor_day)
            cursor_day += timedelta(days=1)

        if not all_candidate_days:
            all_candidate_days = [first_day]

        if deadline:
            computed_pages_per_day = max(
                1,
                int((pages_remaining_total + len(all_candidate_days) - 1) / len(all_candidate_days))
            )
            target_pages_per_day = computed_pages_per_day
        else:
            target_pages_per_day = max(1, int(round(requested_pages_per_day)))

        required_minutes_per_day = min(max_daily_minutes, max(settings["min_session"], int(target_pages_per_day * minutes_per_page)))

        allocations = {}
        pages_remaining = pages_remaining_total
        sessions_created = 0
        daily_targets: Dict[str, int] = {}
        day_load_factors = {
            candidate_day.isoformat(): self._reading_day_load_factor(candidate_day, strategy)
            for candidate_day in all_candidate_days
        }

        def _time_windows() -> List[Tuple[int, int]]:
            preferred = str(preferred_time or "").strip().lower()
            if "manhã" in preferred or "manha" in preferred:
                return [(8, 12)]
            if "tarde" in preferred:
                return [(14, 18)]
            if "noite" in preferred:
                return [(19, 22)]
            if strategy == "intensive":
                return [(8, 12), (14, 18), (19, 22)]
            return [(8, 12), (14, 18), (19, 22)]

        for target_day in all_candidate_days:
            if pages_remaining <= 0:
                break

            date_str = target_day.isoformat()
            load_factor = max(0.0, float(day_load_factors.get(date_str, 1.0) or 0.0))
            if load_factor <= 0:
                continue

            remaining_days = [d for d in all_candidate_days if d >= target_day]
            remaining_weight = sum(
                max(0.0, float(day_load_factors.get(day.isoformat(), 1.0) or 0.0))
                for day in remaining_days
            )
            if remaining_weight <= 0:
                remaining_weight = max(1.0, float(len(remaining_days)))

            if deadline:
                weighted_share = int(round(pages_remaining * (load_factor / remaining_weight)))
                pages_for_day = min(pages_remaining, max(1, weighted_share))
            else:
                pages_for_day = min(
                    pages_remaining,
                    max(1, int(round(target_pages_per_day * load_factor))),
                )

            daily_targets[date_str] = pages_for_day
            weekday = target_day.weekday()
            weekend_light = weekday >= 5 and load_factor < 1.0
            session_minimum = max(20, min(settings["min_session"], 45)) if weekend_light else settings["min_session"]
            session_cap = 1 if weekend_light else settings["sessions_per_day"]
            per_day_minutes_cap = max(
                session_minimum,
                int(round(max_daily_minutes * load_factor)),
            )
            minutes_remaining_day = min(
                per_day_minutes_cap,
                max(session_minimum, int(pages_for_day * minutes_per_page)),
            )

            daily_slots: List[Dict[str, Any]] = []
            for window_start, window_end in _time_windows():
                free_slots = self.find_free_slots(
                    date_str,
                    duration_minutes=session_minimum,
                    start_hour=window_start,
                    end_hour=window_end,
                    consider_preferences=True
                )
                daily_slots.extend(free_slots)

            if not daily_slots:
                continue

            daily_slots.sort(
                key=lambda slot: (
                    -float(slot.get("quality_score", 0.5) or 0.5),
                    str(slot.get("start") or ""),
                )
            )

            sessions_today = 0
            occupied_ranges: List[Tuple[datetime, datetime]] = []
            for slot in daily_slots:
                if minutes_remaining_day <= 0 or pages_remaining <= 0:
                    break
                if sessions_today >= session_cap:
                    break

                try:
                    slot_start = datetime.fromisoformat(str(slot.get("start")).replace(" ", "T"))
                    slot_end = datetime.fromisoformat(str(slot.get("end")).replace(" ", "T"))
                except Exception:
                    continue
                if slot_end <= slot_start:
                    continue

                allocation_minutes = min(
                    int((slot_end - slot_start).total_seconds() // 60),
                    min(settings["max_session"], 45) if weekend_light else settings["max_session"],
                    minutes_remaining_day,
                )
                if allocation_minutes < session_minimum:
                    continue

                alloc_end = slot_start + timedelta(minutes=allocation_minutes)
                if any(slot_start < occ_end and alloc_end > occ_start for occ_start, occ_end in self._occupied_ranges_for_day(target_day)):
                    continue
                overlaps = any(slot_start < occ_end and alloc_end > occ_start for occ_start, occ_end in occupied_ranges)
                if overlaps:
                    continue

                slot_pages = max(1, min(pages_remaining, int(allocation_minutes / minutes_per_page)))
                event_id = self.add_event(
                    title=f"Leitura: {book_progress.get('title', book_id)}",
                    start=slot_start.isoformat(),
                    end=alloc_end.isoformat(),
                    event_type="leitura",
                    discipline=book_progress.get("discipline") or "Leitura",
                    book_id=book_id,
                    difficulty=3,
                    auto_generated=True,
                    scheduling_strategy=strategy,
                    preferred_time=preferred_time,
                    deadline=deadline,
                    pages_planned=slot_pages,
                )

                key = f"{date_str}_{sessions_today + 1}"
                allocations[key] = {
                    "event_id": event_id,
                    "date": date_str,
                    "time_slot": f"{slot_start.strftime('%H:%M')} - {alloc_end.strftime('%H:%M')}",
                    "duration_minutes": allocation_minutes,
                    "pages_planned": slot_pages,
                    "quality_score": float(slot.get("quality_score", 0.5) or 0.5),
                }
                occupied_ranges.append((slot_start, alloc_end))
                sessions_today += 1
                sessions_created += 1
                minutes_remaining_day -= allocation_minutes
                pages_remaining -= slot_pages

        # Registra estatísticas
        self._record_allocation_statistics(allocations, strategy)
        
        return {
            "book_id": book_id,
            "strategy": strategy,
            "total_sessions": len(allocations),
            "allocations": allocations,
            "pages_remaining_unscheduled": max(0, pages_remaining),
            "pages_target_per_day": target_pages_per_day,
            "daily_targets": daily_targets,
            "start_date": first_day.isoformat(),
            "deadline": deadline_day.isoformat(),
            "success": bool(sessions_created > 0),
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
        self.auto_complete_past_events()

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

    def _preferred_study_window(self) -> Tuple[int, int]:
        """Calcula janela diária de estudo baseada no horário de sono."""
        sleep_cfg = self.user_preferences.get("sleep_schedule", {})
        sleep_end = self._normalize_hhmm(sleep_cfg.get("end", "07:00"), "07:00")
        sleep_start = self._normalize_hhmm(sleep_cfg.get("start", "23:00"), "23:00")

        try:
            wake_hour = int(sleep_end.split(":", 1)[0])
        except Exception:
            wake_hour = 7

        try:
            sleep_hour = int(sleep_start.split(":", 1)[0])
        except Exception:
            sleep_hour = 23

        start_hour = max(6, min(12, wake_hour + 1))
        end_hour = max(18, min(23, sleep_hour - 1))

        if end_hour <= start_hour:
            return 8, 22
        return start_hour, end_hour

    def create_review_plan(
        self,
        book_id: str,
        plan_days: int = 7,
        hours_per_session: float = 1.0,
        sessions_per_day: int = 1,
        start_date: str = None,
    ) -> Dict[str, Any]:
        """
        Cria um plano de revisão para uma obra usando slots da agenda + SmartAllocator.

        Args:
            book_id: ID da obra no ReadingManager
            plan_days: Horizonte do plano (3, 7 ou 14 dias)
            hours_per_session: Duração de cada sessão em horas
            sessions_per_day: Quantidade desejada de sessões por dia
            start_date: Data inicial (YYYY-MM-DD). Padrão: hoje

        Returns:
            Resultado com sessões criadas e avisos
        """
        try:
            plan_days = int(plan_days or 7)
        except Exception:
            plan_days = 7
        if plan_days not in (3, 7, 14):
            return {"error": "Plano inválido. Use 3, 7 ou 14 dias."}

        try:
            hours_per_session = float(hours_per_session or 1.0)
        except Exception:
            hours_per_session = 1.0
        hours_per_session = max(0.25, min(8.0, hours_per_session))
        session_minutes = max(15, int(round(hours_per_session * 60)))

        try:
            sessions_per_day = int(sessions_per_day or 1)
        except Exception:
            sessions_per_day = 1
        sessions_per_day = max(1, min(8, sessions_per_day))

        book_progress = self.reading_manager.get_reading_progress(book_id)
        if not book_progress:
            return {"error": "Livro não encontrado"}

        book_title = str(book_progress.get("title", "Livro")).strip() or "Livro"
        completion = float(book_progress.get("percentage", 0.0) or 0.0)

        if start_date:
            try:
                start_day = date.fromisoformat(str(start_date).strip())
            except Exception:
                start_day = datetime.now().date()
        else:
            start_day = datetime.now().date()

        start_hour, end_hour = self._preferred_study_window()
        sessions_created: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for day_offset in range(plan_days):
            target_day = start_day + timedelta(days=day_offset)
            date_str = target_day.isoformat()
            free_slots = self.find_free_slots(
                date_str,
                duration_minutes=session_minutes,
                start_hour=start_hour,
                end_hour=end_hour,
                consider_preferences=True,
            )

            selected_slots = SmartAllocator.select_review_slots(
                available_slots=free_slots,
                sessions_per_day=sessions_per_day,
                session_duration_minutes=session_minutes,
            )

            if len(selected_slots) < sessions_per_day:
                warnings.append(
                    f"{date_str}: apenas {len(selected_slots)}/{sessions_per_day} sessão(ões) encontradas."
                )

            for idx, slot in enumerate(selected_slots, start=1):
                event_id = self.add_event(
                    title=f"Revisão: {book_title}",
                    start=str(slot.get("start", "")).strip(),
                    end=str(slot.get("end", "")).strip(),
                    event_type="revisao",
                    book_id=book_id,
                    discipline="Revisão",
                    difficulty=2,
                    review_plan=True,
                    review_plan_day=day_offset + 1,
                    review_session_index=idx,
                    review_total_days=plan_days,
                    hours_per_session=hours_per_session,
                )
                sessions_created.append(
                    {
                        "event_id": event_id,
                        "date": date_str,
                        "start": slot.get("start"),
                        "end": slot.get("end"),
                        "duration_minutes": int(slot.get("duration_minutes", session_minutes) or session_minutes),
                        "quality_score": float(slot.get("quality_score", 0.5) or 0.5),
                    }
                )

        result = {
            "book_id": str(book_id),
            "book_title": book_title,
            "completion_percentage": completion,
            "plan_days": plan_days,
            "hours_per_session": hours_per_session,
            "sessions_per_day_requested": sessions_per_day,
            "sessions_expected": plan_days * sessions_per_day,
            "sessions_created_count": len(sessions_created),
            "sessions_created": sessions_created,
            "start_date": start_day.isoformat(),
            "end_date": (start_day + timedelta(days=plan_days - 1)).isoformat(),
            "warnings": warnings,
        }

        if not sessions_created:
            result["error"] = (
                "Não foi possível encontrar slots livres para as sessões de revisão."
            )
        return result
    
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
        self.auto_complete_past_events()

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
        self.auto_complete_past_events()

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

    def rebalance_schedule(self, horizon_days: int = 30) -> Dict[str, Any]:
        """
        Recalcula e redistribui compromissos futuros flexíveis.

        Regras:
        - Aulas, provas e seminários permanecem fixos
        - Eventos concluídos ou já iniciados não são movidos
        - A redistribuição usa slots livres priorizados por qualidade
        """
        now = datetime.now()
        horizon_end = (now + timedelta(days=max(7, int(horizon_days or 30)))).date()
        fixed_types = {
            AgendaEventType.AULA,
            AgendaEventType.PROVA,
            AgendaEventType.SEMINARIO,
            AgendaEventType.ORIENTACAO,
            AgendaEventType.REUNIAO,
            AgendaEventType.REVISAO_DOMINICAL,
        }

        movable_events: List[AgendaEvent] = []
        protected_events: List[AgendaEvent] = []

        for event in self.events.values():
            if event.completed:
                protected_events.append(event)
                continue
            if event.end <= now:
                protected_events.append(event)
                continue
            if event.start.date() > horizon_end:
                protected_events.append(event)
                continue
            if event.type in fixed_types or event.priority.value >= EventPriority.FIXO.value:
                protected_events.append(event)
                continue
            movable_events.append(event)

        if not movable_events:
            return {
                "success": True,
                "moved_count": 0,
                "protected_count": len(protected_events),
                "unscheduled_count": 0,
                "updated_dates": [],
            }

        touched_dates = {
            event.start.date().isoformat()
            for event in movable_events + protected_events
            if now.date() <= event.start.date() <= horizon_end
        }

        work_start = 8
        work_end = 22

        free_slots: List[Dict[str, Any]] = []
        existing_day_load_minutes: Dict[str, int] = {}
        day_cursor = now.date()
        while day_cursor <= horizon_end:
            date_str = day_cursor.isoformat()
            day_start = datetime.combine(day_cursor, datetime.min.time()).replace(hour=work_start, minute=0)
            day_end = datetime.combine(day_cursor, datetime.min.time()).replace(hour=work_end, minute=0)

            day_events = [
                event for event in self.events.values()
                if event.start.date() == day_cursor
                and (
                    event in protected_events
                    or event.start <= now
                )
            ]
            productive_minutes = 0
            for event in day_events:
                if event.type in {
                    AgendaEventType.LEITURA,
                    AgendaEventType.PRODUCAO,
                    AgendaEventType.REVISAO,
                    AgendaEventType.TRANSCRICAO,
                    AgendaEventType.CHECKIN,
                }:
                    productive_minutes += max(0, int(event.duration_minutes()))
            existing_day_load_minutes[date_str] = productive_minutes

            occupied_ranges: List[Tuple[datetime, datetime]] = [(event.start, event.end) for event in day_events]
            occupied_ranges.extend(
                (event.start, event.end)
                for event in self._build_virtual_routine_events(day_cursor)
            )
            occupied_ranges.sort(key=lambda item: item[0])

            cursor = max(day_start, now if day_cursor == now.date() else day_start)
            for occ_start, occ_end in occupied_ranges:
                if occ_end <= cursor:
                    continue
                if occ_start > cursor:
                    duration = int((occ_start - cursor).total_seconds() // 60)
                    if duration >= 20:
                        quality = self._calculate_time_quality(cursor, duration)
                        if day_cursor.weekday() >= 5:
                            quality *= 0.9
                        free_slots.append(
                            {
                                "start": cursor.isoformat(),
                                "end": occ_start.isoformat(),
                                "duration_minutes": duration,
                                "quality_score": quality,
                            }
                        )
                cursor = max(cursor, occ_end)

            if cursor < day_end:
                duration = int((day_end - cursor).total_seconds() // 60)
                if duration >= 20:
                    quality = self._calculate_time_quality(cursor, duration)
                    if day_cursor.weekday() >= 5:
                        quality *= 0.9
                    free_slots.append(
                        {
                            "start": cursor.isoformat(),
                            "end": day_end.isoformat(),
                            "duration_minutes": duration,
                            "quality_score": quality,
                        }
                    )
            day_cursor += timedelta(days=1)

        serialized_events: List[Dict[str, Any]] = []
        for event in movable_events:
            deadline = str(event.metadata.get("deadline") or "").strip() if isinstance(event.metadata, dict) else ""
            serialized_events.append(
                {
                    "event_id": event.id,
                    "title": event.title,
                    "type": event.type.value,
                    "start": event.start.isoformat(),
                    "end": event.end.isoformat(),
                    "duration_minutes": max(15, int(event.duration_minutes())),
                    "priority": event.priority.value,
                    "preferred_time": str(event.metadata.get("preferred_time") or "").strip() if isinstance(event.metadata, dict) else "",
                    "deadline": deadline,
                }
            )

        allocator_result = SmartAllocator.redistribute_events(
            serialized_events,
            free_slots,
            user_preferences={
                "weekend_bias": 0.92,
                "existing_day_load_minutes": existing_day_load_minutes,
                "max_daily_minutes": int(
                    self.user_preferences.get("work_preferences", {}).get("max_daily_work_hours", 8) or 8
                ) * 60,
                "spread_bonus": 0.24,
                "same_day_bonus": 0.015,
                "proximity_penalty_per_day": 0.008,
            },
        )

        placements = allocator_result.get("placements", [])
        unscheduled = allocator_result.get("unscheduled", [])
        placement_by_id = {
            str(item.get("event_id") or ""): item
            for item in placements
            if item.get("event_id")
        }

        moved_count = 0
        updated_dates = set(touched_dates)
        for event in movable_events:
            placement = placement_by_id.get(event.id)
            if not placement:
                continue
            try:
                new_start = datetime.fromisoformat(str(placement.get("start") or ""))
                new_end = datetime.fromisoformat(str(placement.get("end") or ""))
            except Exception:
                continue
            if new_end <= new_start:
                continue
            if event.start != new_start or event.end != new_end:
                updated_dates.add(event.start.date().isoformat())
                updated_dates.add(new_start.date().isoformat())
                event.start = new_start
                event.end = new_end
                moved_count += 1

        self._save_events()
        return {
            "success": True,
            "moved_count": moved_count,
            "protected_count": len(protected_events),
            "unscheduled_count": len(unscheduled),
            "updated_dates": sorted(updated_dates),
        }
