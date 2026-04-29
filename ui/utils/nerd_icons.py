"""Helpers para usar glifos Nerd Font de forma consistente na UI."""
from __future__ import annotations

from PyQt6.QtGui import QFont

NERD_FONT_FAMILIES = (
    "FiraCode Nerd Font Propo",
    "FiraCode Nerd Font",
    "FantasqueSansM Nerd Font Propo",
    "FantasqueSansM Nerd Font",
    "Symbols Nerd Font Mono",
)

LEGACY_BOOK_NOTE_PREFIXES = ("\U0001F4D6", "\U0001F4DA")
LEGACY_BOOK_FILE_PATTERNS = tuple(f"{prefix} *.md" for prefix in LEGACY_BOOK_NOTE_PREFIXES)
LEGACY_LINK_ICON = "\U0001F517"


def nerd_font(point_size: int, *, weight: int | QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont()
    font.setFamilies(list(NERD_FONT_FAMILIES))
    font.setPointSize(int(point_size))
    font.setWeight(weight)
    return font


class NerdIcons:
    BOOK = ""
    BULLHORN = ""
    CALENDAR = ""
    CHAT = ""
    COFFEE = ""
    COMPASS = ""
    CUTLERY = ""
    ERROR = ""
    FLASK = ""
    FULLSCREEN = ""
    FULLSCREEN_EXIT = ""
    GRADUATION = ""
    LINK = ""
    MENU = ""
    MOON = ""
    NEWSPAPER = ""
    NOTE = ""
    PIN = ""
    PLUS = ""
    REFRESH = ""
    SEARCH = ""
    SEND = ""
    SETTINGS = ""
    SUCCESS = ""
    SUN = ""
    TARGET = ""
    USERS = ""
    USER = ""
    WARNING = ""
    BED = ""
