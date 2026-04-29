from __future__ import annotations

import importlib.util
import sys
import types
import uuid
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MODULES_DIR = ROOT_DIR / "src" / "core" / "modules"


def _load_agenda_manager_class():
    package_name = f"_agenda_manager_testpkg_{uuid.uuid4().hex}"
    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(MODULES_DIR)]
    sys.modules[package_name] = package_module

    reading_module = types.ModuleType(f"{package_name}.reading_manager")

    class ReadingManager:
        def __init__(self, _vault_path: str | None = None):
            self.progress: dict[str, dict] = {}

        def get_reading_progress(self, book_id: str | None = None):
            if book_id is None:
                return dict(self.progress)
            return dict(self.progress.get(book_id, {}))

    reading_module.ReadingManager = ReadingManager
    sys.modules[reading_module.__name__] = reading_module

    review_module = types.ModuleType(f"{package_name}.review_system")

    class ReviewSystem:
        def __init__(self, _vault_path: str | None = None):
            pass

        def generate_flashcards(self, **_kwargs):
            return []

    review_module.ReviewSystem = ReviewSystem
    sys.modules[review_module.__name__] = review_module

    allocator_module = types.ModuleType(f"{package_name}.smart_allocator")

    class SmartAllocator:
        @staticmethod
        def select_review_slots(*_args, **_kwargs):
            return []

        @staticmethod
        def redistribute_events(*_args, **_kwargs):
            return {"placements": [], "unscheduled": []}

    allocator_module.SmartAllocator = SmartAllocator
    sys.modules[allocator_module.__name__] = allocator_module

    pomodoro_module = types.ModuleType(f"{package_name}.pomodoro_timer")

    class PomodoroTimer:
        def __init__(self, *_args, **_kwargs):
            pass

    pomodoro_module.PomodoroTimer = PomodoroTimer
    sys.modules[pomodoro_module.__name__] = pomodoro_module

    writing_module = types.ModuleType(f"{package_name}.writing_assistant")

    class WritingAssistant:
        def __init__(self, _vault_path: str | None = None):
            pass

    writing_module.WritingAssistant = WritingAssistant
    sys.modules[writing_module.__name__] = writing_module

    agenda_path = MODULES_DIR / "agenda_manager.py"
    spec = importlib.util.spec_from_file_location(f"{package_name}.agenda_manager", agenda_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.AgendaManager


def _load_preference_manager_class():
    spec = importlib.util.spec_from_file_location(
        f"_preference_manager_test_{uuid.uuid4().hex}",
        MODULES_DIR / "preference_manager.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.PreferenceManager


def _overlaps(start: datetime, end: datetime, blocked_start: datetime, blocked_end: datetime) -> bool:
    return start < blocked_end and end > blocked_start


def test_find_free_slots_respects_classes_and_protected_meal_windows(tmp_path: Path):
    agenda_manager_cls = _load_agenda_manager_class()
    manager = agenda_manager_cls(str(tmp_path))

    manager.add_event(
        title="Aula de Ética",
        start="2026-04-23 14:00",
        end="2026-04-23 18:00",
        event_type="aula",
    )

    slots = manager.find_free_slots("2026-04-23", duration_minutes=60, start_hour=8, end_hour=22)

    assert slots
    lunch_start = datetime(2026, 4, 23, 11, 0)
    lunch_end = datetime(2026, 4, 23, 14, 0)
    class_start = datetime(2026, 4, 23, 14, 0)
    class_end = datetime(2026, 4, 23, 18, 0)
    dinner_start = datetime(2026, 4, 23, 18, 0)
    dinner_end = datetime(2026, 4, 23, 20, 0)

    for slot in slots:
        start = datetime.fromisoformat(str(slot["start"]).replace(" ", "T"))
        end = datetime.fromisoformat(str(slot["end"]).replace(" ", "T"))
        assert not _overlaps(start, end, lunch_start, lunch_end)
        assert not _overlaps(start, end, class_start, class_end)
        assert not _overlaps(start, end, dinner_start, dinner_end)


def test_allocate_reading_time_never_places_reading_inside_reserved_blocks(tmp_path: Path):
    agenda_manager_cls = _load_agenda_manager_class()
    manager = agenda_manager_cls(str(tmp_path))
    manager.reading_manager.progress["book-1"] = {
        "title": "Fenomenologia",
        "discipline": "Filosofia",
        "total_pages": 120,
        "current_page": 0,
    }
    manager.add_event(
        title="Aula de Fenomenologia",
        start="2026-04-23 14:00",
        end="2026-04-23 18:00",
        event_type="aula",
    )

    result = manager.allocate_reading_time(
        book_id="book-1",
        pages_per_day=10,
        reading_speed=20.0,
        strategy="balanced",
        start_date="2026-04-23",
        deadline="2026-04-23",
    )

    assert result.get("success") is True
    reading_events = [
        event for event in manager.get_day_events("2026-04-23")
        if event.type.value == "leitura"
    ]
    assert reading_events

    blocked_ranges = [
        (datetime(2026, 4, 23, 11, 0), datetime(2026, 4, 23, 14, 0)),
        (datetime(2026, 4, 23, 14, 0), datetime(2026, 4, 23, 18, 0)),
        (datetime(2026, 4, 23, 18, 0), datetime(2026, 4, 23, 20, 0)),
    ]
    for event in reading_events:
        for blocked_start, blocked_end in blocked_ranges:
            assert not _overlaps(event.start, event.end, blocked_start, blocked_end)


def test_preference_manager_includes_default_protected_time_blocks(tmp_path: Path):
    preference_manager_cls = _load_preference_manager_class()
    manager = preference_manager_cls(str(tmp_path))

    preferences = manager.get_all()

    blocks = preferences.get("protected_time_blocks")
    assert isinstance(blocks, list)
    assert any(block.get("start") == "11:00" and block.get("end") == "14:00" for block in blocks)
    assert any(block.get("start") == "18:00" and block.get("end") == "20:00" for block in blocks)


def test_auto_complete_past_events_marks_event_completed_and_hides_it_from_day_view(tmp_path: Path):
    agenda_manager_cls = _load_agenda_manager_class()
    manager = agenda_manager_cls(str(tmp_path))

    completed_event_id = manager.add_event(
        title="Seminário já encerrado",
        start="2099-04-23 09:00",
        end="2099-04-23 10:00",
        event_type="seminario",
    )
    remaining_event_id = manager.add_event(
        title="Leitura da tarde",
        start="2099-04-23 12:00",
        end="2099-04-23 13:00",
        event_type="leitura",
    )

    updated_ids = manager.auto_complete_past_events(reference_time=datetime(2099, 4, 23, 10, 30))

    assert completed_event_id in updated_ids
    assert manager.events[completed_event_id].completed is True
    assert manager.events[remaining_event_id].completed is False

    visible_ids = {event.id for event in manager.get_day_events("2099-04-23")}
    assert completed_event_id not in visible_ids
    assert remaining_event_id in visible_ids

    reloaded_manager = agenda_manager_cls(str(tmp_path))
    assert reloaded_manager.events[completed_event_id].completed is True
    assert reloaded_manager.events[remaining_event_id].completed is False
