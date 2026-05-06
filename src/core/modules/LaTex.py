#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .obsidian.vault_manager import ObsidianNote, ObsidianVaultManager


class LatexExportValidationError(ValueError):
    """Erro de validação no fluxo de exportação LaTeX."""


@dataclass(slots=True)
class LatexMetadata:
    author: str
    advisor: str
    institution: str
    location: str
    year: str
    work_type: str = "Dissertação"
    degree: str = "Mestre"
    program: str = ""
    concentration_area: str = ""
    department: str = ""
    coadvisor: str = ""
    date: str = ""
    version: str = ""
    volume: str = ""


@dataclass(slots=True)
class LatexExportRequest:
    main_note_path: str
    references_note_path: str
    metadata: LatexMetadata
    optional_sections: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class LatexExportResult:
    title: str
    tex_path: Path
    bib_path: Path
    pdf_path: Path
    compiled_pdf: bool
    warnings: list[str] = field(default_factory=list)
    compiler_log: str = ""


def _normalize_name(value: str) -> str:
    lowered = str(value or "").strip().lower()
    lowered = lowered.removesuffix(".md").removesuffix(".bib").removesuffix(".tex")
    return re.sub(r"[\W_]+", "", lowered, flags=re.UNICODE)


def _escape_latex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _decode_text_bytes(raw: bytes) -> str:
    """Decodifica bytes externos tentando UTF-8 antes de fallbacks comuns."""
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _markdown_fallback_to_latex(markdown: str) -> str:
    """Fallback simples quando Pandoc não estiver disponível."""
    blocks: list[str] = []
    in_code_block = False
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        text = " ".join(line.strip() for line in paragraph if line.strip())
        if text:
            blocks.append(_escape_latex(text))
        paragraph.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            if in_code_block:
                blocks.append(r"\end{verbatim}")
            else:
                blocks.append(r"\begin{verbatim}")
            in_code_block = not in_code_block
            continue

        if in_code_block:
            blocks.append(line)
            continue

        if not stripped:
            flush_paragraph()
            blocks.append("")
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            title = _escape_latex(heading.group(2).strip())
            command = {1: "section", 2: "subsection", 3: "subsubsection"}[level]
            blocks.append(f"\\{command}{{{title}}}")
            continue

        bullet = re.match(r"^[-*+]\s+(.*)$", stripped)
        if bullet:
            flush_paragraph()
            blocks.append(r"\begin{itemize}")
            blocks.append(f"\\item {_escape_latex(bullet.group(1).strip())}")
            blocks.append(r"\end{itemize}")
            continue

        paragraph.append(line)

    flush_paragraph()
    if in_code_block:
        blocks.append(r"\end{verbatim}")
    return "\n\n".join(block for block in blocks if block is not None)


def md_to_latex(md_filepath: str) -> str:
    """
    Converte um arquivo Markdown para LaTeX usando Pandoc.
    Faz fallback para um conversor simples quando Pandoc não está disponível.
    """
    pandoc = shutil.which("pandoc")
    if pandoc:
        try:
            result = subprocess.run(
                [pandoc, md_filepath, "-f", "markdown", "-t", "latex"],
                capture_output=True,
                check=True,
            )
            return _decode_text_bytes(result.stdout)
        except subprocess.CalledProcessError as exc:
            error_output = _decode_text_bytes(exc.stderr or b"")
            raise RuntimeError(f"Erro ao converter {md_filepath} com Pandoc: {error_output}") from exc

    markdown = Path(md_filepath).read_text(encoding="utf-8")
    return _markdown_fallback_to_latex(markdown)


def extract_bib_from_md(md_file: str) -> str:
    """
    Extrai blocos BibTeX/BibLaTeX de um arquivo Markdown.
    """
    content = Path(md_file).read_text(encoding="utf-8")
    lines = content.splitlines()
    bib_entries: list[str] = []
    in_block = False
    fence_char = ""

    def is_bib_fence(info: str) -> bool:
        normalized = info.strip().lower()
        if not normalized:
            return False
        normalized = normalized.strip("{}")
        normalized = normalized.replace(".", " ").replace(",", " ")
        tokens = {token for token in normalized.split() if token}
        return bool(tokens & {"bib", "bibtex", "biblatex"})

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        opening = re.match(r"^(```+|~~~+)\s*(.*)$", lower)
        if not in_block and opening:
            info = opening.group(2)
            if is_bib_fence(info):
                in_block = True
                fence_char = opening.group(1)[0]
            continue

        if in_block:
            if re.match(rf"^{re.escape(fence_char)}{{3,}}\s*$", stripped):
                in_block = False
                fence_char = ""
                continue
            bib_entries.append(line)

    extracted = "\n".join(bib_entries).strip()
    if extracted:
        return extracted

    # Fallback: aceita notas com entradas BibTeX no corpo sem bloco cercado.
    bib_like_lines = [
        line for line in lines
        if line.lstrip().startswith("@") or line.strip().startswith("%")
    ]
    if bib_like_lines:
        start_index = next(
            (index for index, line in enumerate(lines) if line.lstrip().startswith("@")),
            None,
        )
        if start_index is not None:
            return "\n".join(lines[start_index:]).strip()

    return ""


def prepare_bib_file(ref_path: str, output_dir: Path) -> str:
    """
    Garante que exista um arquivo .bib no diretório de saída.
    Retorna o nome do arquivo sem extensão usado em \\bibliography{}.
    """
    ext = os.path.splitext(ref_path)[1].lower()
    bib_name = "bibliografia"
    dest = output_dir / f"{bib_name}.bib"

    if ext == ".bib":
        shutil.copy2(ref_path, dest)
    elif ext == ".md":
        bib_content = extract_bib_from_md(ref_path)
        if not bib_content:
            raise LatexExportValidationError(
                "Nenhum bloco biblatex/bibtex encontrado no arquivo .md de referências."
            )
        dest.write_text(bib_content, encoding="utf-8")
    else:
        raise LatexExportValidationError(
            f"Formato de arquivo de referências não suportado: {ext}. Use .bib ou .md."
        )

    return bib_name


def compile_pdf(tex_path: Path) -> tuple[bool, str]:
    """
    Compila o arquivo .tex usando latexmk.
    Retorna um tuple com status e log de compilação.
    """
    latexmk = shutil.which("latexmk")
    if not latexmk:
        return False, "latexmk não encontrado no sistema."

    result = subprocess.run(
        [latexmk, "-pdf", "-interaction=nonstopmode", tex_path.name],
        cwd=str(tex_path.parent),
        capture_output=True,
    )
    stdout = _decode_text_bytes(result.stdout or b"")
    stderr = _decode_text_bytes(result.stderr or b"")
    log = "\n".join(part for part in [stdout, stderr] if part).strip()
    return result.returncode == 0, log


def extract_latex_error_summary(compiler_log: str) -> str:
    """Extrai a mensagem principal de erro do log do LaTeX."""
    if not compiler_log:
        return ""

    patterns = [
        r"! LaTeX Error: ([^\n]+)",
        r"! Package [^\n]+ Error: ([^\n]+)",
        r"! Undefined control sequence\.\s*\n([^\n]+)",
        r"! Emergency stop\.\s*\n([^\n]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, compiler_log, flags=re.MULTILINE)
        if match:
            return " ".join(part.strip() for part in match.groups() if part and part.strip()).strip()

    bang_line = re.search(r"^!\s*(.+)$", compiler_log, flags=re.MULTILINE)
    if bang_line:
        return bang_line.group(1).strip()

    return ""


class LatexExporter:
    """Exporta notas do vault para um projeto LaTeX ABNT."""

    def __init__(self, vault_path: str):
        self.vault_manager = ObsidianVaultManager(vault_path)
        self.vault_path = self.vault_manager.vault_path
        self.production_dir = Path("03-PRODUÇÃO")
        self.exports_root = self.vault_path / self.production_dir / "_latex"
        self.template_path = Path(__file__).resolve().parent / "templates" / "dissertacao_fflch_usp.tex"

    def list_production_notes(self) -> list[ObsidianNote]:
        return sorted(
            self.vault_manager.get_notes_by_prefix(str(self.production_dir), include_content=False),
            key=lambda note: str(note.path).lower(),
        )

    def get_main_notes(self) -> list[ObsidianNote]:
        return [
            note for note in self.list_production_notes()
            if note.path.suffix.lower() == ".md" and not note.path.name.lower().startswith("ref.")
        ]

    def get_note(self, relative_path: str) -> ObsidianNote:
        note = self.vault_manager.get_note_by_path(relative_path)
        if note is None:
            raise LatexExportValidationError(f"Nota não encontrada: {relative_path}")
        return note

    def extract_title(self, note: ObsidianNote) -> str:
        for line in note.content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
        return note.path.stem.replace("_", " ").replace("-", " ").strip() or "Dissertação"

    def get_matching_reference_notes(self, main_note: ObsidianNote) -> list[ObsidianNote]:
        ref_notes = [
            note for note in self.list_production_notes()
            if note.path.suffix.lower() == ".md" and note.path.name.lower().startswith("ref.")
        ]
        main_key = _normalize_name(main_note.path.stem)
        matched = [
            note for note in ref_notes
            if _normalize_name(note.path.stem.removeprefix("ref.")) == main_key
        ]
        return matched

    def export_from_request(self, request: LatexExportRequest) -> LatexExportResult:
        main_note = self.get_note(request.main_note_path)
        ref_note = self.get_note(request.references_note_path)
        self._validate_request(main_note, ref_note)

        title = self.extract_title(main_note)
        output_dir = self._build_output_dir(main_note)
        output_dir.mkdir(parents=True, exist_ok=True)

        main_md_path = self.vault_path / main_note.path
        ref_md_path = self.vault_path / ref_note.path
        warnings: list[str] = []

        conteudo_latex = md_to_latex(str(main_md_path))
        bib_name = prepare_bib_file(str(ref_md_path), output_dir)
        bib_path = output_dir / f"{bib_name}.bib"

        optional_sections_latex = {
            key: self._load_optional_section(path)
            for key, path in (request.optional_sections or {}).items()
        }

        tex_content = self._render_template(
            title=title,
            metadata=request.metadata,
            conteudo_latex=conteudo_latex,
            bib_name=bib_name,
            optional_sections=optional_sections_latex,
        )

        tex_path = output_dir / "dissertacao.tex"
        tex_path.write_text(tex_content, encoding="utf-8")

        compiled_pdf, compiler_log = compile_pdf(tex_path)
        pdf_path = tex_path.with_suffix(".pdf")
        if compiled_pdf and not pdf_path.exists():
            warnings.append(
                "latexmk retornou sucesso, mas o PDF esperado não foi encontrado no caminho padrão."
            )
            compiled_pdf = False
        if not compiled_pdf:
            error_summary = extract_latex_error_summary(compiler_log)
            if error_summary:
                warnings.append(f"Erro de compilação LaTeX: {error_summary}")

        if not compiled_pdf and "pandoc" not in warnings and not shutil.which("pandoc"):
            warnings.append("Pandoc não encontrado; foi usado um conversor Markdown simplificado.")
        if not compiled_pdf and not shutil.which("latexmk"):
            warnings.append("latexmk não encontrado; o PDF não pôde ser compilado.")

        return LatexExportResult(
            title=title,
            tex_path=tex_path,
            bib_path=bib_path,
            pdf_path=pdf_path,
            compiled_pdf=compiled_pdf,
            warnings=warnings,
            compiler_log=compiler_log,
        )

    def _validate_request(self, main_note: ObsidianNote, ref_note: ObsidianNote) -> None:
        if not str(main_note.path).replace("\\", "/").startswith(f"{self.production_dir.as_posix()}/"):
            raise LatexExportValidationError("A nota principal precisa estar em 03-PRODUÇÃO.")
        if not str(ref_note.path).replace("\\", "/").startswith(f"{self.production_dir.as_posix()}/"):
            raise LatexExportValidationError("A nota de referências precisa estar em 03-PRODUÇÃO.")
        if main_note.path.name.lower().startswith("ref."):
            raise LatexExportValidationError("A nota principal não pode ter prefixo ref.")
        if not ref_note.path.name.lower().startswith("ref."):
            raise LatexExportValidationError("A nota de referências precisa ter prefixo ref.")

    def _build_output_dir(self, main_note: ObsidianNote) -> Path:
        note_dir = main_note.path.parent.relative_to(self.production_dir)
        return self.exports_root / note_dir / main_note.path.stem

    def _load_optional_section(self, relative_path: str) -> str:
        note = self.get_note(relative_path)
        return md_to_latex(str(self.vault_path / note.path))

    def _render_template(
        self,
        *,
        title: str,
        metadata: LatexMetadata,
        conteudo_latex: str,
        bib_name: str,
        optional_sections: dict[str, str],
    ) -> str:
        template = self.template_path.read_text(encoding="utf-8")
        replacements = {
            "__TITULO__": title,
            "__AUTOR__": metadata.author,
            "__ORIENTADOR__": metadata.advisor,
            "__INSTITUICAO__": metadata.institution,
            "__PROGRAMA__": metadata.program,
            "__TIPOTRABALHO__": metadata.work_type,
            "__LOCAL__": metadata.location,
            "__ANO__": metadata.year,
            "__PREAMBULO__": self._build_preambulo(metadata),
            "__CONTEUDO_LATEX__": conteudo_latex,
            "__ARQUIVO_BIB__": bib_name,
            "__COORIENTADOR_BLOCK__": self._coadvisor_block(metadata.coadvisor),
            "__VERSAO_BLOCK__": "",
            "__VOLUME_BLOCK__": "",
            "__FICHA_BLOCK__": self._optional_block(optional_sections.get("ficha_catalografica")),
            "__IMPRIMIR_FICHA_BLOCK__": r"\imprimirfichacatalografica" if optional_sections.get("ficha_catalografica") else "",
            "__ERRATA_BLOCK__": self._named_environment("errata", optional_sections.get("errata")),
            "__BANCA_MEMBROS_BLOCK__": self._build_banca_block(optional_sections.get("banca")),
            "__DEDICATORIA_BLOCK__": self._named_environment("dedicatoria", optional_sections.get("dedicatoria")),
            "__AGRADECIMENTOS_BLOCK__": self._named_environment("agradecimentos", optional_sections.get("agradecimentos")),
            "__EPIGRAFE_BLOCK__": self._named_environment("epigrafe", optional_sections.get("epigrafe")),
            "__RESUMO_BLOCK__": self._named_environment("resumo", optional_sections.get("resumo")),
            "__ABSTRACT_BLOCK__": self._named_environment("resumo}[Abstract]", optional_sections.get("abstract")),
            "__LISTA_ILUSTRACOES_BLOCK__": r"\listoffigures*" if optional_sections.get("lista_ilustracoes") else "",
            "__LISTA_TABELAS_BLOCK__": r"\listoftables*" if optional_sections.get("lista_tabelas") else "",
            "__SIGLAS_BLOCK__": self._named_environment("siglas", optional_sections.get("lista_abreviaturas")),
            "__GLOSSARIO_BLOCK__": self._optional_block(optional_sections.get("glossario")),
            "__APENDICES_BLOCK__": self._appendix_block(optional_sections.get("apendice")),
            "__ANEXOS_BLOCK__": self._annex_block(optional_sections.get("anexo")),
            "__INDICE_BLOCK__": r"\printindex" if optional_sections.get("indice") else "",
        }

        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered

    def _build_preambulo(self, metadata: LatexMetadata) -> str:
        parts = [f"{metadata.work_type} apresentada"]
        if metadata.program:
            parts.append(f"ao programa {metadata.program}")
        if metadata.department:
            parts.append(f"do departamento {metadata.department}")
        if metadata.institution:
            parts.append(f"da {metadata.institution}")
        if metadata.degree:
            parts.append(f"para obtenção do grau de {metadata.degree}")
        if metadata.concentration_area:
            parts.append(f"na área de concentração {metadata.concentration_area}")
        return " ".join(parts) + "."

    def _optional_block(self, content: Optional[str]) -> str:
        return content.strip() if content else ""

    def _coadvisor_block(self, coadvisor: str) -> str:
        normalized = str(coadvisor or "").strip()
        if not normalized:
            return ""
        return f"\\coorientador{{{normalized}}}"

    def _named_environment(self, environment: str, content: Optional[str]) -> str:
        if not content:
            return ""
        if "}[Abstract]" in environment:
            env_name = "resumo"
            return f"\\begin{{{env_name}}}[Abstract]\n{content.strip()}\n\\end{{{env_name}}}"
        return f"\\begin{{{environment}}}\n{content.strip()}\n\\end{{{environment}}}"

    def _build_banca_block(self, content: Optional[str]) -> str:
        if not content:
            return ""
        members = [line.strip() for line in content.splitlines() if line.strip()]
        return "\n".join(
            f"        \\assinatura{{{member}}}{{Instituição: \\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_}}{{Julgamento: \\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_}}"
            for member in members
        )

    def _appendix_block(self, content: Optional[str]) -> str:
        if not content:
            return ""
        return f"\\begin{{apendicesenv}}\n{content.strip()}\n\\end{{apendicesenv}}"

    def _annex_block(self, content: Optional[str]) -> str:
        if not content:
            return ""
        return f"\\begin{{anexosenv}}\n{content.strip()}\n\\end{{anexosenv}}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerar dissertação ABNT a partir de Markdown")
    parser.add_argument("--md", required=True, help="Caminho para o arquivo .md da dissertação")
    parser.add_argument("--ref", required=True, help="Caminho para o arquivo de referências (.bib ou .md)")
    parser.add_argument("--output-dir", default="./output", help="Diretório de saída")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    conteudo_latex = md_to_latex(args.md)
    bib_name = prepare_bib_file(args.ref, out_dir)
    tex_path = out_dir / "dissertacao.tex"
    tex_path.write_text(conteudo_latex + f"\n\n\\bibliography{{{bib_name}}}\n", encoding="utf-8")

    compiled_pdf, compiler_log = compile_pdf(tex_path)
    print(f"Arquivo .tex salvo em {tex_path}")
    print(f"PDF esperado em {tex_path.with_suffix('.pdf')}")
    print("Compilado com sucesso." if compiled_pdf else f"Falha na compilação.\n{compiler_log}")


if __name__ == "__main__":
    main()
