from types import SimpleNamespace
from pathlib import Path

from ui.utils.book_helpers import find_book_directory, find_cover_file, load_book_note_properties


def test_book_helpers_find_book_directory_and_metadata(tmp_path):
    vault_root = tmp_path / "vault"
    book_dir = vault_root / "01-LEITURAS" / "Test Author" / "Test Book"
    book_dir.mkdir(parents=True)

    cover_file = book_dir / "cover.png"
    cover_file.write_bytes(b"PNG\r\n\x1a\n")

    completo_note = book_dir / "Test Book - Completo.md"
    completo_note.write_text(
        "---\n"
        "title: Test Book\n"
        "author: Test Author\n"
        "book_id: book-123\n"
        "isbn: 9781234567890\n"
        "total_pages: 320\n"
        "---\n"
        "Conteúdo do livro.\n",
        encoding="utf-8",
    )

    reading_manager = SimpleNamespace(vault_path=str(vault_root), readings={})

    resolved_dir = find_book_directory(reading_manager, "book-123")
    assert resolved_dir is not None
    assert Path(resolved_dir) == book_dir

    cover_path = find_cover_file(book_dir)
    assert cover_path is not None
    assert Path(cover_path) == cover_file

    props = load_book_note_properties(book_dir, book_id="book-123")
    assert props["title"] == "Test Book"
    assert props["author"] == "Test Author"
    assert props["book_id"] == "book-123"
    assert props["isbn"] == "9781234567890"
    assert props["total_pages"] == 320


def test_book_helpers_find_book_directory_by_title_author(tmp_path):
    vault_root = tmp_path / "vault"
    book_dir = vault_root / "01-LEITURAS" / "Test Author" / "Test Book"
    book_dir.mkdir(parents=True)

    cover_file = book_dir / "cover.png"
    cover_file.write_bytes(b"PNG\r\n\x1a\n")

    completo_note = book_dir / "Test Book - Completo.md"
    completo_note.write_text(
        "---\n"
        "title: Test Book\n"
        "author: Test Author\n"
        "isbn: 9781234567890\n"
        "total_pages: 320\n"
        "---\n"
        "Conteúdo do livro.\n",
        encoding="utf-8",
    )

    reading_manager = SimpleNamespace(vault_path=str(vault_root), readings={})

    resolved_dir = find_book_directory(reading_manager, "", title="Test Book", author="Test Author")
    assert resolved_dir is not None
    assert Path(resolved_dir) == book_dir
