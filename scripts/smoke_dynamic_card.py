"""Smoke test to visualize DynamicEventCard with fake controllers and a processed book.

Run: python scripts/smoke_dynamic_card.py
"""
import sys
import os
import json
import base64
from pathlib import Path

# Ensure project root is on sys.path so `ui` package imports work when running script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from datetime import datetime, timedelta

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

# Inject lightweight ui.utils.nerd_icons and ui.utils.book_helpers to avoid heavy imports
import types
nerd_mod = types.ModuleType('ui.utils.nerd_icons')
class _NI:
    CALENDAR = '📅'
    COFFEE = '☕'
    SUN = '☀️'
    MOON = '🌙'
    WARNING = '⚠️'
    FLASK = '🔬'
    PLUS = '+'
    NOTE = '📝'
    REFRESH = '🔁'

def _nerd_font(size, weight=None):
    try:
        f = QFont()
        f.setPointSize(int(size))
        return f
    except Exception:
        return None

nerd_mod.NerdIcons = _NI
nerd_mod.nerd_font = _nerd_font
sys.modules['ui.utils.nerd_icons'] = nerd_mod

bh_mod = types.ModuleType('ui.utils.book_helpers')
def _find_cover_file(book_dir):
    p = Path(book_dir)
    for name in ('cover.png','cover.jpg'):
        fp = p / name
        if fp.exists():
            return str(fp)
    for fp in p.iterdir():
        if fp.suffix.lower() in ('.png','.jpg','.jpeg'):
            return str(fp)
    return None

def _load_discipline_books(vault_root, discipline):
    vault = Path(vault_root)
    res = []
    base = vault / '01-LEITURAS'
    if base.exists():
        for author in base.iterdir():
            if author.is_dir():
                for book in author.iterdir():
                    if book.is_dir():
                        res.append({'title': book.name, 'work_dir_abs': str(book), 'cover_path': _find_cover_file(book)})
    return res

bh_mod.find_cover_file = _find_cover_file
bh_mod.load_discipline_books = _load_discipline_books
sys.modules['ui.utils.book_helpers'] = bh_mod

import importlib.util
spec = importlib.util.spec_from_file_location('dynamic_event_card_test', ROOT / 'ui' / 'widgets' / 'cards' / 'dynamic_event_card.py')
dynamic_mod = importlib.util.module_from_spec(spec)
sys.modules['dynamic_event_card_test'] = dynamic_mod
spec.loader.exec_module(dynamic_mod)
DynamicEventCard = dynamic_mod.DynamicEventCard


PNG_1x1_BASE64 = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
)


class FakeReadingManager:
    def __init__(self, vault_path):
        self.vault_path = str(vault_path)

    def get_reading_progress(self, book_id=None):
        # If book_id provided, return dict else list
        if book_id:
            return {
                'book_id': book_id,
                'title': 'Test Book',
                'author': 'Author Example',
                'total_pages': 320,
                'current_page': 45,
                'cover': str(Path(self.vault_path) / '01-LEITURAS' / 'Author' / 'Test Book' / 'cover.png')
            }
        # summary list
        now = datetime.now()
        return [
            {'book_id': 'test-book', 'duration_minutes': 120, 'last_read': (now - timedelta(days=1)).isoformat()},
        ]


class FakeReadingController:
    def __init__(self, vault_path):
        self.reading_manager = FakeReadingManager(vault_path)


class FakeAgendaBackend:
    def __init__(self):
        now = datetime.now()
        self.today = now.strftime('%Y-%m-%d')

    def get_day_events(self, date_str):
        if date_str != self.today:
            return []
        now = datetime.now()
        return [
            {
                'id': 'e-aula',
                'title': 'Aula de Física',
                'type': 'aula',
                'start': (now + timedelta(minutes=5)).isoformat(),
                'end': (now + timedelta(minutes=65)).isoformat(),
                'discipline': 'Física',
                'metadata': {},
            },
            {
                'id': 'e-leitura',
                'title': 'Leitura: Capítulo 3',
                'type': 'leitura',
                'start': (now + timedelta(minutes=10)).isoformat(),
                'end': (now + timedelta(minutes=40)).isoformat(),
                'metadata': {'book_id': 'test-book', 'pages_planned': 20},
            }
        ]


class FakeDailyCheckinController:
    def get_checkins(self):
        now = datetime.now()
        return [
            {'timestamp': (now - timedelta(days=i)).isoformat(), 'mood_score': 4.0 + (i % 2) * 0.5}
            for i in range(1, 6)
        ]


def ensure_test_vault(root: Path):
    book_dir = root / '01-LEITURAS' / 'Author' / 'Test Book'
    book_dir.mkdir(parents=True, exist_ok=True)
    # write metadata
    meta = {'title': 'Test Book', 'author': 'Author Example'}
    with open(book_dir / 'metadata.json', 'w', encoding='utf8') as f:
        json.dump(meta, f)
    # write a simple generated cover using QPixmap to avoid corrupted pngs
    cover_path = book_dir / 'cover.png'
    try:
        from PyQt6.QtGui import QPixmap, QColor
        pix = QPixmap(120, 160)
        pix.fill(QColor('#4477AA'))
        pix.save(str(cover_path), 'PNG')
    except Exception:
        # fallback to base64 write if Qt save not available
        with open(cover_path, 'wb') as f:
            f.write(base64.b64decode(PNG_1x1_BASE64))
    return book_dir


def main():
    app = QApplication(sys.argv)

    repo_root = Path(__file__).resolve().parents[1]
    vault_root = repo_root / 'data' / 'test_vault'
    ensure_test_vault(vault_root)

    agenda = FakeAgendaBackend()
    reading = FakeReadingController(vault_root)
    daily = FakeDailyCheckinController()
    vault = type('V', (), {'vault_path': str(vault_root)})()

    card = DynamicEventCard(
        agenda_backend=agenda,
        reading_controller=reading,
        book_controller=None,
        daily_checkin_controller=daily,
        vault_controller=vault,
    )

    card.open_session.connect(lambda payload: print('open_session', payload))
    card.open_class_notes.connect(lambda ev: print('open_class_notes', ev.get('id')))
    card.open_discipline_chat.connect(lambda d: print('open_discipline_chat', d))

    card.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
