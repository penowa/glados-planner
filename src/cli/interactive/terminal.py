# src/cli/interactive/terminal.py (atualização do método _read_key_fixed)
"""
Wrapper avançado para Blessed com double buffering e renderização otimizada.
"""
import time
import sys
import os
import tty
import termios
import select
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
import threading
from collections import defaultdict

try:
    from blessed import Terminal
    HAS_BLESSED = True
except ImportError:
    HAS_BLESSED = False

from src.cli.theme import theme
from src.cli.icons import Icon, icon_text


class Key(Enum):
    """Enum de teclas normalizadas."""
    # Teclas de navegação
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ENTER = "enter"
    ESC = "escape"
    SPACE = "space"
    BACKSPACE = "backspace"
    DELETE = "delete"
    HOME = "home"
    END = "end"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"
    TAB = "tab"
    SHIFT_TAB = "shift_tab"
    INSERT = "insert"

    # Teclas de função
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
    
    # Letras (para atalhos)
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
    COLON = ":"
    SEMICOLON = ";"
    COMMA = ","
    PERIOD = "."
    SLASH = "/"
    BACKSLASH = "\\"
    MINUS = "-"
    EQUALS = "="
    PLUS = "+"
    UNDERSCORE = "_"
    ASTERISK = "*"
    CARET = "^"
    DOLLAR = "$"
    AT = "@"
    EXCLAMATION = "!"
    QUESTION = "?"
    QUOTE = "'"
    DOUBLE_QUOTE = '"'
    LEFT_BRACKET = "["
    RIGHT_BRACKET = "]"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    LESS_THAN = "<"
    GREATER_THAN = ">"
    PIPE = "|"
    AMPERSAND = "&"
    PERCENT = "%"
    HASH = "#"
    TILDE = "~"
    BACKTICK = "`"


class GLTerminal:
    """Terminal otimizado com Blessed e double buffering."""
    
    def __init__(self, use_blessed: bool = True):
        self.use_blessed = use_blessed and HAS_BLESSED
        
        if self.use_blessed:
            try:
                self.term = Terminal()
                self.width = self.term.width
                self.height = self.term.height
            except Exception as e:
                print(f"⚠️ Blessed falhou, usando fallback: {e}")
                self.use_blessed = False
                self.width = 80
                self.height = 24
        else:
            # Tenta obter tamanho do terminal usando stty
            try:
                import subprocess
                result = subprocess.run(['stty', 'size'], capture_output=True, text=True)
                if result.returncode == 0:
                    height, width = map(int, result.stdout.split())
                    self.width = width
                    self.height = height
                else:
                    self.width = 80
                    self.height = 24
            except:
                self.width = 80
                self.height = 24
        
        # Buffers para renderização
        self._current_buffer = {}
        self._next_buffer = {}
        self._dirty_regions = set()
        
        # Cache de estilos
        self._style_cache = {}
        
        # Estado
        self.cursor_visible = False
        self.debug_mode = False
        self.last_render_time = 0
        self.render_count = 0
        
        # Lock para thread safety
        self._lock = threading.RLock()
        
        # Mapeamento de teclas
        self._key_map = self._create_key_map()
        
        # Configuração inicial
        self._setup_terminal()
    
    def _setup_terminal(self):
        """Configura o terminal inicial."""
        try:
            if self.use_blessed:
                print(self.term.enter_fullscreen, end="", flush=True)
                print(self.term.hide_cursor, end="", flush=True)
            else:
                print("\033[?1049h", end="", flush=True)  # Alternar para buffer alternativo
                print("\033[?25l", end="", flush=True)    # Ocultar cursor
        except Exception as e:
            if self.debug_mode:
                print(f"⚠️ Setup terminal falhou: {e}")
    
    def _create_key_map(self) -> Dict[str, Key]:
        """Cria mapeamento de teclas especiais."""
        key_map = {
            # Setas básicas
            '\x1b[A': Key.UP,
            '\x1b[B': Key.DOWN,
            '\x1b[C': Key.RIGHT,
            '\x1b[D': Key.LEFT,
            
            # Setas alternativas (alguns terminais)
            '\x1bOA': Key.UP,
            '\x1bOB': Key.DOWN,
            '\x1bOC': Key.RIGHT,
            '\x1bOD': Key.LEFT,
            
            # Enter e outros
            '\r': Key.ENTER,
            '\n': Key.ENTER,
            ' ': Key.SPACE,
            '\x7f': Key.BACKSPACE,
            '\t': Key.TAB,
            '\x1b[Z': Key.SHIFT_TAB,
            
            # Teclas especiais
            '\x1b[1~': Key.HOME,
            '\x1b[4~': Key.END,
            '\x1b[5~': Key.PAGE_UP,
            '\x1b[6~': Key.PAGE_DOWN,
            '\x1b[3~': Key.DELETE,
            '\x1b[2~': Key.INSERT,
            
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
        }
        
        # ESC sozinho
        key_map['\x1b'] = Key.ESC
        
        if self.use_blessed and HAS_BLESSED:
            # Adiciona mapeamentos do blessed
            blessed_map = {
                self.term.KEY_UP: Key.UP,
                self.term.KEY_DOWN: Key.DOWN,
                self.term.KEY_LEFT: Key.LEFT,
                self.term.KEY_RIGHT: Key.RIGHT,
                self.term.KEY_ENTER: Key.ENTER,
                self.term.KEY_ESCAPE: Key.ESC,
                self.term.KEY_SPACE: Key.SPACE,
                self.term.KEY_BACKSPACE: Key.BACKSPACE,
                self.term.KEY_DELETE: Key.DELETE,
                self.term.KEY_HOME: Key.HOME,
                self.term.KEY_END: Key.END,
                self.term.KEY_PGUP: Key.PAGE_UP,
                self.term.KEY_PGDOWN: Key.PAGE_DOWN,
                self.term.KEY_TAB: Key.TAB,
                
                # Teclas de função
                self.term.KEY_F1: Key.F1,
                self.term.KEY_F2: Key.F2,
                self.term.KEY_F3: Key.F3,
                self.term.KEY_F4: Key.F4,
                self.term.KEY_F5: Key.F5,
                self.term.KEY_F6: Key.F6,
                self.term.KEY_F7: Key.F7,
                self.term.KEY_F8: Key.F8,
                self.term.KEY_F9: Key.F9,
                self.term.KEY_F10: Key.F10,
                self.term.KEY_F11: Key.F11,
                self.term.KEY_F12: Key.F12,
            }
            key_map.update(blessed_map)
        
        return key_map
    
    def get_size(self) -> Tuple[int, int]:
        """Retorna tamanho atual do terminal."""
        try:
            if self.use_blessed:
                with self._lock:
                    self.width = self.term.width
                    self.height = self.term.height
            else:
                # Tenta obter tamanho usando ioctl
                import fcntl
                import struct
                import termios as termios2
                
                # Primeiro tenta com ioctl
                try:
                    hw = struct.unpack('hh', fcntl.ioctl(0, termios2.TIOCGWINSZ, '1234'))
                    self.height, self.width = hw
                except:
                    # Fallback para stty
                    import subprocess
                    result = subprocess.run(['stty', 'size'], capture_output=True, text=True, timeout=0.1)
                    if result.returncode == 0:
                        height, width = map(int, result.stdout.strip().split())
                        self.height = height
                        self.width = width
        except:
            pass  # Mantém valores atuais
        
        return self.width, self.height
    
    def clear(self):
        """Limpa o buffer interno."""
        with self._lock:
            self._next_buffer.clear()
            self._dirty_regions.clear()
    
    def clear_screen(self):
        """Limpa completamente a tela real e buffers."""
        with self._lock:
            # Limpa a tela real
            if self.use_blessed:
                print(self.term.clear, end="", flush=True)
                print(self.term.move(0, 0), end="", flush=True)
            else:
                # Sequências ANSI para limpar tela e posicionar cursor no início
                print("\033[2J\033[H", end="", flush=True)
            
            # Limpa buffers internos
            self._current_buffer.clear()
            self._next_buffer.clear()
            self._dirty_regions.clear()
            
            # Força um flush do stdout
            sys.stdout.flush()
    
    def print_at(self, x: int, y: int, text: str, style: Dict = None):
        """Adiciona texto ao buffer na posição especificada."""
        with self._lock:
            # Valida posição
            if x < 0 or y < 0:
                return
            
            # Aplica estilo se fornecido
            if style:
                styled_text = self._apply_style(text, style)
            else:
                styled_text = text
            
            # Armazena no buffer caractere por caractere
            for i, char in enumerate(styled_text):
                key = (y, x + i)
                self._next_buffer[key] = char
            
            # Marca região como suja
            if styled_text:
                self._dirty_regions.add((y, x, len(styled_text)))
    
    def _apply_style(self, text: str, style: Dict) -> str:
        """Aplica estilos ao texto."""
        if not self.use_blessed:
            # Fallback ANSI básico
            ansi_codes = []
            
            color_map = {
                "primary": "\033[37m",      # Branco
                "accent": "\033[33;1m",     # Amarelo brilhante
                "secondary": "\033[34m",    # Azul
                "success": "\033[32;1m",    # Verde brilhante
                "warning": "\033[33;1m",    # Amarelo brilhante
                "error": "\033[31;1m",      # Vermelho brilhante
                "info": "\033[36m",         # Ciano
                "dim": "\033[2m",           # Dim
            }
            
            if "color" in style:
                color_name = style["color"]
                if color_name in color_map:
                    ansi_codes.append(color_map[color_name])
            
            if style.get("bold"):
                ansi_codes.append("\033[1m")
            if style.get("underline"):
                ansi_codes.append("\033[4m")
            if style.get("reverse"):
                ansi_codes.append("\033[7m")
            if style.get("blink"):
                ansi_codes.append("\033[5m")
            
            if ansi_codes:
                return f"{''.join(ansi_codes)}{text}\033[0m"
            return text
        
        # Usando Blessed
        cache_key = hash(frozenset(style.items()))
        if cache_key in self._style_cache:
            style_func = self._style_cache[cache_key]
        else:
            # Converte estilos para Blessed
            blessed_style = []
            
            # Mapeamento de cores
            color_map = {
                "primary": self.term.silver,
                "accent": self.term.orange,
                "secondary": self.term.blue,
                "success": self.term.green,
                "warning": self.term.yellow,
                "error": self.term.red,
                "info": self.term.gray,
                "dim": self.term.dim,
            }
            
            if "color" in style:
                color_name = style["color"]
                if color_name in color_map:
                    blessed_style.append(color_map[color_name])
            
            if style.get("bold"):
                blessed_style.append(self.term.bold)
            if style.get("underline"):
                blessed_style.append(self.term.underline)
            if style.get("reverse"):
                blessed_style.append(self.term.reverse)
            if style.get("blink"):
                blessed_style.append(self.term.blink)
            
            # Cria função de estilo
            if blessed_style:
                style_func = lambda t: "".join(blessed_style) + t + self.term.normal
            else:
                style_func = lambda t: t
            
            self._style_cache[cache_key] = style_func
        
        return style_func(text)
    
    def flush(self):
        """Renderiza apenas as alterações desde o último flush."""
        with self._lock:
            if not self._dirty_regions:
                return
            
            # Se não usar Blessed, renderiza de forma simples
            if not self.use_blessed:
                self._simple_flush()
                return
            
            # Usando Blessed - calcula regiões otimizadas
            regions = self._optimize_regions()
            
            # Renderiza cada região
            output_lines = []
            for y, x_start, x_end in regions:
                line_chars = []
                for x in range(x_start, x_end):
                    key = (y, x)
                    if key in self._next_buffer:
                        char = self._next_buffer[key]
                        line_chars.append((x, char))
                    elif key in self._current_buffer:
                        # Espaço para limpar caractere anterior
                        line_chars.append((x, " "))
                
                # Ordena por x e renderiza linha
                if line_chars:
                    line_chars.sort(key=lambda c: c[0])
                    # Move cursor para início da linha
                    output_lines.append(self.term.move(y, x_start))
                    
                    current_x = x_start
                    for x, char in line_chars:
                        if x > current_x:
                            # Move para posição correta
                            output_lines.append(self.term.move(y, x))
                        output_lines.append(char)
                        current_x = x + 1
            
            # Renderiza tudo de uma vez
            if output_lines:
                print("".join(output_lines), end="", flush=True)
            
            # Atualiza buffers
            self._current_buffer = self._next_buffer.copy()
            self._dirty_regions.clear()
            self.render_count += 1
            self.last_render_time = time.time()
    
    def _simple_flush(self):
        """Renderização simples sem Blessed."""
        output_lines = []
        
        for (y, x, length) in self._dirty_regions:
            # Pega o conteúdo para esta região
            line_content = []
            for i in range(length):
                key = (y, x + i)
                char = self._next_buffer.get(key, " ")
                line_content.append(char)
            
            # Move cursor para posição e renderiza
            output_lines.append(f"\033[{y+1};{x+1}H")
            output_lines.append("".join(line_content))
        
        if output_lines:
            print("".join(output_lines), end="", flush=True)
        
        self._current_buffer = self._next_buffer.copy()
        self._dirty_regions.clear()
        self.render_count += 1
        self.last_render_time = time.time()
    
    def _optimize_regions(self) -> List[Tuple[int, int, int]]:
        """Otimiza regiões sujas para renderização mínima."""
        # Agrupa por linha
        lines = defaultdict(list)
        for y, x, length in self._dirty_regions:
            lines[y].append((x, x + length))
        
        # Consolida intervalos por linha
        optimized = []
        for y, intervals in lines.items():
            intervals.sort()
            merged = []
            
            if not intervals:
                continue
                
            current_start, current_end = intervals[0]
            
            for start, end in intervals[1:]:
                if start <= current_end:
                    current_end = max(current_end, end)
                else:
                    merged.append((current_start, current_end))
                    current_start, current_end = start, end
            
            merged.append((current_start, current_end))
            
            for start, end in merged:
                optimized.append((y, start, end))
        
        return optimized
    
    def _strip_ansi(self, text: str) -> str:
        """Remove códigos ANSI do texto."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def _read_escape_sequence(self, first_char: str, timeout: float = 0.1) -> str:
        """Lê sequência de escape completa."""
        if first_char != '\x1b':
            return first_char
        
        sequence = first_char
        start_time = time.time()
        
        # Tenta ler mais caracteres da sequência
        while time.time() - start_time < timeout:
            try:
                # Verifica se há mais dados disponíveis
                if select.select([sys.stdin], [], [], 0.01)[0]:
                    next_char = sys.stdin.read(1)
                    sequence += next_char
                    
                    # Verifica se é o fim de uma sequência comum
                    if next_char.isalpha() or next_char == '~' or next_char == ']':
                        break
                    # Se for '[', continua lendo (é o início de uma sequência CSI)
                    elif next_char == '[':
                        continue
                    # Se for 'O', continua lendo (é o início de sequência alternativa)
                    elif next_char == 'O':
                        continue
                    # Para qualquer outro caractere, assume que é o fim
                    else:
                        break
                else:
                    # Não há mais dados disponíveis
                    break
            except:
                break
        
        if self.debug_mode:
            print(f"\rDEBUG Sequence: {repr(sequence)}", end="", flush=True)
        
        return sequence
    
    def get_key(self, timeout: float = None) -> Optional[Key]:
        """Lê uma tecla com timeout opcional."""
        if not self.use_blessed:
            return self._read_key_fixed(timeout)
        
        try:
            with self.term.cbreak():
                if timeout is not None:
                    key = self.term.inkey(timeout=timeout)
                else:
                    key = self.term.inkey()
                
                if key:
                    key_str = str(key)
                    
                    # Debug: mostrar tecla pressionada
                    if self.debug_mode:
                        print(f"\rDEBUG Key: {repr(key_str)} -> ", end="", flush=True)
                    
                    # Tenta no mapa de teclas especiais
                    if key_str in self._key_map:
                        result = self._key_map[key_str]
                        if self.debug_mode:
                            print(f"{result}", end="", flush=True)
                        return result
                    
                    # Caracteres normais
                    if len(key_str) == 1:
                        # Mapeia para enum de caracteres especiais
                        special_char_map = {
                            ':': Key.COLON,
                            ';': Key.SEMICOLON,
                            ',': Key.COMMA,
                            '.': Key.PERIOD,
                            '/': Key.SLASH,
                            '\\': Key.BACKSLASH,
                            '-': Key.MINUS,
                            '=': Key.EQUALS,
                            '+': Key.PLUS,
                            '_': Key.UNDERSCORE,
                            '*': Key.ASTERISK,
                            '^': Key.CARET,
                            '$': Key.DOLLAR,
                            '@': Key.AT,
                            '!': Key.EXCLAMATION,
                            '?': Key.QUESTION,
                            "'": Key.QUOTE,
                            '"': Key.DOUBLE_QUOTE,
                            '[': Key.LEFT_BRACKET,
                            ']': Key.RIGHT_BRACKET,
                            '{': Key.LEFT_BRACE,
                            '}': Key.RIGHT_BRACE,
                            '(': Key.LEFT_PAREN,
                            ')': Key.RIGHT_PAREN,
                            '<': Key.LESS_THAN,
                            '>': Key.GREATER_THAN,
                            '|': Key.PIPE,
                            '&': Key.AMPERSAND,
                            '%': Key.PERCENT,
                            '#': Key.HASH,
                            '~': Key.TILDE,
                            '`': Key.BACKTICK,
                        }
                        
                        if key_str in special_char_map:
                            result = special_char_map[key_str]
                            if self.debug_mode:
                                print(f"{result}", end="", flush=True)
                            return result
                        
                        # Letras (case insensitive)
                        if key_str.isalpha():
                            result = Key(key_str.lower())
                            if self.debug_mode:
                                print(f"{result}", end="", flush=True)
                            return result
                        
                        # Números
                        if key_str.isdigit():
                            digit_map = {
                                '0': Key.ZERO, '1': Key.ONE, '2': Key.TWO,
                                '3': Key.THREE, '4': Key.FOUR, '5': Key.FIVE,
                                '6': Key.SIX, '7': Key.SEVEN, '8': Key.EIGHT,
                                '9': Key.NINE,
                            }
                            result = digit_map.get(key_str)
                            if self.debug_mode:
                                print(f"{result}", end="", flush=True)
                            return result
                        
                        # Retorna como string no enum se possível
                        try:
                            result = Key(key_str)
                            if self.debug_mode:
                                print(f"{result}", end="", flush=True)
                            return result
                        except:
                            pass
        except KeyboardInterrupt:
            return Key.ESC
        except Exception as e:
            if self.debug_mode:
                print(f"\rErro ao ler tecla: {e}", end="", flush=True)
        
        return None
    
    def _read_key_fixed(self, timeout: float = None) -> Optional[Key]:
        """Implementação corrigida para leitura de teclas sem Blessed."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            tty.setraw(fd)
            
            # Configura timeout
            if timeout is None:
                # Timeout curto para leitura não-bloqueante
                read_timeout = 0.1
            else:
                read_timeout = timeout
            
            # Aguarda entrada
            start_time = time.time()
            while True:
                # Verifica timeout
                if timeout is not None and time.time() - start_time >= timeout:
                    return None
                
                # Verifica se há entrada disponível
                rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                if rlist:
                    # Lê o primeiro caractere
                    first_char = sys.stdin.read(1)
                    
                    # Se for ESC, lê sequência completa
                    if first_char == '\x1b':
                        # Lê sequência de escape completa
                        sequence = self._read_escape_sequence(first_char, 0.05)
                    else:
                        sequence = first_char
                    
                    # Mapeia a sequência para uma tecla
                    if sequence in self._key_map:
                        key = self._key_map[sequence]
                        if self.debug_mode:
                            print(f"\rDEBUG: {repr(sequence)} -> {key}", end="", flush=True)
                        return key
                    
                    # Para teclas não mapeadas, verifica se é caractere normal
                    if len(sequence) == 1 and sequence.isprintable():
                        # Letras
                        if sequence.isalpha():
                            return Key(sequence.lower())
                        
                        # Números
                        if sequence.isdigit():
                            digit_map = {
                                '0': Key.ZERO, '1': Key.ONE, '2': Key.TWO,
                                '3': Key.THREE, '4': Key.FOUR, '5': Key.FIVE,
                                '6': Key.SIX, '7': Key.SEVEN, '8': Key.EIGHT,
                                '9': Key.NINE,
                            }
                            return digit_map.get(sequence)
                        
                        # Caracteres especiais
                        special_map = {
                            ':': Key.COLON, ';': Key.SEMICOLON,
                            ',': Key.COMMA, '.': Key.PERIOD,
                            '/': Key.SLASH, '\\': Key.BACKSLASH,
                            '-': Key.MINUS, '=': Key.EQUALS,
                            '+': Key.PLUS, '_': Key.UNDERSCORE,
                            '*': Key.ASTERISK, '^': Key.CARET,
                            '$': Key.DOLLAR, '@': Key.AT,
                            '!': Key.EXCLAMATION, '?': Key.QUESTION,
                            "'": Key.QUOTE, '"': Key.DOUBLE_QUOTE,
                            '[': Key.LEFT_BRACKET, ']': Key.RIGHT_BRACKET,
                            '{': Key.LEFT_BRACE, '}': Key.RIGHT_BRACE,
                            '(': Key.LEFT_PAREN, ')': Key.RIGHT_PAREN,
                            '<': Key.LESS_THAN, '>': Key.GREATER_THAN,
                            '|': Key.PIPE, '&': Key.AMPERSAND,
                            '%': Key.PERCENT, '#': Key.HASH,
                            '~': Key.TILDE, '`': Key.BACKTICK,
                        }
                        if sequence in special_map:
                            return special_map[sequence]
                        
                        # Teclas de controle comuns
                        if sequence == '\r' or sequence == '\n':
                            return Key.ENTER
                        elif sequence == ' ':
                            return Key.SPACE
                        elif sequence == '\t':
                            return Key.TAB
                        elif sequence == '\x7f':
                            return Key.BACKSPACE
                    
                    # Se não mapeou, retorna None
                    return None
                
                # Pequena pausa para evitar uso excessivo da CPU
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            return Key.ESC
        except Exception as e:
            if self.debug_mode:
                print(f"\rErro na leitura de tecla: {e}", end="", flush=True)
            return None
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except:
                pass
    
    def get_key_with_timeout(self, timeout: float = None) -> Optional[Key]:
        """Versão melhorada de get_key com tratamento de timeout para atualizações."""
        try:
            return self.get_key(timeout)
        except Exception as e:
            if self.debug_mode:
                print(f"\rErro em get_key_with_timeout: {e}", end="", flush=True)
            return None
    
    def hide_cursor(self):
        """Esconde o cursor."""
        try:
            if self.use_blessed:
                print(self.term.hide_cursor, end="", flush=True)
            else:
                print("\033[?25l", end="", flush=True)
            self.cursor_visible = False
        except:
            pass
    
    def show_cursor(self):
        """Mostra o cursor."""
        try:
            if self.use_blessed:
                print(self.term.show_cursor, end="", flush=True)
            else:
                print("\033[?25h", end="", flush=True)
            self.cursor_visible = True
        except:
            pass
    
    def save_cursor(self):
        """Salva posição do cursor."""
        try:
            if self.use_blessed:
                print(self.term.save, end="", flush=True)
            else:
                print("\0337", end="", flush=True)
        except:
            pass
    
    def restore_cursor(self):
        """Restaura posição do cursor."""
        try:
            if self.use_blessed:
                print(self.term.restore, end="", flush=True)
            else:
                print("\0338", end="", flush=True)
        except:
            pass
    
    def move_cursor(self, y: int, x: int):
        """Move cursor para posição específica."""
        try:
            if self.use_blessed:
                print(self.term.move(y, x), end="", flush=True)
            else:
                print(f"\033[{y+1};{x+1}H", end="", flush=True)
        except:
            pass
    
    def clear_line(self, y: int):
        """Limpa uma linha específica."""
        try:
            self.move_cursor(y, 0)
            if self.use_blessed:
                print(self.term.clear_eol, end="", flush=True)
            else:
                print("\033[K", end="", flush=True)
        except:
            pass
    
    def cleanup(self):
        """Limpeza ao sair."""
        try:
            self.show_cursor()
            if self.use_blessed:
                print(self.term.exit_fullscreen, end="", flush=True)
            else:
                print("\033[?1049l", end="", flush=True)
            
            # Força nova linha
            print()
        except:
            pass
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de renderização."""
        return {
            "render_count": self.render_count,
            "last_render_time": self.last_render_time,
            "buffer_size": len(self._current_buffer),
            "dirty_regions": len(self._dirty_regions),
            "using_blessed": self.use_blessed,
            "terminal_size": f"{self.width}x{self.height}",
        }
    
    def enable_debug(self, enabled: bool = True):
        """Ativa/desativa modo debug."""
        self.debug_mode = enabled
    
    def test_inputs(self):
        """Testa inputs do terminal."""
        self.clear_screen()
        self.print_at(0, 0, "Teste de Inputs do Terminal", {"color": "accent", "bold": True})
        self.print_at(0, 2, "Pressione teclas para testar (ESC para sair):", {"color": "primary"})
        self.flush()
        
        test_y = 4
        while True:
            key = self.get_key()
            if key == Key.ESC:
                break
            
            if key:
                key_str = f"{key.name} ({key.value})"
                self.clear_line(test_y)
                self.print_at(0, test_y, f"Tecla: {key_str}", {"color": "success"})
                self.flush()
                
                # Mantém apenas as últimas 10 entradas
                if test_y > self.height - 2:
                    self.clear_screen()
                    self.print_at(0, 0, "Teste de Inputs do Terminal", {"color": "accent", "bold": True})
                    self.print_at(0, 2, "Pressione teclas para testar (ESC para sair):", {"color": "primary"})
                    test_y = 4
                else:
                    test_y += 1
    def get_input_line(self, prompt: str = "", max_length: int = 200) -> str:
        """Captura uma linha de input do usuário - Versão corrigida."""
        import sys
        import termios
        import tty
        
        # Se Blessed estiver disponível, usar sua implementação
        if self.use_blessed and HAS_BLESSED:
            self.show_cursor()
            try:
                with self.term.cbreak():
                    input_text = ""
                    
                    while True:
                        # Mostrar prompt
                        print(f"\r{prompt}{input_text}", end="", flush=True)
                        
                        # Ler tecla
                        key = self.term.inkey(timeout=0.1)
                        
                        if not key:
                            continue
                            
                        if key.name == 'KEY_ENTER':
                            print()  # Nova linha
                            return input_text
                        elif key.name == 'KEY_ESCAPE':
                            return ""
                        elif key.name == 'KEY_BACKSPACE':
                            if input_text:
                                input_text = input_text[:-1]
                        elif key.name == 'KEY_DELETE':
                            # Delete não funciona bem em alguns terminais
                            continue
                        elif key.name in ['KEY_LEFT', 'KEY_RIGHT', 'KEY_HOME', 'KEY_END']:
                            # Navegação não suportada nesta versão simplificada
                            continue
                        elif len(key) == 1 and key.isprintable():
                            if len(input_text) < max_length:
                                input_text += key
                                
            finally:
                self.hide_cursor()
        else:
            # Fallback para terminais sem Blessed
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            
            self.show_cursor()
            try:
                tty.setraw(fd)
                
                input_text = ""
                print(prompt, end="", flush=True)
                
                while True:
                    char = sys.stdin.read(1)
                    
                    if char == '\r' or char == '\n':  # Enter
                        print()  # Nova linha
                        return input_text
                    elif char == '\x1b':  # ESC
                        return ""
                    elif char == '\x7f' or char == '\x08':  # Backspace
                        if input_text:
                            input_text = input_text[:-1]
                            # Apagar caractere visualmente
                            print('\b \b', end="", flush=True)
                    elif char.isprintable():
                        if len(input_text) < max_length:
                            input_text += char
                            print(char, end="", flush=True)
                            
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                self.hide_cursor()