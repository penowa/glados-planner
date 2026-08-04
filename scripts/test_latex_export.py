#!/usr/bin/env python3
"""
Script de teste para exportação LaTeX via CLI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from src.core.modules.LaTex import (  # noqa: E402
        LatexExportRequest,
        LatexExportValidationError,
        LatexExporter,
        LatexMetadata,
        md_to_latex,
        prepare_bib_file,
        compile_pdf,
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

# ANSI color helpers
_C_TITLE = "\033[96m"  # cyan
_C_INPUT = "\033[93m"  # yellow
_C_INDEX = "\033[92m"  # green
_C_NOTE = "\033[97m"   # white
_C_BOX = "\033[94m"    # blue
_C_RESET = "\033[0m"


def _print_notes(title: str, notes: List) -> None:
    # Show only filenames (without directory) and remove .md extension for display
    entries: list[str] = []
    for index, note in enumerate(notes, 1):
        name = note.path.name
        if name.lower().endswith('.md'):
            name = name[:-3]
        entries.append((index, name))

    # Build box
    lines = [f"{i:>2}. {n}" for i, n in entries]
    width = max(len(title), *(len(l) for l in lines))
    print()
    print(f"{_C_BOX}┌{'─' * (width + 2)}┐{_C_RESET}")
    print(f"{_C_BOX}│ {_C_TITLE}{title.center(width)}{_C_BOX} │{_C_RESET}")
    print(f"{_C_BOX}├{'─' * (width + 2)}┤{_C_RESET}")
    for i, name in entries:
        idx_label = f"{i:>2}."
        line = f"{idx_label} {name}"
        padding = ' ' * (width - len(line))
        print(f"{_C_BOX}│ {_C_INDEX}{idx_label}{_C_RESET} {_C_NOTE}{name}{padding}{_C_RESET} {_C_BOX}│{_C_RESET}")
    print(f"{_C_BOX}└{'─' * (width + 2)}┘{_C_RESET}")


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


def _select_production_subdir(exporter: LatexExporter, provided: Optional[str] = None) -> str:
    base = exporter.vault_path / exporter.production_dir
    if not base.exists() or not base.is_dir():
        return ""

    entries = [p for p in sorted(base.iterdir()) if p.is_dir()]
    # Represent as relative names under 03-PRODUÇÃO
    rels = [str(p.name) for p in entries]

    if provided:
        if provided in rels:
            return provided
        raise ValueError(f"Subdiretório não encontrado em 03-PRODUÇÃO: {provided}")

    if not rels:
        return ""

    # Print boxed list with colors
    title = "Selecione o repositório/diretório dentro de 03-PRODUÇÃO"
    lines = [f"{i:>2}. {name}" for i, name in enumerate(rels, 1)]
    width = max(len(title), *(len(l) for l in lines))
    print()
    print(f"{_C_BOX}┌{'─' * (width + 2)}┐{_C_RESET}")
    print(f"{_C_BOX}│ {_C_TITLE}{title.center(width)}{_C_BOX} │{_C_RESET}")
    print(f"{_C_BOX}├{'─' * (width + 2)}┤{_C_RESET}")
    for i, name in enumerate(rels, 1):
        idx_label = f"{i:>2}."
        padding = ' ' * (width - (len(idx_label) + 1 + len(name)))
        print(f"{_C_BOX}│ {_C_INDEX}{idx_label}{_C_RESET} {_C_NOTE}{name}{padding}{_C_RESET} {_C_BOX}│{_C_RESET}")
    print(f"{_C_BOX}└{'─' * (width + 2)}┘{_C_RESET}")

    selected = input(f"{_C_INPUT}Número do diretório: {_C_RESET}").strip()
    if not selected.isdigit():
        raise ValueError("Seleção inválida para diretório.")
    idx = int(selected)
    if idx < 1 or idx > len(rels):
        raise ValueError("Seleção fora do intervalo para diretório.")
    return rels[idx - 1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Testa a exportação LaTeX do GLaDOS Planner.")
    parser.add_argument("--vault-path", help="Caminho do vault do Obsidian.", default="/home/penowa/Documentos/Obsidian/Planner/")
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
    parser.add_argument("--simple", action="store_true", help="Fluxo simples: gera .tex mínimo (título, texto, referências opcionais).")
    parser.add_argument("--subdir", help="Nome do subdiretório dentro de 03-PRODUÇÃO para filtrar notas (não interativo).")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Pergunta ao usuário qual abordagem usar se não fornecido por flag
    if not args.simple:
        choice = input(f"{_C_INPUT}Escolha abordagem — (S)imples (título+texto) ou (C)ompleta (ABNT) [C]: {_C_RESET}").strip().lower()
        if choice in ("s", "sim", "y", "yes"):
            args.simple = True

    exporter = LatexExporter(args.vault_path)
    # Pergunta primeiro qual subdiretório em 03-PRODUÇÃO o usuário deseja acessar
    try:
        selected_subdir = _select_production_subdir(exporter, provided=getattr(args, "subdir", None))
    except ValueError as exc:
        print(exc)
        return 1

    prefix = str(exporter.production_dir / selected_subdir) if selected_subdir else str(exporter.production_dir)
    all_notes = exporter.vault_manager.get_notes_by_prefix(prefix, include_content=False)
    main_notes = [note for note in all_notes if note.path.suffix.lower() == ".md" and not note.path.name.lower().startswith("ref.")]
    ref_notes = [note for note in all_notes if note.path.suffix.lower() == ".md" and note.path.name.lower().startswith("ref.")]

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
        references_note_path = None
        if matching_refs:
            try:
                references_note_path = _select_note(exporter, matching_refs, "a nota de referências", args.references_note)
            except ValueError:
                # allow continuing without references in simple flow
                references_note_path = None
        else:
            references_note_path = None
    except ValueError as exc:
        print(exc)
        return 1

    if args.simple:
        metadata = LatexMetadata(
            author="",
            advisor="",
            institution="",
            location="",
            year="",
        )
    else:
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

    # Simple flow: minimal .tex (title, content, optional references)
    if args.simple:
        output_dir = exporter._build_output_dir(selected_main_note)
        output_dir.mkdir(parents=True, exist_ok=True)
        main_md_path = exporter.vault_path / selected_main_note.path
        print(f"Gerando fluxo simples em {output_dir} (arquivos .tex temporários)")
        try:
            # Use work_dir for temporary tex and images
            import tempfile as _temp
            work_dir = Path(_temp.mkdtemp(prefix="latex_build_", dir=str(output_dir)))
            conteudo_latex = md_to_latex(str(main_md_path), output_dir=work_dir, vault_root=exporter.vault_path)
        except Exception as exc:
            print(f"Falha ao converter Markdown: {exc}")
            return 1

        title = exporter.extract_title(selected_main_note)

        tex = []
        tex.append(r"\documentclass[12pt,a4paper]{article}")
        tex.append(r"\usepackage[utf8]{inputenc}")
        tex.append(r"\usepackage[T1]{fontenc}")
        tex.append(r"\usepackage{graphicx}")
        tex.append(r"\usepackage{hyperref}")
        tex.append(r"\begin{document}")
        tex.append(f"\\title{{{title}}}")
        tex.append(f"\\author{{{metadata.author}}}")
        tex.append(r"\maketitle")
        tex.append("\n% Conteúdo convertido de Markdown:\n")
        tex.append(conteudo_latex)

        bib_path = None
        if references_note_path:
            try:
                ref_md_path = exporter.vault_path / exporter.get_note(references_note_path).path
                bib_name = prepare_bib_file(str(ref_md_path), work_dir)
                bib_path = work_dir / f"{bib_name}.bib"
                tex.append(f"\\clearpage\n\\bibliographystyle{{plain}}\n\\bibliography{{{bib_name}}}")
            except LatexExportValidationError as exc:
                print(f"Aviso: referências não adicionadas: {exc}")
            except Exception as exc:
                print(f"Erro ao processar referências: {exc}")

        tex.append(r"\end{document}")

        tex_path = work_dir / "dissertacao_simple.tex"
        tex_path.write_text("\n".join(tex), encoding="utf-8")

        # Compilar no work_dir; mover PDF para output_dir se sucesso, e limpar temporários
        compiled_pdf, compiler_log = compile_pdf(tex_path)
        pdf_in_work = tex_path.with_suffix('.pdf')
        pdf_path = output_dir / pdf_in_work.name
        if compiled_pdf and pdf_in_work.exists():
            shutil.move(str(pdf_in_work), str(pdf_path))
            try:
                shutil.rmtree(work_dir)
            except Exception:
                pass
            print("\nExportação (simples) concluída")
            print(f"  Título: {title}")
            print(f"  PDF: {pdf_path}")
            if bib_path:
                print(f"  BIB: {bib_path}")
            return 0
        else:
            print("Falha na compilação. Arquivos temporários mantidos em:", work_dir)
            if compiler_log:
                print("Log do compilador:\n", compiler_log)
            return 1

    # Full flow (template-based)
    request = LatexExportRequest(
        main_note_path=main_note_path,
        references_note_path=references_note_path if references_note_path else None,
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
