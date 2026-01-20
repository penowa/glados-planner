# src/cli/interactive/integration/agenda_backend_bridge.py
"""
Ponte entre a interface CLI e o backend AgendaManager
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import json

class AgendaViewType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEMESTER = "semester"

class AgendaBackendBridge:
    """Ponte específica para integração com backend da agenda"""
    
    def __init__(self, backend_integration=None):
        self.backend = backend_integration
        self.cache = {
            'daily_events': {'data': None, 'ttl': 300, 'timestamp': None},
            'weekly_overview': {'data': None, 'ttl': 1800, 'timestamp': None},
            'important_dates': {'data': None, 'ttl': 3600, 'timestamp': None},
            'monthly_view': {'data': None, 'ttl': 3600, 'timestamp': None}
        }
        
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica se o cache ainda é válido"""
        if cache_key not in self.cache:
            return False
        
        cache_entry = self.cache[cache_key]
        if cache_entry['data'] is None or cache_entry['timestamp'] is None:
            return False
        
        elapsed = datetime.now() - cache_entry['timestamp']
        return elapsed.total_seconds() < cache_entry['ttl']
    
    def get_view_data(self, view_type: str, date: datetime = None) -> Dict:
        """Obtém dados formatados para cada tipo de visualização"""
        if date is None:
            date = datetime.now()
        
        if view_type == 'daily':
            return self._get_daily_view(date)
        elif view_type == 'weekly':
            return self._get_weekly_view(date)
        elif view_type == 'monthly':
            return self._get_monthly_view(date)
        elif view_type == 'semester':
            return self._get_semester_view(date)
        else:
            raise ValueError(f"Tipo de visualização inválido: {view_type}")
    
    def _get_daily_view(self, date: datetime) -> Dict:
        """Formata dados para visualização diária"""
        cache_key = f"daily_{date.strftime('%Y-%m-%d')}"
        
        # Verifica cache
        if self._is_cache_valid('daily_events'):
            cached = self.cache['daily_events']
            if cached['data'] and cached['data'].get('date') == date.strftime('%Y-%m-%d'):
                return cached['data']
        
        try:
            # Usa backend para obter eventos
            events = self.backend.get_day_events(date.strftime('%Y-%m-%d'))
            
            # Formata para exibição
            data = {
                'date': date.strftime('%Y-%m-%d'),
                'display_date': date.strftime("%A, %d de %B de %Y"),
                'events': self._format_events_for_display(events),
                'stats': self._calculate_daily_stats(events),
                'conflicts': self._detect_conflicts(events),
                'productivity_score': self._calculate_productivity_score(events)
            }
            
            # Atualiza cache
            self.cache['daily_events'] = {
                'data': data,
                'timestamp': datetime.now(),
                'ttl': 300
            }
            
            return data
            
        except Exception as e:
            print(f"Erro ao obter dados diários: {e}")
            return self._get_fallback_data(date, 'daily')
    
    def _get_weekly_view(self, date: datetime) -> Dict:
        """Formata dados para visualização semanal"""
        cache_key = f"weekly_{date.strftime('%Y-W%W')}"
        
        if self._is_cache_valid('weekly_overview'):
            cached = self.cache['weekly_overview']
            return cached['data']
        
        try:
            # Obtém semana (segunda a domingo)
            start_of_week = date - timedelta(days=date.weekday())
            week_days = []
            
            for i in range(7):
                day_date = start_of_week + timedelta(days=i)
                events = self.backend.get_day_events(day_date.strftime('%Y-%m-%d'))
                
                day_data = {
                    'date': day_date,
                    'display_date': day_date.strftime("%a %d/%m"),
                    'events': events,
                    'count': len(events),
                    'productive_hours': self._calculate_productive_hours(events),
                    'has_important': any(e.get('priority') == 'high' for e in events),
                    'completed': sum(1 for e in events if e.get('completed', False))
                }
                week_days.append(day_data)
            
            data = {
                'week_start': start_of_week.strftime('%Y-%m-%d'),
                'week_end': (start_of_week + timedelta(days=6)).strftime('%Y-%m-%d'),
                'week_days': week_days,
                'total_events': sum(d['count'] for d in week_days),
                'total_productive_hours': sum(d['productive_hours'] for d in week_days),
                'week_stats': self._calculate_weekly_stats(week_days)
            }
            
            # Atualiza cache
            self.cache['weekly_overview'] = {
                'data': data,
                'timestamp': datetime.now(),
                'ttl': 1800
            }
            
            return data
            
        except Exception as e:
            print(f"Erro ao obter dados semanais: {e}")
            return self._get_fallback_data(date, 'weekly')
    
    def _get_monthly_view(self, date: datetime) -> Dict:
        """Formata dados para visualização mensal"""
        # Implementação simplificada
        return {
            'month': date.strftime("%B %Y"),
            'weeks': [],
            'total_events': 0,
            'important_dates': []
        }
    
    def _get_semester_view(self, date: datetime) -> Dict:
        """Formata dados para visualização semestral"""
        return {
            'semester': self._get_semester_name(date),
            'months': [],
            'milestones': []
        }
    
    def _format_events_for_display(self, events: List[Dict]) -> List[Dict]:
        """Formata eventos para exibição na interface"""
        formatted = []
        for event in events:
            formatted_event = {
                'id': event.get('id', ''),
                'title': event.get('title', 'Sem título'),
                'time': event.get('start_time', '')[:5] if event.get('start_time') else '',
                'type': event.get('type', 'outro'),
                'priority': event.get('priority', 'medium'),
                'completed': event.get('completed', False),
                'duration': event.get('duration_minutes', 60),
                'location': event.get('location', ''),
                'description': event.get('description', ''),
                'tags': event.get('tags', [])
            }
            formatted.append(formatted_event)
        return sorted(formatted, key=lambda x: x['time'])
    
    def _calculate_daily_stats(self, events: List[Dict]) -> Dict:
        """Calcula estatísticas diárias"""
        total = len(events)
        completed = sum(1 for e in events if e.get('completed', False))
        productive_hours = self._calculate_productive_hours(events)
        
        return {
            'total': total,
            'completed': completed,
            'pending': total - completed,
            'productive_hours': productive_hours,
            'completion_rate': (completed / total * 100) if total > 0 else 0,
            'focus_score': self._calculate_focus_score(events)
        }
    
    def _calculate_weekly_stats(self, week_days: List[Dict]) -> Dict:
        """Calcula estatísticas semanais"""
        total_events = sum(d['count'] for d in week_days)
        total_completed = sum(d['completed'] for d in week_days)
        total_hours = sum(d['productive_hours'] for d in week_days)
        
        return {
            'total_events': total_events,
            'completed_events': total_completed,
            'total_hours': total_hours,
            'avg_daily_hours': total_hours / 7 if len(week_days) > 0 else 0,
            'busiest_day': max(week_days, key=lambda x: x['count'])['display_date'] if week_days else None
        }
    
    def _calculate_productive_hours(self, events: List[Dict]) -> float:
        """Calcula horas produtivas totais"""
        productive_events = [e for e in events if e.get('type') in ['leitura', 'producao', 'revisao', 'aula']]
        total_minutes = sum(e.get('duration_minutes', 0) for e in productive_events)
        return round(total_minutes / 60, 1)
    
    def _calculate_focus_score(self, events: List[Dict]) -> int:
        """Calcula score de foco (0-100)"""
        if not events:
            return 0
        
        productive_events = [e for e in events if e.get('type') in ['leitura', 'producao', 'revisao']]
        if not productive_events:
            return 0
        
        # Simples cálculo baseado em duração e completude
        total_duration = sum(e.get('duration_minutes', 0) for e in productive_events)
        completed_duration = sum(e.get('duration_minutes', 0) for e in productive_events if e.get('completed', False))
        
        if total_duration == 0:
            return 0
        
        return int((completed_duration / total_duration) * 100)
    
    def _calculate_productivity_score(self, events: List[Dict]) -> int:
        """Calcula score de produtividade"""
        return self._calculate_focus_score(events)  # Por enquanto, usa o mesmo
    
    def _detect_conflicts(self, events: List[Dict]) -> List[Dict]:
        """Detecta conflitos de horário"""
        conflicts = []
        sorted_events = sorted(events, key=lambda x: x.get('start_time', ''))
        
        for i in range(len(sorted_events) - 1):
            current = sorted_events[i]
            next_event = sorted_events[i + 1]
            
            if not current.get('start_time') or not next_event.get('start_time'):
                continue
                
            # Verifica se há sobreposição
            current_end = self._add_duration(current.get('start_time'), current.get('duration_minutes', 0))
            if current_end > next_event.get('start_time'):
                conflicts.append({
                    'event1': current.get('title'),
                    'event2': next_event.get('title'),
                    'time': current.get('start_time')
                })
        
        return conflicts
    
    def _add_duration(self, time_str: str, minutes: int) -> str:
        """Adiciona duração a um horário"""
        from datetime import datetime, timedelta
        time_obj = datetime.strptime(time_str, '%H:%M')
        new_time = time_obj + timedelta(minutes=minutes)
        return new_time.strftime('%H:%M')
    
    def _get_semester_name(self, date: datetime) -> str:
        """Determina o nome do semestre"""
        month = date.month
        year = date.year
        
        if 1 <= month <= 6:
            return f"1º Semestre {year}"
        else:
            return f"2º Semestre {year}"
    
    def _get_fallback_data(self, date: datetime, view_type: str) -> Dict:
        """Dados de fallback quando o backend falha"""
        if view_type == 'daily':
            return {
                'date': date.strftime('%Y-%m-%d'),
                'display_date': date.strftime("%A, %d de %B de %Y"),
                'events': [],
                'stats': {'total': 0, 'completed': 0, 'productive_hours': 0},
                'conflicts': [],
                'productivity_score': 0
            }
        elif view_type == 'weekly':
            return {
                'week_start': date.strftime('%Y-%m-%d'),
                'week_days': [],
                'total_events': 0,
                'total_productive_hours': 0,
                'week_stats': {}
            }
        return {}
    
    def get_important_dates(self, start_date: datetime = None) -> Dict:
        """Obtém datas importantes categorizadas"""
        if start_date is None:
            start_date = datetime.now()
        
        # Verifica cache
        if self._is_cache_valid('important_dates'):
            return self.cache['important_dates']['data']
        
        try:
            # Usando backend para obter datas importantes
            # (Assumindo que o backend tem um método para isso)
            important_data = self.backend.get_important_dates(
                start_date.strftime('%Y-%m-%d'),
                (start_date + timedelta(days=90)).strftime('%Y-%m-%d')
            )
            
            # Categoriza os dados
            categorized = {
                'provas': [e for e in important_data if e.get('type') == 'prova'],
                'seminarios': [e for e in important_data if e.get('type') == 'seminario'],
                'entregas': [e for e in important_data if e.get('type') == 'entrega'],
                'recessos': [e for e in important_data if e.get('type') == 'recesso'],
                'revisoes': [e for e in important_data if e.get('type') == 'revisao']
            }
            
            # Atualiza cache
            self.cache['important_dates'] = {
                'data': categorized,
                'timestamp': datetime.now(),
                'ttl': 3600
            }
            
            return categorized
            
        except Exception as e:
            print(f"Erro ao obter datas importantes: {e}")
            return {
                'provas': [],
                'seminarios': [],
                'entregas': [],
                'recessos': [],
                'revisoes': []
            }
    
    def add_event(self, event_data: Dict) -> bool:
        """Adiciona um novo evento"""
        try:
            result = self.backend.add_event(**event_data)
            
            # Invalida cache relevante
            self._invalidate_cache_for_date(event_data.get('date'))
            
            return result
        except Exception as e:
            print(f"Erro ao adicionar evento: {e}")
            return False
    
    def update_event(self, event_id: str, updates: Dict) -> bool:
        """Atualiza um evento existente"""
        try:
            result = self.backend.update_event(event_id, **updates)
            
            # Invalida cache
            if 'date' in updates:
                self._invalidate_cache_for_date(updates['date'])
            
            return result
        except Exception as e:
            print(f"Erro ao atualizar evento: {e}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """Remove um evento"""
        try:
            # Primeiro obtém o evento para saber a data
            event = self.backend.get_event(event_id)
            date = event.get('date') if event else None
            
            result = self.backend.delete_event(event_id)
            
            # Invalida cache
            if date:
                self._invalidate_cache_for_date(date)
            
            return result
        except Exception as e:
            print(f"Erro ao deletar evento: {e}")
            return False
    
    def _invalidate_cache_for_date(self, date_str: str):
        """Invalida cache para uma data específica"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Invalida cache diário
        self.cache['daily_events']['data'] = None
        self.cache['daily_events']['timestamp'] = None
        
        # Invalida cache semanal se a data estiver na semana atual
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        if start_of_week <= date_obj <= end_of_week:
            self.cache['weekly_overview']['data'] = None
            self.cache['weekly_overview']['timestamp'] = None
