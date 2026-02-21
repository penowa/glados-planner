"""
Instalador de modelos GGUF no diretório configurado da aplicação.

Suporta:
- TinyLlama 1.1B (Q4_K_M)
- Qwen3 4B (UD Q4_K_XL)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from core.config.settings import settings


ProgressCallback = Callable[[str, int, int], None]


@dataclass
class ModelSpec:
    key: str
    display_name: str
    repo_id: str
    filename: Optional[str] = None


class ModelInstallError(RuntimeError):
    """Erro de instalação de modelos."""


MODEL_SPECS: Dict[str, ModelSpec] = {
    "tinyllama": ModelSpec(
        key="tinyllama",
        display_name="TinyLlama 1.1B Chat Q4_K_M",
        repo_id="hieupt/TinyLlama-1.1B-Chat-v1.0-Q4_K_M-GGUF",
        filename=None,  # Resolvido automaticamente via API
    ),
    "qwen4b": ModelSpec(
        key="qwen4b",
        display_name="Qwen3 4B UD Q4_K_XL",
        repo_id="unsloth/Qwen3-4B-GGUF",
        filename="Qwen3-4B-UD-Q4_K_XL.gguf",
    ),
}


def normalize_selection(selection: str) -> str:
    value = str(selection or "").strip().lower()
    aliases = {
        "tiny": "tinyllama",
        "tinyllama": "tinyllama",
        "tinyllama_1.1b": "tinyllama",
        "qwen": "qwen4b",
        "qwen4b": "qwen4b",
        "qwen3-4b": "qwen4b",
        "all": "all",
    }
    normalized = aliases.get(value)
    if not normalized:
        raise ModelInstallError(f"Seleção de modelo inválida: {selection}")
    return normalized


def resolve_models_dir(models_dir: Optional[str] = None) -> Path:
    base = Path(models_dir or settings.paths.models_dir).expanduser()
    if not base.is_absolute():
        base = Path(settings.paths.data_dir).parent / base
    base.mkdir(parents=True, exist_ok=True)
    return base.resolve()


def _api_model_url(repo_id: str) -> str:
    # Hugging Face API retorna metadados + arquivos (siblings).
    return f"https://huggingface.co/api/models/{repo_id}"


def _download_url(repo_id: str, filename: str) -> str:
    encoded_file = urllib.parse.quote(filename, safe="/")
    return f"https://huggingface.co/{repo_id}/resolve/main/{encoded_file}?download=true"


def _fetch_repo_gguf_files(repo_id: str, timeout: float = 25.0) -> List[str]:
    req = urllib.request.Request(_api_model_url(repo_id), headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise ModelInstallError(f"Falha ao consultar repositório '{repo_id}': {exc}") from exc

    siblings = payload.get("siblings", []) if isinstance(payload, dict) else []
    files: List[str] = []
    for item in siblings:
        if not isinstance(item, dict):
            continue
        name = str(item.get("rfilename", "")).strip()
        if name.lower().endswith(".gguf"):
            files.append(name)
    return files


def _pick_tinyllama_file(candidates: List[str]) -> str:
    if not candidates:
        raise ModelInstallError("Nenhum arquivo GGUF encontrado no repositório do TinyLlama.")

    preferred_tokens = ("q4_k_m", "tinyllama", "chat")
    ranked = sorted(
        candidates,
        key=lambda name: (
            0 if all(token in name.lower() for token in preferred_tokens) else 1,
            name.lower(),
        ),
    )
    return ranked[0]


def resolve_model_filename(spec: ModelSpec) -> str:
    if spec.filename:
        return spec.filename
    files = _fetch_repo_gguf_files(spec.repo_id)
    if spec.key == "tinyllama":
        return _pick_tinyllama_file(files)
    if not files:
        raise ModelInstallError(f"Nenhum arquivo GGUF encontrado para {spec.display_name}.")
    return sorted(files)[0]


def _download_file(
    url: str,
    target_path: Path,
    progress_callback: Optional[ProgressCallback] = None,
    timeout: float = 30.0,
) -> int:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + ".part")

    req = urllib.request.Request(url, headers={"User-Agent": "glados-model-installer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response, open(temp_path, "wb") as out:
            total_size = int(response.headers.get("Content-Length", "0") or 0)
            downloaded = 0
            last_emit = 0.0
            chunk_size = 1024 * 1024
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                if progress_callback and (now - last_emit >= 0.20):
                    progress_callback(target_path.name, downloaded, total_size)
                    last_emit = now
            if progress_callback:
                progress_callback(target_path.name, downloaded, total_size)
    except urllib.error.URLError as exc:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise ModelInstallError(f"Falha ao baixar '{target_path.name}': {exc}") from exc
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise

    temp_path.replace(target_path)
    return int(target_path.stat().st_size)


def install_models(
    selection: str = "all",
    models_dir: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, object]:
    normalized = normalize_selection(selection)
    targets = ["tinyllama", "qwen4b"] if normalized == "all" else [normalized]
    output_dir = resolve_models_dir(models_dir)

    results: List[Dict[str, object]] = []
    for key in targets:
        spec = MODEL_SPECS[key]
        filename = resolve_model_filename(spec)
        local_path = output_dir / Path(filename).name
        url = _download_url(spec.repo_id, filename)

        if dry_run:
            results.append(
                {
                    "model": key,
                    "display_name": spec.display_name,
                    "filename": Path(filename).name,
                    "path": str(local_path),
                    "url": url,
                    "status": "dry_run",
                }
            )
            continue

        if local_path.exists() and local_path.stat().st_size > 0 and not force:
            results.append(
                {
                    "model": key,
                    "display_name": spec.display_name,
                    "filename": local_path.name,
                    "path": str(local_path),
                    "status": "skipped",
                    "size_bytes": int(local_path.stat().st_size),
                }
            )
            continue

        size_bytes = _download_file(
            url=url,
            target_path=local_path,
            progress_callback=progress_callback,
        )
        results.append(
            {
                "model": key,
                "display_name": spec.display_name,
                "filename": local_path.name,
                "path": str(local_path),
                "status": "downloaded",
                "size_bytes": size_bytes,
            }
        )

    downloaded = [item for item in results if item.get("status") == "downloaded"]
    skipped = [item for item in results if item.get("status") == "skipped"]
    dry_items = [item for item in results if item.get("status") == "dry_run"]
    return {
        "selection": normalized,
        "models_dir": str(output_dir),
        "results": results,
        "downloaded_count": len(downloaded),
        "skipped_count": len(skipped),
        "dry_run_count": len(dry_items),
    }
