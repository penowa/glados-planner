# src/core/llm/glados/personality/config.py
from pydantic import BaseModel
from typing import Dict

class GladosPersonalityConfig(BaseModel):
    user_name: str = "Helio"
    glados_name: str = "GLaDOS"
    personality_intensity: float = 0.7
    enable_sarcasm: bool = True
    
    class Config:
        from_attributes = True
