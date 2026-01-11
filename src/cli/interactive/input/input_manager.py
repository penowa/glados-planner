# src/cli/interactive/input/input_manager.py
import threading
import time
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum
from cli.theme import theme
from cli.icons import Icon

@dataclass
class InputEvent:
    """Evento de input processado"""
    key: str
    raw: str
    timestamp: float
    source: str = "keyboard"
    modifiers: List[str] = None
    
    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = []

class InputMode(Enum):
    """Modos de entrada disponíveis"""
    NORMAL = "normal"      # Navegação padrão
    INSERT = "insert"      # Modo texto (como Vim)
    COMMAND = "command"    # Modo comando
    SEARCH = "search"      # Busca
    VISUAL = "visual"      # Seleção visual

class InputManager:
    """Gerenciador avançado de input com múltiplos modos e macros"""
    
    def __init__(self):
        from .keyboard_handler import KeyboardHandler
        
        self.handler = KeyboardHandler()
        self.mode = InputMode.NORMAL
        self._listeners = []
        self._macros = {}
        self._recording = False
        self._macro_buffer = []
        self._active = False
        self._thread = None
        
        # Mapeamento de teclas por modo
        self._key_maps = {
            InputMode.NORMAL: self._normal_key_map(),
            InputMode.INSERT: self._insert_key_map(),
            InputMode.COMMAND: self._command_key_map(),
        }
        
        # Configurações
        self.timeout = 0.1  # Timeout para leitura não-bloqueante
        self.auto_repeat = True
        self.repeat_delay = 0.3
        self.repeat_interval = 0.05
        
        # Estado
        self._last_key = None
        self._last_key_time = 0
        self._repeat_count = 0
    
    def _normal_key_map(self) -> Dict:
        """Mapeamento para modo normal (navegação)"""
        return {
            'h': 'left', 'j': 'down', 'k': 'up', 'l': 'right',
            'gg': 'top', 'G': 'bottom',
            'dd': 'delete', 'yy': 'copy',
            'p': 'paste', 'u': 'undo', 'Ctrl+r': 'redo',
            '/': self._enter_search_mode,
            ':': self._enter_command_mode,
            'i': self._enter_insert_mode,
            'v': self._enter_visual_mode,
        }
    
    def _insert_key_map(self) -> Dict:
        """Mapeamento para modo insert"""
        return {
            'Esc': self._enter_normal_mode,
            'Ctrl+[': self._enter_normal_mode,
        }
    
    def _command_key_map(self) -> Dict:
        """Mapeamento para modo comando"""
        return {
            'Esc': self._enter_normal_mode,
            'Enter': self._execute_command,
        }
    
    def start(self) -> None:
        """Inicia thread de captura de input"""
        if not self._active:
            self._active = True
            self._thread = threading.Thread(target=self._input_loop, daemon=True)
            self._thread.start()
            theme.print(f"{Icon.INFO} InputManager iniciado", style="info")
    
    def stop(self) -> None:
        """Para captura de input"""
        self._active = False
        if self._thread:
            self._thread.join(timeout=1.0)
        theme.print(f"{Icon.INFO} InputManager parado", style="info")
    
    def _input_loop(self) -> None:
        """Loop principal de captura de input"""
        while self._active:
            try:
                key = self.handler.wait_for_input()
                if key:
                    event = self._process_key(key)
                    self._notify_listeners(event)
                    
                    # Gravação de macro
                    if self._recording:
                        self._macro_buffer.append(event.key)
                
                time.sleep(self.timeout)
            except Exception as e:
                theme.print(f"{Icon.ERROR} Erro no InputManager: {e}", style="error")
    
    def _process_key(self, key) -> InputEvent:
        """Processa tecla com base no modo atual"""
        from .keyboard_handler import Key
        
        raw_key = key.value if isinstance(key, Key) else str(key)
        current_time = time.time()
        
        # Detecta repetição
        if raw_key == self._last_key and current_time - self._last_key_time < 0.5:
            self._repeat_count += 1
        else:
            self._repeat_count = 1
        
        # Mapeia tecla com base no modo
        mapped_key = self._map_key(raw_key)
        
        event = InputEvent(
            key=mapped_key,
            raw=raw_key,
            timestamp=current_time,
            modifiers=self._get_modifiers(raw_key)
        )
        
        # Atualiza estado
        self._last_key = raw_key
        self._last_key_time = current_time
        
        return event
    
    def _map_key(self, raw_key: str) -> str:
        """Mapeia tecla com base no modo atual"""
        key_map = self._key_maps.get(self.mode, {})
        
        # Verifica mapeamento direto
        if raw_key in key_map:
            action = key_map[raw_key]
            if callable(action):
                return action()
            return action
        
        # Fallback para a própria tecla
        return raw_key
    
    def _get_modifiers(self, key: str) -> List[str]:
        """Detecta modificadores de tecla"""
        modifiers = []
        # Implementação simplificada - em produção usar readchar.key.CTRL, etc.
        return modifiers
    
    def add_listener(self, callback: Callable) -> None:
        """Adiciona listener para eventos de input"""
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable) -> None:
        """Remove listener"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, event: InputEvent) -> None:
        """Notifica todos os listeners"""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                theme.print(f"{Icon.ERROR} Erro no listener: {e}", style="error")
    
    # Métodos de mudança de modo
    def _enter_normal_mode(self) -> str:
        self.mode = InputMode.NORMAL
        return "normal_mode"
    
    def _enter_insert_mode(self) -> str:
        self.mode = InputMode.INSERT
        return "insert_mode"
    
    def _enter_command_mode(self) -> str:
        self.mode = InputMode.COMMAND
        return "command_mode"
    
    def _enter_search_mode(self) -> str:
        self.mode = InputMode.SEARCH
        return "search_mode"
    
    def _enter_visual_mode(self) -> str:
        self.mode = InputMode.VISUAL
        return "visual_mode"
    
    def _execute_command(self) -> str:
        # Em implementação real, processaria comando
        return "command_executed"
    
    # Sistema de macros
    def start_recording(self, macro_name: str) -> bool:
        """Inicia gravação de macro"""
        if self._recording:
            return False
        
        self._recording = True
        self._macro_buffer = []
        self._current_macro_name = macro_name
        theme.print(f"{Icon.INFO} Gravando macro '{macro_name}'...", style="info")
        return True
    
    def stop_recording(self) -> bool:
        """Para gravação e salva macro"""
        if not self._recording:
            return False
        
        self._recording = False
        self._macros[self._current_macro_name] = self._macro_buffer.copy()
        theme.print(f"{Icon.SUCCESS} Macro '{self._current_macro_name}' salva ({len(self._macro_buffer)} ações)", style="success")
        return True
    
    def play_macro(self, macro_name: str) -> bool:
        """Executa macro gravada"""
        if macro_name not in self._macros:
            return False
        
        for key in self._macros[macro_name]:
            event = InputEvent(
                key=key,
                raw=key,
                timestamp=time.time()
            )
            self._notify_listeners(event)
            time.sleep(0.01)  # Pequeno delay entre ações
        
        return True

class TextInput:
    """Widget para entrada de texto com validação"""
    
    def __init__(self, 
                 prompt: str = "> ",
                 default: str = "",
                 validator: Optional[Callable] = None,
                 completer: Optional[Callable] = None):
        self.prompt = prompt
        self.value = default
        self._cursor_pos = len(default)
        self.validator = validator
        self.completer = completer
        self.active = False
        self.history = []
        self._history_index = -1
        self._suggestion = ""
    
    def render(self) -> str:
        """Renderiza campo de entrada"""
        # Mostra prompt e texto atual
        display_text = self.value
        
        # Adiciona cursor
        cursor_char = "|"
        if self.active:
            cursor = display_text[:self._cursor_pos] + cursor_char + display_text[self._cursor_pos:]
        else:
            cursor = display_text
        
        # Adiciona sugestão se disponível
        if self._suggestion and self.active:
            suggestion_display = self._suggestion[len(self.value):]
            if suggestion_display:
                cursor += f"[dim]{suggestion_display}[/dim]"
        
        return f"{self.prompt}{cursor}"
    
    def handle_key(self, key: str) -> bool:
        """Processa tecla de entrada"""
        if not self.active:
            return False
        
        if key == 'backspace':
            if self._cursor_pos > 0:
                self.value = self.value[:self._cursor_pos-1] + self.value[self._cursor_pos:]
                self._cursor_pos -= 1
        elif key == 'delete':
            if self._cursor_pos < len(self.value):
                self.value = self.value[:self._cursor_pos] + self.value[self._cursor_pos+1:]
        elif key == 'left':
            self._cursor_pos = max(0, self._cursor_pos - 1)
        elif key == 'right':
            self._cursor_pos = min(len(self.value), self._cursor_pos + 1)
        elif key == 'home':
            self._cursor_pos = 0
        elif key == 'end':
            self._cursor_pos = len(self.value)
        elif len(key) == 1 and key.isprintable():
            # Caractere normal
            self.value = self.value[:self._cursor_pos] + key + self.value[self._cursor_pos:]
            self._cursor_pos += 1
            
            # Atualiza sugestão
            if self.completer:
                self._update_suggestion()
        elif key == 'tab' and self._suggestion:
            # Auto-completar
            self.value = self._suggestion
            self._cursor_pos = len(self.value)
            self._suggestion = ""
        elif key == 'up':
            # Histórico para cima
            self._navigate_history(-1)
        elif key == 'down':
            # Histórico para baixo
            self._navigate_history(1)
        elif key == 'enter':
            # Finaliza entrada
            self.active = False
            self.history.append(self.value)
            return True
        
        return False
    
    def _update_suggestion(self) -> None:
        """Atualiza sugestão de auto-complete"""
        if self.completer:
            suggestions = self.completer(self.value)
            if suggestions:
                self._suggestion = suggestions[0]
            else:
                self._suggestion = ""
    
    def _navigate_history(self, direction: int) -> None:
        """Navega no histórico"""
        if not self.history:
            return
        
        self._history_index += direction
        self._history_index = max(-1, min(self._history_index, len(self.history) - 1))
        
        if self._history_index == -1:
            self.value = ""
        else:
            self.value = self.history[self._history_index]
        
        self._cursor_pos = len(self.value)
