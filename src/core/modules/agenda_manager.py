# [file name]: src/core/modules/agenda_manager.py
"""
Gerenciador de agenda acadêmica
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path

@dataclass
class CalendarEvent:
    """Evento do calendário acadêmico"""
    id: str
    title: str
    description: str
    start: str
    end: str
    event_type: str  # aula, prova, entrega, reunião, etc.
    discipline: str
    priority: str  # alta, média, baixa
    completed: bool
    notes: str

class AgendaManager:
    """Gerencia agenda e prazos acadêmicos"""
    
    def __init__(self, vault_path: str):
        """
        Inicializa o gerenciador de agenda
        
        Args:
            vault_path: Caminho para o vault do Obsidian
        """
        self.vault_path = Path(vault_path).expanduser()
        self.calendar_file = self.vault_path / "04-AGENDA" / "calendario_academico.json"
        
        # Carrega eventos existentes
        self.events = self._load_events()
        self.next_id = max([int(e.id) for e in self.events.values()], default=0) + 1
    
    def _load_events(self) -> Dict[str, CalendarEvent]:
        """Carrega eventos do arquivo"""
        events = {}
        
        if self.calendar_file.exists():
            try:
                with open(self.calendar_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for event_id, event_data in data.items():
                    events[event_id] = CalendarEvent(
                        id=event_id,
                        title=event_data.get('title', ''),
                        description=event_data.get('description', ''),
                        start=event_data.get('start', ''),
                        end=event_data.get('end', ''),
                        event_type=event_data.get('event_type', 'outro'),
                        discipline=event_data.get('discipline', ''),
                        priority=event_data.get('priority', 'média'),
                        completed=event_data.get('completed', False),
                        notes=event_data.get('notes', '')
                    )
            except Exception as e:
                print(f"Erro ao carregar eventos: {e}")
        
        return events
    
    def _save_events(self):
        """Salva eventos no arquivo"""
        try:
            data = {}
            for event_id, event in self.events.items():
                data[event_id] = {
                    'title': event.title,
                    'description': event.description,
                    'start': event.start,
                    'end': event.end,
                    'event_type': event.event_type,
                    'discipline': event.discipline,
                    'priority': event.priority,
                    'completed': event.completed,
                    'notes': event.notes
                }
            
            # Garante que o diretório existe
            self.calendar_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.calendar_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar eventos: {e}")
    
    def get_daily_summary(self, date: str = None) -> Dict:
        """
        Obtém resumo diário de eventos
        
        Args:
            date: Data no formato YYYY-MM-DD (opcional, usa hoje se None)
            
        Returns:
            Resumo diário
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        daily_events = []
        for event in self.events.values():
            event_date = event.start[:10]  # Extrai apenas a data
            if event_date == date:
                daily_events.append({
                    "id": event.id,
                    "title": event.title,
                    "time": event.start[11:16] if len(event.start) > 10 else "dia todo",
                    "type": event.event_type,
                    "discipline": event.discipline,
                    "priority": event.priority,
                    "completed": event.completed
                })
        
        # Ordena por hora
        daily_events.sort(key=lambda x: x["time"])
        
        # Estatísticas
        total = len(daily_events)
        completed = sum(1 for e in daily_events if e["completed"])
        
        return {
            "date": date,
            "total_events": total,
            "completed_events": completed,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "events": daily_events
        }
    
    def add_event(self, title: str, start: str, end: str = None, 
                  event_type: str = "outro", discipline: str = "", 
                  priority: str = "média", description: str = "") -> str:
        """
        Adiciona um novo evento
        
        Args:
            title: Título do evento
            start: Data/hora de início (YYYY-MM-DD ou YYYY-MM-DD HH:MM)
            end: Data/hora de término (opcional)
            event_type: Tipo do evento
            discipline: Disciplina relacionada
            priority: Prioridade (alta, média, baixa)
            description: Descrição do evento
            
        Returns:
            ID do evento criado
        """
        event_id = str(self.next_id)
        self.next_id += 1
        
        # Formata datas
        if len(start) == 10:  # Apenas data
            start += " 00:00"
            if end is None:
                end = start[:10] + " 23:59"
            elif len(end) == 10:
                end += " 23:59"
        elif end is None:
            # Assume 1 hora de duração
            start_dt = datetime.fromisoformat(start)
            end_dt = start_dt + timedelta(hours=1)
            end = end_dt.isoformat()[:16]
        
        new_event = CalendarEvent(
            id=event_id,
            title=title,
            description=description,
            start=start,
            end=end,
            event_type=event_type,
            discipline=discipline,
            priority=priority,
            completed=False,
            notes=""
        )
        
        self.events[event_id] = new_event
        self._save_events()
        
        return event_id
    
    def get_overdue_tasks(self) -> List[Dict]:
        """
        Obtém tarefas atrasadas
        
        Returns:
            Lista de tarefas atrasadas
        """
        overdue = []
        now = datetime.now()
        
        for event in self.events.values():
            if not event.completed:
                try:
                    event_end = datetime.fromisoformat(event.end)
                    if event_end < now:
                        overdue.append({
                            "id": event.id,
                            "title": event.title,
                            "due_date": event.end,
                            "days_late": (now - event_end).days,
                            "discipline": event.discipline,
                            "priority": event.priority
                        })
                except:
                    continue
        
        # Ordena por dias de atraso
        overdue.sort(key=lambda x: x["days_late"], reverse=True)
        return overdue
    
    def complete_event(self, event_id: str, notes: str = "") -> bool:
        """
        Marca um evento como concluído
        
        Args:
            event_id: ID do evento
            notes: Notas sobre a conclusão
            
        Returns:
            True se bem-sucedido
        """
        if event_id in self.events:
            self.events[event_id].completed = True
            if notes:
                self.events[event_id].notes = notes
            self._save_events()
            return True
        return False
    
    def get_upcoming_events(self, days: int = 7) -> List[Dict]:
        """
        Obtém eventos futuros
        
        Args:
            days: Número de dias para frente
            
        Returns:
            Lista de eventos futuros
        """
        upcoming = []
        now = datetime.now()
        future_limit = now + timedelta(days=days)
        
        for event in self.events.values():
            try:
                event_start = datetime.fromisoformat(event.start)
                if now <= event_start <= future_limit:
                    upcoming.append({
                        "id": event.id,
                        "title": event.title,
                        "start": event.start,
                        "type": event.event_type,
                        "discipline": event.discipline,
                        "priority": event.priority,
                        "days_until": (event_start - now).days
                    })
            except:
                continue
        
        # Ordena por data
        upcoming.sort(key=lambda x: x["start"])
        return upcoming
    
    def get_statistics(self) -> Dict:
        """
        Obtém estatísticas da agenda
        
        Returns:
            Estatísticas da agenda
        """
        total = len(self.events)
        completed = sum(1 for e in self.events.values() if e.completed)
        
        # Por tipo
        by_type = {}
        for event in self.events.values():
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
        
        # Por disciplina
        by_discipline = {}
        for event in self.events.values():
            if event.discipline:
                by_discipline[event.discipline] = by_discipline.get(event.discipline, 0) + 1
        
        # Por prioridade
        by_priority = {"alta": 0, "média": 0, "baixa": 0}
        for event in self.events.values():
            if event.priority in by_priority:
                by_priority[event.priority] += 1
        
        return {
            "total_events": total,
            "completed_events": completed,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "by_type": by_type,
            "by_discipline": by_discipline,
            "by_priority": by_priority,
            "overdue_tasks": len(self.get_overdue_tasks()),
            "upcoming_events": len(self.get_upcoming_events())
        }
    
    def import_from_vault(self) -> Dict:
        """
        Importa eventos do vault do Obsidian
        
        Returns:
            Estatísticas da importação
        """
        stats = {
            "files_scanned": 0,
            "events_found": 0,
            "events_imported": 0,
            "errors": 0
        }
        
        try:
            # Procura arquivos de calendário no vault
            calendar_files = list(self.vault_path.glob("**/*calendario*.md"))
            calendar_files.extend(self.vault_path.glob("**/*agenda*.md"))
            
            for file_path in calendar_files:
                stats["files_scanned"] += 1
                
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    import re
                    # Procura por eventos no formato do Obsidian
                    # Exemplo: - [ ] 2024-01-10 Entrega do paper
                    event_matches = re.findall(r'- \[( |x)\] (\d{4}-\d{2}-\d{2}) (.+)', content)
                    
                    for checked, date_str, title in event_matches:
                        stats["events_found"] += 1
                        
                        # Verifica se já existe
                        exists = False
                        for event in self.events.values():
                            if event.title == title and event.start.startswith(date_str):
                                exists = True
                                break
                        
                        if not exists:
                            # Extrai disciplina do caminho do arquivo
                            discipline = file_path.parent.name
                            if discipline.startswith("02-"):
                                discipline = discipline[3:]
                            
                            # Determina tipo baseado no título
                            event_type = "tarefa"
                            if "prova" in title.lower() or "teste" in title.lower():
                                event_type = "prova"
                            elif "aula" in title.lower():
                                event_type = "aula"
                            elif "entrega" in title.lower() or "paper" in title.lower():
                                event_type = "entrega"
                            
                            # Adiciona evento
                            self.add_event(
                                title=title.strip(),
                                start=date_str,
                                event_type=event_type,
                                discipline=discipline,
                                priority="média",
                                description=f"Importado de {file_path.name}"
                            )
                            
                            stats["events_imported"] += 1
                
                except Exception as e:
                    print(f"Erro ao processar {file_path}: {e}")
                    stats["errors"] += 1
        
        except Exception as e:
            print(f"Erro na importação: {e}")
            stats["errors"] += 1
        
        return stats
