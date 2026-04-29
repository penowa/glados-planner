from pathlib import Path

from ui.utils.discipline_semantic_context import (
    build_discipline_semantic_context,
    collect_discipline_scoped_notes,
    rank_scoped_notes,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_collect_discipline_scoped_notes_includes_books_and_annotations(tmp_path: Path):
    vault_root = tmp_path
    discipline_note = vault_root / "05-DISCIPLINAS" / "introducao-a-filosofia.md"
    primary = vault_root / "01-LEITURAS" / "Platao" / "Republica" / "📖 Republica.md"
    chapter = vault_root / "01-LEITURAS" / "Platao" / "Republica" / "001 - Livro I.md"
    annotation = vault_root / "02-ANOTAÇÕES" / "Aula 01.md"

    _write(
        discipline_note,
        "# Disciplina: Introducao a Filosofia\n\n## Obras\n- [[01-LEITURAS/Platao/Republica/📖 Republica|Republica]]\n",
    )
    _write(
        primary,
        "---\nbook_id: rep-1\ntitle: Republica\ntype: book\ntags: [platao, politica]\n---\n\n# Republica\n\nJustica e educacao filosofica.\n",
    )
    _write(chapter, "# Livro I\n\nDebate sobre justica.\n")
    _write(
        annotation,
        "---\ntitle: Aula 01\ndiscipline: Introducao a Filosofia\nworks:\n  - 01-LEITURAS/Platao/Republica/📖 Republica\nwork_notes:\n  - 01-LEITURAS/Platao/Republica/001 - Livro I\ntags: [aula]\n---\n\n## Anotacoes\n[[01-LEITURAS/Platao/Republica/📖 Republica|Republica]]\n",
    )

    notes = collect_discipline_scoped_notes(vault_root, "Introducao a Filosofia")
    rel_paths = {note.relative_path for note in notes}
    categories = {note.relative_path: note.category for note in notes}

    assert "05-DISCIPLINAS/introducao-a-filosofia.md" in rel_paths
    assert "01-LEITURAS/Platao/Republica/📖 Republica.md" in rel_paths
    assert "01-LEITURAS/Platao/Republica/001 - Livro I.md" in rel_paths
    assert "02-ANOTAÇÕES/Aula 01.md" in rel_paths
    assert categories["01-LEITURAS/Platao/Republica/📖 Republica.md"] == "book_primary"
    assert categories["02-ANOTAÇÕES/Aula 01.md"] == "annotation"


def test_rank_scoped_notes_prioritizes_primary_book_and_related_annotations(tmp_path: Path):
    vault_root = tmp_path
    discipline_note = vault_root / "05-DISCIPLINAS" / "introducao-a-filosofia.md"
    primary = vault_root / "01-LEITURAS" / "Aristoteles" / "Metafisica" / "📖 Metafisica.md"
    chapter = vault_root / "01-LEITURAS" / "Aristoteles" / "Metafisica" / "001 - Livro A.md"
    annotation = vault_root / "02-ANOTAÇÕES" / "Aula metafisica.md"

    _write(
        discipline_note,
        "# Disciplina: Introducao a Filosofia\n\n## Obras\n- [[01-LEITURAS/Aristoteles/Metafisica/📖 Metafisica|Metafisica]]\n",
    )
    _write(
        primary,
        "---\ntitle: Metafisica\ntype: book\ntags: [aristoteles, metafisica]\n---\n\n# Metafisica\n\nA metafisica investiga causas, principios e o ser enquanto ser.\n",
    )
    _write(
        chapter,
        "# Livro A\n\nCapitulo introdutorio sobre causas e principios.\n",
    )
    _write(
        annotation,
        "---\ntitle: Aula de metafisica\ndiscipline: Introducao a Filosofia\nworks:\n  - 01-LEITURAS/Aristoteles/Metafisica/📖 Metafisica\n---\n\nA aula relaciona metafisica, causas e principios com a leitura da obra.\n",
    )

    notes = collect_discipline_scoped_notes(vault_root, "Introducao a Filosofia")
    ranked = rank_scoped_notes(notes, "causas e principios na metafisica", max_results=3)

    assert ranked
    assert ranked[0].relative_path == "01-LEITURAS/Aristoteles/Metafisica/📖 Metafisica.md"
    assert any(note.relative_path == "02-ANOTAÇÕES/Aula metafisica.md" for note in ranked)


def test_build_discipline_semantic_context_lists_works_and_ranked_notes(tmp_path: Path):
    vault_root = tmp_path
    discipline_note = vault_root / "05-DISCIPLINAS" / "introducao-a-filosofia.md"
    primary = vault_root / "01-LEITURAS" / "Descartes" / "Meditacoes" / "📖 Meditacoes.md"

    _write(
        discipline_note,
        "# Disciplina: Introducao a Filosofia\n\n## Obras\n- [[01-LEITURAS/Descartes/Meditacoes/📖 Meditacoes|Meditacoes]]\n",
    )
    _write(
        primary,
        "---\ntitle: Meditacoes\ntype: book\ntags: [descartes, epistemologia]\n---\n\n# Meditacoes\n\nDuvida metodica e busca por certeza.\n",
    )

    context = build_discipline_semantic_context(
        vault_root,
        "Introducao a Filosofia",
        "duvida metodica",
    )

    assert "DISCIPLINA: Introducao a Filosofia" in context
    assert "OBRAS_IDENTIFICADAS: 1" in context
    assert "01-LEITURAS/Descartes/Meditacoes/📖 Meditacoes" in context
    assert "[NOTA 1] [OBRA_COMPLETA] 01-LEITURAS/Descartes/Meditacoes/📖 Meditacoes.md" in context
