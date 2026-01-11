import readchar
from enum import Enum

class Key(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ENTER = "enter"
    ESC = "esc"
    SPACE = "space"
    H = "h"      # Ajuda
    S = "s"      # Sair
    R = "r"      # Recarregar
    C = "c"      # Check-in rápido
    E = "e"      # Modo emergência
    M = "m"      # Mostrar/ocultar menu

class KeyboardHandler:
    def __init__(self):
        self._callbacks = {}
        self._active = True
        
    def register_callback(self, key: Key, callback):
        self._callbacks[key] = callback
    
    def wait_for_input(self):
        """Aguarda entrada e retorna tecla mapeada"""
        while self._active:
            try:
                key = readchar.readkey()
                
                # Mapeamento de teclas especiais
                if key == readchar.key.UP:
                    return Key.UP
                elif key == readchar.key.DOWN:
                    return Key.DOWN
                elif key in ('\r', '\n'):
                    return Key.ENTER
                elif key == readchar.key.ESC:
                    return Key.ESC
                elif key == ' ':
                    return Key.SPACE
                elif key.lower() == 'h':
                    return Key.H
                elif key.lower() == 's':
                    return Key.S
                elif key.lower() == 'r':
                    return Key.R
                elif key.lower() == 'c':
                    return Key.C
                elif key.lower() == 'e':
                    return Key.E
                elif key.lower() == 'm':
                    return Key.M
                    
                # Para teclas não mapeadas, retorna char
                return key
            except KeyboardInterrupt:
                return Key.ESC
    
    def stop(self):
        self._active = False
