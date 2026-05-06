#!/usr/bin/env python3
"""
Script de teste para exportação LaTeX via CLI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from src.core.modules.LaTex import (  # noqa: E402
        LatexExportRequest,
        LatexExportValidationError,
        LatexExporter,
        LatexMetadata,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - guard rail para ambiente parcial
    missing_name = getattr(exc, "name", "dependência desconhecida")
    print(
        "Dependência ausente para executar o teste de exportação LaTeX: "
        f"{missing_name}. Instale os requisitos do projeto antes de rodar este script."
    )
    raise SystemExit(1) from exc


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or default


def _print_notes(title: str, notes: List) -> None:
    print(f"\n{title}")
    for index, note in enumerate(notes, 1):
        print(f"  {index:>2}. {note.path}")


def _select_note(exporter: LatexExporter, notes: List, label: str, provided: Optional[str] = None) -> str:
    if provided:
        matches = [note for note in notes if str(note.path) == provided]
        if not matches:
            raise ValueError(f"{label} não encontrado: {provided}")
        return str(matches[0].path)

    _print_notes(f"Selecione {label}", notes)
    selected = input(f"Número de {label}: ").strip()
    if not selected.isdigit():
        raise ValueError(f"Seleção inválida para {label}.")
    index = int(selected)
    if index < 1 or index > len(notes):
        raise ValueError(f"Seleção fora do intervalo para {label}.")
    return str(notes[index - 1].path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Testa a exportação LaTeX do GLaDOS Planner.")
    parser.add_argument("--vault-path", help="Caminho do vault do Obsidian.")
    parser.add_argument("--list", action="store_true", help="Lista notas encontradas em 03-PRODUÇÃO e sai.")
    parser.add_argument("--main-note", help="Caminho relativo da nota principal.")
    parser.add_argument("--references-note", help="Caminho relativo da nota de referências BibTeX.")
    parser.add_argument("--author", default="", help="Autor.")
    parser.add_argument("--advisor", default="", help="Orientador.")
    parser.add_argument("--institution", default="", help="Instituição.")
    parser.add_argument("--location", default="", help="Local.")
    parser.add_argument("--year", default="", help="Ano.")
    parser.add_argument("--work-type", default="Dissertação", help="Tipo de trabalho.")
    parser.add_argument("--degree", default="Mestre", help="Grau obtido.")
    parser.add_argument("--program", default="", help="Programa.")
    parser.add_argument("--concentration-area", default="", help="Área de concentração.")
    parser.add_argument("--department", default="", help="Departamento.")
    parser.add_argument("--coadvisor", default="", help="Coorientador.")
    parser.add_argument("--date", default="", help="Data completa.")
    parser.add_argument("--version", default="", help="Versão do trabalho.")
    parser.add_argument("--volume", default="", help="Número do volume.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    exporter = LatexExporter(args.vault_path)
    main_notes = exporter.get_main_notes()
    ref_notes = [note for note in exporter.list_production_notes() if note.path.name.lower().startswith("ref.")]

    if args.list:
        _print_notes("Notas principais", main_notes)
        _print_notes("Notas de referências", ref_notes)
        return 0

    if not main_notes:
        print("Nenhuma nota principal encontrada em 03-PRODUÇÃO.")
        return 1

    try:
        main_note_path = _select_note(exporter, main_notes, "a nota principal", args.main_note)
        selected_main_note = exporter.get_note(main_note_path)
        matching_refs = exporter.get_matching_reference_notes(selected_main_note) or ref_notes
        if not matching_refs:
            print("Nenhuma nota de referências encontrada em 03-PRODUÇÃO.")
            return 1
        references_note_path = _select_note(exporter, matching_refs, "a nota de referências", args.references_note)
    except ValueError as exc:
        print(exc)
        return 1

    metadata = LatexMetadata(
        author=args.author or _prompt("Autor"),
        advisor=args.advisor or _prompt("Orientador"),
        institution=args.institution or _prompt("Instituição"),
        location=args.location or _prompt("Local"),
        year=args.year or _prompt("Ano"),
        work_type=args.work_type or "Dissertação",
        degree=args.degree or "Mestre",
        program=args.program or _prompt("Programa", default=""),
        concentration_area=args.concentration_area or _prompt("Área de concentração", default=""),
        department=args.department or _prompt("Departamento", default=""),
        coadvisor=args.coadvisor or _prompt("Coorientador", default=""),
        date=args.date or _prompt("Data completa", default=""),
        version=args.version or _prompt("Versão", default=""),
        volume=args.volume or _prompt("Volume", default=""),
    )

    request = LatexExportRequest(
        main_note_path=main_note_path,
        references_note_path=references_note_path,
        metadata=metadata,
        optional_sections={},
    )

    try:
        result = exporter.export_from_request(request)
    except LatexExportValidationError as exc:
        print(f"Erro de validação: {exc}")
        return 1
    except Exception as exc:
        print(f"Erro inesperado: {exc}")
        return 1

    print("\nExportação concluída")
    print(f"  Título: {result.title}")
    print(f"  TEX: {result.tex_path}")
    print(f"  BIB: {result.bib_path}")
    print(f"  PDF: {result.pdf_path}")
    print(f"  PDF compilado: {'sim' if result.compiled_pdf else 'não'}")
    if result.warnings:
        print("\nAvisos:")
        for warning in result.warnings:
            print(f"  - {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
