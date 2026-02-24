#!/usr/bin/env python3
"""
Instala modelos GGUF no diretório de modelos da aplicação.

Exemplos:
  ./venv/bin/python scripts/install_llm_models.py --model tinyllama
  ./venv/bin/python scripts/install_llm_models.py --model all
  ./venv/bin/python scripts/install_llm_models.py --model qwen4b --force
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.llm.model_installer import install_models, ModelInstallError  # noqa: E402


def _format_bytes(size: int) -> str:
    value = float(max(0, int(size or 0)))
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    return f"{value:.2f} {units[idx]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Instalador de modelos LLM (GGUF)")
    parser.add_argument(
        "--model",
        default="all",
        choices=["tinyllama", "qwen4b", "all"],
        help="Modelo a baixar",
    )
    parser.add_argument(
        "--models-dir",
        default="",
        help="Diretório de destino dos modelos (opcional)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebaixar mesmo se arquivo já existir",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas resolve URLs/paths sem baixar",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saída em JSON",
    )
    args = parser.parse_args()

    last_log = 0.0

    def on_progress(file_name: str, downloaded: int, total: int):
        nonlocal last_log
        now = time.time()
        if now - last_log < 0.25:
            return
        if total > 0:
            pct = (downloaded / total) * 100.0
            print(
                f"[download] {file_name}: {pct:6.2f}% "
                f"({_format_bytes(downloaded)} / {_format_bytes(total)})",
                flush=True,
            )
        else:
            print(f"[download] {file_name}: {_format_bytes(downloaded)}", flush=True)
        last_log = now

    try:
        report = install_models(
            selection=args.model,
            models_dir=args.models_dir or None,
            force=bool(args.force),
            dry_run=bool(args.dry_run),
            progress_callback=on_progress if (not args.dry_run and not args.json) else None,
        )
    except ModelInstallError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Falha inesperada: {exc}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    print(f"Destino: {report.get('models_dir')}")
    for item in report.get("results", []):
        status = str(item.get("status"))
        name = str(item.get("filename") or item.get("display_name") or item.get("model"))
        path = str(item.get("path", ""))
        size_text = _format_bytes(int(item.get("size_bytes", 0) or 0))
        if status == "downloaded":
            print(f"  - [ok] {name} -> {path} ({size_text})")
        elif status == "skipped":
            print(f"  - [skip] {name} já existe em {path} ({size_text})")
        else:
            print(f"  - [dry] {name} -> {path}")

    print(
        f"Resumo: baixados={report.get('downloaded_count', 0)} | "
        f"existentes={report.get('skipped_count', 0)} | "
        f"dry-run={report.get('dry_run_count', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
