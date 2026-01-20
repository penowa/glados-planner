# src/cli/integration/agenda_bridge.py
"""
Ponte robusta entre CLI e AgendaManager - Versão corrigida
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os
import yaml
import logging
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)

class AgendaBridge:
    def __init__(self, backend_integration=None):
        self.backend = backend_integration
        self._agenda_manager = None
        self._vault_path = None
        self._cache = {
            'daily': {},
            'weekly': {}
        }
        
    @property
    def vault_path(self) -> str:
        """Obtém caminho do vault ou falha."""
        if self._vault_path is None:
            self._vault_path = self._get_vault_path()
        return self._vault_path
    
    def _get_vault_path(self) -> str:
        """Obtém caminho do vault ou lança exceção."""
        sources = [
            self._from_backend,
            self._from_settings,
            self._from_environment,
            self._from_defaults
        ]
        
        for source in sources:
            try:
                path = source()
                if path and os.path.exists(path):
                    expanded = os.path.expanduser(path)
                    if os.path.exists(expanded):
                        logger.info(f"Vault encontrado: {expanded}")
                        return expanded
            except Exception as e:
                logger.debug(f"Fonte {source.__name__} falhou: {e}")
                continue
        
        raise RuntimeError(
            "VAULT_PATH não configurado.\n"
            "Configure em:\n"
            "  1. ~/.glados/settings.yaml (obsidian.vault_path)\n"
            "  2. Variável de ambiente OBSIDIAN_VAULT_PATH\n"
            "  3. Ou passe --vault-path ao iniciar"
        )
    
    def _from_backend(self) -> Optional[str]:
        if self.backend and hasattr(self.backend, 'obsidian'):
            return getattr(self.backend.obsidian, 'vault_path', None)
        return None
    
    def _from_settings(self) -> Optional[str]:
        config_paths = [
            Path.home() / '.glados' / 'settings.yaml',
            Path.cwd() / 'settings.yaml',
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                        vault_path = config.get('obsidian', {}).get('vault_path')
                        if vault_path:
                            logger.info(f"Vault do settings: {vault_path}")
                            return vault_path
                except Exception as e:
                    logger.warning(f"Erro ao ler config {config_path}: {e}")
                    continue
        return None
    
    def _from_environment(self) -> Optional[str]:
        return os.environ.get('OBSIDIAN_VAULT_PATH')
    
    def _from_defaults(self) -> Optional[str]:
        defaults = [
            "~/Documentos/Obsidian/Philosophy_Vault",
            "~/Obsidian/Philosophy_Vault",
            "~/Documents/Obsidian/Philosophy_Vault",
        ]
        
        for path in defaults:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                logger.info(f"Vault padrão encontrado: {expanded}")
                return expanded
        return None
    
    @property
    def agenda_manager(self):
        """Inicializa AgendaManager ou falha."""
        if self._agenda_manager is None:
            try:
                from src.core.modules.agenda_manager import AgendaManager
                self._agenda_manager = AgendaManager(vault_path=self.vault_path)
                logger.info(f"AgendaManager inicializado com vault: {self.vault_path}")
            except ImportError as e:
                raise RuntimeError(
                    f"AgendaManager não disponível: {e}\n"
                    "Execute o backend primeiro: python run_backend.py"
                ) from e
            except Exception as e:
                logger.error(f"Erro ao inicializar AgendaManager: {e}")
                raise RuntimeError(
                    f"Erro ao inicializar AgendaManager: {e}\n"
                    f"Vault path: {self.vault_path}"
                ) from e
        return self._agenda_manager
    
    def is_available(self) -> bool:
        """Verifica se AgendaManager está disponível."""
        try:
            return self.agenda_manager is not None
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return False
    
    # ============ API PRINCIPAL ============
    
    def get_daily_view(self, date: datetime = None) -> Dict[str, Any]:
        """Obtém dados para visualização diária."""
        try:
            # Converter datetime para string no formato YYYY-MM-DD
            if date is None:
                date_str = datetime.now().strftime('%Y-%m-%d')
            else:
                date_str = date.strftime('%Y-%m-%d')
            
            logger.debug(f"Buscando eventos diários para: {date_str}")
            
            # Verificar cache
            cache_key = f"daily_{date_str}"
            if cache_key in self._cache['daily']:
                cached = self._cache['daily'][cache_key]
                if datetime.now().timestamp() - cached['timestamp'] < 60:  # 1 minuto
                    return cached['data']
            
            # Obter eventos do backend
            events = self.agenda_manager.get_day_events(date_str)
            
            # Formatar dados
            formatted_data = self._format_daily_events(events)
            
            # Atualizar cache
            self._cache['daily'][cache_key] = {
                'data': formatted_data,
                'timestamp': datetime.now().timestamp()
            }
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Erro ao obter eventos diários: {e}")
            logger.debug(traceback.format_exc())
            raise RuntimeError(f"Erro ao obter eventos diários: {e}")
    
    def get_weekly_view(self, date: datetime = None) -> Dict[str, Any]:
        """Obtém dados para visualização semanal."""
        try:
            # Converter datetime para string
            if date is None:
                date_str = datetime.now().strftime('%Y-%m-%d')
            else:
                date_str = date.strftime('%Y-%m-%d')
            
            logger.debug(f"Buscando dados semanais a partir de: {date_str}")
            
            # Verificar cache
            cache_key = f"weekly_{date_str}"
            if cache_key in self._cache['weekly']:
                cached = self._cache['weekly'][cache_key]
                if datetime.now().timestamp() - cached['timestamp'] < 300:  # 5 minutos
                    return cached['data']
            
            # Obter dados do backend
            try:
                # Tentar com parâmetro
                week_data = self.agenda_manager.generate_weekly_review(date_str)
            except TypeError as e:
                logger.warning(f"generate_weekly_review não aceita parâmetro: {e}")
                # Tentar sem parâmetro
                week_data = self.agenda_manager.generate_weekly_review()
            
            # Formatar dados
            formatted_data = self._format_weekly_data(week_data)
            
            # Atualizar cache
            self._cache['weekly'][cache_key] = {
                'data': formatted_data,
                'timestamp': datetime.now().timestamp()
            }
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Erro ao obter dados semanais: {e}")
            logger.debug(traceback.format_exc())
            # Retornar dados de fallback
            return self._generate_fallback_week_data()
    
    def add_event(self, event_data: Dict[str, Any]) -> str:
        """Adiciona novo evento e retorna ID."""
        try:
            logger.debug(f"Adicionando evento: {event_data.get('title')}")
            
            # Preparar dados para o backend
            required_fields = ['title', 'start', 'end']
            for field in required_fields:
                if field not in event_data:
                    raise ValueError(f"Campo obrigatório faltando: {field}")
            
            # Chamar o método do backend
            event_id = self.agenda_manager.add_event(
                title=event_data['title'],
                start=event_data['start'],
                end=event_data['end'],
                event_type=event_data.get('type', 'casual'),
                **{k: v for k, v in event_data.items() 
                   if k not in ['title', 'start', 'end', 'type']}
            )
            
            # Limpar cache
            self._clear_cache()
            
            return event_id
            
        except Exception as e:
            logger.error(f"Erro ao adicionar evento: {e}")
            raise RuntimeError(f"Erro ao adicionar evento: {e}")
    
    def update_event(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Atualiza evento existente."""
        try:
            logger.debug(f"Atualizando evento {event_id}: {updates}")
            
            if event_id in self.agenda_manager.events:
                event = self.agenda_manager.events[event_id]
                
                # Aplicar atualizações
                if 'completed' in updates:
                    event.completed = updates['completed']
                
                if 'title' in updates:
                    event.title = updates['title']
                
                if 'priority' in updates:
                    # Mapear prioridade string para valor numérico
                    priority_map = {
                        'critical': 5,
                        'high': 3,
                        'medium': 2,
                        'low': 1
                    }
                    event.priority = priority_map.get(updates['priority'], 2)
                
                # Salvar alterações
                self.agenda_manager._save_events()
                
                # Limpar cache
                self._clear_cache()
                
                return True
            
            logger.warning(f"Evento não encontrado: {event_id}")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao atualizar evento: {e}")
            raise RuntimeError(f"Erro ao atualizar evento: {e}")
    
    def delete_event(self, event_id: str) -> bool:
        """Remove evento."""
        try:
            logger.debug(f"Removendo evento: {event_id}")
            
            if event_id in self.agenda_manager.events:
                # Remover do dicionário de eventos
                del self.agenda_manager.events[event_id]
                
                # Salvar alterações
                self.agenda_manager._save_events()
                
                # Limpar cache
                self._clear_cache()
                
                return True
            
            logger.warning(f"Evento não encontrado: {event_id}")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao remover evento: {e}")
            raise RuntimeError(f"Erro ao remover evento: {e}")
    
    def get_important_dates(self, start_date: datetime = None) -> Dict[str, Any]:
        """Obtém datas importantes."""
        try:
            # Obter prazos do backend
            if start_date is None:
                start_date = datetime.now()
            
            deadlines = self.agenda_manager.get_upcoming_deadlines(days=30)
            
            # Organizar por categoria
            organized = {
                'provas': [],
                'seminarios': [],
                'entregas': [],
                'recessos': [],
                'revisoes': []
            }
            
            for deadline in deadlines:
                title = deadline.get('title', '').lower()
                
                if 'prova' in title or 'teste' in title:
                    organized['provas'].append(deadline)
                elif 'seminário' in title or 'seminario' in title or 'apresentação' in title:
                    organized['seminarios'].append(deadline)
                elif 'entrega' in title or 'trabalho' in title:
                    organized['entregas'].append(deadline)
                elif 'revisão' in title or 'revisao' in title:
                    organized['revisoes'].append(deadline)
                else:
                    # Verificar tipo do evento
                    event_type = deadline.get('type', '')
                    if event_type == 'revisao':
                        organized['revisoes'].append(deadline)
            
            return organized
            
        except Exception as e:
            logger.error(f"Erro ao obter datas importantes: {e}")
            # Retornar estrutura vazia
            return {
                'provas': [],
                'seminarios': [],
                'entregas': [],
                'recessos': [],
                'revisoes': []
            }
    
    def get_analysis_data(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Obtém dados para análise."""
        try:
            if start_date is None:
                start_date = datetime.now() - timedelta(days=7)
            if end_date is None:
                end_date = datetime.now()
            
            # Obter insights de produtividade
            insights = self.agenda_manager.get_productivity_insights()
            
            # Obter sugestões de otimização
            suggestions = self.agenda_manager.suggest_optimizations()
            
            # Coletar estatísticas dos últimos 7 dias
            stats = {
                'total_events': 0,
                'completed_events': 0,
                'productive_hours': 0,
                'completion_rate': 0
            }
            
            # Calcular para cada dia
            current = start_date
            while current <= end_date:
                try:
                    daily_data = self.get_daily_view(current)
                    stats['total_events'] += daily_data['stats']['total']
                    stats['completed_events'] += daily_data['stats']['completed']
                    stats['productive_hours'] += daily_data['stats']['productive_hours']
                    current += timedelta(days=1)
                except:
                    current += timedelta(days=1)
            
            if stats['total_events'] > 0:
                stats['completion_rate'] = (stats['completed_events'] / stats['total_events']) * 100
            
            return {
                'period': f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')}",
                'stats': stats,
                'insights': insights,
                'suggestions': suggestions,
                'trends': self._calculate_trends(start_date, end_date),
                'recommendations': self._generate_recommendations(stats, suggestions)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter dados de análise: {e}")
            return {
                'period': f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')}",
                'stats': {},
                'insights': {},
                'suggestions': [],
                'trends': [],
                'recommendations': []
            }
    
    # ============ FORMATADORES ============
    
    def _format_daily_events(self, events: List) -> Dict[str, Any]:
        """Formata eventos do backend para CLI."""
        if not events:
            return {
                'events': [],
                'stats': self._calculate_daily_stats([]),
                'conflicts': []
            }
        
        formatted = []
        
        for event in events:
            try:
                # Extrair dados do objeto AgendaEvent
                if hasattr(event, 'id'):
                    # É um objeto AgendaEvent
                    event_dict = {
                        'id': event.id,
                        'title': event.title,
                        'type': event.type.value if hasattr(event.type, 'value') else str(event.type),
                        'time': self._format_time(event.start),
                        'duration': event.duration_minutes() if hasattr(event, 'duration_minutes') else 60,
                        'priority': self._map_priority(
                            event.priority.value if hasattr(event.priority, 'value') else event.priority
                        ),
                        'completed': event.completed,
                        'description': event.metadata.get('description', '') if hasattr(event, 'metadata') else '',
                        'tags': []
                    }
                else:
                    # É um dicionário
                    event_dict = {
                        'id': event.get('id', ''),
                        'title': event.get('title', 'Sem título'),
                        'type': event.get('type', 'outro'),
                        'time': self._format_time(event.get('start')),
                        'duration': event.get('duration_minutes', 60),
                        'priority': self._map_priority(event.get('priority', 2)),
                        'completed': event.get('completed', False),
                        'description': event.get('description', ''),
                        'tags': event.get('tags', [])
                    }
                
                formatted.append(event_dict)
                
            except Exception as e:
                logger.warning(f"Erro ao formatar evento: {e}")
                continue
        
        return {
            'events': formatted,
            'stats': self._calculate_daily_stats(formatted),
            'conflicts': self._detect_conflicts(formatted),
        }
    
    def _format_weekly_data(self, week_data: Any) -> Dict[str, Any]:
        """Formata dados semanais."""
        logger.debug(f"Formatando dados semanais do tipo: {type(week_data)}")
        
        # Caso especial: se week_data for uma lista, são eventos
        if isinstance(week_data, list):
            return self._format_events_as_week(week_data)
        
        # Extrair dias da semana
        week_days = []
        stats = {}
        
        if hasattr(week_data, 'days'):
            # É um objeto com atributo days
            raw_days = week_data.days
            stats = getattr(week_data, 'stats', {})
        elif isinstance(week_data, dict):
            # É um dicionário
            raw_days = week_data.get('days', [])
            stats = week_data.get('stats', {})
        else:
            # Formato desconhecido
            logger.warning(f"Formato inesperado para dados semanais: {type(week_data)}")
            return self._generate_fallback_week_data()
        
        # Processar cada dia
        for day in raw_days:
            try:
                if hasattr(day, 'date'):
                    # Objeto com atributos
                    day_date = day.date
                    events_count = len(day.events) if hasattr(day, 'events') else 0
                    productive_hours = day.productive_hours if hasattr(day, 'productive_hours') else 0
                    has_important = day.has_important if hasattr(day, 'has_important') else False
                else:
                    # Dicionário
                    day_date = day.get('date', datetime.now())
                    events_count = len(day.get('events', []))
                    productive_hours = day.get('productive_hours', 0)
                    has_important = day.get('has_important', False)
                
                # Converter para datetime se necessário
                if isinstance(day_date, str):
                    try:
                        day_date = datetime.strptime(day_date, '%Y-%m-%d')
                    except:
                        day_date = datetime.now()
                
                week_days.append({
                    'date': day_date,
                    'display_date': day_date.strftime('%d/%m'),
                    'count': events_count,
                    'productive_hours': productive_hours,
                    'has_important': has_important
                })
                
            except Exception as e:
                logger.warning(f"Erro ao processar dia da semana: {e}")
                continue
        
        return {
            'week_days': week_days,
            'stats': {
                'total_events': stats.get('total_events', 0),
                'total_productive_hours': stats.get('total_productive_hours', 0),
                'completion_rate': stats.get('completion_rate', 0)
            }
        }
    
    def _format_events_as_week(self, events: List) -> Dict[str, Any]:
        """Formata lista de eventos como dados semanais."""
        # Agrupar eventos por dia
        events_by_day = {}
        
        for event in events:
            try:
                if hasattr(event, 'start'):
                    event_date = event.start.date()
                elif isinstance(event, dict):
                    event_date = datetime.strptime(event.get('start', ''), '%Y-%m-%d').date()
                else:
                    continue
                
                if event_date not in events_by_day:
                    events_by_day[event_date] = []
                
                events_by_day[event_date].append(event)
            except:
                continue
        
        # Criar estrutura de dias da semana
        week_days = []
        total_events = 0
        total_productive_hours = 0
        
        # Gerar 7 dias a partir de hoje
        today = datetime.now().date()
        for i in range(7):
            day_date = today + timedelta(days=i)
            day_events = events_by_day.get(day_date, [])
            
            # Calcular horas produtivas
            productive_hours = 0
            for event in day_events:
                if hasattr(event, 'duration_minutes'):
                    duration = event.duration_minutes()
                elif isinstance(event, dict):
                    duration = event.get('duration_minutes', 0)
                else:
                    duration = 0
                
                productive_hours += duration / 60
            
            total_events += len(day_events)
            total_productive_hours += productive_hours
            
            week_days.append({
                'date': datetime.combine(day_date, datetime.min.time()),
                'display_date': day_date.strftime('%d/%m'),
                'count': len(day_events),
                'productive_hours': productive_hours,
                'has_important': any(
                    'importante' in str(getattr(e, 'title', '')).lower() or 
                    'prova' in str(getattr(e, 'title', '')).lower() or
                    'entrega' in str(getattr(e, 'title', '')).lower()
                    for e in day_events
                )
            })
        
        return {
            'week_days': week_days,
            'stats': {
                'total_events': total_events,
                'total_productive_hours': total_productive_hours,
                'completion_rate': 0  # Não temos essa informação
            }
        }
    
    def _generate_fallback_week_data(self) -> Dict[str, Any]:
        """Gera dados de fallback para visualização semanal."""
        week_days = []
        today = datetime.now()
        
        # Gerar 7 dias a partir de hoje
        for i in range(7):
            day_date = today + timedelta(days=i)
            week_days.append({
                'date': day_date,
                'display_date': day_date.strftime('%d/%m'),
                'count': 0,
                'productive_hours': 0,
                'has_important': False
            })
        
        return {
            'week_days': week_days,
            'stats': {
                'total_events': 0,
                'total_productive_hours': 0,
                'completion_rate': 0
            }
        }
    
    def _format_time(self, dt: Any) -> str:
        """Formata datetime para string de hora."""
        if dt is None:
            return '--:--'
        
        # Se já for string no formato ISO
        if isinstance(dt, str):
            try:
                if 'T' in dt:
                    # Formato ISO: YYYY-MM-DDTHH:MM:SS
                    dt_obj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                    return dt_obj.strftime('%H:%M')
                elif len(dt) >= 5 and ':' in dt:
                    # Já está no formato HH:MM
                    return dt[:5]
                else:
                    return '--:--'
            except:
                return '--:--'
        
        # Se for datetime
        if hasattr(dt, 'strftime'):
            return dt.strftime('%H:%M')
        
        return '--:--'
    
    def _map_priority(self, priority: Any) -> str:
        """Mapeia prioridade para string."""
        if priority is None:
            return 'medium'
        
        # Se for int
        if isinstance(priority, int):
            priority_map = {
                5: 'critical',  # BLOQUEIO
                4: 'high',      # FIXO
                3: 'high',      # ALTA
                2: 'medium',    # MEDIA
                1: 'low'        # BAIXA
            }
            return priority_map.get(priority, 'medium')
        
        # Se for string
        priority_str = str(priority).lower()
        if 'critical' in priority_str or 'bloqueio' in priority_str or '5' in priority_str:
            return 'critical'
        elif 'high' in priority_str or 'alta' in priority_str or 'fixo' in priority_str or '4' in priority_str or '3' in priority_str:
            return 'high'
        elif 'low' in priority_str or 'baixa' in priority_str or '1' in priority_str:
            return 'low'
        else:
            return 'medium'
    
    def _calculate_daily_stats(self, events: List) -> Dict[str, Any]:
        """Calcula estatísticas do dia."""
        total = len(events)
        completed = sum(1 for e in events if e.get('completed', False))
        productive_minutes = sum(e.get('duration', 0) for e in events if e.get('completed', False))
        productive_hours = productive_minutes / 60 if productive_minutes > 0 else 0
        productivity_score = int((completed / total * 100) if total > 0 else 0)
        
        return {
            'total': total,
            'completed': completed,
            'productive_hours': round(productive_hours, 1),
            'productivity_score': productivity_score
        }
    
    def _detect_conflicts(self, events: List) -> List[Dict]:
        """Detecta conflitos de horário."""
        conflicts = []
        
        try:
            # Converter horários para minutos do dia para comparação
            events_with_time = []
            for event in events:
                time_str = event.get('time', '--:--')
                if time_str != '--:--':
                    try:
                        hour, minute = map(int, time_str.split(':'))
                        total_minutes = hour * 60 + minute
                        events_with_time.append({
                            'event': event,
                            'minutes': total_minutes,
                            'duration': event.get('duration', 60)
                        })
                    except:
                        continue
            
            # Ordenar por horário
            events_with_time.sort(key=lambda x: x['minutes'])
            
            # Verificar conflitos
            for i in range(len(events_with_time) - 1):
                current = events_with_time[i]
                next_event = events_with_time[i + 1]
                
                # Se os eventos se sobrepõem
                current_end = current['minutes'] + current['duration']
                if current_end > next_event['minutes']:
                    conflicts.append({
                        'event1': current['event']['title'],
                        'event2': next_event['event']['title'],
                        'time': f"{current['event']['time']} - {next_event['event']['time']}",
                        'overlap_minutes': current_end - next_event['minutes']
                    })
        
        except Exception as e:
            logger.warning(f"Erro ao detectar conflitos: {e}")
        
        return conflicts
    
    def _clear_cache(self):
        """Limpa cache."""
        self._cache['daily'] = {}
        self._cache['weekly'] = {}
        logger.debug("Cache limpo")
    
    def _calculate_trends(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Calcula tendências de produtividade."""
        trends = []
        
        try:
            # Coletar dados diários
            daily_stats = []
            current = start_date
            while current <= end_date:
                try:
                    data = self.get_daily_view(current)
                    daily_stats.append({
                        'date': current.strftime('%d/%m'),
                        'completed': data['stats']['completed'],
                        'total': data['stats']['total'],
                        'productive_hours': data['stats']['productive_hours']
                    })
                except:
                    pass
                current += timedelta(days=1)
            
            if len(daily_stats) >= 2:
                # Calcular tendência de conclusão
                first = daily_stats[0]
                last = daily_stats[-1]
                
                if first['total'] > 0 and last['total'] > 0:
                    first_rate = (first['completed'] / first['total']) * 100
                    last_rate = (last['completed'] / last['total']) * 100
                    
                    if last_rate > first_rate + 10:
                        trends.append({
                            'type': 'positive',
                            'message': 'Tendência positiva na taxa de conclusão',
                            'change': f"{first_rate:.1f}% → {last_rate:.1f}%"
                        })
                    elif last_rate < first_rate - 10:
                        trends.append({
                            'type': 'warning',
                            'message': 'Tendência negativa na taxa de conclusão',
                            'change': f"{first_rate:.1f}% → {last_rate:.1f}%"
                        })
                
                # Calcular tendência de horas produtivas
                avg_hours_start = sum(d['productive_hours'] for d in daily_stats[:3]) / 3
                avg_hours_end = sum(d['productive_hours'] for d in daily_stats[-3:]) / 3
                
                if avg_hours_end > avg_hours_start + 2:
                    trends.append({
                        'type': 'positive',
                        'message': 'Aumento significativo nas horas produtivas',
                        'change': f"{avg_hours_start:.1f}h → {avg_hours_end:.1f}h"
                    })
                elif avg_hours_end < avg_hours_start - 2:
                    trends.append({
                        'type': 'warning',
                        'message': 'Queda nas horas produtivas',
                        'change': f"{avg_hours_start:.1f}h → {avg_hours_end:.1f}h"
                    })
        
        except Exception as e:
            logger.warning(f"Erro ao calcular tendências: {e}")
        
        return trends
    
    def _generate_recommendations(self, stats: Dict, suggestions: List) -> List[Dict]:
        """Gera recomendações baseadas em estatísticas."""
        recommendations = []
        
        try:
            # Baseado na taxa de conclusão
            completion_rate = stats.get('completion_rate', 0)
            if completion_rate < 50:
                recommendations.append({
                    'priority': 'high',
                    'title': 'Baixa taxa de conclusão',
                    'message': 'Considere ajustar metas ou melhorar o foco',
                    'action': 'Revisar prioridades e eliminar distrações'
                })
            elif completion_rate > 90:
                recommendations.append({
                    'priority': 'low',
                    'title': 'Alta taxa de conclusão',
                    'message': 'Excelente! Pode ser hora de aumentar os desafios',
                    'action': 'Adicionar metas mais ambiciosas'
                })
            
            # Baseado em horas produtivas
            productive_hours = stats.get('productive_hours', 0)
            days_in_period = 7  # assumindo semana
            avg_daily_hours = productive_hours / days_in_period if days_in_period > 0 else 0
            
            if avg_daily_hours > 8:
                recommendations.append({
                    'priority': 'high',
                    'title': 'Sobrecarga de trabalho',
                    'message': f'Média de {avg_daily_hours:.1f}h produtivas por dia',
                    'action': 'Considere incluir mais pausas e tempo de lazer'
                })
            elif avg_daily_hours < 2:
                recommendations.append({
                    'priority': 'medium',
                    'title': 'Baixa produtividade',
                    'message': f'Apenas {avg_daily_hours:.1f}h produtivas por dia',
                    'action': 'Revisar rotina e encontrar horários mais produtivos'
                })
            
            # Adicionar sugestões do backend
            for suggestion in suggestions:
                recommendations.append({
                    'priority': 'medium',
                    'title': 'Otimização sugerida',
                    'message': suggestion.get('message', ''),
                    'action': suggestion.get('suggestion', '')
                })
        
        except Exception as e:
            logger.warning(f"Erro ao gerar recomendações: {e}")
        
        return recommendations
