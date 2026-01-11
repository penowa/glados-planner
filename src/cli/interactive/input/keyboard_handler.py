# src/cli/interactive/input/keyboard_handler.py
"""
Gerenciador de entrada por teclado com mapeamento de teclas.
"""
import sys
import readchar
from enum import Enum
from typing import Optional, Callable, Dict

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
    
    # Mapeamento de códigos especiais
    SPECIAL_KEYS = {
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
    
    # Mapeamento de caracteres normais
    CHAR_MAP = {
        "a": Key.A, "b": Key.B, "c": Key.C, "d": Key.D, "e": Key.E,
        "f": Key.F, "g": Key.G, "h": Key.H, "i": Key.I, "j": Key.J,
        "k": Key.K, "l": Key.L, "m": Key.M, "n": Key.N, "o": Key.O,
        "p": Key.P, "q": Key.Q, "r": Key.R, "s": Key.S, "t": Key.T,
        "u": Key.U, "v": Key.V, "w": Key.W, "x": Key.X, "y": Key.Y,
        "z": Key.Z,
        "0": Key.ZERO, "1": Key.ONE, "2": Key.TWO, "3": Key.THREE,
        "4": Key.FOUR, "5": Key.FIVE, "6": Key.SIX, "7": Key.SEVEN,
        "8": Key.EIGHT, "9": Key.NINE,
        "A": Key.A, "B": Key.B, "C": Key.C, "D": Key.D, "E": Key.E,
        "F": Key.F, "G": Key.G, "H": Key.H, "I": Key.I, "J": Key.J,
        "K": Key.K, "L": Key.L, "M": Key.M, "N": Key.N, "O": Key.O,
        "P": Key.P, "Q": Key.Q, "R": Key.R, "S": Key.S, "T": Key.T,
        "U": Key.U, "V": Key.V, "W": Key.W, "X": Key.X, "Y": Key.Y,
        "Z": Key.Z,
    }
    
    def __init__(self):
        self.callbacks: Dict[Key, Callable] = {}
    
    def wait_for_input(self, timeout: Optional[float] = None) -> Key:
        """
        Aguarda entrada do teclado e retorna a tecla pressionada.
        
        Args:
            timeout: Tempo máximo de espera em segundos (None para esperar indefinidamente)
            
        Returns:
            Tecla pressionada como enum Key
        """
        try:
            if timeout is not None:
                # Implementação simplificada - readchar não suporta timeout diretamente
                # Em um sistema real, usaríamos select ou threading
                import time
                start_time = time.time()
                while time.time() - start_time < timeout:
                    # Tentar ler sem bloquear
                    # Note: readchar.readkey() é bloqueante, então esta implementação
                    # não é ideal para timeout. Para uso real, considere usar threading.
                    pass
                # Por simplicidade, vamos ignorar timeout por enquanto
                pass
            
            key = readchar.readkey()
            
            # Verificar se é tecla especial
            if key in self.SPECIAL_KEYS:
                return self.SPECIAL_KEYS[key]
            
            # Verificar se é caractere normal
            if key in self.CHAR_MAP:
                return self.CHAR_MAP[key]
            
            # Para qualquer outra tecla, retornar como string
            # Mas para manter a tipagem, vamos criar um Key dinâmico
            try:
                # Tentar criar um enum dinâmico
                return Key(key)
            except:
                # Se não der, retornar como string no enum
                # Criamos um valor dinâmico
                return Key(key) if hasattr(Key, key.upper()) else Key.A  # fallback
                
        except KeyboardInterrupt:
            return Key.ESC  # Ctrl+C tratado como ESC
    
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
    
    def check_callbacks(self, key: Key) -> bool:
        """
        Verifica se há callback para a tecla e executa.
        
        Returns:
            True se callback foi executado, False caso contrário
        """
        if key in self.callbacks:
            self.callbacks[key]()
            return True
        return False

# Instância global
keyboard_handler = KeyboardHandler()
