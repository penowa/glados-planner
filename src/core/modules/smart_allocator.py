"""
Algoritmos inteligentes de alocação.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List
import re


class SmartAllocator:
    @staticmethod
    def allocate_time(book: Dict[str, Any], available_slots: List[Dict[str, Any]], user_preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Aloca sessões de leitura em slots disponíveis com heurística de qualidade.
        """
        total_pages = int(book.get("total_pages", 0) or 0)
        current_page = int(book.get("current_page", 0) or 0)
        remaining = max(0, total_pages - current_page)
        if remaining <= 0:
            return []

        reading_speed = float(user_preferences.get("reading_speed_pages_hour", 10.0) or 10.0)
        pages_per_minute = max(0.05, reading_speed / 60.0)
        target_pages_per_session = int(user_preferences.get("target_pages_per_session", 20) or 20)

        allocations: List[Dict[str, Any]] = []
        sorted_slots = sorted(
            available_slots,
            key=lambda s: float(s.get("quality_score", 0.5)),
            reverse=True,
        )

        for slot in sorted_slots:
            if remaining <= 0:
                break
            duration = int(slot.get("duration_minutes", 0) or 0)
            if duration < 25:
                continue
            alloc_pages = max(5, min(remaining, int(duration * pages_per_minute), target_pages_per_session))
            allocations.append(
                {
                    "start": slot.get("start"),
                    "end": slot.get("end"),
                    "duration_minutes": duration,
                    "pages": alloc_pages,
                    "quality_score": float(slot.get("quality_score", 0.5)),
                }
            )
            remaining -= alloc_pages

        return allocations

    @staticmethod
    def select_review_slots(
        available_slots: List[Dict[str, Any]],
        sessions_per_day: int,
        session_duration_minutes: int,
    ) -> List[Dict[str, Any]]:
        """
        Seleciona os melhores slots para revisão em um dia.

        Critérios:
        - Prioriza maior `quality_score`
        - Garante duração mínima da sessão
        - Evita sobreposição entre slots selecionados
        """
        target_sessions = max(1, int(sessions_per_day or 1))
        target_duration = max(15, int(session_duration_minutes or 30))

        sorted_slots = sorted(
            available_slots or [],
            key=lambda s: (
                float(s.get("quality_score", 0.5) or 0.5),
                str(s.get("start") or ""),
            ),
            reverse=True,
        )

        selected: List[Dict[str, Any]] = []
        occupied_ranges: List[tuple[datetime, datetime]] = []

        for slot in sorted_slots:
            if len(selected) >= target_sessions:
                break

            start_str = str(slot.get("start") or "").strip()
            end_str = str(slot.get("end") or "").strip()
            if not start_str or not end_str:
                continue

            start_dt = SmartAllocator._parse_dt(start_str)
            end_dt = SmartAllocator._parse_dt(end_str)
            if not start_dt or not end_dt or end_dt <= start_dt:
                continue

            slot_duration = int((end_dt - start_dt).total_seconds() // 60)
            if slot_duration < target_duration:
                continue

            # Trunca o slot ao tamanho desejado da sessão.
            alloc_end_dt = start_dt + timedelta(minutes=target_duration)

            has_overlap = False
            for occ_start, occ_end in occupied_ranges:
                if start_dt < occ_end and alloc_end_dt > occ_start:
                    has_overlap = True
                    break
            if has_overlap:
                continue

            selected.append(
                {
                    "start": start_dt.strftime("%Y-%m-%d %H:%M"),
                    "end": alloc_end_dt.strftime("%Y-%m-%d %H:%M"),
                    "duration_minutes": target_duration,
                    "quality_score": float(slot.get("quality_score", 0.5) or 0.5),
                }
            )
            occupied_ranges.append((start_dt, alloc_end_dt))

        selected.sort(key=lambda slot: slot.get("start", ""))
        return selected

    @staticmethod
    def estimate_difficulty(text_chunk: str, user_history: Dict[str, Any]) -> float:
        """
        Estima dificuldade (0.0 - 1.0) por complexidade lexical + fator histórico.
        """
        text = (text_chunk or "").strip()
        if not text:
            return 0.0

        words = re.findall(r"\w+", text, flags=re.UNICODE)
        if not words:
            return 0.0

        avg_word_len = sum(len(w) for w in words) / len(words)
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        sentence_count = max(1, len(re.findall(r"[.!?]+", text)))
        words_per_sentence = len(words) / sentence_count

        lexical_score = min(1.0, (avg_word_len / 10.0) * 0.45 + unique_ratio * 0.25 + (words_per_sentence / 40.0) * 0.30)

        user_factor = float(user_history.get("difficulty_multiplier", 1.0) or 1.0)
        score = lexical_score * user_factor
        return max(0.0, min(1.0, round(score, 4)))

    @staticmethod
    def generate_review_schedule(book_id: str, retention_data: Dict[str, Any], goal: str) -> List[Dict[str, Any]]:
        """
        Gera plano de revisão espaçada simples.
        """
        now = datetime.now()
        base_intervals = [1, 3, 7, 14, 30]

        retention = float(retention_data.get("retention_score", 0.65) or 0.65)
        if retention < 0.5:
            intervals = [1, 2, 4, 7, 14]
        elif retention > 0.8:
            intervals = [2, 5, 10, 21, 45]
        else:
            intervals = base_intervals

        goal_lower = str(goal or "").lower()
        duration = 45 if "profund" in goal_lower or "prova" in goal_lower else 30

        plan = []
        for i, days in enumerate(intervals, start=1):
            start_dt = now + timedelta(days=days)
            start_dt = start_dt.replace(hour=9, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(minutes=duration)
            plan.append(
                {
                    "book_id": book_id,
                    "session": i,
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "goal": goal,
                    "interval_days": days,
                }
            )

        return plan

    @staticmethod
    def _parse_dt(value: str) -> datetime | None:
        raw = str(value or "").strip().replace("Z", "+00:00")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass

        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None
