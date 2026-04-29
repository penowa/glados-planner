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
    def redistribute_events(
        events: List[Dict[str, Any]],
        available_slots: List[Dict[str, Any]],
        user_preferences: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Redistribui eventos em slots livres com heurística de qualidade/proximidade.

        Args:
            events: lista de eventos flexíveis
            available_slots: slots livres já calculados
            user_preferences: preferências opcionais do usuário

        Returns:
            dict com `placements` e `unscheduled`
        """
        preferences = user_preferences or {}
        slots: List[Dict[str, Any]] = []
        existing_day_load_minutes = {
            str(key): int(value or 0)
            for key, value in (preferences.get("existing_day_load_minutes", {}) or {}).items()
        }
        day_load_minutes = dict(existing_day_load_minutes)
        max_daily_minutes = max(60, int(preferences.get("max_daily_minutes", 360) or 360))
        spread_bonus = float(preferences.get("spread_bonus", 0.22) or 0.22)
        same_day_bonus = float(preferences.get("same_day_bonus", 0.02) or 0.02)
        proximity_penalty_per_day = float(preferences.get("proximity_penalty_per_day", 0.01) or 0.01)

        candidate_days = {
            SmartAllocator._parse_dt(str(slot.get("start") or "")).date().isoformat()
            for slot in available_slots or []
            if SmartAllocator._parse_dt(str(slot.get("start") or ""))
        }
        movable_total_minutes = sum(max(15, int(event.get("duration_minutes", 30) or 30)) for event in (events or []))
        existing_total_minutes = sum(day_load_minutes.values())
        effective_day_count = max(1, len(candidate_days))
        target_daily_minutes = int(
            preferences.get(
                "target_daily_minutes",
                max(60, min(max_daily_minutes, round((existing_total_minutes + movable_total_minutes) / effective_day_count))),
            ) or 60
        )

        for slot in available_slots or []:
            start_dt = SmartAllocator._parse_dt(str(slot.get("start") or ""))
            end_dt = SmartAllocator._parse_dt(str(slot.get("end") or ""))
            if not start_dt or not end_dt or end_dt <= start_dt:
                continue
            slots.append(
                {
                    "start": start_dt,
                    "end": end_dt,
                    "quality_score": float(slot.get("quality_score", 0.5) or 0.5),
                }
            )

        ranked_events = sorted(
            events or [],
            key=lambda event: (
                -int(event.get("priority", 1) or 1),
                str(event.get("deadline") or "9999-12-31"),
                str(event.get("start") or ""),
            ),
        )

        placements: List[Dict[str, Any]] = []
        unscheduled: List[Dict[str, Any]] = []

        for event in ranked_events:
            duration = max(15, int(event.get("duration_minutes", 30) or 30))
            original_start = SmartAllocator._parse_dt(str(event.get("start") or ""))
            deadline_dt = SmartAllocator._parse_dt(str(event.get("deadline") or ""))
            best_idx = -1
            best_score = float("-inf")

            for idx, slot in enumerate(slots):
                slot_start = slot["start"]
                slot_end = slot["end"]
                slot_duration = int((slot_end - slot_start).total_seconds() // 60)
                if slot_duration < duration:
                    continue
                if deadline_dt and slot_start.date() > deadline_dt.date():
                    continue

                score = float(slot.get("quality_score", 0.5) or 0.5)
                day_key = slot_start.date().isoformat()
                current_day_load = int(day_load_minutes.get(day_key, 0) or 0)
                if original_start:
                    day_diff = abs((slot_start.date() - original_start.date()).days)
                    score -= min(0.16, day_diff * proximity_penalty_per_day)
                    if slot_start.date() == original_start.date():
                        score += same_day_bonus
                    if slot_start.weekday() == original_start.weekday():
                        score += 0.01

                if current_day_load <= 0:
                    score += spread_bonus
                else:
                    load_ratio = current_day_load / max(1, target_daily_minutes)
                    score -= min(0.45, load_ratio * 0.18)

                projected_ratio = (current_day_load + duration) / max(1, max_daily_minutes)
                if projected_ratio > 1.0:
                    score -= min(0.60, (projected_ratio - 1.0) * 0.8)
                elif projected_ratio < 0.65:
                    score += min(0.12, (0.65 - projected_ratio) * 0.2)

                preferred_time = str(event.get("preferred_time") or "").strip().lower()
                if preferred_time:
                    hour = slot_start.hour
                    if ("manhã" in preferred_time or "manha" in preferred_time) and 8 <= hour < 12:
                        score += 0.08
                    elif "tarde" in preferred_time and 14 <= hour < 18:
                        score += 0.08
                    elif "noite" in preferred_time and 19 <= hour < 22:
                        score += 0.08

                if slot_start.weekday() >= 5:
                    weekend_bias = float(
                        preferences.get("weekend_bias", 0.92 if str(event.get("type") or "") == "leitura" else 0.96)
                    )
                    score *= weekend_bias

                score += min(0.10, int(event.get("priority", 1) or 1) * 0.02)
                if score > best_score:
                    best_score = score
                    best_idx = idx

            if best_idx < 0:
                unscheduled.append(dict(event))
                continue

            chosen = slots.pop(best_idx)
            alloc_start = chosen["start"]
            alloc_end = alloc_start + timedelta(minutes=duration)
            placements.append(
                {
                    "event_id": event.get("event_id"),
                    "start": alloc_start.isoformat(),
                    "end": alloc_end.isoformat(),
                    "quality_score": round(best_score, 4),
                }
            )
            day_load_minutes[alloc_start.date().isoformat()] = (
                int(day_load_minutes.get(alloc_start.date().isoformat(), 0) or 0) + duration
            )

            if alloc_end < chosen["end"]:
                slots.append(
                    {
                        "start": alloc_end,
                        "end": chosen["end"],
                        "quality_score": float(chosen.get("quality_score", 0.5) or 0.5),
                    }
                )

        placements.sort(key=lambda item: str(item.get("start") or ""))
        unscheduled.sort(key=lambda item: str(item.get("start") or ""))
        return {"placements": placements, "unscheduled": unscheduled}

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
