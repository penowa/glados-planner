# src/cli/interactive/widgets/notification_widget.py
"""
Widget de notificações para a Agenda
"""
from datetime import datetime
from typing import List, Dict

from cli.theme import theme
from cli.icons import Icon, icon_text

class NotificationWidget:
    """Widget para exibir notificações da agenda"""
    
    @staticmethod
    def render_notifications(notifications: List[Dict], width: int = 50):
        """Renderiza lista de notificações"""
        if not notifications:
            return
        
        theme.rule(" 🔔 NOTIFICAÇÕES ", style="subtitle")
        
        for notif in notifications[:5]:  # Limita a 5 notificações
            NotificationWidget._render_notification(notif, width)
        
        if len(notifications) > 5:
            theme.print(f"... +{len(notifications)-5} notificações", style="dim")
        
        theme.rule(style="secondary")
    
    @staticmethod
    def _render_notification(notification: Dict, width: int):
        """Renderiza uma notificação individual"""
        notif_type = notification.get('type', 'info')
        message = notification.get('message', '')[:width - 5]
        
        # Ícone baseado no tipo
        icon_map = {
            'warning': '⚠️',
            'error': '❌',
            'success': '✅',
            'info': 'ℹ️',
            'reminder': '⏰'
        }
        
        icon = icon_map.get(notif_type, '•')
        
        # Estilo baseado no tipo
        style_map = {
            'warning': 'warning',
            'error': 'error',
            'success': 'success',
            'info': 'info',
            'reminder': 'accent'
        }
        
        style = style_map.get(notif_type, 'dim')
        
        # Renderiza
        theme.print(f"{icon} {message}", style=style)
    
    @staticmethod
    def generate_agenda_notifications(agenda_data: Dict) -> List[Dict]:
        """Gera notificações baseadas nos dados da agenda"""
        notifications = []
        
        # Verifica conflitos
        conflicts = agenda_data.get('conflicts', [])
        for conflict in conflicts:
            notifications.append({
                'type': 'warning',
                'message': f"Conflito: {conflict['event1']} ↔ {conflict['event2']}"
            })
        
        # Verifica eventos importantes próximos
        # (Implementação simplificada)
        
        # Verifica produtividade baixa
        stats = agenda_data.get('stats', {})
        if stats.get('completion_rate', 100) < 50:
            notifications.append({
                'type': 'warning',
                'message': f"Taxa de conclusão baixa: {stats['completion_rate']:.1f}%"
            })
        
        return notifications
