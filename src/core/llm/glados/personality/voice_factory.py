"""Factory para seleção de personalidade do assistente."""
from __future__ import annotations

from typing import Optional

from .glados_voice import GladosVoice
from .marvin_voice import MarvinVoice

_VALID_PROFILES = {"auto", "glados", "marvin"}


def resolve_personality_profile(
    assistant_name: Optional[str] = None,
    profile: Optional[str] = None,
) -> str:
    """Resolve perfil final entre glados/marvin."""
    explicit = str(profile or "").strip().lower()
    if explicit in _VALID_PROFILES and explicit != "auto":
        return explicit

    normalized_name = str(assistant_name or "").strip().lower()
    marvin_markers = ("marvin", "paranoid android", "androide paranoide", "andróide paranóide")
    if any(marker in normalized_name for marker in marvin_markers):
        return "marvin"

    return "glados"


def create_personality_voice(
    user_name: str = "Helio",
    intensity: float = 0.7,
    assistant_name: Optional[str] = None,
    profile: Optional[str] = None,
):
    """Cria instância de personalidade mantendo compatibilidade com GladosVoice."""
    resolved_profile = resolve_personality_profile(
        assistant_name=assistant_name,
        profile=profile,
    )
    clean_assistant_name = str(assistant_name or "").strip()

    if resolved_profile == "marvin":
        return MarvinVoice(
            user_name=user_name,
            intensity=intensity,
            assistant_name=clean_assistant_name or "Marvin",
        )

    return GladosVoice(
        user_name=user_name,
        intensity=intensity,
        assistant_name=clean_assistant_name or "GLaDOS",
    )
