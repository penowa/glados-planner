"""
Submenus especializados da Agenda Inteligente - Versão completamente corrigida
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
import logging
import sys
import tty
import termios

from src.cli.integration.agenda_bridge import AgendaBridge
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
from src.cli.interactive.terminal import Key

logger = logging.getLogger(__name__)

class BaseSubmenu:
    """Classe base para submenus com correções."""
    
    def __init__(self, terminal, bridge: AgendaBridge, title: str):
        self.terminal = terminal
        self.bridge = bridge
        self.title = title
        self.running = True
        self.result = None
        self.needs_redraw = True
        self.last_width = 0
        self.last_height = 0
        self.last_render_time = 0
        self.min_render_interval = 0.2
        self.last_input_time = time.time()
        self.input_timeout = 0.1
    
    def show(self) -> Optional[Dict]:
        """Loop principal do submenu - versão otimizada sem flickering."""
        self.running = True
        
        # Salvar configurações do terminal
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            # Configurar terminal para modo raw
            tty.setraw(fd)
            
            # Renderização inicial
            self._force_clean_transition()
            self._draw()
            
            while self.running:
                # Verificar se precisa redesenhar
                width, height = self.terminal.get_size()
                should_redraw = (
                    self.needs_redraw or 
                    width != self.last_width or 
                    height != self.last_height
                )
                
                if should_redraw:
                    self._draw()
                    self.last_width = width
                    self.last_height = height
                    self.needs_redraw = False
                
                # Ler tecla com timeout curto
                key = self.terminal.get_key(self.input_timeout)
                
                if key:
                    action_result = self._handle_key(key)
                    if action_result is not None:
                        return action_result
                        
        except KeyboardInterrupt:
            logger.debug("Submenu interrompido por Ctrl+C")
            return {'cancelled': True}
        except Exception as e:
            logger.error(f"Erro no submenu {self.title}: {e}")
            return {'error': str(e)}
        finally:
            # Restaurar configurações do terminal
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except:
                pass
            
        return self.result
    
    def _force_clean_transition(self):
        """Força uma transição limpa."""
        self.terminal.clear_screen()
        self.terminal.flush()
        time.sleep(0.05)
    
    def _draw(self):
        """Método de desenho otimizado."""
        self.terminal.clear_screen()
        self._render()
        self.terminal.flush()
    
    def _render(self):
        """Renderiza o submenu - deve ser sobrescrito."""
        pass
    
    def _handle_key(self, key) -> Optional[Dict]:
        """Processa entrada do teclado - deve ser sobrescrito."""
        pass
    
    def _get_key_name(self, key):
        """Obtém nome da tecla de forma segura."""
        if key is None:
            return None
        if isinstance(key, Key):
            return key.name.lower()
        if isinstance(key, str):
            return key.lower()
        return str(key)
    
    def _clear_area(self, x: int, y: int, width: int, height: int):
        """Limpa uma área retangular da tela."""
        for row in range(y, y + height):
            if row < self.last_height:
                self.terminal.print_at(x, row, " " * min(width, self.last_width - x), {})


class AddEventSubmenu(BaseSubmenu):
    """Submenu inteligente para adição de eventos."""
    
    EVENT_TYPES = [
        ("📚 Aula Regular", "aula"),
        ("📖 Leitura Programada", "leitura"),
        ("🎯 Sessão de Produção", "producao"),
        ("🔄 Revisão Espaçada", "revisao"),
        ("👥 Grupo de Estudo", "grupo_estudo"),
        ("📝 Prova/Avaliação", "prova"),
        ("🎤 Seminário/Apresentação", "seminario"),
        ("📦 Entrega de Trabalho", "entrega"),
        ("🤖 Defesa/Orientação", "orientacao"),
        ("😴 Descanso/Sono", "sono"),
        ("🍽️ Refeição", "refeicao"),
        ("🎮 Lazer", "lazer"),
        ("📝 Outro", "outro")
    ]
    
    PRIORITIES = [
        ("🔴 Crítica", "critical"),
        ("🟠 Alta", "high"),
        ("🟡 Média", "medium"),
        ("🟢 Baixa", "low")
    ]
    
    def __init__(self, terminal, bridge: AgendaBridge, 
                 date: datetime = None, edit_mode: bool = False, 
                 event_data: Dict = None):
        title = "Editar Evento" if edit_mode else "Adicionar Evento"
        super().__init__(terminal, bridge, title)
        
        self.date = date or datetime.now()
        self.edit_mode = edit_mode
        
        # Garantir que event_data seja um dicionário válido
        if not isinstance(event_data, dict):
            logger.warning(f"event_data não é um dicionário: {type(event_data)}")
            event_data = {}
        
        self.event_data = event_data or {}
        
        # Estado do formulário com valores padrão
        self.current_section = 0
        self.selected_index = 0
        self.current_field = 0
        
        # Extrair dados do evento com fallbacks seguros
        self.form = {
            'title': self._safe_get(event_data, 'title', ''),
            'type': self._safe_get(event_data, 'type', 'outro'),
            'priority': self._safe_get(event_data, 'priority', 'medium'),
            'description': self._safe_get(event_data, 'description', ''),
            'start_time': self._safe_get(event_data, 'time', '09:00'),
            'duration': self._safe_get(event_data, 'duration', 60),
            'tags': self._safe_get(event_data, 'tags', []),
            'completed': self._safe_get(event_data, 'completed', False)
        }
        
        # Índices atuais com validação
        self.type_index = self._find_type_index(self.form['type'])
        self.priority_index = self._find_priority_index(self.form['priority'])
        
        # IDs para edição
        if edit_mode:
            self.event_id = self._safe_get(event_data, 'id')
    
    def _safe_get(self, obj, key, default=None):
        """Obtém valor de forma segura."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return default
    
    def _find_type_index(self, type_code: str) -> int:
        """Encontra índice do tipo de evento."""
        for i, (_, code) in enumerate(self.EVENT_TYPES):
            if code == type_code:
                return i
        return len(self.EVENT_TYPES) - 1  # Default para "outro"
    
    def _find_priority_index(self, priority_code: str) -> int:
        """Encontra índice da prioridade."""
        for i, (_, code) in enumerate(self.PRIORITIES):
            if code == priority_code:
                return i
        return 2  # Default para "medium"
    
    # ... restante dos métodos existentes (renderização e handlers) ...
