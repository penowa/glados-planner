from datetime import datetime
from pathlib import Path

from ui.utils.class_notes import (
    ANNOTATIONS_HEADER,
    build_class_note_content,
    build_class_note_relative_path,
    load_discipline_works,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_discipline_works_collects_primary_and_related_notes(tmp_path: Path):
    vault_root = tmp_path
    discipline_note = vault_root / "05-DISCIPLINAS" / "etica.md"
    primary = vault_root / "01-LEITURAS" / "Autor" / "Obra" / "📖 Obra.md"
    chapter = vault_root / "01-LEITURAS" / "Autor" / "Obra" / "Capitulo 1.md"

    _write(
        discipline_note,
        "# Disciplina: Ética\n\n## Obras\n- [[01-LEITURAS/Autor/Obra/📖 Obra|Obra]]\n",
    )
    _write(
        primary,
        "---\nbook_id: obra-1\ntype: book\n---\n\n# Obra\n",
    )
    _write(chapter, "# Capítulo 1\n")

    works = load_discipline_works(vault_root, "Ética")

    assert len(works) == 1
    assert works[0].title == "Obra"
    assert works[0].primary_target == "01-LEITURAS/Autor/Obra/📖 Obra"
    assert works[0].note_targets == ("01-LEITURAS/Autor/Obra/Capitulo 1",)


def test_build_class_note_content_preserves_existing_annotations(tmp_path: Path):
    vault_root = tmp_path
    discipline_note = vault_root / "05-DISCIPLINAS" / "etica.md"
    primary = vault_root / "01-LEITURAS" / "Autor" / "Obra" / "📖 Obra.md"
    chapter = vault_root / "01-LEITURAS" / "Autor" / "Obra" / "Capitulo 1.md"
    _write(
        discipline_note,
        "# Disciplina: Ética\n\n## Obras\n- [[01-LEITURAS/Autor/Obra/📖 Obra|Obra]]\n",
    )
    _write(primary, "# Obra\n")
    _write(chapter, "# Capítulo 1\n")

    works = load_discipline_works(vault_root, "Ética")

    event_data = {
        "id": "evt-1",
        "title": "Aula de Ética",
        "start": datetime(2026, 4, 7, 9, 30).isoformat(),
        "discipline": "Ética",
    }
    existing = f"# Antiga\n\n{ANNOTATIONS_HEADER}\n\n- ponto importante\n"

    frontmatter, content = build_class_note_content(
        discipline="Ética",
        event_data=event_data,
        selected_works=works,
        existing_content=existing,
    )

    assert frontmatter["discipline"] == "Ética"
    assert frontmatter["event_id"] == "evt-1"
    assert "## Obras da aula" in content
    assert "[[01-LEITURAS/Autor/Obra/📖 Obra|📖 Obra]]" in content
    assert "### Obra" in content
    assert "[[01-LEITURAS/Autor/Obra/Capitulo 1|Capitulo 1]]" in content
    assert "- ponto importante" in content


def test_build_class_note_relative_path_uses_production_folder():
    event_data = {
        "start": datetime(2026, 4, 7, 9, 30).isoformat(),
    }

    relative_path = build_class_note_relative_path("História da Filosofia", event_data)

    assert relative_path == "03-PRODUÇÃO/Aula de História da Filosofia do dia 07-04-2026.md"
