# src/cli/interactive/screens/agenda_submenus.py
"""
Submenus especializados da Agenda Inteligente
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from enum import Enum

from src.cli.theme import theme, theme
from src.cli.icons import Icon, icon_text

class ImportantDatesSubmenu:
    """Submenu para gerenciamento de marcos importantes"""
    
    def __init__(self, terminal, backend_bridge, start_date=None):
        self.terminal = terminal
        self.bridge = backend_bridge
        self.start_date = start_date or datetime.now()
        
        # Categorias
        self.categories = ['provas', 'seminarios', 'entregas', 'recessos', 'revisoes']
        self.category_names = {
            'provas': '📝 Provas/Avaliações',
            'seminarios': '🎤 Seminários/Apresentações',
            'entregas': '📦 Entregas de Trabalho',
            'recessos': '🎉 Recessos/Feriados',
            'revisoes': '🔄 Sessões de Revisão'
        }
        
        self.selected_category = 0
        self.selected_item = 0
        self.important_dates = {}
        self.running = True
        
        # Carrega dados
        self._load_data()
    
    def _load_data(self):
        """Carrega datas importantes"""
        self.important_dates = self.bridge.get_important_dates(self.start_date)
    
    def render(self):
        """Renderiza o submenu"""
        width, height = self.terminal.get_size()
        
        # Limpa a tela
        theme.clear()
        
        # Título
        theme.rule(" 📌 DATAS IMPORTANTES ", style="title")
        theme.print(f"{Icon.GLADOS.value} Período: próximos 90 dias", style="accent")
        theme.rule(style="secondary")
        
        # Divide tela em duas colunas
        cat_width = width // 3
        content_width = width - cat_width - 2
        
        # Coluna da esquerda: Categorias
        self._render_categories(cat_width, height)
        
        # Coluna da direita: Itens da categoria selecionada
        self._render_category_items(cat_width, content_width, height)
        
        # Rodapé
        theme.rule(style="dim")
        theme.print("↑↓: Navegar • ←→: Mudar categoria • ENTER: Ver detalhes • ESC: Voltar", style="dim")
    
    def _render_categories(self, width: int, height: int):
        """Renderiza lista de categorias"""
        for i, cat_key in enumerate(self.categories):
            cat_name = self.category_names.get(cat_key, cat_key)
            is_selected = (i == self.selected_category)
            
            # Contagem de itens
            items = self.important_dates.get(cat_key, [])
            count = len(items)
            
            # Formata linha
            line = f"{cat_name} ({count})"
            
            # Aplica estilo
            if is_selected:
                style = {"color": "accent", "bold": True}
            else:
                style = {"color": "primary"}
            
            # Renderiza
            theme.print_at(0, 3 + i, line.ljust(width), **style)
    
    def _render_category_items(self, start_x: int, width: int, height: int):
        """Renderiza itens da categoria selecionada"""
        cat_key = self.categories[self.selected_category]
        items = self.important_dates.get(cat_key, [])
        
        # Título da categoria
        cat_name = self.category_names.get(cat_key, cat_key)
        theme.print_at(start_x, 1, f" {cat_name} ", style="subtitle")
        
        # Itens
        max_items = height - 5
        start_index = max(0, self.selected_item - max_items // 2)
        end_index = min(len(items), start_index + max_items)
        
        for i in range(start_index, end_index):
            item = items[i]
            is_selected = (i == self.selected_item)
            y_pos = 3 + (i - start_index)
            
            self._render_important_item(item, start_x, y_pos, width, is_selected)
        
        # Indicador de scroll
        if len(items) > max_items:
            theme.print_at(start_x, height - 2, 
                         f"... {len(items) - end_index} mais itens ...", 
                         style="dim")
    
    def _render_important_item(self, item: Dict, x: int, y: int, width: int, selected: bool):
        """Renderiza um item importante"""
        # Formata data
        date_str = item.get('date', '')
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            display_date = date_obj.strftime('%d/%m')
        except:
            display_date = date_str
        
        # Título truncado
        title = item.get('title', 'Sem título')
        max_title_len = width - 15
        if len(title) > max_title_len:
            title = title[:max_title_len-3] + "..."
        
        # Prioridade
        priority = item.get('priority', 'medium')
        priority_icon = "⚠️" if priority == 'high' else "ℹ️"
        
        # Linha formatada
        line = f"{display_date:6s} {priority_icon} {title}"
        
        # Estilo
        style = "warning" if priority == 'high' else "primary"
        if selected:
            style += "_bold"
        
        # Renderiza
        theme.print_at(x, y, line, style=style)
    
    def handle_input(self, key):
        """Processa entrada no submenu"""
        if key == 'KEY_ESCAPE':
            return 'exit'
        elif key == 'KEY_UP':
            self._navigate_items(-1)
        elif key == 'KEY_DOWN':
            self._navigate_items(1)
        elif key == 'KEY_LEFT':
            self._navigate_categories(-1)
        elif key == 'KEY_RIGHT':
            self._navigate_categories(1)
        elif key == 'ENTER':
            self._select_item()
        
        return None
    
    def _navigate_categories(self, direction: int):
        """Navega entre categorias"""
        self.selected_category = (self.selected_category + direction) % len(self.categories)
        self.selected_item = 0
    
    def _navigate_items(self, direction: int):
        """Navega entre itens"""
        cat_key = self.categories[self.selected_category]
        items = self.important_dates.get(cat_key, [])
        
        if items:
            self.selected_item = (self.selected_item + direction) % len(items)
    
    def _select_item(self):
        """Seleciona um item para ver detalhes"""
        cat_key = self.categories[self.selected_category]
        items = self.important_dates.get(cat_key, [])
        
        if 0 <= self.selected_item < len(items):
            item = items[self.selected_item]
            self._show_item_details(item)
    
    def _show_item_details(self, item: Dict):
        """Mostra detalhes do item selecionado"""
        width, height = self.terminal.get_size()
        
        # Salva tela atual
        theme.save_screen()
        
        # Janela de detalhes
        detail_width = min(60, width - 4)
        detail_height = min(20, height - 4)
        start_x = (width - detail_width) // 2
        start_y = (height - detail_height) // 2
        
        # Desenha janela
        theme.draw_box(start_x, start_y, detail_width, detail_height, 
                      title="Detalhes", style="accent")
        
        # Conteúdo
        content_x = start_x + 2
        content_y = start_y + 2
        
        # Título
        theme.print_at(content_x, content_y, item.get('title', 'Sem título'), 
                      style="accent", bold=True)
        
        # Informações
        info_lines = [
            f"Data: {item.get('date', '')}",
            f"Tipo: {item.get('type', '')}",
            f"Prioridade: {item.get('priority', 'medium')}",
            f"Disciplina: {item.get('discipline', '')}"
        ]
        
        for i, line in enumerate(info_lines):
            theme.print_at(content_x, content_y + 2 + i, line, style="primary")
        
        # Descrição
        if item.get('description'):
            theme.print_at(content_x, content_y + 7, "Descrição:", style="secondary")
            # Quebra linha da descrição
            desc = item['description']
            for i in range(0, len(desc), detail_width - 4):
                line = desc[i:i+detail_width-4]
                theme.print_at(content_x, content_y + 8 + i//(detail_width-4), 
                             line, style="info")
        
        # Rodapé
        theme.print_at(content_x, start_y + detail_height - 2, 
                      "Pressione qualquer tecla para voltar...", 
                      style="dim")
        
        # Aguarda
        self.terminal.get_key()
        
        # Restaura tela
        theme.restore_screen()


class AddEventSubmenu:
    """Submenu inteligente para adição de eventos"""
    
    MODES = {
        'academic': {
            'name': '🎯 Acadêmico',
            'options': [
                ('Aula Regular', 'aula'),
                ('Leitura Programada', 'leitura'),
                ('Sessão de Produção', 'producao'),
                ('Revisão Espaçada', 'revisao'),
                ('Grupo de Estudo', 'grupo_estudo')
            ]
        },
        'important': {
            'name': '⚠️ Marco Importante',
            'options': [
                ('Prova/Avaliação', 'prova'),
                ('Seminário/Apresentação', 'seminario'),
                ('Entrega de Trabalho', 'entrega'),
                ('Defesa/Orientação', 'orientacao')
            ]
        },
        'personal': {
            'name': '🧠 Pessoal',
            'options': [
                ('Check-in Diário', 'checkin'),
                ('Descanso/Sono', 'sono'),
                ('Refeição', 'refeicao'),
                ('Lazer', 'lazer')
            ]
        }
    }
    
    def __init__(self, terminal, backend_bridge, date=None, 
                 edit_mode=False, event_data=None):
        self.terminal = terminal
        self.bridge = backend_bridge
        self.date = date or datetime.now()
        self.edit_mode = edit_mode
        self.event_data = event_data or {}
        
        # Estado do formulário
        self.current_section = 0  # 0: tipo, 1: detalhes, 2: confirmação
        self.selected_mode = 0
        self.selected_option = 0
        self.form_data = {
            'title': '',
            'type': '',
            'time': '09:00',
            'duration': 60,
            'priority': 'medium',
            'description': '',
            'tags': []
        }
        
        # Preenche com dados existentes se em modo edição
        if edit_mode and event_data:
            self._load_existing_data()
        
        self.running = True
    
    def _load_existing_data(self):
        """Carrega dados do evento existente"""
        self.form_data.update({
            'title': self.event_data.get('title', ''),
            'type': self.event_data.get('type', ''),
            'time': self.event_data.get('time', '09:00'),
            'duration': self.event_data.get('duration', 60),
            'priority': self.event_data.get('priority', 'medium'),
            'description': self.event_data.get('description', ''),
            'tags': self.event_data.get('tags', [])
        })
        
        # Encontra o modo e opção correspondentes
        for mode_idx, (mode_key, mode_data) in enumerate(self.MODES.items()):
            for opt_idx, (opt_name, opt_type) in enumerate(mode_data['options']):
                if opt_type == self.form_data['type']:
                    self.selected_mode = mode_idx
                    self.selected_option = opt_idx
                    break
    
    def render(self):
        """Renderiza o submenu de adição"""
        width, height = self.terminal.get_size()
        
        theme.clear()
        
        # Título baseado no modo
        if self.edit_mode:
            title = f" ✏️ EDITAR EVENTO "
        else:
            title = f" ➕ ADICIONAR EVENTO "
        
        theme.rule(title, style="title")
        theme.print(f"Data: {self.date.strftime('%d/%m/%Y')}", style="accent")
        theme.rule(style="secondary")
        
        # Renderiza seção atual
        if self.current_section == 0:
            self._render_type_selection(width, height)
        elif self.current_section == 1:
            self._render_details_form(width, height)
        elif self.current_section == 2:
            self._render_confirmation(width, height)
        
        # Rodapé com ajuda
        self._render_footer(width)
    
    def _render_type_selection(self, width: int, height: int):
        """Renderiza seleção de tipo de evento"""
        theme.print("Selecione o tipo de evento:", style="primary")
        theme.rule(style="dim")
        
        # Lista modos
        mode_keys = list(self.MODES.keys())
        for i, mode_key in enumerate(mode_keys):
            mode_data = self.MODES[mode_key]
            is_selected = (i == self.selected_mode)
            
            # Nome do modo
            mode_line = f"  {mode_data['name']}"
            if is_selected:
                theme.print(mode_line, style="accent", bold=True)
            else:
                theme.print(mode_line, style="primary")
            
            # Opções deste modo (se selecionado)
            if is_selected:
                for j, (opt_name, opt_type) in enumerate(mode_data['options']):
                    is_opt_selected = (j == self.selected_option)
                    
                    opt_line = f"    {'▶' if is_opt_selected else ' '} {opt_name}"
                    if is_opt_selected:
                        theme.print(opt_line, style="warning")
                    else:
                        theme.print(opt_line, style="info")
        
        theme.rule(style="dim")
    
    def _render_details_form(self, width: int, height: int):
        """Renderiza formulário de detalhes"""
        # Obtém tipo selecionado
        mode_key = list(self.MODES.keys())[self.selected_mode]
        mode_data = self.MODES[mode_key]
        selected_type = mode_data['options'][self.selected_option][1]
        
        theme.print(f"Detalhes do evento ({selected_type}):", style="primary")
        theme.rule(style="dim")
        
        # Campos do formulário
        fields = [
            ('Título:', 'title', 30),
            ('Horário (HH:MM):', 'time', 5),
            ('Duração (minutos):', 'duration', 3),
            ('Prioridade:', 'priority', ['low', 'medium', 'high']),
            ('Descrição:', 'description', 5)  # 5 linhas
        ]
        
        # Renderiza campos
        current_line = 4
        for label, field_key, field_info in fields:
            theme.print_at(2, current_line, label, style="primary")
            
            # Campo de entrada
            if isinstance(field_info, list):  # Lista de opções
                current_value = self.form_data.get(field_key, '')
                field_display = f"[{current_value}]"
                theme.print_at(20, current_line, field_display, style="info")
            elif field_key == 'description':  # Área de texto
                desc = self.form_data.get('description', '')
                for i, line in enumerate(desc.split('\n')[:field_info]):
                    theme.print_at(20, current_line + i, line[:40], style="info")
                current_line += field_info - 1
            else:  # Campo de texto simples
                current_value = str(self.form_data.get(field_key, ''))
                field_display = current_value.ljust(field_info)
                theme.print_at(20, current_line, field_display, style="info")
            
            current_line += 1
        
        theme.rule(style="dim")
    
    def _render_confirmation(self, width: int, height: int):
        """Renderiza tela de confirmação"""
        theme.print("Confirme os dados do evento:", style="primary")
        theme.rule(style="dim")
        
        # Resumo
        summary = [
            f"Título: {self.form_data['title']}",
            f"Tipo: {self.form_data['type']}",
            f"Data: {self.date.strftime('%d/%m/%Y')}",
            f"Horário: {self.form_data['time']}",
            f"Duração: {self.form_data['duration']} minutos",
            f"Prioridade: {self.form_data['priority']}"
        ]
        
        for i, line in enumerate(summary):
            theme.print_at(2, 4 + i, line, style="info")
        
        if self.form_data.get('description'):
            theme.print_at(2, 10, "Descrição:", style="secondary")
            desc_lines = self.form_data['description'].split('\n')
            for i, line in enumerate(desc_lines[:5]):
                theme.print_at(2, 11 + i, line[:60], style="dim")
        
        theme.rule(style="dim")
        theme.print("ENTER: Confirmar • ESC: Cancelar", style="dim")
    
    def _render_footer(self, width: int):
        """Renderiza rodapé com ajuda contextual"""
        help_text = ""
        if self.current_section == 0:
            help_text = "↑↓: Navegar • →: Selecionar • ESC: Cancelar"
        elif self.current_section == 1:
            help_text = "TAB: Próximo campo • ENTER: Confirmar • ESC: Voltar"
        elif self.current_section == 2:
            help_text = "ENTER: Salvar • ESC: Voltar"
        
        theme.print(help_text.center(width), style="dim")
    
    def handle_input(self, key):
        """Processa entrada no submenu"""
        if key == 'KEY_ESCAPE':
            if self.current_section == 0:
                return 'exit'
            else:
                self.current_section -= 1
        elif self.current_section == 0:
            return self._handle_type_selection(key)
        elif self.current_section == 1:
            return self._handle_form_input(key)
        elif self.current_section == 2:
            return self._handle_confirmation(key)
        
        return None
    
    def _handle_type_selection(self, key):
        """Processa entrada na seleção de tipo"""
        if key == 'KEY_UP':
            self.selected_mode = (self.selected_mode - 1) % len(self.MODES)
            self.selected_option = 0
        elif key == 'KEY_DOWN':
            self.selected_mode = (self.selected_mode + 1) % len(self.MODES)
            self.selected_option = 0
        elif key == 'KEY_RIGHT' or key == 'ENTER':
            # Avança para o formulário
            self._update_form_with_selection()
            self.current_section = 1
        elif key == 'KEY_LEFT':
            # Navega entre opções do modo atual
            mode_key = list(self.MODES.keys())[self.selected_mode]
            options = self.MODES[mode_key]['options']
            self.selected_option = (self.selected_option + 1) % len(options)
        
        return None
    
    def _update_form_with_selection(self):
        """Atualiza form_data com a seleção atual"""
        mode_key = list(self.MODES.keys())[self.selected_mode]
        mode_data = self.MODES[mode_key]
        selected_option = mode_data['options'][self.selected_option]
        
        self.form_data['type'] = selected_option[1]
        
        # Sugere título baseado no tipo
        if not self.form_data['title'] or self.form_data['title'] == self.event_data.get('title', ''):
            self.form_data['title'] = selected_option[0]
    
    def _handle_form_input(self, key):
        """Processa entrada no formulário"""
        # Implementação simplificada
        if key == 'TAB':
            # Avança para confirmação
            self.current_section = 2
        elif key == 'ENTER':
            # Salva evento
            return self._save_event()
        
        return None
    
    def _handle_confirmation(self, key):
        """Processa entrada na confirmação"""
        if key == 'ENTER':
            return self._save_event()
        
        return None
    
    def _save_event(self):
        """Salva o evento no backend"""
        # Prepara dados do evento
        event_data = {
            'title': self.form_data['title'],
            'type': self.form_data['type'],
            'date': self.date.strftime('%Y-%m-%d'),
            'start_time': self.form_data['time'],
            'duration_minutes': self.form_data['duration'],
            'priority': self.form_data['priority'],
            'description': self.form_data.get('description', ''),
            'completed': False
        }
        
        try:
            if self.edit_mode and self.event_data.get('id'):
                # Modo edição
                success = self.bridge.update_event(
                    self.event_data['id'],
                    event_data
                )
                message = "Evento atualizado com sucesso!"
            else:
                # Modo adição
                success = self.bridge.add_event(event_data)
                message = "Evento adicionado com sucesso!"
            
            if success:
                # Mostra feedback
                theme.clear()
                theme.rule(" ✅ SUCESSO ", style="success")
                theme.print(message, style="success")
                theme.print("Retornando à agenda...", style="dim")
                self.terminal.flush()
                import time
                time.sleep(1.5)
                
                return 'exit'
            else:
                theme.print("Erro ao salvar evento!", style="error")
                time.sleep(1)
                
        except Exception as e:
            theme.print(f"Erro: {e}", style="error")
            time.sleep(1)
        
        return None


class AnalysisSubmenu:
    """Submenu de análise de produtividade"""
    
    def __init__(self, terminal, backend_bridge, date=None):
        self.terminal = terminal
        self.bridge = backend_bridge
        self.date = date or datetime.now()
        self.running = True
        
        # Dados de análise
        self.analysis_data = self._generate_analysis()
    
    def _generate_analysis(self):
        """Gera dados de análise"""
        # Obtém dados da semana
        week_data = self.bridge.get_view_data('weekly', self.date)
        
        # Calcula métricas
        week_days = week_data.get('week_days', [])
        
        if not week_days:
            return {
                'summary': 'Sem dados suficientes para análise',
                'metrics': {},
                'recommendations': []
            }
        
        # Métricas básicas
        total_events = sum(d.get('count', 0) for d in week_days)
        completed_events = sum(d.get('completed', 0) for d in week_days)
        total_hours = sum(d.get('productive_hours', 0) for d in week_days)
        
        # Dias mais/menos produtivos
        productive_days = sorted(week_days, key=lambda x: x.get('productive_hours', 0), reverse=True)
        
        return {
            'summary': f"Análise da semana de {week_data.get('week_start', '')} a {week_data.get('week_end', '')}",
            'metrics': {
                'total_events': total_events,
                'completed_events': completed_events,
                'completion_rate': (completed_events / total_events * 100) if total_events > 0 else 0,
                'total_hours': total_hours,
                'avg_daily_hours': total_hours / len(week_days) if week_days else 0,
                'most_productive_day': productive_days[0]['display_date'] if productive_days else None,
                'least_productive_day': productive_days[-1]['display_date'] if productive_days else None
            },
            'recommendations': self._generate_recommendations(week_days)
        }
    
    def _generate_recommendations(self, week_days):
        """Gera recomendações baseadas nos dados"""
        recommendations = []
        
        # Calcula médias
        daily_hours = [d.get('productive_hours', 0) for d in week_days]
        avg_hours = sum(daily_hours) / len(daily_hours) if daily_hours else 0
        
        # Recomendações baseadas em padrões
        if avg_hours > 6:
            recommendations.append("Considere reduzir a carga horária diária para evitar burnout")
        elif avg_hours < 2:
            recommendations.append("Tente aumentar o tempo de estudo produtivo em 1 hora por dia")
        
        # Verifica distribuição
        max_hours = max(daily_hours) if daily_hours else 0
        min_hours = min(daily_hours) if daily_hours else 0
        
        if max_hours - min_hours > 4:
            recommendations.append("Distribua melhor as horas de estudo entre os dias da semana")
        
        # Adiciona recomendações padrão
        recommendations.extend([
            "Faça pausas regulares a cada 45-60 minutos de estudo",
            "Mantenha horários consistentes para criar rotina",
            "Revise o material no mesmo dia da aula para melhor retenção"
        ])
        
        return recommendations
    
    def render(self):
        """Renderiza o submenu de análise"""
        width, height = self.terminal.get_size()
        
        theme.clear()
        
        # Título
        theme.rule(" 📊 ANÁLISE DE PRODUTIVIDADE ", style="title")
        theme.print(f"{Icon.GLADOS.value} {self.analysis_data['summary']}", style="accent")
        theme.rule(style="secondary")
        
        # Métricas
        theme.print("Métricas da semana:", style="primary")
        
        metrics = self.analysis_data['metrics']
        metric_lines = [
            f"Eventos totais: {metrics.get('total_events', 0)}",
            f"Eventos concluídos: {metrics.get('completed_events', 0)}",
            f"Taxa de conclusão: {metrics.get('completion_rate', 0):.1f}%",
            f"Horas produtivas: {metrics.get('total_hours', 0):.1f}h",
            f"Média diária: {metrics.get('avg_daily_hours', 0):.1f}h/dia"
        ]
        
        for i, line in enumerate(metric_lines):
            theme.print_at(2, 5 + i, line, style="info")
        
        # Dia mais produtivo
        if metrics.get('most_productive_day'):
            theme.print_at(2, 10, f"Dia mais produtivo: {metrics['most_productive_day']}", 
                          style="success")
        
        # Recomendações
        theme.print_at(0, 12, "Recomendações:", style="primary")
        
        recs = self.analysis_data.get('recommendations', [])
        for i, rec in enumerate(recs[:5]):  # Limita a 5 recomendações
            theme.print_at(2, 13 + i, f"• {rec}", style="dim")
        
        # Rodapé
        theme.rule(style="dim")
        theme.print("ESC: Voltar à agenda", style="dim")
    
    def handle_input(self, key):
        """Processa entrada no submenu"""
        if key == 'KEY_ESCAPE':
            return 'exit'
        
        return None
