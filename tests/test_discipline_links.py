from pathlib import Path

from ui.utils.discipline_links import append_annotation_note_links
from ui.utils.discipline_semantic_context import list_discipline_annotation_candidates


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_append_annotation_note_links_creates_section_and_deduplicates(tmp_path: Path):
    vault_root = tmp_path
    discipline_note = vault_root / "05-DISCIPLINAS" / "introducao-a-filosofia.md"
    annotation = vault_root / "02-ANOTAÇÕES" / "Aula 01.md"

    _write(
        discipline_note,
        "# Disciplina: Introducao a Filosofia\n\n## Agenda\n\n## Obras\n",
    )
    _write(annotation, "# Aula 01\n\nConteudo.\n")

    first = append_annotation_note_links(
        vault_root,
        "Introducao a Filosofia",
        [annotation],
    )
    second = append_annotation_note_links(
        vault_root,
        "Introducao a Filosofia",
        [annotation],
    )

    content = discipline_note.read_text(encoding="utf-8")

    assert first["added_links"] == 1
    assert second["added_links"] == 0
    assert "## Anotações" in content
    assert content.count("- [[02-ANOTAÇÕES/Aula 01|Aula 01]]") == 1


def test_list_discipline_annotation_candidates_marks_related_and_already_added(tmp_path: Path):
    vault_root = tmp_path
    discipline_note = vault_root / "05-DISCIPLINAS" / "introducao-a-filosofia.md"
    primary = vault_root / "01-LEITURAS" / "Platao" / "Republica" / "📖 Republica.md"
    related = vault_root / "02-ANOTAÇÕES" / "Nota relacionada.md"
    added = vault_root / "02-ANOTAÇÕES" / "Nota adicionada.md"
    loose = vault_root / "02-ANOTAÇÕES" / "Nota solta.md"

    _write(
        discipline_note,
        (
            "# Disciplina: Introducao a Filosofia\n\n"
            "## Agenda\n\n"
            "## Obras\n"
            "- [[01-LEITURAS/Platao/Republica/📖 Republica|Republica]]\n\n"
            "## Anotações\n"
            "- [[02-ANOTAÇÕES/Nota adicionada|Nota adicionada]]\n"
        ),
    )
    _write(
        primary,
        "---\ntitle: Republica\ntype: book\n---\n\n# Republica\n\nJustica e cidade.\n",
    )
    _write(
        related,
        (
            "---\n"
            "title: Nota relacionada\n"
            "works:\n"
            "  - 01-LEITURAS/Platao/Republica/📖 Republica\n"
            "---\n\n"
            "Comentário conectado à obra.\n"
        ),
    )
    _write(
        added,
        (
            "---\n"
            "title: Nota adicionada\n"
            "discipline: Introducao a Filosofia\n"
            "---\n\n"
            "Comentário já adicionado.\n"
        ),
    )
    _write(loose, "# Nota solta\n\nSem vínculo.\n")

    candidates = {
        item.relative_path: item
        for item in list_discipline_annotation_candidates(vault_root, "Introducao a Filosofia")
    }

    assert candidates["02-ANOTAÇÕES/Nota relacionada.md"].related_by_link is True
    assert candidates["02-ANOTAÇÕES/Nota relacionada.md"].already_linked_in_discipline is False
    assert candidates["02-ANOTAÇÕES/Nota adicionada.md"].related_by_link is True
    assert candidates["02-ANOTAÇÕES/Nota adicionada.md"].already_linked_in_discipline is True
    assert candidates["02-ANOTAÇÕES/Nota solta.md"].related_by_link is False
    assert candidates["02-ANOTAÇÕES/Nota solta.md"].already_linked_in_discipline is False
