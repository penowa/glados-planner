#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI temática do GLaDOS com resposta ancorada apenas no vault.

O fluxo evita um modelo separado no script: ele reaproveita o backend local
já otimizado pelo projeto, busca notas relevantes no vault e injeta um
contexto estrito para manter as respostas dentro do material disponível.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Sequence

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_text = str(candidate)
    if candidate_text not in sys.path:
        sys.path.insert(0, candidate_text)

from src.core.config.settings import settings
from src.core.llm.backend_router import llm as backend_llm
from src.core.llm.glados.personality import create_personality_voice
from src.core.llm.runtime_discovery import detect_nvidia_gpus


@dataclass(frozen=True)
class ChatProfile:
    max_notes: int
    excerpt_chars: int
    max_tokens: int
    top_p: float
    temperature: float
    repeat_penalty: float


def resolve_vault_path(raw_value: str | None) -> Path:
    value = str(raw_value or settings.paths.vault or "").strip()
    path = Path(value).expanduser()
    if not path.is_absolute():
        base_dir = PROJECT_ROOT
        path = base_dir / path
    return path


def choose_profile() -> ChatProfile:
    gpus = detect_nvidia_gpus()
    if not gpus:
        return ChatProfile(
            max_notes=12,
            excerpt_chars=140,
            max_tokens=512,
            top_p=0.82,
            temperature=0.14,
            repeat_penalty=1.12,
        )

    total_vram = max(int(gpu.get("memory_total_mb", 0) or 0) for gpu in gpus)
    if total_vram <= 2304:
        return ChatProfile(
            max_notes=12,
            excerpt_chars=140,
            max_tokens=512,
            top_p=0.82,
            temperature=0.16,
            repeat_penalty=1.11,
        )
    if total_vram <= 4096:
        return ChatProfile(
            max_notes=16,
            excerpt_chars=160,
            max_tokens=640,
            top_p=0.84,
            temperature=0.18,
            repeat_penalty=1.10,
        )
    return ChatProfile(
        max_notes=20,
        excerpt_chars=180,
        max_tokens=768,
        top_p=0.86,
        temperature=0.20,
        repeat_penalty=1.10,
    )


def configure_runtime(profile: ChatProfile, backend=None) -> None:
    try:
        target_backend = backend or backend_llm
        target_backend.set_generation_params(
            temperature=profile.temperature,
            top_p=profile.top_p,
            repeat_penalty=profile.repeat_penalty,
            max_tokens=profile.max_tokens,
        )
    except Exception:
        pass


def load_backend_quietly():
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        backend = backend_llm.reload()
    return backend, buffer.getvalue()


def generate_answer(query: str, profile: ChatProfile) -> dict[str, Any]:
    return backend_llm.generate(
        query=query,
        user_name=str(getattr(settings.llm.glados, "user_name", "Usuário") or "Usuário"),
        use_semantic=False,
        max_tokens=profile.max_tokens,
        request_metadata={
            "vault_only": True,
            "disable_sembrain_fallback": True,
            "navigation_max_notes": profile.max_notes,
            "navigation_excerpt_chars": profile.excerpt_chars,
            "source": "scripts.chat_glados",
        },
    )


def _source_label(note: Any) -> str:
    if isinstance(note, dict):
        path = str(note.get("path", "") or "").strip()
        title = str(note.get("title", "") or "").strip()
    else:
        path = str(getattr(note, "path", "") or "").strip()
        title = str(getattr(note, "title", "") or "").strip()
    if path:
        return Path(path).name
    if title:
        return f"{title}.md" if not title.lower().endswith(".md") else title
    return "fonte.md"


def annotate_response_with_citations(text: str, notes: Sequence[Any]) -> str:
    value = str(text or "").strip()
    if not value:
        return value

    source_labels = [_source_label(note) for note in notes if note]
    source_labels = [label for index, label in enumerate(source_labels) if label and label not in source_labels[:index]]
    if not source_labels:
        return value

    if re.search(r"\([^)]+\.md\)", value):
        return value

    paragraphs = re.split(r"\n\s*\n", value)
    annotated_paragraphs: List[str] = []
    sentence_index = 0

    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped:
            continue

        pieces = re.split(r"(?<=[.!?])\s+", stripped)
        rebuilt: List[str] = []
        for piece in pieces:
            sentence = piece.strip()
            if not sentence:
                continue
            normalized = sentence.lower()
            if normalized.startswith(("ah,", "sim,", "aqui,", "chamou,", "concluído", "de nada", "consultando", "olá", "pronta para", "encerrando")):
                rebuilt.append(sentence)
                continue
            if re.search(r"\([^)]+\.md\)$", sentence):
                rebuilt.append(sentence)
                continue
            citation = source_labels[min(sentence_index, len(source_labels) - 1)]
            sentence_index += 1
            rebuilt.append(f"{sentence} ({citation})")
        if rebuilt:
            annotated_paragraphs.append(" ".join(rebuilt))

    return "\n\n".join(annotated_paragraphs) if annotated_paragraphs else value


def print_sources(notes: Sequence[dict]) -> None:
    if not notes:
        return

    console = Console()
    rendered: List[str] = []
    for note in notes:
        if isinstance(note, dict):
            path = str(note.get("path", "") or "")
            title = str(note.get("title", "") or "")
        else:
            path = str(getattr(note, "path", "") or "")
            title = str(getattr(note, "title", "") or "")
        if path:
            rendered.append(f"{title} ({path})" if title else path)

    if rendered:
        console.print("\n[bold magenta]Fontes:[/bold magenta]")
        for item in rendered[:12]:
            console.print(f"[dim]- {item}[/dim]")


def build_personality():
    return create_personality_voice(
        user_name=str(getattr(settings.llm.glados, "user_name", "Usuário") or "Usuário"),
        intensity=float(getattr(settings.llm.glados, "personality_intensity", 0.7) or 0.7),
        assistant_name=str(getattr(settings.llm.glados, "glados_name", "GLaDOS") or "GLaDOS"),
        profile=str(getattr(settings.llm.glados, "personality_profile", "auto") or "auto"),
    )


def render_splash(console: Console, voice, profile: ChatProfile, vault_path: Path) -> None:
    lines = [
        f"Vault: {vault_path}",
        f"Notas por consulta: {profile.max_notes}",
        f"Janela de saída: até {profile.max_tokens} tokens",
        "",
        *voice.get_splash_lines(),
    ]
    console.print(
        Panel(
            Text("\n".join(lines)),
            title=f"{voice.assistant_name} :: vault-only",
            subtitle=voice.get_session_message(),
            box=box.DOUBLE,
            border_style="magenta",
            padding=(1, 2),
        )
    )
    console.print(Text(voice.get_prompt_hint(), style="dim"))
    console.print()


def render_gpu_notice(console: Console, backend) -> None:
    gpu_devices = detect_nvidia_gpus()
    model = getattr(backend, "model", None)
    runtime_device = str(getattr(model, "runtime_device", "") or "").strip()
    runtime_backend = str(getattr(model, "runtime_backend", "") or "").strip().lower()

    if not gpu_devices:
        return

    if runtime_backend == "gpu" or "n_gpu_layers=" in runtime_device:
        console.print("[green]GPU detectada e carregamento offload ativado.[/green]")
        return

    console.print(
        "[yellow]GPU NVIDIA detectada, mas este build do llama-cpp está em CPU.[/yellow]\n"
        "[dim]Para a GTX 750 Ti, use backend Vulkan:[/dim] "
        "[bold]./scripts/install_llama_cpp_gpu.sh vulkan[/bold]"
    )


def chat_loop(vault, profile: ChatProfile, voice) -> None:
    console = Console()
    console.print(
        Panel(
            f"[bold magenta]{voice.assistant_name}[/bold magenta] está aguardando uma pergunta útil.\n"
            f"[dim]Vault-only • {profile.max_notes} notas • {profile.max_tokens} tokens[/dim]",
            box=box.ROUNDED,
            border_style="magenta",
            padding=(0, 2),
        )
    )

    while True:
        try:
            question = input(f"{voice.assistant_name} >>> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Encerrando.[/dim]")
            return

        if not question:
            continue
        if question.lower() in {"sair", "exit", "quit"}:
            console.print("[dim]Encerrando.[/dim]")
            return

        with console.status("[magenta]Navegando pelo vault por disciplina...[/magenta]", spinner="dots"):
            response = generate_answer(question, profile)

        if not isinstance(response, dict):
            response = {"text": str(response or "")}

        packet = dict(response.get("navigation_packet") or {})
        notes = list(packet.get("notes", []) or [])
        answer = str(response.get("text") or response.get("response") or "").strip()
        if not answer:
            console.print("[yellow]Não encontrei essa informação nas notas selecionadas.[/yellow]")
            continue

        answer = annotate_response_with_citations(answer, notes)

        discipline = str(packet.get("discipline", "Geral") or "Geral")
        anchor = packet.get("anchor") or {}
        anchor_title = str(anchor.get("title", "") or "").strip()
        if anchor_title:
            console.print(f"[dim]Disciplina: {discipline} • Âncora: {anchor_title}[/dim]")
        else:
            console.print(f"[dim]Disciplina: {discipline}[/dim]")

        console.print("\n[bold magenta]Resposta:[/bold magenta]")
        console.print(answer)
        print_sources(notes)
        console.print("[dim]" + "─" * 66 + "[/dim]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chat temático do GLaDOS com respostas ancoradas no vault."
    )
    parser.add_argument(
        "--vault",
        default=settings.paths.vault,
        help="Caminho do vault do Obsidian.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    vault_path = resolve_vault_path(args.vault)
    if not vault_path.is_dir():
        print(f"Erro: o vault '{vault_path}' não é um diretório válido.")
        raise SystemExit(1)

    settings.paths.vault = str(vault_path)
    settings.llm.device_mode = "gpu_only"
    settings.llm.use_gpu = True
    settings.llm.use_cpu = False
    profile = choose_profile()
    console = Console()
    voice = build_personality()
    render_splash(console, voice, profile, vault_path)

    try:
        backend, _boot_log = load_backend_quietly()
        vault = getattr(backend, "vault_structure", None)
        if vault is None:
            raise RuntimeError("Backend inicializado sem vault_structure.")
    except Exception as exc:
        print(f"Erro ao carregar o vault: {exc}")
        raise SystemExit(1)

    configure_runtime(profile, backend)
    model = getattr(backend, "model", None)
    runtime_backend = str(getattr(model, "runtime_backend", "") or "").strip().lower()
    runtime_device = str(getattr(model, "runtime_device", "") or "").strip()
    if runtime_backend != "gpu" and "GPU" not in runtime_device:
        console.print(
            "[bold red]Erro:[/bold red] o backend não carregou em GPU-only.\n"
            "[dim]Reinstale o llama-cpp-python com Vulkan e confirme que o offload está ativo.[/dim]\n"
            "[dim]Use:[/dim] [bold]./scripts/install_llama_cpp_gpu.sh vulkan[/bold]"
        )
        raise SystemExit(1)

    render_gpu_notice(console, backend)
    chat_loop(vault, profile, voice)


if __name__ == "__main__":
    main()
