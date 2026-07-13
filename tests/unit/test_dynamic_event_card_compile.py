import py_compile
import pathlib


def test_compile_dynamic_card():
    base = pathlib.Path(__file__).resolve().parents[2]
    files = [
        base / 'ui' / 'widgets' / 'cards' / 'dynamic_event_card.py',
        base / 'ui' / 'utils' / 'book_helpers.py',
    ]
    for f in files:
        py_compile.compile(str(f), doraise=True)
