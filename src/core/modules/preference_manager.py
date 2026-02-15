"""
Sistema de aprendizado e persistência de preferências do usuário.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List
import json
import os


class PreferenceManager:
    def __init__(self, vault_path: str | None = None):
        if vault_path is None:
            try:
                from ...config.settings import settings
                vault_path = settings.paths.vault
            except Exception:
                vault_path = os.path.expanduser("~/Documentos/Obsidian/Philosophy_Vault")

        base = Path(vault_path).expanduser() / "06-RECURSOS"
        self.preferences_file = base / "preferences.json"
        self.history_file = base / "preferences_learning_history.json"
        self.learning_history: List[Dict[str, Any]] = self._load_history()

    def _load_preferences(self) -> Dict[str, Any]:
        if not self.preferences_file.exists():
            return {}
        try:
            with open(self.preferences_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_preferences(self, data: Dict[str, Any]) -> None:
        self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.preferences_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_history(self) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def _save_history(self) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.learning_history[-500:], f, indent=2, ensure_ascii=False)

    def get_all(self) -> Dict[str, Any]:
        """Retorna preferências completas."""
        return self._load_preferences()

    def update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza preferências e registra histórico básico."""
        current = self._load_preferences()
        merged = {**current, **(updates or {})}
        self._save_preferences(merged)
        self.learning_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "manual_update",
                "keys": sorted(list((updates or {}).keys())),
            }
        )
        self._save_history()
        return merged

    def detect_patterns(self) -> Dict[str, Any]:
        """
        Detecta padrões de produtividade a partir do histórico salvo.
        """
        if not self.learning_history:
            return {
                "patterns": [],
                "message": "Histórico insuficiente para detectar padrões.",
            }

        hour_scores: Dict[int, List[float]] = {}
        for entry in self.learning_history:
            ts = entry.get("timestamp")
            score = entry.get("score")
            if not ts or score is None:
                continue
            try:
                dt = datetime.fromisoformat(str(ts))
                hour_scores.setdefault(dt.hour, []).append(float(score))
            except Exception:
                continue

        ranked = sorted(
            (
                {
                    "hour": hour,
                    "avg_score": round(mean(scores), 3),
                    "samples": len(scores),
                }
                for hour, scores in hour_scores.items()
                if scores
            ),
            key=lambda x: x["avg_score"],
            reverse=True,
        )

        return {
            "patterns": ranked[:8],
            "sample_size": sum(item["samples"] for item in ranked),
        }

    def optimize_schedule(self, current_schedule: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reordena agenda priorizando horários historicamente melhores.
        """
        patterns = self.detect_patterns().get("patterns", [])
        if not patterns:
            return current_schedule

        hour_weight = {int(p["hour"]): float(p["avg_score"]) for p in patterns}

        def score(event: Dict[str, Any]) -> float:
            start = str(event.get("start", ""))
            try:
                hour = datetime.fromisoformat(start.replace("Z", "+00:00")).hour
            except Exception:
                return 0.0
            return hour_weight.get(hour, 0.0)

        return sorted(current_schedule, key=score, reverse=True)

    def adjust_difficulty_estimates(self) -> Dict[str, Any]:
        """
        Ajusta fator global de dificuldade baseado em feedback recente.
        """
        feedback = [
            float(entry.get("difficulty_delta"))
            for entry in self.learning_history[-200:]
            if entry.get("difficulty_delta") is not None
        ]

        if not feedback:
            return {"global_multiplier": 1.0, "samples": 0}

        avg_delta = mean(feedback)
        multiplier = max(0.7, min(1.4, 1.0 + avg_delta))
        result = {"global_multiplier": round(multiplier, 3), "samples": len(feedback)}

        prefs = self._load_preferences()
        learning_style = prefs.get("learning_style", {})
        learning_style["difficulty_multiplier"] = result["global_multiplier"]
        prefs["learning_style"] = learning_style
        self._save_preferences(prefs)

        return result
