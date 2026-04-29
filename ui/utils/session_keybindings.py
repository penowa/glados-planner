"""
Definicoes compartilhadas para atalhos configuraveis da SessionView.
"""

from __future__ import annotations

from typing import Dict, List


SESSION_SHORTCUT_DEFINITIONS: List[dict[str, str]] = [
    {
        "id": "prev_pages",
        "label": "Paginas anteriores",
        "default": "Alt+Left",
        "handler": "_go_prev_pages",
    },
    {
        "id": "next_pages",
        "label": "Proximas paginas",
        "default": "Alt+Right",
        "handler": "_go_next_pages",
    },
    {
        "id": "toggle_search",
        "label": "Abrir busca",
        "default": "Slash",
        "handler": "_open_search_bar",
    },
    {
        "id": "toggle_notes",
        "label": "Abrir notas",
        "default": "Ctrl+M",
        "handler": "_open_note_tab",
    },
    {
        "id": "toggle_fullscreen",
        "label": "Alternar tela cheia",
        "default": "F11",
        "handler": "_toggle_fullscreen_mode",
    },
    {
        "id": "open_pdf",
        "label": "Abrir PDF no Zathura",
        "default": "Ctrl+J",
        "handler": "_open_current_pdf_session",
    },
    {
        "id": "pomodoro_start",
        "label": "Pomodoro iniciar",
        "default": "Ctrl+Alt+P",
        "handler": "_start_pomodoro",
    },
    {
        "id": "pomodoro_pause",
        "label": "Pomodoro pausar",
        "default": "Ctrl+Alt+Space",
        "handler": "_pause_pomodoro",
    },
    {
        "id": "end_session",
        "label": "Encerrar sessao",
        "default": "Ctrl+Alt+W",
        "handler": "_on_end_session_clicked",
    },
    {
        "id": "fullscreen_left",
        "label": "Tela cheia: esquerda",
        "default": "Left",
        "handler": "_on_fullscreen_left",
    },
    {
        "id": "fullscreen_right",
        "label": "Tela cheia: direita",
        "default": "Right",
        "handler": "_on_fullscreen_right",
    },
    {
        "id": "fullscreen_up",
        "label": "Tela cheia: cima",
        "default": "Up",
        "handler": "_on_fullscreen_up",
    },
    {
        "id": "fullscreen_down",
        "label": "Tela cheia: baixo",
        "default": "Down",
        "handler": "_on_fullscreen_down",
    },
    {
        "id": "fullscreen_escape",
        "label": "Tela cheia: sair",
        "default": "Escape",
        "handler": "_on_fullscreen_escape",
    },
]


def default_session_shortcuts() -> Dict[str, str]:
    return {item["id"]: item["default"] for item in SESSION_SHORTCUT_DEFINITIONS}
