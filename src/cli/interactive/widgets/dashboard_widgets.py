"""
dashboard_widgets.py - Widgets temáticos avançados para o dashboard.
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from ...components import components
from ...theme import theme
from ...icons import Icon
from ...personality import personality, Context


class WidgetType(Enum):
    """Tipos de widgets disponíveis."""
    PROGRESS_CIRCLE = "progress_circle"
    STATS_GRID = "stats_grid"
    TIMELINE = "timeline"
    SPARKLINE = "sparkline"
    HEATMAP = "heatmap"
    GAUGE = "gauge"


class DashboardWidgetFactory:
    """Fábrica de widgets temáticos para dashboard."""
    
    @staticmethod
    def create_progress_circle(title: str, value: float, max_value: float = 100, 
                               size: int = 8, show_percentage: bool = True) -> str:
        """Cria widget de círculo de progresso."""
        percentage = min(100, max(0, (value / max_value) * 100)) if max_value > 0 else 0
        
        # Caracteres para o círculo
        circle_chars = "◐◓◑◒"
        char_idx = int(datetime.now().timestamp() * 2) % len(circle_chars)
        circle_char = circle_chars[char_idx]
        
        # Cores baseadas no progresso
        if percentage >= 80:
            color = "success"
        elif percentage >= 50:
            color = "warning"
        else:
            color = "error"
        
        # Criar círculo ASCII
        circle_lines = []
        for i in range(size):
            line = ""
            for j in range(size * 2):
                dx = j - size
                dy = i - size // 2
                dist = (dx * dx + dy * dy * 4) ** 0.5
                
                if dist < size * 0.8 * (percentage / 100):
                    line += theme.colorize("█", color)
                elif dist < size:
                    line += theme.colorize("░", "text_dim")
                else:
                    line += " "
            circle_lines.append(line)
        
        circle = "\n".join(circle_lines)
        
        # Texto
        if show_percentage:
            text = f"{percentage:.1f}%"
        else:
            text = f"{value}/{max_value}"
        
        content = f"{circle}\n\n{text}"
        return components.panel(content, title, border=True)
    
    @staticmethod
    def create_stats_grid(stats: List[Tuple[str, str, str]], 
                          columns: int = 2, title: str = "Estatísticas") -> str:
        """Cria grid de estatísticas."""
        if not stats:
            return components.alert("Nenhuma estatística disponível", "info")
        
        # Organizar em grid
        rows = []
        for i in range(0, len(stats), columns):
            row_items = stats[i:i + columns]
            row = []
            
            for label, value, icon in row_items:
                cell = f"{icon} {label}: {theme.colorize(value, 'highlight')}"
                row.append(cell.ljust(30))
            
            rows.append("  ".join(row))
        
        content = "\n".join(rows)
        return components.panel(content, title, border=True)
    
    @staticmethod
    def create_timeline(events: List[Dict[str, Any]], title: str = "Linha do Tempo") -> str:
        """Cria widget de linha do tempo."""
        if not events:
            return components.alert("Nenhum evento recente", "info")
        
        content_lines = []
        for event in events[:5]:  # Limitar a 5 eventos
            time = event.get("time", "")
            icon = event.get("icon", "•")
            title_event = event.get("title", "")
            status = event.get("status", "")
            
            # Cor baseada no status
            if status == "completed":
                time_color = "text_dim"
            elif status == "in_progress":
                time_color = "highlight"
            else:
                time_color = "text"
            
            time_formatted = theme.colorize(time, time_color)
            line = f"{time_formatted} {icon} {title_event}"
            content_lines.append(line)
        
        content = "\n".join(content_lines)
        return components.panel(content, title, border=True)
    
    @staticmethod
    def create_sparkline(data: List[float], title: str = "Tendência", 
                        width: int = 30, height: int = 4) -> str:
        """Cria widget de sparkline."""
        if not data:
            return components.alert("Dados insuficientes", "info")
        
        # Normalizar dados
        min_val = min(data)
        max_val = max(data)
        range_val = max_val - min_val if max_val > min_val else 1
        
        # Criar matriz
        matrix = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Plotar dados
        for i, value in enumerate(data[-width:]):  # Últimos N pontos
            if i >= width:
                break
            
            # Normalizar para altura do gráfico
            normalized = (value - min_val) / range_val
            y = int(normalized * (height - 1))
            y = height - 1 - y  # Inverter Y
            
            # Caracteres de plotagem
            chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
            char_idx = int(normalized * (len(chars) - 1))
            
            if 0 <= y < height and 0 <= i < width:
                matrix[y][i] = theme.colorize(chars[char_idx], "accent")
        
        # Converter para string
        sparkline = "\n".join(["".join(row) for row in matrix])
        
        # Estatísticas
        current = data[-1] if data else 0
        change = ((current - data[0]) / data[0] * 100) if data[0] != 0 else 0
        
        stats = f"Atual: {current:.1f} | Variação: {change:+.1f}%"
        
        content = f"{sparkline}\n\n{stats}"
        return components.panel(content, title, border=True)
    
    @staticmethod
    def create_heatmap(data: Dict[str, List[int]], 
                      days: int = 7, title: str = "Atividade") -> str:
        """Cria widget de heatmap de atividade."""
        if not data:
            return components.alert("Sem dados de atividade", "info")
        
        # Dias da semana
        days_abbr = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        
        # Cores para intensidade
        intensity_colors = ["text_dim", "accent", "warning", "error", "success"]
        
        # Criar heatmap
        content_lines = []
        
        # Cabeçalho
        header = "     " + " ".join(days_abbr)
        content_lines.append(header)
        
        # Para cada hora do dia (simplificado: manhã, tarde, noite)
        time_slots = ["Manhã", "Tarde", "Noite"]
        
        for time_slot in time_slots:
            line = f"{time_slot:4} "
            
            for day in range(days):
                # Calcular intensidade (simulado)
                intensity = data.get(time_slot, [0] * days)[day % len(data.get(time_slot, []))]
                intensity = min(4, max(0, intensity // 25))  # Normalizar para 0-4
                
                block = theme.colorize("█", intensity_colors[intensity])
                line += block + " "
            
            content_lines.append(line)
        
        # Legenda
        legend = "     " + theme.colorize("█", "text_dim") + " Baixa  " + \
                        theme.colorize("█", "accent") + " Média  " + \
                        theme.colorize("█", "warning") + " Alta"
        
        content_lines.append("\n" + legend)
        
        content = "\n".join(content_lines)
        return components.panel(content, title, border=True)
    
    @staticmethod
    def create_gauge(value: float, min_val: float = 0, max_val: float = 100,
                    label: str = "Progresso", unit: str = "%") -> str:
        """Cria widget de gauge/medidor."""
        percentage = min(100, max(0, (value - min_val) / (max_val - min_val) * 100))
        
        # Determinar cor
        if percentage >= 75:
            color = "success"
            face = "😊"
        elif percentage >= 50:
            color = "warning"
            face = "😐"
        else:
            color = "error"
            face = "😟"
        
        # Criar gauge ASCII
        gauge_width = 20
        filled = int(gauge_width * percentage / 100)
        
        gauge_line = "["
        gauge_line += theme.colorize("█" * filled, color)
        gauge_line += theme.colorize("░" * (gauge_width - filled), "text_dim")
        gauge_line += "]"
        
        # Marcadores
        markers = f"{min_val}{' ' * (gauge_width - 6)}{max_val}"
        
        # Valor atual
        value_display = f"{value:.1f}{unit}"
        
        content = f"""
{gauge_line}
{markers}

{face} {label}: {theme.colorize(value_display, color)}

Progresso: {percentage:.1f}%
"""
        
        return components.panel(content.strip(), "📊 Medidor", border=True)


# Exemplos de uso
widget_factory = DashboardWidgetFactory()
