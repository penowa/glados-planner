# src/cli/interactive/screens/agenda_screen.py (modificações no método _handle_input)
"""
Tela principal da Agenda Inteligente - Versão otimizada sem flickering
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
import calendar
import logging
import sys
import tty
import termios

from .base_screen import BaseScreen
from src.cli.integration.agenda_bridge import AgendaBridge
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
from src.cli.interactive.terminal import Key

logger = logging.getLogger(__name__)

class AgendaScreen(BaseScreen):
    """Tela principal de agenda com renderização otimizada."""
    
    VIEWS = ['daily', 'weekly', 'monthly', 'semester']
    VIEW_NAMES = {
        'daily': 'Diária',
        'weekly': 'Semanal', 
        'monthly': 'Mensal',
        'semester': 'Semestral'
    }
    
    PRIORITY_COLORS = {
        'critical': 'error',
        'high': 'warning',
        'medium': 'primary',
        'low': 'info',
        'completed': 'success'
    }
    
    EVENT_ICONS = {
        'aula': Icon.BOOK,
        'leitura': Icon.BOOK,
        'producao': Icon.TARGET,
        'revisao': Icon.FLASHCARD,
        'prova': Icon.ALERT,
        'seminario': Icon.TARGET,
        'entrega': Icon.TASK,
        'orientacao': Icon.GLADOS,
        'sono': '😴',
        'refeicao': '🍽️',
        'lazer': '🎮',
        'outro': Icon.TASK
    }
    
    def __init__(self, terminal, backend_integration=None):
        super().__init__(terminal)
        
        # Inicializar bridge
        try:
            self.bridge = AgendaBridge(backend_integration)
            if not self.bridge.is_available():
                logger.warning("AgendaManager não disponível")
                self._show_fatal_error("AgendaManager não disponível")
        except Exception as e:
            logger.error(f"Erro ao inicializar bridge: {e}")
            self._show_fatal_error(str(e))
            raise
        
        # Estado da tela
        self.current_view = 0  # daily
        self.current_date = datetime.now()
        self.selected_index = 0
        self.view_data = None
        self.submenu_active = False
        self.error_message = None
        
        # Controles de renderização (como na dashboard)
        self.needs_redraw = True
        self.last_clock_update = 0
        self.last_data_update = 0
        self.input_timeout = 0.1  # Timeout curto como na dashboard
        
        # Cache do tamanho do terminal
        self.last_width = 0
        self.last_height = 0
        
        # Cache de dados
        self._data_cache = {}
        self._cache_timestamps = {}
        
        # Flags para limpeza de tela
        self._needs_full_clear = True  # Inicialmente precisa limpar
        
        # Carregar dados iniciais
        self._load_data()
    
    def show(self) -> Optional[str]:
        """Loop principal otimizado (padrão dashboard)."""
        self.running = True
        
        # Limpeza inicial da tela
        self.terminal.clear_screen()
        
        while self.running:
            try:
                # Verificar se precisa limpar completamente
                if self._needs_full_clear:
                    self.terminal.clear_screen()
                    self._needs_full_clear = False
                    self.needs_redraw = True  # Forçar redesenho completo
                
                # Atualiza tela se necessário
                if self.needs_redraw and not self.submenu_active:
                    self._draw()
                    self.needs_redraw = False
                
                # Obtém input com timeout curto
                key = self.terminal.get_key(self.input_timeout)
                
                # Processa input se houver
                if key and not self.submenu_active:
                    result = self._handle_input(key)
                    if result:
                        return result
                
                # Atualizações periódicas
                current_time = time.time()
                
                # Atualizar relógio no cabeçalho a cada segundo
                if current_time - self.last_clock_update >= 1.0:
                    self._update_clock()
                    self.last_clock_update = current_time
                
                # Atualizar dados a cada 30 segundos
                if current_time - self.last_data_update >= 30:
                    self._load_data()
                    
            except KeyboardInterrupt:
                self.running = False
                return 'back'
            except Exception as e:
                logger.error(f"Erro no loop principal: {e}")
                self.error_message = str(e)[:100]
                self.needs_redraw = True
        
        return None
    
    def _draw(self):
        """Renderiza a tela inteira de uma vez."""
        try:
            width, height = self.terminal.get_size()
            
            # Limpa apenas o buffer interno para renderização normal
            # Não limpa a tela física para evitar flickering
            self.terminal.clear()
            
            # Cabeçalho (linhas 0-4)
            self._render_header(width)
            
            # Conteúdo principal (a partir da linha 5)
            content_height = height - 10
            view_type = self.VIEWS[self.current_view]
            
            # Mostrar mensagem de erro se houver
            if self.error_message:
                self._show_error(width, height)
            else:
                try:
                    start_y = 5
                    if view_type == 'daily':
                        self._render_daily_view(0, start_y, width, content_height)
                    elif view_type == 'weekly':
                        self._render_weekly_view(0, start_y, width, content_height)
                    elif view_type == 'monthly':
                        self._render_monthly_view(0, start_y, width, content_height)
                    elif view_type == 'semester':
                        self._render_semester_view(0, start_y, width, content_height)
                except Exception as e:
                    logger.error(f"Erro ao renderizar view {view_type}: {e}")
                    self._show_simple_message(f"Erro: {str(e)[:50]}", width, height)
            
            # Rodapé (últimas 3 linhas)
            self._render_footer(width, height)
            
            self.terminal.flush()
            self.last_width = width
            self.last_height = height
            
        except Exception as e:
            logger.error(f"Erro crítico ao desenhar: {e}")
    
    def _update_clock(self):
        """Atualiza apenas o relógio no cabeçalho (renderização parcial)."""
        try:
            width, _ = self.terminal.get_size()
            
            # Linha do relógio (linha 0)
            time_str = datetime.now().strftime("%H:%M")
            clock_text = f"🕐 {time_str}"
            clock_x = width - len(clock_text) - 1
            
            # Salva a posição atual do cursor
            self.terminal.save_cursor()
            
            # Move para a posição do relógio e atualiza
            self.terminal.move_cursor(0, clock_x)
            self.terminal.print_at(clock_x, 0, clock_text, {"color": "info"})
            
            # Restaura posição do cursor
            self.terminal.restore_cursor()
            self.terminal.flush()
            
        except Exception as e:
            logger.debug(f"Erro ao atualizar relógio: {e}")
    
    def _render_header(self, width: int):
        """Renderiza cabeçalho fixo da agenda."""
        view_name = self.VIEW_NAMES[self.VIEWS[self.current_view]]
        date_str = self.current_date.strftime("%d/%m/%Y")
        
        # Linha 0: Relógio e data
        time_str = datetime.now().strftime("%H:%M")
        date_display = f"📅 {date_str}"
        clock_text = f"🕐 {time_str}"
        
        self.terminal.print_at(0, 0, date_display, {"color": "primary"})
        self.terminal.print_at(width - len(clock_text) - 1, 0, clock_text, {"color": "info"})
        
        # Linha 1: Título
        title = f"AGENDA {view_name.upper()}"
        title_x = max(0, (width - len(title)) // 2)
        self.terminal.print_at(title_x, 1, title, {"color": "accent", "bold": True})
        
        # Linha 2: Status do backend
        try:
            if self.bridge and self.bridge.is_available():
                status = "✅ Backend conectado"
                color = "success"
            else:
                status = "⚠️ Backend offline"
                color = "warning"
        except:
            status = "❓ Status desconhecido"
            color = "warning"
        
        self.terminal.print_at(0, 2, status, {"color": color})
        
        # Linha 3: Navegação (ATUALIZADA - adicionado Q)
        nav = "[TAB: Views] [←→: Datas] [↑↓: Selecionar] [A: Adicionar] [ENTER: Detalhes] [Q: Dashboard]"
        if len(nav) > width:
            nav = nav[:width-3] + "..."
        self.terminal.print_at(0, 3, nav, {"color": "dim"})
        
        # Linha 4: Separador
        self.terminal.print_at(0, 4, "─" * width, {"color": "dim"})
    
    def _render_daily_view(self, x: int, y: int, width: int, height: int):
        """Renderiza visualização diária otimizada."""
        if not self.view_data:
            self.terminal.print_at(x, y, "Carregando eventos...", {"color": "warning"})
            return
        
        events = self.view_data.get('events', [])
        
        if not events:
            msg = "📭 Nenhum evento agendado para hoje!"
            msg_x = max(0, (width - len(msg)) // 2)
            self.terminal.print_at(msg_x, y, msg, {"color": "info"})
            return
        
        # Renderizar eventos
        max_events = min(len(events), height - 5)
        for i in range(max_events):
            event_y = y + i
            event = events[i]
            is_selected = (i == self.selected_index)
            
            # Limpar linha antes de renderizar
            self.terminal.print_at(x, event_y, " " * width, {})
            self._render_event_line(event, x, event_y, width, is_selected)
        
        # Estatísticas
        if self.view_data.get('stats') and max_events + 2 < height:
            stats = self.view_data['stats']
            stats_y = y + max_events + 1
            
            total = stats.get('total', 0)
            completed = stats.get('completed', 0)
            
            if total > 0:
                progress = int((completed / total) * 20)
                progress_bar = "█" * progress + "░" * (20 - progress)
                stats_text = f"📊 [{progress_bar}] {completed}/{total}"
            else:
                stats_text = "📊 [Sem eventos]"
            
            self.terminal.print_at(x, stats_y, stats_text, {"color": "info"})
    
    def _render_weekly_view(self, x: int, y: int, width: int, height: int):
        """Renderiza visualização semanal otimizada."""
        if not self.view_data:
            self.terminal.print_at(x, y, "Carregando semana...", {"color": "warning"})
            return
        
        week_days = self.view_data.get('week_days', [])
        
        if not week_days:
            msg = "📭 Sem dados para esta semana"
            msg_x = max(0, (width - len(msg)) // 2)
            self.terminal.print_at(msg_x, y, msg, {"color": "info"})
            return
        
        # Layout responsivo
        if width >= 100:
            self._render_weekly_detailed(x, y, width, height, week_days)
        elif width >= 70:
            self._render_weekly_compact(x, y, width, height, week_days)
        else:
            self._render_weekly_minimal(x, y, width, height, week_days)
    
    def _render_weekly_compact(self, x: int, y: int, width: int, height: int, week_days: List):
        """Layout compacto para semana (70-99 colunas)."""
        col_width = width // 7
        days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        
        # Cabeçalhos
        for i, day in enumerate(days):
            if i < len(week_days):
                day_data = week_days[i]
                header = f"{day} {day_data.get('display_date', '')}"
                is_today = day_data.get('date', datetime.now()).date() == datetime.now().date()
                
                style = {"color": "accent" if is_today else "primary", "bold": True}
                self.terminal.print_at(x + i * col_width, y, header.center(col_width), style)
        
        # Conteúdo
        for i, day_data in enumerate(week_days[:7]):
            col_x = x + i * col_width
            content_y = y + 1
            
            # Número de eventos
            count = day_data.get('count', 0)
            count_str = f"{count} ev"
            color = "success" if count > 0 else "dim"
            self.terminal.print_at(col_x, content_y, count_str.center(col_width), 
                                 {"color": color})
            
            # Horas produtivas
            hours = day_data.get('productive_hours', 0)
            hours_str = f"{hours:.1f}h"
            color = "success" if hours > 0 else "dim"
            self.terminal.print_at(col_x, content_y + 1, hours_str.center(col_width), 
                                 {"color": color})
            
            # Indicador de seleção
            if i == self.selected_index:
                self.terminal.print_at(col_x, content_y + 2, "↑".center(col_width),
                                     {"color": "accent", "bold": True})
    
    def _render_weekly_detailed(self, x: int, y: int, width: int, height: int, week_days: List):
        """Layout detalhado para telas grandes (100+ colunas)."""
        col_width = width // 7
        
        # Cabeçalhos
        for i, day_data in enumerate(week_days[:7]):
            header = f"{day_data.get('display_date', '')}"
            is_today = day_data.get('date', datetime.now()).date() == datetime.now().date()
            
            style = {"color": "accent" if is_today else "primary", "bold": True}
            self.terminal.print_at(x + i * col_width, y, header.center(col_width), style)
        
        # Eventos por dia
        max_events_per_day = height - 2
        for day_idx, day_data in enumerate(week_days[:7]):
            events = day_data.get('events', [])[:max_events_per_day]
            for event_idx, event in enumerate(events):
                event_y = y + 1 + event_idx
                event_x = x + (day_idx * col_width)
                
                # Formatar evento
                time_str = event.get('time', '--:--')[:5]
                title = event.get('title', '')[:col_width - 7]
                line = f"{time_str} {title}"
                
                # Estilo
                priority = event.get('priority', 'medium')
                color = self.PRIORITY_COLORS.get(priority, 'primary')
                if event.get('completed', False):
                    color = 'success'
                
                self.terminal.print_at(event_x, event_y, line.ljust(col_width), {"color": color})
    
    def _render_weekly_minimal(self, x: int, y: int, width: int, height: int, week_days: List):
        """Layout mínimo para telas pequenas (< 70 colunas)."""
        # Mostrar apenas 3-4 dias visíveis com scroll
        start_idx = max(0, min(self.selected_index - 1, len(week_days) - 3))
        visible_days = week_days[start_idx:start_idx + min(3, width // 20)]
        
        col_width = min(20, width // len(visible_days)) if visible_days else 20
        
        for i, day_data in enumerate(visible_days):
            col_x = x + (i * col_width)
            
            # Cabeçalho
            header = f"{day_data.get('display_date', '')}"
            is_selected = (start_idx + i == self.selected_index)
            is_today = day_data.get('date', datetime.now()).date() == datetime.now().date()
            
            header_style = {"bold": True}
            if is_selected:
                header_style.update({"color": "accent", "reverse": True})
            elif is_today:
                header_style["color"] = "accent"
            else:
                header_style["color"] = "primary"
            
            self.terminal.print_at(col_x, y, header.center(col_width), header_style)
            
            # Conteúdo
            count = day_data.get('count', 0)
            hours = day_data.get('productive_hours', 0)
            
            count_str = f"{count} ev"
            hours_str = f"{hours:.1f}h"
            
            count_color = "success" if count > 0 else "dim"
            hours_color = "success" if hours > 0 else "dim"
            
            self.terminal.print_at(col_x, y + 1, count_str.center(col_width), {"color": count_color})
            self.terminal.print_at(col_x, y + 2, hours_str.center(col_width), {"color": hours_color})
    
    def _render_monthly_view(self, x: int, y: int, width: int, height: int):
        """Renderiza visualização mensal otimizada e estável."""
        try:
            # Usar cache para evitar regeneração constante
            cache_key = f"monthly_{self.current_date.year}_{self.current_date.month}"
            
            if cache_key in self._data_cache:
                month_data = self._data_cache[cache_key]
            else:
                month_data = self._generate_monthly_data()
                self._data_cache[cache_key] = month_data
                self._cache_timestamps[cache_key] = time.time()
        
            year = month_data['year']
            month = month_data['month']
            days = month_data['days']
        
            # Título do mês (centralizado)
            month_name = datetime(year, month, 1).strftime("%B %Y").capitalize()
            title = f"📅 {month_name}"
            title_x = max(0, (width - len(title)) // 2)
            self.terminal.print_at(title_x, y, title, {"color": "accent", "bold": True})
        
            # Dias da semana - layout fixo e simples
            weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
            col_width = 4  # Fixo para consistência
        
            # Cabeçalhos dos dias (linha y+2)
            for i, day in enumerate(weekdays):
                day_x = x + (i * col_width)
                if day_x + 3 <= width:
                    self.terminal.print_at(day_x, y + 2, day.center(3), 
                                         {"color": "primary", "bold": True})
        
            # Calcular primeiro dia do mês
            first_day = datetime(year, month, 1)
            first_weekday = (first_day.weekday() + 1) % 7  # 0=domingo
        
            # Renderizar dias (começa na linha y+4)
            current_row = 0
            current_col = first_weekday
            today = datetime.now().date()
        
            for idx, day_info in enumerate(days):
                day_num = day_info['day_num']
                col_x = x + (current_col * col_width)
                row_y = y + 4 + current_row
            
                if col_x < width and row_y < height:
                    # Determinar estilo
                    if idx == self.selected_index:
                        style = {"color": "accent", "bold": True, "reverse": True}
                    elif day_info.get('is_today'):
                        style = {"color": "accent", "bold": True}
                    elif day_info.get('is_weekend'):
                        style = {"color": "warning"}
                    elif day_info.get('has_events'):
                        style = {"color": "success", "bold": True}
                    else:
                        style = {"color": "primary"}
                
                    # Formatar número (2 dígitos)
                    day_str = f"{day_num:2d}"
                    self.terminal.print_at(col_x, row_y, day_str, style)
            
                # Avançar para próxima coluna
                current_col += 1
                if current_col >= 7:
                    current_col = 0
                    current_row += 1
        
            # Estatísticas (se houver espaço)
            stats_y = y + 4 + current_row + 2
            if stats_y < height - 2:
                stats = month_data.get('stats', {})
                total_events = stats.get('total_events', 0)
                
                if total_events > 0:
                    hours = stats.get('productive_hours', 0)
                    stats_text = f"📊 {total_events} eventos • ⏱️ {hours:.1f}h"
                    stats_x = max(0, (width - len(stats_text)) // 2)
                    self.terminal.print_at(stats_x, stats_y, stats_text, {"color": "info"})
        
        except Exception as e:
            logger.error(f"Erro ao renderizar mensal: {e}")
            msg = "📅 Calendário Mensal"
            msg_x = max(0, (width - len(msg)) // 2)
            self.terminal.print_at(msg_x, y + height // 2, msg, {"color": "info"})

    def _render_semester_view(self, x: int, y: int, width: int, height: int):
        """Renderiza visualização semestral otimizada e estável."""
        try:
            # Usar cache
            cache_key = f"semester_{self.current_date.year}_{self.current_date.month // 7}"
            
            if cache_key in self._data_cache:
                semester_data = self._data_cache[cache_key]
            else:
                semester_data = self._generate_semester_data()
                self._data_cache[cache_key] = semester_data
                self._cache_timestamps[cache_key] = time.time()
            
            # Título
            title = f"🎓 {semester_data['period']}"
            title_x = max(0, (width - len(title)) // 2)
            self.terminal.print_at(title_x, y, title, {"color": "accent", "bold": True})
            
            months = semester_data['months']
            
            # Layout responsivo baseado na largura
            if width >= 80:
                cols = 3
                col_width = 26
            elif width >= 60:
                cols = 2
                col_width = 30
            else:
                cols = 1
                col_width = min(40, width - 2)
            
            # Renderizar meses em grade
            row_height = 3
            for i, month_data in enumerate(months):
                if i >= 6:  # Máximo 6 meses
                    break
                    
                row = i // cols
                col = i % cols
                
                month_x = x + (col * col_width)
                month_y = y + 2 + (row * row_height)
                
                if month_x >= width:
                    continue
                
                # Nome do mês
                month_name = f"{month_data['name']}/{str(month_data['year'])[2:]}"
                if i == self.selected_index:
                    style = {"color": "accent", "bold": True, "reverse": True}
                else:
                    style = {"color": "primary", "bold": True}
                
                self.terminal.print_at(month_x, month_y, month_name.ljust(col_width - 2), style)
                
                # Estatísticas do mês
                events_count = month_data['events_count']
                if events_count > 0:
                    events_text = f"  {events_count} eventos"
                    color = "success" if events_count > 3 else "primary"
                    self.terminal.print_at(month_x, month_y + 1, events_text, {"color": color})
            
            # Estatísticas do semestre
            total_rows = (min(len(months), 6) + cols - 1) // cols
            stats_y = y + 2 + (total_rows * row_height) + 1
            
            if stats_y < height - 2:
                stats = semester_data['stats']
                stats_text = f"📊 {stats['total_events']} eventos • ✅ {stats['completion_rate']:.1f}%"
                if len(stats_text) > width:
                    stats_text = stats_text[:width-3] + "..."
                stats_x = max(0, (width - len(stats_text)) // 2)
                self.terminal.print_at(stats_x, stats_y, stats_text, {"color": "info"})
            
        except Exception as e:
            logger.error(f"Erro ao renderizar semestral: {e}")
            msg = "🎓 Visualização Semestral"
            msg_x = max(0, (width - len(msg)) // 2)
            self.terminal.print_at(msg_x, y + height // 2, msg, {"color": "info"})
    
    def _render_event_line(self, event: Dict, x: int, y: int, width: int, selected: bool):
        """Renderiza uma linha de evento de forma otimizada."""
        try:
            # Ícone
            icon = self.EVENT_ICONS.get(event.get('type', 'outro'), Icon.TASK)
            if isinstance(icon, Icon):
                icon_str = icon.value
            else:
                icon_str = icon
            
            # Estilo
            priority = event.get('priority', 'medium')
            completed = event.get('completed', False)
            
            if completed:
                style_name = 'completed'
            else:
                style_name = priority
            
            color = self.PRIORITY_COLORS.get(style_name, 'primary')
            
            # Seleção
            if selected:
                style = {"color": "accent", "bold": True, "reverse": True}
            else:
                style = {"color": color}
                if completed:
                    style["dim"] = True
            
            # Formatar linha
            time_str = event.get('time', '--:--')
            title = event.get('title', 'Sem título')
            
            if completed:
                title = f"✓ {title}"
            
            max_title = width - 15
            if len(title) > max_title:
                title = title[:max_title - 3] + "..."
            
            line = f"{icon_str} {time_str:5s} {title}"
            self.terminal.print_at(x, y, line, style)
            
        except Exception as e:
            logger.debug(f"Erro ao renderizar linha de evento: {e}")
    
    def _render_footer(self, width: int, height: int):
        """Renderiza rodapé fixo."""
        footer_y = height - 3
        
        # Separador
        self.terminal.print_at(0, footer_y, "─" * width, {"color": "dim"})
        
        # Ajuda contextual (ATUALIZADA - adicionado Q)
        view_type = self.VIEWS[self.current_view]
        
        if view_type == 'daily':
            help_text = "ENTER: Detalhes • ESPAÇO: Concluir • A: Adicionar • DEL: Remover • Q: Dashboard"
        elif view_type == 'weekly':
            help_text = "ENTER: Ver dia • ↑↓: Selecionar dia • ←→: Navegar semanas • Q: Dashboard"
        elif view_type == 'monthly':
            help_text = "ENTER: Ver dia • ←→: Navegar meses • Q: Dashboard"
        elif view_type == 'semester':
            help_text = "ENTER: Ver mês • ←→: Navegar semestres • Q: Dashboard"
        
        help_text += " • TAB: Trocar view • R: Recarregar"
        
        # Centralizar
        if len(help_text) > width:
            help_text = help_text[:width-3] + "..."
        
        help_x = max(0, (width - len(help_text)) // 2)
        self.terminal.print_at(help_x, footer_y + 1, help_text, {"color": "dim"})
    
    def _load_data(self):
        """Carrega dados com cache inteligente."""
        view_type = self.VIEWS[self.current_view]
        
        # Verificar cache primeiro
        cache_key = f"{view_type}_{self.current_date.strftime('%Y%m%d')}"
        current_time = time.time()
        
        # Cache válido por 5 minutos para daily/weekly, 30 minutos para monthly/semester
        cache_ttl = 300 if view_type in ['daily', 'weekly'] else 1800
        
        if (cache_key in self._data_cache and 
            current_time - self._cache_timestamps.get(cache_key, 0) < cache_ttl):
            self.view_data = self._data_cache[cache_key]
            self.last_data_update = current_time
            self.needs_redraw = True
            return
        
        try:
            logger.debug(f"Carregando dados para view: {view_type}")
            
            if view_type == 'daily':
                self.view_data = self.bridge.get_daily_view(self.current_date)
            elif view_type == 'weekly':
                self.view_data = self.bridge.get_weekly_view(self.current_date)
            elif view_type == 'monthly':
                self.view_data = self._generate_monthly_data()
            elif view_type == 'semester':
                self.view_data = self._generate_semester_data()
            
            # Armazenar em cache
            self._data_cache[cache_key] = self.view_data
            self._cache_timestamps[cache_key] = current_time
            
            self.error_message = None
            self.last_data_update = current_time
            self.needs_redraw = True
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            self.error_message = f"Erro: {str(e)[:50]}"
            self.view_data = self._get_fallback_data(view_type)
            self.needs_redraw = True
    
    def _generate_monthly_data(self) -> Dict[str, Any]:
        """Gera dados para visualização mensal (simplificado)."""
        try:
            year = self.current_date.year
            month = self.current_date.month
            
            # Obter dias do mês
            _, num_days = calendar.monthrange(year, month)
            
            days = []
            today = datetime.now().date()
            
            # Apenas estrutura básica - eventos podem ser carregados sob demanda
            for day in range(1, num_days + 1):
                date = datetime(year, month, day)
                days.append({
                    'day_num': day,
                    'date': date,
                    'is_today': date.date() == today,
                    'is_weekend': date.weekday() >= 5,
                    'has_events': False  # Simplificado para performance
                })
            
            return {
                'month': month,
                'year': year,
                'days': days,
                'stats': {'total_events': 0, 'productive_hours': 0}
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar dados mensais: {e}")
            return self._get_fallback_data('monthly')
    
    def _generate_semester_data(self) -> Dict[str, Any]:
        """Gera dados para visualização semestral (simplificado)."""
        try:
            current_year = self.current_date.year
            current_month = self.current_date.month
            
            # Determinar semestre
            if current_month <= 6:
                start_month = 1
                end_month = 6
                period = f"1º Semestre {current_year}"
            else:
                start_month = 7
                end_month = 12
                period = f"2º Semestre {current_year}"
            
            months = []
            for month_num in range(start_month, end_month + 1):
                date = datetime(current_year, month_num, 1)
                months.append({
                    'month': month_num,
                    'year': current_year,
                    'name': date.strftime('%b'),
                    'events_count': 0,
                    'important_dates': []
                })
            
            return {
                'period': period,
                'months': months,
                'stats': {'total_events': 0, 'completion_rate': 0}
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar dados semestrais: {e}")
            return self._get_fallback_data('semester')
    
    def _get_fallback_data(self, view_type: str) -> Dict:
        """Dados de fallback simplificados."""
        if view_type == 'daily':
            return {
                'events': [],
                'stats': {'total': 0, 'completed': 0, 'productive_hours': 0},
                'is_fallback': True
            }
        elif view_type == 'weekly':
            week_days = []
            for i in range(7):
                day_date = self.current_date + timedelta(days=i)
                week_days.append({
                    'date': day_date,
                    'display_date': day_date.strftime('%d/%m'),
                    'count': 0,
                    'productive_hours': 0
                })
            return {'week_days': week_days, 'is_fallback': True}
        elif view_type == 'monthly':
            return self._generate_monthly_data()
        elif view_type == 'semester':
            return self._generate_semester_data()
    
    def _handle_input(self, key) -> Optional[str]:
        """Processa entrada do teclado de forma otimizada."""
        try:
            if key is None:
                return None
            
            # Converter tecla
            key_name = None
            if isinstance(key, Key):
                key_name = key.name.lower()
            elif isinstance(key, str):
                key_name = key.lower()
            else:
                return None
            
            # Limpar erro se houver input
            if self.error_message:
                self.error_message = None
                self.needs_redraw = True
            
            # CASOS QUE PRECISAM DE LIMPEZA COMPLETA:
            
            # 1. Troca de visualização (TAB)
            if key_name == 'tab':
                self.current_view = (self.current_view + 1) % len(self.VIEWS)
                self.selected_index = 0
                self._needs_full_clear = True  # Forçar limpeza completa
                self._load_data()  # Isso marcará needs_redraw
                return None
            
            # 2. Navegação entre períodos (← →)
            elif key_name == 'left' or key_name == 'right':
                # Para views mensais e semestrais, precisa de limpeza completa
                view_type = self.VIEWS[self.current_view]
                if view_type in ['monthly', 'semester']:
                    self._needs_full_clear = True
                self._navigate_period(-1 if key_name == 'left' else 1)
                return None
            
            # 3. Navegação de seleção (↑ ↓) - NÃO precisa de limpeza completa
            elif key_name == 'up':
                self._move_selection(-1)
                return None
            
            elif key_name == 'down':
                self._move_selection(1)
                return None
            
            # 4. Ações que podem precisar de limpeza completa
            
            # Enter: pode mudar para outra view (daily -> detalhes não precisa)
            elif key_name == 'enter':
                result = self._select_item()
                # Se select_item mudou a view (semanal -> diária, etc.)
                # ele já terá chamado _load_data que marcará needs_redraw
                # Mas não forçamos limpeza completa aqui
                return result
            
            # 5. Tecla Q para retornar ao dashboard (NOVIDADE)
            elif key_name == 'q':
                self.running = False
                return 'goto:dashboard'  # Comando especial para retornar ao dashboard
            
            # 6. ESC mantém comportamento original (voltar)
            elif key_name == 'escape':
                self.running = False
                return 'back'  # Mantém o comportamento original
            
            # 7. Outras ações que não precisam de limpeza completa
            
            elif key_name == 'space':
                self._toggle_completion()
                return None
            
            elif key_name == 'a':
                return self._open_add_menu()
            
            elif key_name == 'delete':
                self._delete_selected()
                return None
            
            elif key_name == 'r':
                # Limpar cache e recarregar - precisa de limpeza
                self._data_cache.clear()
                self._needs_full_clear = True
                self._load_data()
                return None
            
            # 8. Tecla D também para dashboard (alternativa)
            elif key_name == 'd':
                self.running = False
                return 'goto:dashboard'
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao processar tecla: {e}")
            self.error_message = f"Erro: {str(e)[:50]}"
            self.needs_redraw = True
            return None
    
    def _navigate_period(self, direction: int):
        """Navega entre períodos de forma otimizada."""
        view_type = self.VIEWS[self.current_view]
        
        if view_type == 'daily':
            self.current_date += timedelta(days=direction)
        elif view_type == 'weekly':
            self.current_date += timedelta(weeks=direction)
        elif view_type == 'monthly':
            # Navegar meses mantendo dia válido
            month = self.current_date.month + direction
            year = self.current_date.year
            
            if month > 12:
                month = 1
                year += 1
            elif month < 1:
                month = 12
                year -= 1
            
            try:
                self.current_date = datetime(year, month, min(self.current_date.day, 28))
            except:
                self.current_date = datetime(year, month, 1)
        elif view_type == 'semester':
            # Navegar semestres
            if direction > 0:
                if self.current_date.month <= 6:
                    self.current_date = datetime(self.current_date.year, 7, 1)
                else:
                    self.current_date = datetime(self.current_date.year + 1, 1, 1)
            else:
                if self.current_date.month <= 6:
                    self.current_date = datetime(self.current_date.year - 1, 7, 1)
                else:
                    self.current_date = datetime(self.current_date.year, 1, 1)
        
        self.selected_index = 0
        self._load_data()
    
    def _move_selection(self, direction: int):
        """Move seleção atual com limites apropriados."""
        if not self.view_data:
            return
        
        view_type = self.VIEWS[self.current_view]
        
        if view_type == 'daily':
            max_index = len(self.view_data.get('events', [])) - 1
        elif view_type == 'weekly':
            max_index = min(6, len(self.view_data.get('week_days', [])) - 1)
        elif view_type == 'monthly':
            max_index = len(self.view_data.get('days', [])) - 1
        elif view_type == 'semester':
            max_index = len(self.view_data.get('months', [])) - 1
        else:
            return
        
        new_index = self.selected_index + direction
        if 0 <= new_index <= max_index:
            self.selected_index = new_index
            self.needs_redraw = True
    
    def _select_item(self) -> Optional[str]:
        """Seleciona item atual."""
        view_type = self.VIEWS[self.current_view]
        
        if view_type == 'daily':
            events = self.view_data.get('events', [])
            if 0 <= self.selected_index < len(events):
                return self._show_event_details(events[self.selected_index])
        
        elif view_type == 'weekly':
            week_days = self.view_data.get('week_days', [])
            if 0 <= self.selected_index < len(week_days):
                day_data = week_days[self.selected_index]
                self.current_date = day_data.get('date', self.current_date)
                self.current_view = 0  # Muda para daily
                self.selected_index = 0
                self._needs_full_clear = True  # Mudança de view
                self._load_data()
        
        elif view_type == 'monthly':
            days = self.view_data.get('days', [])
            if 0 <= self.selected_index < len(days):
                day_data = days[self.selected_index]
                self.current_date = day_data.get('date', self.current_date)
                self.current_view = 0  # Muda para daily
                self.selected_index = 0
                self._needs_full_clear = True  # Mudança de view
                self._load_data()
        
        elif view_type == 'semester':
            months = self.view_data.get('months', [])
            if 0 <= self.selected_index < len(months):
                month_data = months[self.selected_index]
                self.current_date = datetime(month_data['year'], month_data['month'], 1)
                self.current_view = 2  # Muda para monthly
                self.selected_index = 0
                self._needs_full_clear = True  # Mudança de view
                self._load_data()
        
        return None
    
    def _toggle_completion(self):
        """Alterna estado de conclusão (apenas daily view)."""
        if self.VIEWS[self.current_view] != 'daily':
            return
        
        events = self.view_data.get('events', [])
        if 0 <= self.selected_index < len(events):
            event = events[self.selected_index]
            event_id = event.get('id')
            
            if event_id:
                try:
                    new_state = not event.get('completed', False)
                    self.bridge.update_event(event_id, {'completed': new_state})
                    
                    # Limpar cache e recarregar
                    self._data_cache.clear()
                    self._load_data()
                    
                except Exception as e:
                    logger.error(f"Erro ao alternar conclusão: {e}")
    
    def _delete_selected(self):
        """Remove item selecionado (apenas daily view)."""
        if self.VIEWS[self.current_view] != 'daily':
            return
        
        events = self.view_data.get('events', [])
        if 0 <= self.selected_index < len(events):
            event = events[self.selected_index]
            event_id = event.get('id')
            
            if event_id:
                # Confirmação simples
                width, height = self.terminal.get_size()
                msg = f"Remover '{event['title'][:30]}'? (s/N)"
                x = max(0, (width - len(msg)) // 2)
                y = height // 2
                
                self.terminal.print_at(x, y, msg, {"color": "warning", "bold": True})
                self.terminal.flush()
                
                # Aguardar confirmação
                start = time.time()
                while time.time() - start < 5:
                    key = self.terminal.get_key(0.1)
                    if key:
                        if isinstance(key, str) and key.lower() == 's':
                            try:
                                self.bridge.delete_event(event_id)
                                self._data_cache.clear()
                                self._needs_full_clear = True
                                self._load_data()
                            except Exception as e:
                                logger.error(f"Erro ao remover evento: {e}")
                        else:
                            # Apenas redesenhar sem limpar completamente
                            self.needs_redraw = True
                        break
                
                self.needs_redraw = True
    
    def _open_add_menu(self) -> Optional[str]:
        """Abre menu de adição (versão simplificada)."""
        try:
            self.submenu_active = True
            
            from .agenda_submenus import AddEventSubmenu
            
            # Configurar terminal
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
            
            try:
                submenu = AddEventSubmenu(self.terminal, self.bridge, self.current_date)
                result = submenu.show()
                
                if result and (result.get('added') or result.get('updated')):
                    self._data_cache.clear()
                    self._needs_full_clear = True
                    self._load_data()
                
                return None
                
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                self.submenu_active = False
                # Ao retornar do submenu, precisa redesenhar
                self.needs_redraw = True
            
        except ImportError:
            self._show_simple_message("Submenu de adição em desenvolvimento", 
                                    *self.terminal.get_size())
            return None
        except Exception as e:
            logger.error(f"Erro ao abrir menu de adição: {e}")
            self.submenu_active = False
            self.needs_redraw = True
            return None
    
    def _show_simple_message(self, message: str, width: int, height: int):
        """Mostra mensagem simples."""
        # Salvar estado e limpar completamente para mensagem
        self.terminal.save_cursor()
        self.terminal.clear_screen()
        
        msg_x = max(0, (width - len(message)) // 2)
        msg_y = height // 2
        
        self.terminal.print_at(msg_x, msg_y, message, {"color": "info"})
        self.terminal.flush()
        time.sleep(1.5)
        
        # Restaurar e marcar para redesenho completo
        self.terminal.restore_cursor()
        self._needs_full_clear = True
    
    def _show_error(self, width: int, height: int):
        """Mostra mensagem de erro."""
        error_y = height // 2
        error_msg = f"❌ {self.error_message}"
        error_x = max(0, (width - len(error_msg)) // 2)
        
        self.terminal.print_at(error_x, error_y, error_msg, {"color": "error", "bold": True})
        
        instruction = "Pressione R para recarregar ou Q para voltar ao Dashboard"
        instruction_x = max(0, (width - len(instruction)) // 2)
        self.terminal.print_at(instruction_x, error_y + 1, instruction, {"color": "dim"})
    
    def _show_fatal_error(self, message: str):
        """Mostra erro fatal e sai."""
        width, height = self.terminal.get_size()
        self.terminal.clear_screen()
        
        error_box = [
            "╔══════════════════════════════════════════════════════╗",
            "║                    ERRO CRÍTICO                      ║",
            "╠══════════════════════════════════════════════════════╣",
            f"║ {message:<54} ║",
            "╠══════════════════════════════════════════════════════╣",
            "║ AgendaManager não está disponível.                   ║",
            "║                                                      ║",
            "║ Soluções possíveis:                                  ║",
            "║ 1. Execute o backend: python run_backend.py          ║",
            "║ 2. Configure o vault em ~/.glados/settings.yaml      ║",
            "║ 3. Use --vault-path ao iniciar                       ║",
            "║                                                      ║",
            "║ Pressione Q para voltar ao Dashboard...              ║",
            "╚══════════════════════════════════════════════════════╝"
        ]
        
        start_y = (height - len(error_box)) // 2
        for i, line in enumerate(error_box):
            x = (width - len(line)) // 2
            self.terminal.print_at(max(0, x), start_y + i, line, {"color": "error"})
        
        self.terminal.flush()
        self.terminal.get_key()
        raise RuntimeError(f"Agenda não disponível: {message}")
    
    def _show_event_details(self, event: Dict) -> Optional[str]:
        """Mostra detalhes do evento em tela cheia."""
        width, height = self.terminal.get_size()
        
        # Salvar estado e limpar completamente
        self.terminal.save_cursor()
        self.terminal.clear_screen()
        
        # Título
        title = f"📋 {event.get('title', 'Evento')}"
        self.terminal.print_at(0, 1, title, {"color": "accent", "bold": True})
        
        # Separador
        self.terminal.print_at(0, 2, "─" * width, {"color": "dim"})
        
        # Informações
        info_y = 4
        info = [
            f"⏰ Horário: {event.get('time', '--:--')}",
            f"📁 Tipo: {event.get('type', 'outro')}",
            f"🎯 Prioridade: {event.get('priority', 'medium')}",
            f"✅ Status: {'✓ Concluído' if event.get('completed') else '○ Pendente'}",
            f"🆔 ID: {event.get('id', 'N/A')}"
        ]
        
        for i, line in enumerate(info):
            color = "success" if "Concluído" in line else "primary"
            self.terminal.print_at(2, info_y + i, line, {"color": color})
        
        # Rodapé
        self.terminal.print_at(0, height - 1, "Pressione qualquer tecla para voltar... (Q para Dashboard)", {"color": "dim"})
        
        self.terminal.flush()
        self.terminal.get_key()
        
        # Restaurar e marcar para limpeza completa
        self.terminal.restore_cursor()
        self._needs_full_clear = True
        return None
