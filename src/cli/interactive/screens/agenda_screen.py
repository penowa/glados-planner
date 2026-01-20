# src/cli/interactive/screens/agenda_screen.py
"""
Tela principal da Agenda Inteligente - Versão corrigida e otimizada
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
import calendar
import logging

from .base_screen import BaseScreen
from src.cli.integration.agenda_bridge import AgendaBridge
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
from src.cli.interactive.terminal import Key

logger = logging.getLogger(__name__)

class AgendaScreen(BaseScreen):
    """Tela principal de agenda com todas as visualizações."""
    
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
        
        # Controles de renderização
        self.needs_redraw = True
        self.last_update = time.time()
        
        # Carregar dados iniciais
        self._load_data()
    
    def show(self) -> Optional[str]:
        """Loop principal da tela."""
        self.running = True
        
        while self.running:
            try:
                if self.needs_redraw:
                    self._render()
                    self.needs_redraw = False
                
                key = self.terminal.get_key(0.1)
                
                if key:
                    result = self._handle_key(key)
                    if result:
                        return result
                
                # Atualização periódica a cada 30 segundos
                if time.time() - self.last_update > 30:
                    self._load_data()
                    self.needs_redraw = True
                    
            except KeyboardInterrupt:
                self.running = False
                return 'back'
            except Exception as e:
                logger.error(f"Erro no loop principal: {e}")
                self.error_message = str(e)
                self.needs_redraw = True
        
        return None
    
    def _render(self):
        """Renderiza toda a tela."""
        try:
            width, height = self.terminal.get_size()
            self.terminal.clear_screen()
            
            # Cabeçalho fixo
            self._render_header(width)
            
            # Conteúdo principal
            content_height = height - 10
            view_type = self.VIEWS[self.current_view]
            
            # Mostrar mensagem de erro se houver
            if self.error_message:
                self._show_error(self.error_message, width, height)
            else:
                try:
                    if view_type == 'daily':
                        self._render_daily_view(0, 6, width, content_height)
                    elif view_type == 'weekly':
                        self._render_weekly_view(0, 6, width, content_height)
                    elif view_type == 'monthly':
                        self._render_monthly_view(0, 6, width, content_height)
                    elif view_type == 'semester':
                        self._render_semester_view(0, 6, width, content_height)
                except Exception as e:
                    logger.error(f"Erro ao renderizar view {view_type}: {e}")
                    self._show_error(f"Erro ao renderizar: {str(e)}", width, height)
            
            # Rodapé
            self._render_footer(width, height)
            
            self.terminal.flush()
            
        except Exception as e:
            logger.error(f"Erro crítico ao renderizar: {e}")
    
    def _render_header(self, width: int):
        """Renderiza cabeçalho da agenda."""
        view_name = self.VIEW_NAMES[self.VIEWS[self.current_view]]
        date_str = self.current_date.strftime("%d/%m/%Y")
        
        # Linha 1: Título
        title = f"📅 AGENDA {view_name.upper()} - {date_str}"
        self.terminal.print_at(0, 1, title, {"color": "accent", "bold": True})
        
        # Linha 2: Status do backend
        try:
            if self.bridge and self.bridge.is_available():
                status = "✅ Backend conectado"
                color = "success"
            else:
                status = "❌ Backend offline"
                color = "error"
        except:
            status = "❓ Status desconhecido"
            color = "warning"
        
        self.terminal.print_at(0, 2, status, {"color": color})
        
        # Linha 3: Navegação
        nav = "[TAB: Views] [←→: Datas] [↑↓: Selecionar] [A: Adicionar] [I: Importantes] [N: Análise] [R: Recarregar]"
        self.terminal.print_at(0, 3, nav, {"color": "dim"})
        
        # Separador
        self.terminal.print_at(0, 4, "─" * width, {"color": "dim"})
    
    def _render_daily_view(self, x: int, y: int, width: int, height: int):
        """Renderiza visualização diária."""
        if not self.view_data:
            self.terminal.print_at(x, y, "Carregando...", {"color": "warning"})
            return
        
        events = self.view_data.get('events', [])
        
        if not events:
            msg = "📭 Nenhum evento agendado para hoje!"
            self.terminal.print_at(x + (width - len(msg)) // 2, y, msg, {"color": "info"})
            return
        
        # Renderizar eventos
        max_events = min(len(events), height - 2)  # Deixar espaço para estatísticas
        for i in range(max_events):
            event_y = y + i
            event = events[i]
            is_selected = (i == self.selected_index)
            
            self._render_event_line(event, x, event_y, width, is_selected)
        
        # Estatísticas
        if self.view_data.get('stats'):
            stats = self.view_data['stats']
            stats_y = y + max_events + 1
            
            # Barra de progresso
            total = stats.get('total', 0)
            completed = stats.get('completed', 0)
            
            if total > 0:
                progress = int((completed / total) * 20)  # 20 caracteres de largura
                progress_bar = "█" * progress + "░" * (20 - progress)
                progress_text = f" [{progress_bar}] {completed}/{total}"
            else:
                progress_text = " [Sem eventos]"
            
            stats_text = f"📊{progress_text} • ⏱️ {stats.get('productive_hours', 0):.1f}h • 🎯 {stats.get('productivity_score', 0)}%"
            self.terminal.print_at(x, stats_y, stats_text, {"color": "info"})
            
            # Conflitos se houver
            conflicts = self.view_data.get('conflicts', [])
            if conflicts:
                conflict_y = stats_y + 1
                conflict_msg = f"⚠️ {len(conflicts)} conflito(s) de horário"
                self.terminal.print_at(x, conflict_y, conflict_msg, {"color": "warning"})
    
    def _render_weekly_view(self, x: int, y: int, width: int, height: int):
        """Renderiza visualização semanal."""
        if not self.view_data:
            self.terminal.print_at(x, y, "Carregando...", {"color": "warning"})
            return
        
        week_days = self.view_data.get('week_days', [])
        
        if not week_days:
            msg = "📭 Sem dados para esta semana"
            self.terminal.print_at(x + (width - len(msg)) // 2, y, msg, {"color": "info"})
            return
        
        # Layout responsivo
        if width >= 120:
            self._render_weekly_detailed(x, y, width, height, week_days)
        elif width >= 80:
            self._render_weekly_compact(x, y, width, height, week_days)
        else:
            self._render_weekly_minimal(x, y, width, height, week_days)
    
    def _render_weekly_compact(self, x: int, y: int, width: int, height: int, week_days: List):
        """Layout compacto para semana."""
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
            
            # Indicador de importante
            if day_data.get('has_important', False):
                self.terminal.print_at(col_x + col_width - 2, content_y, "⚠️", 
                                     {"color": "warning"})
            
            # Indicador de seleção
            if i == self.selected_index:
                self.terminal.print_at(col_x, content_y + 2, "↑".center(col_width),
                                     {"color": "accent", "bold": True})
    
    def _render_weekly_minimal(self, x: int, y: int, width: int, height: int, week_days: List):
        """Layout mínimo para telas pequenas."""
        # Mostrar apenas 3 dias de cada vez
        start_idx = max(0, min(self.selected_index - 1, len(week_days) - 3))
        visible_days = week_days[start_idx:start_idx + 3]
        
        for i, day_data in enumerate(visible_days):
            col_x = x + (i * (width // 3))
            col_width = width // 3
            
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
            content = f"{count} ev\n{hours:.1f}h"
            
            content_lines = content.split('\n')
            for j, line in enumerate(content_lines):
                line_y = y + 1 + j
                color = "success" if (j == 0 and count > 0) or (j == 1 and hours > 0) else "dim"
                self.terminal.print_at(col_x, line_y, line.center(col_width), {"color": color})
            
            # Indicador de importante
            if day_data.get('has_important', False):
                self.terminal.print_at(col_x + col_width - 2, y + 1, "⚠️", {"color": "warning"})
    
    def _render_monthly_view(self, x: int, y: int, width: int, height: int):
        """Renderiza visualização mensal."""
        try:
            # Gerar dados do mês atual
            month_data = self._generate_monthly_data()
            
            year = month_data['year']
            month = month_data['month']
            days = month_data['days']
            
            # Cabeçalho do mês
            month_name = datetime(year, month, 1).strftime("%B %Y").capitalize()
            header = f"📅 {month_name}"
            self.terminal.print_at(x + (width - len(header)) // 2, y, header, 
                                 {"color": "accent", "bold": True})
            
            # Dias da semana - CORREÇÃO: usar array correto
            weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
            col_width = width // 7
            
            # Cabeçalhos dos dias
            for i, day in enumerate(weekdays):
                day_x = x + (i * col_width)
                self.terminal.print_at(day_x, y + 2, day.center(col_width), 
                                     {"color": "primary", "bold": True})
            
            # Calendário - CORREÇÃO: cálculo correto do primeiro dia
            first_day = datetime(year, month, 1)
            first_weekday = first_day.weekday()  # 0=segunda, 6=domingo
            
            # Converter para nosso formato (0=domingo)
            first_weekday = (first_weekday + 1) % 7
            
            current_row = y + 4
            current_col = 0
            
            # Dias em branco antes do primeiro dia
            for i in range(first_weekday):
                day_x = x + (current_col * col_width)
                self.terminal.print_at(day_x, current_row, " ".center(col_width), 
                                     {"color": "dim"})
                current_col += 1
            
            # Dias do mês
            for day_num in range(1, len(days) + 1):
                day_x = x + (current_col * col_width)
                
                # Encontrar informações do dia
                day_info = next((d for d in days if d.get('day_num') == day_num), None)
                
                if day_info:
                    day_str = day_info['display']
                    
                    # Estilo baseado no dia
                    style = {"color": "info"}
                    if day_info.get('is_today'):
                        style = {"color": "accent", "bold": True, "reverse": True}
                    elif day_info.get('is_weekend'):
                        style["color"] = "warning"
                    elif day_info.get('has_events'):
                        style["color"] = "success"
                    
                    self.terminal.print_at(day_x, current_row, day_str.center(col_width), style)
                else:
                    # Dia sem informações
                    self.terminal.print_at(day_x, current_row, str(day_num).center(col_width), 
                                         {"color": "dim"})
                
                current_col += 1
                if current_col >= 7:
                    current_col = 0
                    current_row += 1
            
            # Estatísticas
            if current_row < y + height - 3:
                stats_y = current_row + 2
                stats = month_data.get('stats', {})
                stats_text = f"📊 {stats.get('total_events', 0)} eventos"
                if 'productive_hours' in stats:
                    stats_text += f" • ⏱️ {stats['productive_hours']}h produtivas"
                
                self.terminal.print_at(x, stats_y, stats_text, {"color": "info"})
                
        except Exception as e:
            logger.error(f"Erro ao renderizar visualização mensal: {e}")
            # Mensagem de fallback mais informativa
            msg = f"📅 Calendário do mês (erro: {str(e)[:30]})"
            self.terminal.print_at(x + (width - len(msg)) // 2, y + height // 2, 
                                 msg, {"color": "warning"})
    
    def _render_semester_view(self, x: int, y: int, width: int, height: int):
        """Renderiza visualização semestral."""
        try:
            # Gerar dados do semestre
            semester_data = self._generate_semester_data()
            
            # Título
            title = f"🎓 {semester_data['period']}"
            self.terminal.print_at(x + (width - len(title)) // 2, y, title, 
                                 {"color": "accent", "bold": True})
            
            # Meses
            months = semester_data['months']
            col_width = width // 3
            row_height = 4
            
            for i, month_data in enumerate(months):
                row = i // 3
                col = i % 3
                
                month_x = x + (col * col_width)
                month_y = y + 2 + (row * row_height)
                
                # Nome do mês
                month_name = f"{month_data['name']}/{str(month_data['year'])[-2:]}"
                self.terminal.print_at(month_x, month_y, month_name.center(col_width), 
                                     {"color": "primary", "bold": True})
                
                # Eventos
                events_count = month_data['events_count']
                events_text = f"{events_count} eventos"
                color = "success" if events_count > 0 else "dim"
                self.terminal.print_at(month_x, month_y + 1, events_text.center(col_width), 
                                     {"color": color})
                
                # Datas importantes
                important_dates = month_data['important_dates']
                if important_dates:
                    dates_text = f"{len(important_dates)} importante(s)"
                    self.terminal.print_at(month_x, month_y + 2, dates_text.center(col_width), 
                                         {"color": "warning"})
            
            # Estatísticas
            stats_y = y + 2 + ((len(months) + 2) // 3) * row_height
            stats = semester_data['stats']
            stats_text = f"📊 {stats['total_events']} eventos • ✅ {stats['completion_rate']:.1f}% conclusão"
            self.terminal.print_at(x + (width - len(stats_text)) // 2, stats_y, 
                                 stats_text, {"color": "info"})
            
        except Exception as e:
            logger.error(f"Erro ao renderizar visualização semestral: {e}")
            msg = "🎓 Visualização semestral em desenvolvimento"
            self.terminal.print_at(x + (width - len(msg)) // 2, y + height // 2, 
                                 msg, {"color": "info"})
    
    def _render_event_line(self, event: Dict, x: int, y: int, width: int, selected: bool):
        """Renderiza uma linha de evento."""
        try:
            # Ícone
            icon = self.EVENT_ICONS.get(event.get('type', 'outro'), Icon.TASK)
            if isinstance(icon, Icon):
                icon_str = icon.value
            else:
                icon_str = icon
            
            # Estilo baseado na prioridade e status
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
            
            # Adicionar indicador de concluído
            if completed:
                title = f"✓ {title}"
            
            # Truncar se necessário
            max_title = width - 15
            if len(title) > max_title:
                title = title[:max_title - 3] + "..."
            
            line = f"{icon_str} {time_str:5s} {title}"
            self.terminal.print_at(x, y, line, style)
            
        except Exception as e:
            logger.warning(f"Erro ao renderizar linha de evento: {e}")
    
    def _render_footer(self, width: int, height: int):
        """Renderiza rodapé."""
        footer_y = height - 3
        
        # Separador
        self.terminal.print_at(0, footer_y, "─" * width, {"color": "dim"})
        
        # Ajuda contextual baseada na view atual
        view_type = self.VIEWS[self.current_view]
        
        if view_type == 'daily':
            help_text = "ENTER: Detalhes • ESPAÇO: Concluir • E: Editar • DEL: Remover"
        elif view_type == 'weekly':
            help_text = "ENTER: Ver dia • ↑↓: Selecionar dia • ←→: Navegar semanas"
        elif view_type == 'monthly':
            help_text = "←→: Navegar meses • ENTER: Ver dia selecionado"
        elif view_type == 'semester':
            help_text = "←→: Navegar semestres • ENTER: Ver mês selecionado"
        
        help_text += " • ESC: Voltar • R: Recarregar"
        self.terminal.print_at(0, footer_y + 1, help_text.center(width), {"color": "dim"})
        
        # Relógio
        time_str = datetime.now().strftime("%H:%M:%S")
        self.terminal.print_at(width - 10, 0, f"🕐 {time_str}", {"color": "info"})
    
    def _show_error(self, message: str, width: int, height: int):
        """Mostra mensagem de erro."""
        error_y = height // 2
        error_msg = f"❌ {message}"
        self.terminal.print_at((width - len(error_msg)) // 2, error_y, 
                             error_msg, {"color": "error", "bold": True})
        
        # Instrução
        instruction = "Pressione ESC para voltar ou R para recarregar"
        self.terminal.print_at((width - len(instruction)) // 2, error_y + 1, 
                             instruction, {"color": "dim"})
    
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
            "║ Pressione qualquer tecla para voltar...              ║",
            "╚══════════════════════════════════════════════════════╝"
        ]
        
        start_y = (height - len(error_box)) // 2
        for i, line in enumerate(error_box):
            x = (width - len(line)) // 2
            self.terminal.print_at(max(0, x), start_y + i, line, {"color": "error"})
        
        self.terminal.flush()
        self.terminal.get_key()
        raise RuntimeError(f"Agenda não disponível: {message}")
    
    def _load_data(self):
        """Carrega dados da view atual."""
        view_type = self.VIEWS[self.current_view]
        
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
            
            self.error_message = None
            logger.debug(f"Dados carregados: {self.view_data is not None}")
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            self.error_message = f"Erro ao carregar dados: {str(e)}"
            self.view_data = self._get_fallback_data(view_type)
        
        self.last_update = time.time()
        self.needs_redraw = True
    
    def _generate_monthly_data(self) -> Dict[str, Any]:
        """Gera dados para visualização mensal."""
        try:
            year = self.current_date.year
            month = self.current_date.month
            
            # Obter dias do mês
            _, num_days = calendar.monthrange(year, month)
            
            days = []
            total_events = 0
            productive_hours = 0
            
            today = datetime.now().date()
            
            # Coletar eventos para cada dia - OTIMIZADO
            all_events = []
            try:
                # Tentar obter eventos do mês inteiro de forma mais eficiente
                start_date = datetime(year, month, 1)
                end_date = datetime(year, month, num_days)
                
                # Buscar eventos em lotes (poderia ser otimizado no backend)
                for day in range(1, num_days + 1):
                    date = datetime(year, month, day)
                    
                    # Verificar se há eventos neste dia
                    try:
                        daily_data = self.bridge.get_daily_view(date)
                        has_events = len(daily_data.get('events', [])) > 0
                        total_events += len(daily_data['events'])
                        productive_hours += daily_data.get('stats', {}).get('productive_hours', 0)
                    except:
                        has_events = False
                    
                    days.append({
                        'day_num': day,
                        'date': date,
                        'display': str(day),
                        'has_events': has_events,
                        'is_today': date.date() == today,
                        'is_weekend': date.weekday() >= 5
                    })
            except Exception as e:
                logger.warning(f"Erro ao buscar eventos mensais: {e}")
                # Fallback: apenas dias básicos
                for day in range(1, num_days + 1):
                    date = datetime(year, month, day)
                    days.append({
                        'day_num': day,
                        'date': date,
                        'display': str(day),
                        'has_events': False,
                        'is_today': date.date() == today,
                        'is_weekend': date.weekday() >= 5
                    })
            
            return {
                'month': month,
                'year': year,
                'days': days,
                'stats': {
                    'total_events': total_events,
                    'productive_hours': round(productive_hours, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar dados mensais: {e}")
            return self._get_fallback_data('monthly')
    
    def _generate_semester_data(self) -> Dict[str, Any]:
        """Gera dados para visualização semestral."""
        try:
            # Semestre atual (janeiro-junho ou julho-dezembro)
            current_year = self.current_date.year
            current_month = self.current_date.month
            
            if current_month <= 6:
                # Primeiro semestre
                start_month = 1
                end_month = 6
                period = f"1º Semestre {current_year}"
            else:
                # Segundo semestre
                start_month = 7
                end_month = 12
                period = f"2º Semestre {current_year}"
            
            months = []
            total_events = 0
            completed_events = 0
            
            # Coletar dados para cada mês
            for month_num in range(start_month, end_month + 1):
                date = datetime(current_year, month_num, 1)
                
                # Coletar eventos do mês
                month_events = 0
                important_dates = []
                
                # Verificar alguns dias do mês para estimativa
                for day in [1, 10, 20]:
                    try:
                        check_date = datetime(current_year, month_num, day)
                        daily_data = self.bridge.get_daily_view(check_date)
                        month_events += len(daily_data['events'])
                        completed_events += daily_data['stats']['completed']
                        
                        # Verificar eventos importantes
                        for event in daily_data['events']:
                            title_lower = event['title'].lower()
                            if any(keyword in title_lower for keyword in ['prova', 'entrega', 'seminário', 'seminario']):
                                important_dates.append({
                                    'day': day,
                                    'title': event['title']
                                })
                    except:
                        continue
                
                total_events += month_events
                
                months.append({
                    'month': month_num,
                    'year': current_year,
                    'name': date.strftime('%b'),
                    'events_count': month_events,
                    'important_dates': important_dates[:3]  # Limitar a 3
                })
            
            # Calcular taxa de conclusão
            completion_rate = (completed_events / total_events * 100) if total_events > 0 else 0
            
            return {
                'period': period,
                'months': months,
                'stats': {
                    'total_events': total_events,
                    'completion_rate': round(completion_rate, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar dados semestrais: {e}")
            return self._get_fallback_data('semester')
    
    def _get_fallback_data(self, view_type: str) -> Dict:
        """Dados de fallback quando o backend falha."""
        logger.warning(f"Usando dados de fallback para {view_type}")
        
        if view_type == 'daily':
            return {
                'events': [],
                'stats': {
                    'total': 0, 
                    'completed': 0, 
                    'productive_hours': 0,
                    'productivity_score': 0
                },
                'conflicts': [],
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
                    'productive_hours': 0,
                    'has_important': False
                })
            return {
                'week_days': week_days, 
                'stats': {
                    'total_events': 0, 
                    'total_productive_hours': 0,
                    'completion_rate': 0
                },
                'is_fallback': True
            }
        elif view_type == 'monthly':
            return self._generate_monthly_data()
        elif view_type == 'semester':
            return self._generate_semester_data()
    
    def _handle_key(self, key) -> Optional[str]:
        """Processa entrada do teclado."""
        try:
            original_key = key
            if isinstance(key, Key):
                key = key.name.lower()
            
            # DEBUG: Log da tecla pressionada
            logger.debug(f"Tecla pressionada: {original_key} -> {key}")
            
            # Limpar mensagem de erro
            if self.error_message and key not in ['escape', 'r']:
                self.error_message = None
            
            # Teclas de navegação
            if key == 'tab':
                self.current_view = (self.current_view + 1) % len(self.VIEWS)
                self.selected_index = 0
                self.terminal.clear_screen()  # Limpar antes de recarregar
                self._load_data()
                return None
            
            elif key == 'left':
                self._navigate_period(-1)
                self.terminal.clear_screen()  # Limpar antes de recarregar
                return None
            
            elif key == 'right':
                self._navigate_period(1)
                self.terminal.clear_screen()  # Limpar antes de recarregar
                return None
            
            elif key == 'up':
                self._move_selection(-1)
                self.needs_redraw = True  # Forçar redesenho
                return None
            
            elif key == 'down':
                self._move_selection(1)
                self.needs_redraw = True  # Forçar redesenho
                return None
            
            # Teclas de ação
            elif key == 'enter':
                self.terminal.clear_screen()  # Limpar antes de abrir detalhes
                return self._select_item()
            
            elif key == 'space':
                self._toggle_completion()
                self.needs_redraw = True  # Forçar redesenho
                return None
            
            elif key == 'a':
                self.terminal.clear_screen()  # Limpar antes de abrir submenu
                return self._open_add_menu()
            
            elif key == 'i':
                self.terminal.clear_screen()  # Limpar antes de abrir submenu
                return self._open_important_dates()
            
            elif key == 'n':
                self.terminal.clear_screen()  # Limpar antes de abrir submenu
                return self._open_analysis()
            
            elif key == 'e':
                self.terminal.clear_screen()  # Limpar antes de editar
                return self._edit_selected()
            
            elif key in ['delete', 'backspace']:
                self._delete_selected()
                self.needs_redraw = True  # Forçar redesenho
                return None
            
            elif key == 'r':
                self.terminal.clear_screen()  # Limpar antes de recarregar
                self._load_data()
                return None
            
            elif key == 'escape':
                logger.debug("ESC pressionado - retornando ao dashboard")
                self.running = False
                self.terminal.clear_screen()  # Limpar antes de sair
                self.menu_stack.pop()  # Isso deve funcionar com o screen_manager
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao processar tecla: {e}")
            return None
    
    def _navigate_period(self, direction: int):
        """Navega entre períodos."""
        view_type = self.VIEWS[self.current_view]
        
        if view_type == 'daily':
            self.current_date += timedelta(days=direction)
        elif view_type == 'weekly':
            self.current_date += timedelta(weeks=direction)
        elif view_type == 'monthly':
            # Navegar meses
            new_month = self.current_date.month + direction
            new_year = self.current_date.year
            
            if new_month > 12:
                new_month = 1
                new_year += 1
            elif new_month < 1:
                new_month = 12
                new_year -= 1
            
            self.current_date = datetime(new_year, new_month, 1)
        elif view_type == 'semester':
            # Navegar semestres
            current_month = self.current_date.month
            if direction > 0:
                # Próximo semestre
                if current_month <= 6:
                    self.current_date = datetime(self.current_date.year, 7, 1)
                else:
                    self.current_date = datetime(self.current_date.year + 1, 1, 1)
            else:
                # Semestre anterior
                if current_month <= 6:
                    self.current_date = datetime(self.current_date.year - 1, 7, 1)
                else:
                    self.current_date = datetime(self.current_date.year, 1, 1)
        
        self.selected_index = 0
        self._ensure_clean_state()  # Usar novo método
        self._load_data()
    
    def _ensure_clean_state(self):
        """Garante que o estado esteja limpo para nova renderização."""
        self.terminal.clear_screen()
        self.needs_redraw = True
        self.error_message = None
    
    def _move_selection(self, direction: int):
        """Move seleção atual."""
        if not self.view_data:
            return
        
        view_type = self.VIEWS[self.current_view]
        
        if view_type == 'daily':
            events = self.view_data.get('events', [])
            max_index = len(events) - 1
        elif view_type == 'weekly':
            week_days = self.view_data.get('week_days', [])
            max_index = min(6, len(week_days) - 1)
        elif view_type == 'monthly':
            # Para mensal, selecionar um dia
            days = self.view_data.get('days', [])
            max_index = len(days) - 1
        elif view_type == 'semester':
            # Para semestral, selecionar um mês
            months = self.view_data.get('months', [])
            max_index = len(months) - 1
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
                self.terminal.clear_screen()  # Limpar antes de mudar
                self._load_data()
        
        elif view_type == 'monthly':
            days = self.view_data.get('days', [])
            if 0 <= self.selected_index < len(days):
                day_data = days[self.selected_index]
                self.current_date = day_data.get('date', self.current_date)
                self.current_view = 0  # Muda para daily
                self.selected_index = 0
                self.terminal.clear_screen()  # Limpar antes de mudar
                self._load_data()
        
        elif view_type == 'semester':
            months = self.view_data.get('months', [])
            if 0 <= self.selected_index < len(months):
                month_data = months[self.selected_index]
                self.current_date = datetime(month_data['year'], month_data['month'], 1)
                self.current_view = 2  # Muda para monthly
                self.selected_index = 0
                self.terminal.clear_screen()  # Limpar antes de mudar
                self._load_data()
        
        return None
    
    def _toggle_completion(self):
        """Alterna estado de conclusão."""
        if self.VIEWS[self.current_view] != 'daily':
            return
        
        events = self.view_data.get('events', [])
        if 0 <= self.selected_index < len(events):
            event = events[self.selected_index]
            event_id = event.get('id')
            
            if event_id:
                try:
                    new_state = not event.get('completed', False)
                    success = self.bridge.update_event(event_id, {'completed': new_state})
                    
                    if success:
                        # Atualizar visualização
                        self.terminal.clear_screen()
                        self._load_data()
                    else:
                        logger.warning(f"Falha ao atualizar evento {event_id}")
                except Exception as e:
                    logger.error(f"Erro ao alternar conclusão: {e}")
    
    def _open_add_menu(self) -> Optional[str]:
        """Abre menu de adição."""
        try:
            from .agenda_submenus import AddEventSubmenu
            self.submenu_active = True
            
            # Criar e mostrar submenu
            submenu = AddEventSubmenu(self.terminal, self.bridge, self.current_date)
            result = submenu.show()
            
            self.submenu_active = False
            
            # Recarregar dados se um evento foi adicionado
            if result and result.get('added', False):
                self.terminal.clear_screen()
                self._load_data()
            
            return None
            
        except ImportError as e:
            logger.warning(f"Submenu não disponível, usando fallback: {e}")
            # Fallback: diálogo simples
            title = "➕ Adicionar Evento"
            prompt = "Digite o título do evento:"
            
            event_title = self._show_simple_input_dialog(title, prompt)
            
            if event_title:
                try:
                    # Adicionar evento básico
                    success = self.bridge.add_event({
                        'title': event_title,
                        'date': self.current_date.strftime('%Y-%m-%d'),
                        'time': '09:00',
                        'type': 'outro',
                        'priority': 'medium'
                    })
                    
                    if success:
                        self.terminal.clear_screen()
                        self._load_data()
                except Exception as e:
                    logger.error(f"Erro ao adicionar evento: {e}")
            
            return None
    
    def _open_important_dates(self) -> Optional[str]:
        """Abre datas importantes."""
        try:
            from .agenda_submenus import ImportantDatesSubmenu
            
            # Obter datas importantes
            important_dates = self.bridge.get_important_dates(self.current_date)
            
            # Criar e mostrar submenu
            submenu = ImportantDatesSubmenu(self.terminal, important_dates)
            result = submenu.show()
            
            # Se uma data foi selecionada, navegar para ela
            if result and 'date' in result:
                self.current_date = result['date']
                self.current_view = 0  # Mudar para visualização diária
                self.selected_index = 0
                self.terminal.clear_screen()
                self._load_data()
            
            return None
            
        except ImportError as e:
            logger.warning(f"Submenu não disponível: {e}")
            # Mostrar mensagem simples
            width, height = self.terminal.get_size()
            msg = "Submenu de datas importantes em desenvolvimento"
            self.terminal.print_at((width - len(msg)) // 2, height // 2, msg, {"color": "info"})
            self.terminal.flush()
            time.sleep(2)
            return None
    
    def _open_analysis(self) -> Optional[str]:
        """Abre análise."""
        try:
            from .agenda_submenus import AnalysisSubmenu
            
            # Obter dados de análise (últimos 30 dias)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            analysis_data = self.bridge.get_analysis_data(start_date, end_date)
            
            # Criar e mostrar submenu
            submenu = AnalysisSubmenu(self.terminal, analysis_data)
            submenu.show()
            
            return None
            
        except ImportError as e:
            logger.warning(f"Submenu não disponível: {e}")
            # Mostrar mensagem simples
            width, height = self.terminal.get_size()
            msg = "Submenu de análise em desenvolvimento"
            self.terminal.print_at((width - len(msg)) // 2, height // 2, msg, {"color": "info"})
            self.terminal.flush()
            time.sleep(2)
            return None
    
    def _edit_selected(self) -> Optional[str]:
        """Edita item selecionado."""
        if self.VIEWS[self.current_view] != 'daily':
            return None
        
        events = self.view_data.get('events', [])
        if 0 <= self.selected_index < len(events):
            try:
                from .agenda_submenus import EditEventSubmenu
                
                event = events[self.selected_index]
                submenu = EditEventSubmenu(self.terminal, self.bridge, event)
                result = submenu.show()
                
                # Recarregar dados se o evento foi editado
                if result and result.get('updated', False):
                    self.terminal.clear_screen()
                    self._load_data()
                
                return None
                
            except ImportError:
                # Mostrar detalhes como fallback
                return self._show_event_details(events[self.selected_index])
        
        return None
    
    def _delete_selected(self):
        """Remove item selecionado."""
        if self.VIEWS[self.current_view] != 'daily':
            return
        
        events = self.view_data.get('events', [])
        if 0 <= self.selected_index < len(events):
            event = events[self.selected_index]
            event_id = event.get('id')
            
            if event_id:
                # Confirmação
                width, height = self.terminal.get_size()
                msg = f"Remover '{event['title']}'? (s/N)"
                x = (width - len(msg)) // 2
                y = height // 2
                
                # Salvar tela atual
                self.terminal.save_cursor()
                self.terminal.print_at(x, y, msg, {"color": "warning", "bold": True})
                self.terminal.flush()
                
                # Aguardar confirmação
                start = time.time()
                confirmed = False
                
                while time.time() - start < 5:  # Timeout de 5 segundos
                    key = self.terminal.get_key(0.1)
                    if key:
                        if isinstance(key, str) and key.lower() == 's':
                            try:
                                success = self.bridge.delete_event(event_id)
                                if success:
                                    confirmed = True
                                break
                            except Exception as e:
                                logger.error(f"Erro ao remover evento: {e}")
                                break
                        else:
                            # Qualquer outra tecla cancela
                            break
                
                # Restaurar tela
                self.terminal.restore_cursor()
                
                if confirmed:
                    self.terminal.clear_screen()
                    self._load_data()
                else:
                    self.needs_redraw = True
    
    def _show_event_details(self, event: Dict) -> Optional[str]:
        """Mostra detalhes do evento."""
        width, height = self.terminal.get_size()
        
        # Salvar estado atual
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
            f"⏱️ Duração: {event.get('duration', 60)}min",
            f"🆔 ID: {event.get('id', 'N/A')}"
        ]
        
        for i, line in enumerate(info):
            color = "primary"
            if "Concluído" in line:
                color = "success"
            elif "Pendente" in line:
                color = "warning"
            
            self.terminal.print_at(2, info_y + i, line, {"color": color})
        
        # Descrição
        desc_y = info_y + len(info) + 2
        if event.get('description'):
            self.terminal.print_at(0, desc_y, "📝 Descrição:", {"color": "secondary"})
            desc = event['description']
            max_width = width - 4
            
            # Quebrar texto
            lines = []
            words = desc.split()
            current_line = ""
            
            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    current_line += " " + word if current_line else word
                else:
                    lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            for i, line in enumerate(lines):
                self.terminal.print_at(2, desc_y + 1 + i, line, {"color": "info"})
        
        # Rodapé
        self.terminal.print_at(0, height - 1, 
                             "Pressione qualquer tecla para voltar...", 
                             {"color": "dim"})
        
        self.terminal.flush()
        self.terminal.get_key()
        
        # Restaurar
        self.terminal.restore_cursor()
        self.needs_redraw = True
        return None
    
    def _show_simple_input_dialog(self, title: str, prompt: str) -> Optional[str]:
        """Mostra um diálogo simples de entrada."""
        width, height = self.terminal.get_size()
        
        # Salvar tela atual
        self.terminal.save_cursor()
        self.terminal.clear_screen()
        
        # Desenhar caixa de diálogo
        box_width = min(60, width - 4)
        box_height = 8
        start_x = (width - box_width) // 2
        start_y = (height - box_height) // 2
        
        # Título
        self.terminal.print_at(start_x, start_y, f"╔{'═' * (box_width - 2)}╗", 
                             {"color": "accent"})
        self.terminal.print_at(start_x + 2, start_y, title, 
                             {"color": "accent", "bold": True})
        
        # Conteúdo
        self.terminal.print_at(start_x, start_y + 2, f"║{' ' * (box_width - 2)}║", 
                             {"color": "accent"})
        self.terminal.print_at(start_x + 2, start_y + 2, prompt, 
                             {"color": "primary"})
        
        # Campo de entrada
        input_y = start_y + 4
        self.terminal.print_at(start_x, input_y, f"╠{'═' * (box_width - 2)}╣", 
                             {"color": "accent"})
        self.terminal.print_at(start_x + 2, input_y + 1, "> ", {"color": "success"})
        
        self.terminal.flush()
        self.terminal.show_cursor()
        
        # Ler entrada
        import sys
        import tty
        import termios
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setraw(fd)
            input_text = ""
            cursor_pos = 0
            
            while True:
                char = sys.stdin.read(1)
                
                if char == '\r' or char == '\n':  # Enter
                    break
                elif char == '\x7f':  # Backspace
                    if cursor_pos > 0:
                        input_text = input_text[:cursor_pos-1] + input_text[cursor_pos:]
                        cursor_pos -= 1
                elif char == '\x1b':  # ESC
                    input_text = None
                    break
                else:
                    input_text = input_text[:cursor_pos] + char + input_text[cursor_pos:]
                    cursor_pos += 1
                
                # Atualizar display
                self.terminal.print_at(start_x + 4, input_y + 1, 
                                     input_text.ljust(box_width - 6), {"color": "info"})
                self.terminal.move_cursor(input_y + 1, start_x + 4 + cursor_pos)
                self.terminal.flush()
        
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            self.terminal.hide_cursor()
            self.terminal.restore_cursor()
        
        return input_text
