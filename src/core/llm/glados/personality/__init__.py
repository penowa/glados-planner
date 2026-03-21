"""Personalidades disponíveis para o assistente."""

from .glados_voice import GladosVoice
from .marvin_voice import MarvinVoice
from .voice_factory import create_personality_voice, resolve_personality_profile

__all__ = [
    "GladosVoice",
    "MarvinVoice",
    "create_personality_voice",
    "resolve_personality_profile",
]
