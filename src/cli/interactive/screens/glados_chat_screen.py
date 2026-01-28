"""
Tela de chat GLaDOS - Versão com sistema de input dedicado
Mantendo a estrutura estética original com modo de input exclusivo
"""
import os
import time
import json
import hashlib
import threading
import itertools
import re
from queue import Queue
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
import logging

from .base_screen import BaseScreen
from src.cli.integration.backend_integration import get_backend
from src.cli.interactive.terminal import Key
from src.cli.icons import Icon, icon_text

logger = logging.getLogger(__name__)


class ChatInputMode:
    """Modo de input dedicado para o chat GLaDOS."""
    
    def __init__(self, terminal):
        self.terminal = terminal
        self.text = ""
        self.cursor_pos = 0
        self.history = []
        self.history_index = -1
        self.active = False
        self._current_before_history = ""
        
    def activate(self, initial_text=""):
        """Ativa o modo de input."""
        if self.active:
            return
        
        self.active = True
        self.text = initial_text
        self.cursor_pos = len(initial_text)
        self.terminal.show_cursor()
        
    def deactivate(self):
        """Desativa o modo de input."""
        if not self.active:
            return
        
        self.active = False
        self.terminal.hide_cursor()
        return self.text
    
    def handle_key(self, key):
        """Processa uma tecla no modo de input."""
        if isinstance(key, str) and len(key) == 1:
            # Caractere normal
            self._insert_char(key)
            return True
            
        elif isinstance(key, Key):
            key_name = key.name.lower() if hasattr(key, 'name') else str(key).lower()
            
            if key_name == 'enter':
                return 'submit'
            elif key_name == 'escape':
                return 'cancel'
            elif key_name == 'backspace':
                self._delete_backward()
                return True
            elif key_name == 'delete':
                self._delete_forward()
                return True
            elif key_name == 'left':
                self._move_cursor(-1)
                return True
            elif key_name == 'right':
                self._move_cursor(1)
                return True
            elif key_name == 'home':
                self.cursor_pos = 0
                return True
            elif key_name == 'end':
                self.cursor_pos = len(self.text)
                return True
            elif key_name == 'up':
                self._navigate_history(-1)
                return True
            elif key_name == 'down':
                self._navigate_history(1)
                return True
        
        return False
    
    def _insert_char(self, char):
        """Insere um caractere na posição do cursor."""
        # Ignorar caracteres de controle (exceto backspace/delete que já são tratados)
        if ord(char) < 32 or ord(char) == 127:
            return
            
        self.text = self.text[:self.cursor_pos] + char + self.text[self.cursor_pos:]
        self.cursor_pos += 1
    
    def _delete_backward(self):
        """Remove caractere antes do cursor."""
        if self.cursor_pos > 0:
            self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
            self.cursor_pos -= 1
    
    def _delete_forward(self):
        """Remove caractere na posição do cursor."""
        if self.cursor_pos < len(self.text):
            self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
    
    def _move_cursor(self, direction):
        """Move o cursor na direção especificada."""
        new_pos = self.cursor_pos + direction
        if 0 <= new_pos <= len(self.text):
            self.cursor_pos = new_pos
    
    def _navigate_history(self, direction):
        """Navega pelo histórico."""
        if not self.history:
            return
            
        if self.history_index == -1:
            # Primeira navegação, salvar texto atual
            self._current_before_history = self.text
            
        new_index = self.history_index + direction
        
        if direction < 0:  # Para cima
            if new_index < 0:
                new_index = len(self.history) - 1
        else:  # Para baixo
            if new_index >= len(self.history):
                new_index = -1
        
        self.history_index = new_index
        
        if self.history_index == -1:
            self.text = self._current_before_history
        else:
            self.text = self.history[self.history_index]
        
        self.cursor_pos = len(self.text)
    
    def save_to_history(self):
        """Salva o texto atual no histórico."""
        if self.text.strip():
            self.history.append(self.text)
            if len(self.history) > 100:  # Limitar histórico
                self.history = self.history[-100:]
        self.history_index = -1


class GladosChatScreen(BaseScreen):
    """Tela de chat GLaDOS com sistema de input dedicado."""
    
    def __init__(self, terminal, backend_integration=None):
        super().__init__(terminal)
        self.title = "GLaDOS Chat"
        
        # === SISTEMA DE INPUT DEDICADO ===
        self.input_mode = ChatInputMode(terminal)
        self.in_input_mode = False
        
        # === ESTADOS PRINCIPAIS ===
        self.history = []             # Lista de (pergunta, resposta, fontes)
        self.show_sources = True      # Mostrar painel de fontes
        
        # === CONEXÃO BACKEND ===
        try:
            if backend_integration:
                self.backend = backend_integration
            else:
                self.backend = get_backend()
            
            self.llm_bridge = self.backend.llm
            self.obsidian_bridge = self.backend.obsidian
            self.agenda_bridge = self.backend.agenda
            
            # Verificar disponibilidade
            self.llm_available = self.llm_bridge.is_available()
            
        except Exception as e:
            logger.error(f"Erro ao inicializar backend: {e}")
            self._show_error_screen(f"Erro de inicialização: {str(e)}")
            raise
        
        # === CONTROLES DE RENDERIZAÇÃO ===
        self.last_width = 0
        self.last_height = 0
        self.needs_redraw = True
        self.running = False
        
        # Animações
        self.cursor_visible = True
        self.cursor_timer = 0
        self.processing_dots = 0
        self.is_processing = False
        self.processing_thread = None
        
        # Sistema de estilos
        self._init_styles()
        
        # Cache de dados
        self._data_cache = {}
        self._cache_timestamps = {}
        
    def _init_styles(self):
        """Inicializa os estilos baseados na paleta de cores GLaDOS."""
        # Paleta de cores baseada na documentação de identidade visual
        self.styles = {
            "primary": {"color": "primary", "bold": False},
            "accent": {"color": "accent", "bold": True},
            "secondary": {"color": "secondary", "bold": False},
            "success": {"color": "success", "bold": False},
            "warning": {"color": "warning", "bold": False},
            "error": {"color": "error", "bold": True},
            "info": {"color": "info", "bold": False},
            "dim": {"color": "dim", "bold": False},
        }
        
        # Mapeamento de tipos de mensagem para estilos
        self.message_styles = {
            "success": ("success", Icon.SUCCESS),
            "error": ("error", Icon.ERROR),
            "warning": ("warning", Icon.WARNING),
            "info": ("info", Icon.INFO)
        }
    
    def _get_style(self, style_name: str, **kwargs) -> Dict[str, Any]:
        """Retorna um dicionário de estilo para uso com terminal.print_at()."""
        style = self.styles.get(style_name, self.styles["primary"]).copy()
        
        # Aplica modificações
        if "bold" in kwargs:
            style["bold"] = kwargs["bold"]
        if "underline" in kwargs:
            style["underline"] = kwargs["underline"]
        if "reverse" in kwargs:
            style["reverse"] = kwargs["reverse"]
        
        return style
    
    def show(self) -> Optional[str]:
        """Loop principal otimizado."""
        self.running = True
        self.terminal.clear_screen()
        
        # Mostrar mensagem de boas-vindas
        from src.cli.personality import personality, Context
        welcome = personality.get_phrase(Context.GREETING)
        if welcome:
            self._show_message(welcome, 2.0)
        time.sleep(0.6)
        last_time = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                
                # Atualizar cursor piscante (2Hz)
                if current_time - self.cursor_timer >= 0.5:
                    self.cursor_visible = not self.cursor_visible
                    self.cursor_timer = current_time
                    self.needs_redraw = True
                
                # Atualizar dots de processamento (4Hz)
                if self.is_processing:
                    self.processing_dots = (self.processing_dots + 1) % 4
                    if current_time - last_time >= 0.25:
                        self.needs_redraw = True
                        last_time = current_time
                
                # Redesenhar se necessário
                if self.needs_redraw:
                    self._draw()
                    self.needs_redraw = False
                
                # Leitura baseada no modo atual
                key = self._get_simple_input()
                
                if key:
                    result = self._handle_input(key)
                    if result:
                        return result
                
                # Verificar se thread de processamento terminou
                if (self.processing_thread and 
                    not self.processing_thread.is_alive()):
                    self._handle_processing_complete()
                
                # Pausa mínima para evitar uso excessivo da CPU
                time.sleep(0.01)
                
            except KeyboardInterrupt:
                from src.cli.personality import personality, Context
                farewell = personality.get_phrase(Context.FAREWELL)
                if farewell:
                    self._show_message(farewell, "glados", 0.5)
                time.sleep(0.6)
                return 'back'
            except Exception as e:
                logger.error(f"Erro no loop principal: {e}")
                self.needs_redraw = True
        
        return None
    
    def _get_simple_input(self):
        """Leitura de input baseada no modo atual."""
        try:
            if self.in_input_mode:
                # No modo de input, usamos leitura direta
                return self._get_input_mode_key()
            else:
                # Fora do modo de input, usamos get_key normal
                return self.terminal.get_key(0.1)
        except Exception as e:
            logger.debug(f"Erro na leitura de tecla: {e}")
            return None
    
    def _get_input_mode_key(self):
        """Lê uma tecla no modo de input dedicado."""
        try:
            # Timeout curto para manter responsividade
            key = self.terminal.get_key(0.05)
            
            # Log para diagnóstico
            if key and self.terminal.debug_mode:
                logger.debug(f"Input mode key: {repr(key)}")
                
            return key
        except Exception as e:
            logger.debug(f"Erro no input mode: {e}")
            return None
    
    def _draw(self):
        """Renderização otimizada mantendo a estética original."""
        try:
            width, height = self.terminal.get_size()
            
            # Limpa apenas o buffer interno
            self.terminal.clear()
            
            # 1. Cabeçalho
            self._draw_header(width)
            
            # 2. Histórico do chat
            chat_end_y = self._draw_chat_history(width, height)
            
            # 3. Painel de fontes (se houver)
            if self.show_sources and self.history and self.history[-1][2]:
                last_sources = self.history[-1][2]
                self._draw_sources_panel(last_sources, width, height, chat_end_y)
            
            # 4. Área de input
            self._draw_input_area(width, height)
            
            # 5. Rodapé
            self._draw_footer(width, height)
            
            self.terminal.flush()
            self.last_width = width
            self.last_height = height
            
        except Exception as e:
            logger.error(f"Erro no draw: {e}")
    
    def _draw_header(self, width: int):
        """Desenha cabeçalho."""
        # Título
        title = icon_text(Icon.GLADOS, " GLaDOS Chat")
        self.terminal.print_at(0, 0, title, self._get_style("accent", bold=True))
        
        # Status
        status_x = width - 15
        if self.llm_available:
            status = icon_text(Icon.SUCCESS, " Conectado")
            style = self._get_style("success")
        else:
            status = icon_text(Icon.ERROR, " Offline")
            style = self._get_style("error")
        
        self.terminal.print_at(status_x, 0, status, style)
        
        # Separador
        sep = "─" * width
        self.terminal.print_at(0, 1, sep, self._get_style("dim"))
    
    def _draw_chat_history(self, width: int, height: int) -> int:
        """Desenha histórico do chat."""
        start_y = 3
        available_height = height - 8  # Cabeçalho(2) + Input(3) + Rodapé(3)
        
        if not self.history:
            # Mensagem de boas-vindas
            lines = [
                "",
                icon_text(Icon.GLADOS, " Bem-vindo de volta Hélio, o que ta faz precisar de um cérebro melhor do que o seu?"),
                "",
            ]
            
            for i, line in enumerate(lines):
                if start_y + i >= height - 5:
                    break
                x = max(0, (width - len(self._strip_ansi(line))) // 2)
                self.terminal.print_at(x, start_y + i, line, self._get_style("info"))
            
            return start_y + len(lines)
        
        # Mostrar últimas mensagens (no máximo 4)
        messages_to_show = self.history[-4:]
        current_y = start_y
        
        for question, answer, sources in messages_to_show:
            # Pergunta do usuário (truncar se necessário)
            user_line = icon_text(Icon.USER, f" Você: {question}")
            display_line = self._truncate_line(user_line, width - 2)
            self.terminal.print_at(2, current_y, display_line, self._get_style("primary", bold=True))
            current_y += 1
            
            # Resposta do GLaDOS (limitar a 3 linhas)
            answer_lines = self._wrap_text(answer, width - 6)
            for line in answer_lines[:3]:
                gpt_line = icon_text(Icon.GLADOS, f"  {line}")
                self.terminal.print_at(2, current_y, gpt_line, self._get_style("secondary"))
                current_y += 1
            
            current_y += 1  # Espaço entre mensagens
            
            if current_y >= height - 8:
                break
        
        return current_y
    
    def _draw_sources_panel(self, sources: List[Dict], width: int, height: int, start_y: int):
        """Desenha painel lateral com fontes."""
        if not sources or not self.show_sources:
            return
        
        panel_width = min(35, width // 3)
        panel_x = width - panel_width
        
        # Título
        title = icon_text(Icon.BOOK, " Fontes:")
        self.terminal.print_at(panel_x, start_y, title, self._get_style("accent"))
        
        # Separador
        self.terminal.print_at(panel_x, start_y + 1, "─" * panel_width, self._get_style("dim"))
        
        # Lista de fontes
        max_sources = min(len(sources), 3, height - start_y - 6)
        for i, source in enumerate(sources[:max_sources]):
            y = start_y + 2 + i
            
            # Nome do arquivo
            path = source.get("path", "")
            if path:
                name = os.path.basename(path).replace(".md", "")
                if len(name) > 20:
                    name = name[:17] + "..."
            else:
                name = "Desconhecido"
            
            # Barra de relevância
            score = int(source.get("score", 0.5) * 100)
            bar_len = 8
            filled = int(score / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            
            line = icon_text(Icon.NOTE, f" {name:<16} {bar} {score:3d}%")
            display_line = self._truncate_line(line, panel_width)
            
            self.terminal.print_at(panel_x, y, display_line, self._get_style("info"))
    
    def _draw_input_area(self, width: int, height: int):
        """Desenha área de input."""
        input_y = height - 4
        
        # Separador
        sep = "─" * width
        self.terminal.print_at(0, input_y - 1, sep, self._get_style("dim"))
        
        if self.in_input_mode:
            # Modo de input ativo
            prompt = icon_text(Icon.PORTAL, "> ")
            prompt_len = len(self._strip_ansi(prompt))
            
            # Mostrar texto atual
            display_text = self.input_mode.text
            cursor_pos = self.input_mode.cursor_pos
            
            # Mostrar prompt
            self.terminal.print_at(0, input_y, prompt, self._get_style("accent", bold=True))
            
            # Mostrar texto com cursor
            text_x = prompt_len
            self.terminal.print_at(text_x, input_y, display_text, self._get_style("primary", bold=True))
            
            # Mostrar cursor piscante
            if self.cursor_visible:
                cursor_x = text_x + cursor_pos
                if cursor_x < width:
                    cursor_char = display_text[cursor_pos] if cursor_pos < len(display_text) else " "
                    self.terminal.print_at(cursor_x, input_y, cursor_char, 
                                         self._get_style("accent", reverse=True, bold=True))
        
        elif self.is_processing:
            # Processando
            dots = "." * (self.processing_dots + 1)
            prompt = icon_text(Icon.LOADING, f" Processando{dots}")
            self.terminal.print_at(0, input_y, prompt, self._get_style("warning"))
        
        else:
            # Modo normal (pronto para ativar input)
            prompt = icon_text(Icon.PORTAL, "> Pressione ENTER para digitar...")
            self.terminal.print_at(0, input_y, prompt, self._get_style("accent", bold=True))
    
    def _draw_footer(self, width: int, height: int):
        """Desenha rodapé."""
        footer_y = height - 2
        
        if self.in_input_mode:
            # Comandos no modo de input
            commands = [
                icon_text(Icon.COMPLETE, "ENTER:Enviar"),
                icon_text(Icon.BACK, "ESC:Cancelar"),
                icon_text(Icon.ARROW_DOWN, "←→:Mover cursor"),
                icon_text(Icon.DELETE, "BACKSPACE:Apagar"),
                icon_text(Icon.ARROW_UP, "↑↓:Histórico")
            ]
        else:
            # Comandos no modo normal
            commands = [
                icon_text(Icon.COMPLETE, "ENTER:Iniciar digitação"),
                icon_text(Icon.BACK, "ESC:Voltar"),
                icon_text(Icon.HELP, "F1:Ajuda"),
                icon_text(Icon.NOTE, "P:Dashboard"),
                icon_text(Icon.BOOK, f"F4:Fontes {'ON' if self.show_sources else 'OFF'}")
            ]
        
        commands_text = " | ".join(commands)
        if len(self._strip_ansi(commands_text)) > width:
            commands_text = self._truncate_line(commands_text, width - 3)
        
        x = max(0, (width - len(self._strip_ansi(commands_text))) // 2)
        self.terminal.print_at(x, footer_y, commands_text, self._get_style("dim"))
        
        # Relógio
        time_str = datetime.now().strftime("%H:%M")
        clock = icon_text(Icon.TIMER, time_str)
        self.terminal.print_at(width - len(self._strip_ansi(clock)) - 1, 0, clock, self._get_style("info"))
    
    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """Quebra texto em múltiplas linhas."""
        # Remover códigos ANSI para cálculo de largura
        clean_text = self._strip_ansi(text)
        words = clean_text.split()
        
        lines = []
        current_line = []
        current_len = 0
        
        for word in words:
            word_len = len(word) + 1  # +1 para espaço
            
            if current_len + word_len <= max_width:
                current_line.append(word)
                current_len += word_len
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_len = word_len
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _truncate_line(self, text: str, max_width: int) -> str:
        """Trunca uma linha mantendo códigos ANSI."""
        clean_text = self._strip_ansi(text)
        if len(clean_text) <= max_width:
            return text
        
        # Encontrar onde truncar preservando códigos ANSI
        ansi_codes = []
        clean_chars = []
        
        i = 0
        while i < len(text):
            if text[i] == '\x1b':  # Código ANSI
                j = i
                while j < len(text) and text[j] != 'm':
                    j += 1
                if j < len(text):
                    ansi_codes.append(text[i:j+1])
                    i = j + 1
            else:
                clean_chars.append(text[i])
                i += 1
        
        # Truncar caracteres limpos
        truncated_clean = ''.join(clean_chars)[:max_width-3] + "..."
        
        # Reconstruir com códigos ANSI
        result = ''.join(ansi_codes) + truncated_clean + '\x1b[0m'
        return result
    
    def _strip_ansi(self, text: str) -> str:
        """Remove códigos ANSI de uma string."""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def _handle_input(self, key) -> Optional[str]:
        """Processa input do usuário."""
        if not key:
            return None
        
        # Se estivermos no modo de input dedicado
        if self.in_input_mode:
            result = self.input_mode.handle_key(key)
            
            if result == 'submit':
                # Sai do modo de input e retorna o texto
                self.in_input_mode = False
                text = self.input_mode.deactivate()
                self.input_mode.save_to_history()
                return self._process_input_text(text)
                
            elif result == 'cancel':
                # Sai do modo de input sem enviar
                self.in_input_mode = False
                self.input_mode.deactivate()
                self.input_mode.text = ""  # Limpa o texto
                self.needs_redraw = True
                return None
                
            elif result:
                # Input processado pelo modo de input
                self.needs_redraw = True
                return None
        
        # Se não estiver no modo de input, processa teclas normais
        if isinstance(key, Key):
            return self._handle_special_key(key)
        elif isinstance(key, str) and len(key) == 1:
            # Caractere normal fora do modo de input - ativa modo de input
            self._activate_input_mode(key)
            return None
        
        return None
    
    def _activate_input_mode(self, first_char=""):
        """Ativa o modo de input dedicado."""
        if self.is_processing:
            return
            
        self.in_input_mode = True
        self.input_mode.activate(first_char)
        self.needs_redraw = True
    
    def _process_input_text(self, text):
        """Processa o texto enviado pelo usuário."""
        if not text.strip():
            self._show_message("Digite algo antes de enviar", "warning", 1.0)
            return None
        
        if not self.llm_available:
            self._show_message("LLM não está disponível. Execute o backend primeiro.", "error", 2.0)
            return None
        
        # Iniciar processamento
        self._start_processing(text.strip())
        return None
    
    def _handle_special_key(self, key: Key) -> Optional[str]:
        """Processa tecla especial."""
        key_name = key.name.lower() if hasattr(key, 'name') else str(key).lower()
        
        if key_name == 'escape':
            return self._handle_escape()
        
        elif key_name == 'enter':
            return self._handle_enter()
        
        elif key_name == 'backspace':
            if self.in_input_mode:
                self.input_mode.handle_key(key)
                self.needs_redraw = True
            return None
        
        elif key_name == 'delete':
            if self.in_input_mode:
                self.input_mode.handle_key(key)
                self.needs_redraw = True
            return None
        
        elif key_name == 'left':
            if self.in_input_mode:
                self.input_mode.handle_key(key)
                self.needs_redraw = True
            return None
        
        elif key_name == 'right':
            if self.in_input_mode:
                self.input_mode.handle_key(key)
                self.needs_redraw = True
            return None
        
        elif key_name == 'home':
            if self.in_input_mode:
                self.input_mode.handle_key(key)
                self.needs_redraw = True
            return None
        
        elif key_name == 'end':
            if self.in_input_mode:
                self.input_mode.handle_key(key)
                self.needs_redraw = True
            return None
        
        elif key_name == 'up':
            if self.in_input_mode:
                self.input_mode.handle_key(key)
                self.needs_redraw = True
            elif self.history:
                # Buscar última pergunta do histórico
                last_question = self.history[-1][0]
                self._activate_input_mode(last_question)
            return None
        
        elif key_name == 'down':
            if self.in_input_mode:
                self.input_mode.handle_key(key)
                self.needs_redraw = True
            else:
                # Limpa modo de input se não ativo
                self._activate_input_mode("")
            return None
        
        elif key_name == 'f1':
            return self._show_help()
        
        elif key_name == 'f2':
            return self._export_last_response()
        
        elif key_name == 'f3':
            return self._create_agenda_task()
        
        elif key_name == 'f4':
            self.show_sources = not self.show_sources
            self.needs_redraw = True
            return None
        
        elif key_name == 'p' or key_name == 'P':
            # Retornar ao dashboard
            from src.cli.personality import personality, Context
            farewell = personality.get_phrase(Context.FAREWELL)
            if farewell:
                self._show_message(farewell, "info", 0.5)
            time.sleep(0.3)
            return 'goto:dashboard'
        
        return None
    
    def _handle_escape(self) -> Optional[str]:
        """Processa tecla ESC."""
        if self.in_input_mode:
            # Sai do modo de input sem enviar
            self.in_input_mode = False
            self.input_mode.deactivate()
            self.input_mode.text = ""
            self.needs_redraw = True
            return None
        
        from src.cli.personality import personality, Context
        farewell = personality.get_phrase(Context.FAREWELL)
        if farewell:
            self._show_message(farewell, "info", 0.5)
        time.sleep(0.3)
        return 'back'
    
    def _handle_enter(self) -> Optional[str]:
        """Processa tecla ENTER."""
        if self.is_processing:
            self._show_message("Já está processando...", "warning", 1.0)
            return None
        
        if self.in_input_mode:
            # Se já estiver no modo de input, ENTER envia
            self.in_input_mode = False
            text = self.input_mode.deactivate()
            self.input_mode.save_to_history()
            return self._process_input_text(text)
        else:
            # Se não estiver no modo de input, ENTER ativa
            self._activate_input_mode()
            return None
    
    def _start_processing(self, question: str):
        """Inicia processamento da pergunta."""
        self.is_processing = True
        self.processing_dots = 0
        
        # Criar queue para resultado
        self.result_queue = Queue()
        
        def process_thread():
            try:
                logger.info(f"Iniciando processamento da pergunta: {question[:50]}...")
                
                # Usar bridge LLM
                response_data = self.llm_bridge.query_with_context(
                    question=question,
                    use_semantic=True,
                    max_tokens=512,
                    user_name="Helio"
                )
                
                logger.info(f"Resposta recebida: {len(response_data.get('response', ''))} caracteres")
                self.result_queue.put(('success', response_data))
                
            except Exception as e:
                logger.error(f"Erro no thread de processamento: {e}")
                self.result_queue.put(('error', str(e)))
        
        # Iniciar thread
        self.processing_thread = threading.Thread(target=process_thread, daemon=True)
        self.processing_thread.start()
        
        self._show_message("Processando sua pergunta...", "info", 0.5)
    
    def _handle_processing_complete(self):
        """Lida com conclusão do processamento."""
        try:
            logger.info("Processamento concluído, lidando com resultado...")
            
            if self.result_queue.empty():
                # Timeout
                error_msg = "Timeout ao processar resposta (30s)"
                from src.cli.personality import personality, Context
                response_text = f"{personality.get_phrase(Context.ERROR)}\nErro: {error_msg}"
                sources = []
            else:
                result_type, result_data = self.result_queue.get()
                
                if result_type == 'success':
                    # Extrair resposta formatada
                    response_text = result_data.get('response', 'Sem resposta')
                    sources = result_data.get('sources', [])
                    
                    # Adicionar prefixo da personalidade se necessário
                    from src.cli.personality import personality, Context
                    if response_text and not response_text.startswith(personality.name):
                        prefix = personality.get_phrase(Context.INFO, include_context=False)
                        if prefix:
                            response_text = f"{prefix}\n\n{response_text}"
                else:
                    # Erro
                    error_msg = result_data
                    from src.cli.personality import personality, Context
                    response_text = f"{personality.get_phrase(Context.ERROR)}\nErro: {error_msg}"
                    sources = []
            
            # Adicionar ao histórico
            from src.cli.personality import personality, Context
            self.history.append((f"Pergunta {len(self.history)+1}", response_text, sources))
            
            # Limitar histórico
            if len(self.history) > 20:
                self.history = self.history[-20:]
            
            # Notificar sucesso
            self._show_message("Resposta recebida!", "success", 1.0)
            
        except Exception as e:
            logger.error(f"Erro ao lidar com processamento completo: {e}")
            from src.cli.personality import personality, Context
            error_msg = f"{personality.get_phrase(Context.ERROR)}\nErro: {str(e)}"
            self.history.append(("Erro", error_msg, []))
            self._show_message("Erro ao processar resposta", "error", 1.5)
        
        finally:
            # Resetar estados
            self.is_processing = False
            self.processing_thread = None
            self.result_queue = None
            self.needs_redraw = True
    
    def _show_message(self, message: str, msg_type: str = "info", duration: float = 1.0):
        """Mostra mensagem temporária."""
        width, height = self.terminal.get_size()
        msg_y = height - 5
        
        # Salvar área
        self.terminal.save_cursor()
        
        # Limpar linha
        self.terminal.clear_line(msg_y)
        
        # Centralizar mensagem
        clean_msg = self._strip_ansi(message)
        x = max(0, (width - len(clean_msg)) // 2)
        
        # Cor baseada no tipo
        color, icon = self.message_styles.get(msg_type, ("info", Icon.INFO))
        styled_msg = icon_text(icon, f" {message}")
        
        self.terminal.print_at(x, msg_y, styled_msg, self._get_style(color, bold=True))
        self.terminal.flush()
        
        # Aguardar
        time.sleep(duration)
        
        # Restaurar
        self.terminal.restore_cursor()
        self.needs_redraw = True
    
    def _show_error_screen(self, message: str):
        """Mostra tela de erro."""
        width, height = self.terminal.get_size()
        
        error_box = [
            "╔════════════════════════════════════════╗",
            "║         ERRO DE INICIALIZAÇÃO          ║",
            "╠════════════════════════════════════════╣",
            f"║ {message:<38} ║",
            "╠════════════════════════════════════════╣",
            "║ Pressione qualquer tecla para sair...  ║",
            "╚════════════════════════════════════════╝"
        ]
        
        # Centralizar
        start_y = max(0, (height - len(error_box)) // 2)
        
        for i, line in enumerate(error_box):
            x = max(0, (width - len(line)) // 2)
            self.terminal.print_at(x, start_y + i, line, self._get_style("error"))
        
        self.terminal.flush()
        self.terminal.get_key()
    
    def _show_help(self):
        """Mostra tela de ajuda."""
        width, height = self.terminal.get_size()
        
        help_lines = [
            icon_text(Icon.HELP, " AJUDA DO GLaDOS CHAT"),
            "═" * 40,
            "Sistema de Input Dedicado:",
            "  • Pressione ENTER para ativar modo de digitação",
            "  • Ou digite qualquer tecla para começar",
            "  • No modo digitação: digite normalmente",
            "  • ENTER: Enviar mensagem",
            "  • ESC: Cancelar e voltar",
            "",
            "Navegação no Modo Digitação:",
            icon_text(Icon.ARROW_LEFT, " SETAS: Mover cursor"),
            icon_text(Icon.BACKSPACE, " BACKSPACE/DELETE: Apagar"),
            icon_text(Icon.HOME, " HOME/END: Início/Fim do texto"),
            icon_text(Icon.ARROW_UP, " ↑↓: Histórico de mensagens"),
            "",
            "Comandos Gerais:",
            icon_text(Icon.NOTE, " P - Dashboard principal"),
            icon_text(Icon.HELP, " F1 - Esta tela de ajuda"),
            icon_text(Icon.NOTE, " F2 - Exportar última resposta"),
            icon_text(Icon.CALENDAR, " F3 - Criar tarefa na agenda"),
            icon_text(Icon.BOOK, " F4 - Alternar painel de fontes"),
            "",
            "Pressione qualquer tecla para continuar..."
        ]
        
        # Limpar e mostrar
        self.terminal.clear_screen()
        
        start_y = max(0, (height - len(help_lines)) // 2)
        for i, line in enumerate(help_lines):
            clean_line = self._strip_ansi(line)
            x = max(0, (width - len(clean_line)) // 2)
            
            # Estilizar
            if i == 0:
                style = self._get_style("accent", bold=True)
            elif i == 2 or i == 11:
                style = self._get_style("secondary", bold=True)
            else:
                style = self._get_style("primary")
            
            self.terminal.print_at(x, start_y + i, line, style)
        
        self.terminal.flush()
        
        # Aguardar tecla
        self.terminal.get_key()
        
        # Marcar para redesenho
        self.needs_redraw = True
        return None
    
    def _export_last_response(self):
        """Exporta última resposta para o vault."""
        if not self.history:
            self._show_message("Nenhuma resposta para exportar", "warning", 1.0)
            return None
        
        try:
            last_q, last_a, sources = self.history[-1]
            
            # Criar conteúdo da nota
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            query_hash = hashlib.md5(last_q.encode()).hexdigest()[:8]
            
            content = f"""# Consulta GLaDOS - {timestamp}

## Pergunta:
{last_q}

## Resposta:
{last_a}

## Fontes utilizadas:
"""
            for source in sources:
                path = source.get("path", "")
                if path:
                    name = os.path.basename(path).replace(".md", "")
                    content += f"- [[{name}]]\n"
            
            content += f"\n---\n*Exportado automaticamente do GLaDOS Chat*"
            
            # Criar arquivo
            from pathlib import Path
            vault_path = Path.home() / "Documentos" / "Obsidian" / "Philosophy_Vault"
            export_dir = vault_path / "GLaDOS" / "Consultas"
            export_dir.mkdir(parents=True, exist_ok=True)
            
            filename = export_dir / f"consulta_{timestamp[:10]}_{query_hash}.md"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self._show_message(f"Exportado para: {filename.name}", "success", 2.0)
            
        except Exception as e:
            logger.error(f"Erro ao exportar: {e}")
            self._show_message(f"Erro: {str(e)}", "error", 2.0)
        
        return None
    
    def _create_agenda_task(self):
        """Cria tarefa na agenda."""
        if not self.history:
            self._show_message("Nenhuma conversa recente", "warning", 1.0)
            return None
        
        try:
            last_q, last_a, _ = self.history[-1]
            
            # Se agenda bridge estiver disponível
            if hasattr(self.backend, 'agenda') and self.backend.agenda:
                task_data = {
                    "title": f"Estudo: {last_q[:40]}...",
                    "description": f"Consulta GLaDOS:\n\nP: {last_q}\n\nR: {last_a[:200]}...",
                    "duration": 60,
                    "priority": 3
                }
                
                result = self.backend.agenda.create_task(task_data)
                
                if result.get('success', False):
                    self._show_message("Tarefa criada na agenda!", "success", 1.5)
                else:
                    self._show_message("Erro ao criar tarefa", "error", 1.5)
            else:
                self._show_message("Módulo de agenda não disponível", "warning", 1.5)
                
        except Exception as e:
            logger.error(f"Erro ao criar tarefa: {e}")
            self._show_message(f"Erro: {str(e)}", "error", 1.5)
        
        return None