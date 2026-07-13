import sys
import pytest
from datetime import datetime, timedelta


try:
    from PyQt6.QtWidgets import QApplication
    from ui.widgets.cards.dynamic_event_card import DynamicEventCard
except Exception:
    QApplication = None
    DynamicEventCard = None


class FakeAgendaBackend:
    def __init__(self, events_by_day):
        self._events = events_by_day

    def get_day_events(self, date_str):
        return self._events.get(date_str, [])


@pytest.mark.skipif(DynamicEventCard is None, reason="PyQt6 or module missing")
def test_dynamic_card_detects_leitura(qtbot):
    now = datetime.now()
    ev = {'id': 'e1', 'title': 'Leitura', 'type': 'leitura', 'start': (now + timedelta(minutes=5)).isoformat()}
    day = now.strftime('%Y-%m-%d')
    backend = FakeAgendaBackend({day: [ev]})
    app = QApplication.instance() or QApplication(sys.argv)
    card = DynamicEventCard(agenda_backend=backend, reading_controller=None, book_controller=None, daily_checkin_controller=None, vault_controller=None)
    card._update_state()
    assert card._current_state == 'leitura'


@pytest.mark.skipif(DynamicEventCard is None, reason="PyQt6 or module missing")
def test_dynamic_card_detects_aula(qtbot):
    now = datetime.now()
    ev = {'id': 'e2', 'title': 'Aula', 'type': 'aula', 'start': (now + timedelta(minutes=10)).isoformat(), 'discipline': 'Math'}
    day = now.strftime('%Y-%m-%d')
    backend = FakeAgendaBackend({day: [ev]})
    app = QApplication.instance() or QApplication(sys.argv)
    card = DynamicEventCard(agenda_backend=backend, reading_controller=None, book_controller=None, daily_checkin_controller=None, vault_controller=None)
    card._update_state()
    assert card._current_state == 'aula'


@pytest.mark.skipif(DynamicEventCard is None, reason="PyQt6 or module missing")
def test_dynamic_card_ongoing_aula(qtbot):
    now = datetime.now()
    ev = {
        'id': 'e3',
        'title': 'Aula contínua',
        'type': 'aula',
        'start': (now - timedelta(hours=1)).isoformat(),
        'end': (now + timedelta(hours=1)).isoformat(),
        'discipline': 'Math'
    }
    day = now.strftime('%Y-%m-%d')
    backend = FakeAgendaBackend({day: [ev]})
    app = QApplication.instance() or QApplication(sys.argv)
    card = DynamicEventCard(agenda_backend=backend, reading_controller=None, book_controller=None, daily_checkin_controller=None, vault_controller=None)
    card._update_state()
    assert card._current_state == 'aula'


@pytest.mark.skipif(DynamicEventCard is None, reason="PyQt6 or module missing")
def test_dynamic_card_ongoing_leitura(qtbot):
    now = datetime.now()
    ev = {
        'id': 'e4',
        'title': 'Leitura contínua',
        'type': 'leitura',
        'start': (now - timedelta(minutes=30)).isoformat(),
        'end': (now + timedelta(minutes=30)).isoformat(),
        'metadata': {'book_id': 'test-book'}
    }
    day = now.strftime('%Y-%m-%d')
    backend = FakeAgendaBackend({day: [ev]})
    app = QApplication.instance() or QApplication(sys.argv)
    card = DynamicEventCard(agenda_backend=backend, reading_controller=None, book_controller=None, daily_checkin_controller=None, vault_controller=None)
    card._update_state()
    assert card._current_state == 'leitura'


@pytest.mark.skipif(DynamicEventCard is None, reason="PyQt6 or module missing")
def test_dynamic_card_base_when_no_upcoming(qtbot):
    now = datetime.now()
    day = now.strftime('%Y-%m-%d')
    backend = FakeAgendaBackend({day: []})
    app = QApplication.instance() or QApplication(sys.argv)
    card = DynamicEventCard(agenda_backend=backend, reading_controller=None, book_controller=None, daily_checkin_controller=None, vault_controller=None)
    card._update_state()
    assert card._current_state == 'base'
