# src/cli/interactive/input/keyboard_handler.py
"""
Gerenciador de entrada por teclado com mapeamento de teclas.
"""
import sys
import readchar
from enum import Enum
from typing import Optional, Callable, Dict, Union
import time

class Key(Enum):
    """Enumeração de teclas mapeadas."""
    # Navegação básica
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ENTER = "enter"
    ESC = "esc"
    SPACE = " "
    TAB = "\t"
    BACKSPACE = "\x7f"
    
    # Letras (comandos rápidos)
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"
    I = "i"
    J = "j"
    K = "k"
    L = "l"
    M = "m"
    N = "n"
    O = "o"
    P = "p"
    Q = "q"
    R = "r"
    S = "s"
    T = "t"
    U = "u"
    V = "v"
    W = "w"
    X = "x"
    Y = "y"
    Z = "z"
    
    # Números
    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    
    # Caracteres especiais
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"
    HOME = "home"
    END = "end"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"
    INSERT = "insert"
    DELETE = "delete"

class KeyboardHandler:
    """
    Gerencia a entrada por teclado com leitura não-bloqueante.
    """
    
    def __init__(self):
        self.callbacks: Dict[Key, Callable] = {}
        self._debug = False
    
    def _map_special_key(self, key_sequence: str) -> Optional[Key]:
        """Mapeia sequências de escape para teclas especiais."""
        # Mapeamento de sequências de escape para teclas
        special_mappings = {
            # Setas
            '\x1b[A': Key.UP,
            '\x1b[B': Key.DOWN,
            '\x1b[D': Key.LEFT,
            '\x1b[C': Key.RIGHT,
            
            # Setas alternativas (alguns terminais)
            '\x1bOA': Key.UP,
            '\x1bOB': Key.DOWN,
            '\x1bOC': Key.RIGHT,
            '\x1bOD': Key.LEFT,
            
            # Teclas de função
            '\x1bOP': Key.F1,
            '\x1bOQ': Key.F2,
            '\x1bOR': Key.F3,
            '\x1bOS': Key.F4,
            '\x1b[15~': Key.F5,
            '\x1b[17~': Key.F6,
            '\x1b[18~': Key.F7,
            '\x1b[19~': Key.F8,
            '\x1b[20~': Key.F9,
            '\x1b[21~': Key.F10,
            '\x1b[23~': Key.F11,
            '\x1b[24~': Key.F12,
            
            # Navegação
            '\x1b[1~': Key.HOME,
            '\x1b[4~': Key.END,
            '\x1b[5~': Key.PAGE_UP,
            '\x1b[6~': Key.PAGE_DOWN,
            '\x1b[3~': Key.DELETE,
            '\x1b[2~': Key.INSERT,
            
            # Shift + Tab
            '\x1b[Z': Key.TAB,  # Note: Shift+Tab é tratado como TAB para simplificar
            
            # Mapeamento usando readchar.key (se disponível)
            **self._get_readchar_mappings()
        }
        
        return special_mappings.get(key_sequence)
    
    def _get_readchar_mappings(self) -> Dict[str, Key]:
        """Obtém mapeamentos do readchar.key se disponível."""
        mappings = {}
        
        try:
            # Teclas especiais do readchar
            if hasattr(readchar, 'key'):
                readchar_mappings = {
                    readchar.key.UP: Key.UP,
                    readchar.key.DOWN: Key.DOWN,
                    readchar.key.LEFT: Key.LEFT,
                    readchar.key.RIGHT: Key.RIGHT,
                    readchar.key.ENTER: Key.ENTER,
                    readchar.key.ESC: Key.ESC,
                    readchar.key.SPACE: Key.SPACE,
                    readchar.key.TAB: Key.TAB,
                    readchar.key.BACKSPACE: Key.BACKSPACE,
                    readchar.key.F1: Key.F1,
                    readchar.key.F2: Key.F2,
                    readchar.key.F3: Key.F3,
                    readchar.key.F4: Key.F4,
                    readchar.key.F5: Key.F5,
                    readchar.key.F6: Key.F6,
                    readchar.key.F7: Key.F7,
                    readchar.key.F8: Key.F8,
                    readchar.key.F9: Key.F9,
                    readchar.key.F10: Key.F10,
                    readchar.key.F11: Key.F11,
                    readchar.key.F12: Key.F12,
                    readchar.key.HOME: Key.HOME,
                    readchar.key.END: Key.END,
                    readchar.key.PAGE_UP: Key.PAGE_UP,
                    readchar.key.PAGE_DOWN: Key.PAGE_DOWN,
                    readchar.key.INSERT: Key.INSERT,
                    readchar.key.DELETE: Key.DELETE,
                }
                
                # Converter para strings para comparação
                for key_obj, key_enum in readchar_mappings.items():
                    if isinstance(key_obj, str):
                        mappings[key_obj] = key_enum
        except:
            pass
        
        return mappings
    
    def _map_normal_key(self, key: str) -> Optional[Key]:
        """Mapeia teclas normais."""
        if len(key) == 1:
            # Letras
            if key.isalpha():
                return Key(key.lower())
            
            # Números
            if key.isdigit():
                digit_map = {
                    '0': Key.ZERO, '1': Key.ONE, '2': Key.TWO,
                    '3': Key.THREE, '4': Key.FOUR, '5': Key.FIVE,
                    '6': Key.SIX, '7': Key.SEVEN, '8': Key.EIGHT,
                    '9': Key.NINE,
                }
                return digit_map.get(key)
            
            # Caracteres especiais comuns
            char_map = {
                '\r': Key.ENTER,
                '\n': Key.ENTER,
                ' ': Key.SPACE,
                '\t': Key.TAB,
                '\x7f': Key.BACKSPACE,
                '\x1b': Key.ESC,
            }
            return char_map.get(key)
        
        return None
    
    def enable_debug(self, enabled: bool = True):
        """Ativa/desativa modo debug."""
        self._debug = enabled
    
    def wait_for_input(self, timeout: Optional[float] = None) -> Union[Key, str, None]:
        """
        Aguarda entrada do teclado e retorna a tecla pressionada.
        
        Args:
            timeout: Tempo máximo de espera em segundos (None para esperar indefinidamente)
            
        Returns:
            Tecla pressionada como enum Key ou string, None se timeout
        """
        try:
            if timeout is not None:
                # Implementação com timeout usando polling
                import select
                
                start_time = time.time()
                while True:
                    # Verifica se há entrada disponível
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = readchar.readkey()
                        
                        if self._debug:
                            print(f"\rDEBUG: Raw key: {repr(key)}", end="", flush=True)
                        
                        # Tenta mapear como tecla especial
                        mapped = self._map_special_key(key)
                        if mapped:
                            return mapped
                        
                        # Tenta mapear como tecla normal
                        mapped = self._map_normal_key(key)
                        if mapped:
                            return mapped
                        
                        # Se não mapeou, retorna como string
                        return key
                    
                    # Verifica timeout
                    if time.time() - start_time >= timeout:
                        return None
            else:
                # Leitura bloqueante
                key = readchar.readkey()
                
                if self._debug:
                    print(f"\rDEBUG: Raw key: {repr(key)}", end="", flush=True)
                
                # Tenta mapear como tecla especial
                mapped = self._map_special_key(key)
                if mapped:
                    return mapped
                
                # Tenta mapear como tecla normal
                mapped = self._map_normal_key(key)
                if mapped:
                    return mapped
                
                # Se não mapeou, retorna como string
                return key
                
        except KeyboardInterrupt:
            return Key.ESC  # Ctrl+C tratado como ESC
        except Exception as e:
            if self._debug:
                print(f"\rErro ao ler tecla: {e}", end="", flush=True)
            return None
    
    def get_key(self) -> Union[Key, str, None]:
        """Alias para wait_for_input sem timeout."""
        return self.wait_for_input()
    
    def check_input(self) -> Union[Key, str, None]:
        """Verifica se há entrada disponível sem bloquear."""
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            return self.get_key()
        return None
    
    def register_callback(self, key: Key, callback: Callable):
        """Registra um callback para uma tecla específica."""
        self.callbacks[key] = callback
    
    def unregister_callback(self, key: Key):
        """Remove o callback de uma tecla."""
        if key in self.callbacks:
            del self.callbacks[key]
    
    def clear_callbacks(self):
        """Remove todos os callbacks."""
        self.callbacks.clear()
    
    def execute_callback(self, key: Key) -> bool:
        """
        Executa callback para a tecla se existir.
        
        Returns:
            True se callback foi executado, False caso contrário
        """
        if key in self.callbacks:
            self.callbacks[key]()
            return True
        return False

# Instância global
keyboard_handler = KeyboardHandler()
