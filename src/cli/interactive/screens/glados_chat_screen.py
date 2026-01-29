"""
glados_chat_screen.py
Tela de chat interativo com o LLM GLaDOS (CLI)
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict

from .base_screen import BaseScreen
from src.cli.interactive.terminal import Key
from src.cli.integration.backend_integration import get_backend

logger = logging.getLogger(__name__)


class GladosChatScreen(BaseScreen):
    """Tela de chat minimalista com GLaDOS."""

    def __init__(self, terminal):
        super().__init__(terminal)

        self.title = "🤖 GLaDOS Chat"
        self.llm_bridge = get_backend().llm

        # Estado
        self.history: List[tuple[str, str, List[Dict]]] = []
        self.current_input = ""
        self.is_thinking = False

        # Renderização
        self.needs_redraw = True
        self.input_timeout = 0.1

        self.max_history = 50
        self.max_input_length = 200

    # ==========================================================
    # Loop principal
    # ==========================================================
    def show(self) -> Optional[str]:
        self.running = True
        self.terminal.clear_screen()

        while self.running:
            try:
                if self.needs_redraw:
                    self._draw()
                    self.needs_redraw = False

                key = self.terminal.get_key(self.input_timeout)
                if key:
                    result = self._handle_key(key)
                    if result:
                        return result

            except KeyboardInterrupt:
                return "back"
            except Exception:
                logger.exception("Erro na GladosChatScreen")
                self.needs_redraw = True

        return None

    # ==========================================================
    # Renderização
    # ==========================================================
    def _draw(self):
        width, height = self.terminal.get_size()
        self.terminal.clear()

        self._draw_header(width)
        self._draw_chat_area(width, height)
        self._draw_input_area(width, height)
        self._draw_footer(width, height)

        if self.is_thinking:
            self._draw_thinking_indicator(width, height)

        self.terminal.flush()

    def _draw_header(self, width: int):
        title = self.title
        x = max(0, (width - len(title)) // 2)
        self.terminal.print_at(x, 0, title, {"color": "accent", "bold": True})
        self.terminal.print_at(0, 1, "─" * width, {"color": "dim"})

    def _draw_chat_area(self, width: int, height: int):
        y = 2
        max_y = height - 5

        for question, answer, _ in self.history[-5:]:
            if y >= max_y:
                break

            self.terminal.print_at(
                1, y, f"> {question}"[:width - 2], {"color": "secondary"}
            )
            y += 1

            for line in answer.splitlines():
                if y >= max_y:
                    break
                self.terminal.print_at(
                    2, y, line[:width - 3], {"color": "primary"}
                )
                y += 1

            y += 1

    def _draw_input_area(self, width: int, height: int):
        prompt = "> "
        text = (prompt + self.current_input)[-(width - 2):]

        self.terminal.print_at(0, height - 3, "─" * width, {"color": "dim"})
        self.terminal.print_at(1, height - 2, text, {"color": "primary"})

    def _draw_footer(self, width: int, height: int):
        footer = "[ENTER Enviar] [ESC Voltar] [Q Dashboard]"
        x = max(0, (width - len(footer)) // 2)
        self.terminal.print_at(x, height - 1, footer, {"color": "dim"})

    def _draw_thinking_indicator(self, width: int, height: int):
        msg = "🤖 GLaDOS está pensando..."
        x = max(0, (width - len(msg)) // 2)
        y = height - 4
        self.terminal.print_at(x, y, msg, {"color": "warning", "bold": True})

    # ==========================================================
    # Input (CONFORME DOCUMENTAÇÃO)
    # ==========================================================
    def _handle_key(self, key) -> Optional[str]:

        # Navegação
        if key == Key.ESC:
            return "back"

        if key == Key.Q:
            return "goto:dashboard"

        # Enviar pergunta
        if key == Key.ENTER:
            if self.current_input.strip() and not self.is_thinking:
                self._process_query()
            return None

        # Backspace
        if key == Key.BACKSPACE:
            self.current_input = self.current_input[:-1]
            self.needs_redraw = True
            return None

        # INPUT DE TEXTO (FORMA CORRETA)
        if isinstance(key, tuple) and key[0] == Key.CHAR:
            char = key[1]
            if len(self.current_input) < self.max_input_length:
                self.current_input += char
                self.needs_redraw = True
            return None

        return None

    # ==========================================================
    # LLM
    # ==========================================================
    def _process_query(self):
        question = self.current_input.strip()
        self.current_input = ""
        self.is_thinking = True
        self.needs_redraw = True
        self._draw()

        try:
            response = self.llm_bridge.query_with_context(
                question=question,
                use_semantic=True,
                max_tokens=512
            )

            self.history.append((
                question,
                response.get("response", ""),
                response.get("sources", [])
            ))

            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

        except Exception as e:
            logger.exception("Erro LLM")
            self.history.append((question, f"Erro: {e}", []))

        finally:
            self.is_thinking = False
            self.needs_redraw = True
