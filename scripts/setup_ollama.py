#!/usr/bin/env python3
"""Automacao de setup do Ollama para onboarding.

Fluxo:
1) Descobre binario `ollama`
2) Verifica conectividade em /api/tags
3) Se necessario, inicia `ollama serve`
4) Opcionalmente executa `ollama pull <modelo>`
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlsplit, urlunsplit

DEFAULT_API_BASE = "http://127.0.0.1:11434"
DEFAULT_CLOUD_MODEL = "qwen3.5:cloud"
CONNECT_URL_PATTERN = re.compile(r"https?://ollama\.com/connect[^\s'\"]+")
SIGNED_USER_PATTERN = re.compile(r"signed in as user ['\"]([^'\"]+)['\"]", flags=re.IGNORECASE)


def normalize_api_base(api_base: str) -> str:
    value = str(api_base or "").strip().rstrip("/")
    if not value:
        return DEFAULT_API_BASE
    try:
        parsed = urlsplit(value)
    except Exception:
        return value
    if not parsed.scheme:
        return value
    host = (parsed.hostname or "").strip().lower()
    if host != "localhost":
        return value
    netloc = "127.0.0.1"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)).rstrip("/")


def extract_ollama_model_name(model_text: str) -> str:
    value = str(model_text or "").strip()
    if not value:
        return ""
    if value.lower().startswith("ollama/"):
        _, short = value.split("/", 1)
        return short.strip()
    return value


def find_ollama_binary() -> str | None:
    candidates: list[Path] = []

    env_bin = str(os.environ.get("OLLAMA_BIN", "") or "").strip()
    if env_bin:
        candidates.append(Path(env_bin).expanduser())

    which_bin = shutil.which("ollama")
    if which_bin:
        candidates.append(Path(which_bin))

    candidates.append(Path.home() / ".local" / "bin" / "ollama")
    candidates.append(Path("/usr/bin/ollama"))

    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except Exception:
            resolved = candidate
        if resolved.exists() and os.access(resolved, os.X_OK):
            return str(resolved)
    return None


def check_python_cloud_dependencies() -> dict:
    required_modules = ("litellm", "openai", "backoff", "multipart")
    missing: dict[str, str] = {}
    for module_name in required_modules:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            missing[module_name] = str(exc)
    return {
        "ok": not missing,
        "missing": missing,
    }


def install_python_dependencies(requirements_file: str) -> tuple[bool, str]:
    req_path = Path(requirements_file or "").expanduser()
    if not req_path.is_absolute():
        req_path = Path(__file__).resolve().parents[1] / req_path
    if not req_path.exists():
        return False, f"Arquivo de dependencias nao encontrado: {req_path}"

    install_commands = [
        [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
        [sys.executable, "-m", "pip", "install", "--user", "-r", str(req_path)],
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--user",
            "--break-system-packages",
            "-r",
            str(req_path),
        ],
    ]

    last_error = ""
    for command in install_commands:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"},
        )
        if proc.returncode == 0:
            return True, ""

        stderr = str(proc.stderr or "").strip()
        stdout = str(proc.stdout or "").strip()
        detail = stderr or stdout or f"codigo {proc.returncode}"
        last_error = detail

        lower_detail = detail.lower()
        if "not recognized" in lower_detail and "--break-system-packages" in " ".join(command):
            # pip antigo: ignora tentativa com flag nao suportada.
            continue

    return False, f"Falha ao instalar dependencias Python: {last_error}"


def extract_connect_url(text: str) -> str:
    match = CONNECT_URL_PATTERN.search(str(text or ""))
    return str(match.group(0)).strip() if match else ""


def extract_signed_user(text: str) -> str:
    match = SIGNED_USER_PATTERN.search(str(text or ""))
    return str(match.group(1)).strip() if match else ""


def probe_ollama(api_base: str, timeout_seconds: float = 2.0) -> dict:
    target = normalize_api_base(api_base)
    url = f"{target}/api/tags"
    req = urllib_request.Request(url, method="GET")
    opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))

    try:
        with opener.open(req, timeout=max(0.5, float(timeout_seconds))) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(body or "{}")
        models_payload = payload.get("models", []) if isinstance(payload, dict) else []
        names: list[str] = []
        for item in models_payload:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if name:
                    names.append(name)

        return {
            "reachable": True,
            "api_base": target,
            "models": names,
            "models_count": len(names),
            "error": "",
        }
    except urllib_error.URLError as exc:
        return {
            "reachable": False,
            "api_base": target,
            "models": [],
            "models_count": 0,
            "error": str(getattr(exc, "reason", exc)),
        }
    except Exception as exc:
        return {
            "reachable": False,
            "api_base": target,
            "models": [],
            "models_count": 0,
            "error": str(exc),
        }


def start_ollama_serve(ollama_bin: str, api_base: str) -> subprocess.Popen:
    env = os.environ.copy()
    env["OLLAMA_HOST"] = normalize_api_base(api_base)
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": env,
    }
    if os.name != "nt":
        kwargs["start_new_session"] = True
    return subprocess.Popen([ollama_bin, "serve"], **kwargs)


def wait_until_reachable(api_base: str, timeout_seconds: float = 18.0) -> dict:
    deadline = time.time() + max(1.0, float(timeout_seconds))
    while time.time() < deadline:
        report = probe_ollama(api_base=api_base, timeout_seconds=1.5)
        if report.get("reachable"):
            return report
        time.sleep(0.35)
    return probe_ollama(api_base=api_base, timeout_seconds=1.5)


def pull_model(ollama_bin: str, api_base: str, model_name: str, timeout_seconds: int) -> dict:
    env = os.environ.copy()
    env["OLLAMA_HOST"] = normalize_api_base(api_base)
    proc = subprocess.run(
        [ollama_bin, "pull", model_name],
        capture_output=True,
        text=True,
        env=env,
        timeout=max(10, int(timeout_seconds)),
        check=False,
    )

    stdout = str(proc.stdout or "").strip()
    stderr = str(proc.stderr or "").strip()
    if proc.returncode != 0:
        error = stderr or stdout or f"ollama pull retornou codigo {proc.returncode}"
        return {"ok": False, "error": error, "stdout": stdout, "stderr": stderr}

    return {"ok": True, "error": "", "stdout": stdout, "stderr": stderr}


def run_signin(ollama_bin: str, timeout_seconds: int) -> dict:
    try:
        proc = subprocess.run(
            [ollama_bin, "signin"],
            capture_output=True,
            text=True,
            timeout=max(15, int(timeout_seconds)),
            check=False,
        )
        stdout = str(proc.stdout or "").strip()
        stderr = str(proc.stderr or "").strip()
        combined = "\n".join(part for part in (stdout, stderr) if part).strip()
        connect_url = extract_connect_url(combined)
        user_name = extract_signed_user(combined)
        if proc.returncode != 0:
            detail = stderr or stdout or f"ollama signin retornou codigo {proc.returncode}"
            return {
                "ok": False,
                "error": detail,
                "signin_url": connect_url,
                "signed_user": user_name,
            }
        return {
            "ok": True,
            "error": "",
            "signin_url": connect_url,
            "signed_user": user_name,
        }
    except subprocess.TimeoutExpired as exc:
        partial = "\n".join(
            part for part in (str(exc.stdout or "").strip(), str(exc.stderr or "").strip()) if part
        ).strip()
        connect_url = extract_connect_url(partial)
        return {
            "ok": False,
            "error": "Timeout no 'ollama signin'. Conclua o login no navegador e tente novamente.",
            "signin_url": connect_url,
            "signed_user": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Falha ao executar 'ollama signin': {exc}",
            "signin_url": "",
            "signed_user": "",
        }


def to_stdout_json(payload: dict):
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup automatizado do Ollama para onboarding")
    parser.add_argument("--model", default=DEFAULT_CLOUD_MODEL, help="Modelo a garantir no Ollama")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="Host do Ollama")
    parser.add_argument("--timeout-seconds", type=int, default=20, help="Timeout para aguardar servico")
    parser.add_argument("--pull-timeout-seconds", type=int, default=1800, help="Timeout do ollama pull")
    parser.add_argument("--signin-timeout-seconds", type=int, default=900, help="Timeout para ollama signin")
    parser.add_argument("--skip-pull", action="store_true", help="Nao baixar modelo")
    parser.add_argument("--signin", action="store_true", help="Executa login no Ollama antes do pull")
    parser.add_argument("--no-start", action="store_true", help="Nao iniciar ollama serve automaticamente")
    parser.add_argument(
        "--install-python-deps",
        action="store_true",
        help="Instala dependencias cloud (litellm/openai) antes do setup",
    )
    parser.add_argument(
        "--python-deps-file",
        default="requirements-llm.txt",
        help="Arquivo de dependencias para --install-python-deps",
    )
    parser.add_argument(
        "--skip-python-deps-check",
        action="store_true",
        help="Nao valida dependencias Python do backend cloud",
    )
    parser.add_argument("--json", action="store_true", help="Saida em JSON")
    args = parser.parse_args()

    api_base = normalize_api_base(args.api_base)
    model_name = extract_ollama_model_name(args.model)

    report = {
        "ok": False,
        "api_base": api_base,
        "model": model_name,
        "ollama_bin": "",
        "service_reachable": False,
        "service_was_running": False,
        "service_started": False,
        "signin_attempted": False,
        "signin_ok": False,
        "signin_user": "",
        "signin_url": "",
        "model_already_available": False,
        "model_pulled": False,
        "models_count": 0,
        "python_deps_ok": True,
        "python_deps_missing": [],
        "python_deps_error": "",
        "error": "",
    }

    if args.install_python_deps:
        ok, install_error = install_python_dependencies(args.python_deps_file)
        if not ok:
            report["error"] = install_error
            report["python_deps_ok"] = False
            report["python_deps_error"] = install_error
            if args.json:
                to_stdout_json(report)
            else:
                print(f"Erro: {report['error']}", file=sys.stderr)
            return 7

    if not args.skip_python_deps_check:
        deps_report = check_python_cloud_dependencies()
        report["python_deps_ok"] = bool(deps_report.get("ok", False))
        missing_map = deps_report.get("missing") or {}
        report["python_deps_missing"] = sorted(list(missing_map.keys()))
        if not report["python_deps_ok"]:
            details = "; ".join(f"{name}: {err}" for name, err in missing_map.items())
            report["python_deps_error"] = details
            report["error"] = (
                "Dependencias Python do backend cloud estao ausentes. "
                "Execute: python -m pip install -r requirements-llm.txt"
            )
            if details:
                report["error"] += f" ({details})"
            if args.json:
                to_stdout_json(report)
            else:
                print(f"Erro: {report['error']}", file=sys.stderr)
            return 7

    if not model_name and not args.skip_pull:
        report["error"] = "Modelo Ollama invalido."
        if args.json:
            to_stdout_json(report)
        else:
            print(f"Erro: {report['error']}", file=sys.stderr)
        return 2

    ollama_bin = find_ollama_binary()
    if not ollama_bin:
        report["error"] = "Binario 'ollama' nao encontrado no PATH."
        if args.json:
            to_stdout_json(report)
        else:
            print(f"Erro: {report['error']}", file=sys.stderr)
        return 2

    report["ollama_bin"] = ollama_bin

    probe = probe_ollama(api_base=api_base, timeout_seconds=2.0)
    if probe.get("reachable"):
        report["service_reachable"] = True
        report["service_was_running"] = True
        report["models_count"] = int(probe.get("models_count", 0) or 0)
    elif not args.no_start:
        try:
            serve_proc = start_ollama_serve(ollama_bin=ollama_bin, api_base=api_base)
            report["service_started"] = True
            probe = wait_until_reachable(api_base=api_base, timeout_seconds=args.timeout_seconds)
            if not probe.get("reachable") and serve_proc.poll() is not None:
                report["error"] = "Falha ao iniciar 'ollama serve'."
            else:
                report["service_reachable"] = bool(probe.get("reachable", False))
                report["models_count"] = int(probe.get("models_count", 0) or 0)
        except Exception as exc:
            report["error"] = f"Falha ao iniciar Ollama automaticamente: {exc}"
    else:
        report["error"] = (
            "Ollama indisponivel e inicio automatico desativado (--no-start)."
        )

    if not report["service_reachable"]:
        if not report["error"]:
            report["error"] = (
                f"Nao foi possivel conectar ao Ollama em {api_base}."
            )
        if args.json:
            to_stdout_json(report)
        else:
            print(f"Erro: {report['error']}", file=sys.stderr)
        return 3

    if args.signin:
        report["signin_attempted"] = True
        signin_result = run_signin(
            ollama_bin=ollama_bin,
            timeout_seconds=args.signin_timeout_seconds,
        )
        report["signin_ok"] = bool(signin_result.get("ok", False))
        report["signin_user"] = str(signin_result.get("signed_user", "") or "")
        report["signin_url"] = str(signin_result.get("signin_url", "") or "")
        if not report["signin_ok"]:
            report["error"] = str(signin_result.get("error") or "Falha no login do Ollama.")
            if args.json:
                to_stdout_json(report)
            else:
                print(f"Erro: {report['error']}", file=sys.stderr)
                if report["signin_url"]:
                    print(f"Conecte sua conta em: {report['signin_url']}", file=sys.stderr)
            return 6

    if args.skip_pull:
        report["ok"] = True
        if args.json:
            to_stdout_json(report)
        else:
            print(f"Ollama conectado em {api_base} (sem pull).")
        return 0

    current_models = set(str(name).strip() for name in probe.get("models", []) if str(name).strip())
    if model_name in current_models:
        report["model_already_available"] = True
        report["ok"] = True
        if args.json:
            to_stdout_json(report)
        else:
            print(f"Modelo '{model_name}' ja disponivel no Ollama.")
        return 0

    pull_result = pull_model(
        ollama_bin=ollama_bin,
        api_base=api_base,
        model_name=model_name,
        timeout_seconds=args.pull_timeout_seconds,
    )
    if not pull_result.get("ok"):
        report["error"] = str(pull_result.get("error") or "Falha no ollama pull.")
        if args.json:
            to_stdout_json(report)
        else:
            print(f"Erro: {report['error']}", file=sys.stderr)
        return 4

    probe_after_pull = probe_ollama(api_base=api_base, timeout_seconds=2.0)
    report["service_reachable"] = bool(probe_after_pull.get("reachable", False))
    report["models_count"] = int(probe_after_pull.get("models_count", 0) or 0)

    after_models = set(
        str(name).strip() for name in probe_after_pull.get("models", []) if str(name).strip()
    )
    if model_name in after_models:
        report["model_pulled"] = True
        report["ok"] = True
    else:
        report["error"] = (
            f"Ollama respondeu, mas o modelo '{model_name}' nao apareceu em /api/tags apos o pull."
        )

    if args.json:
        to_stdout_json(report)
    else:
        if report["ok"]:
            print(
                f"Ollama pronto em {api_base}; modelo '{model_name}' disponivel. "
                f"Modelos detectados: {report['models_count']}"
            )
        else:
            print(f"Erro: {report['error']}", file=sys.stderr)

    return 0 if report["ok"] else 5


if __name__ == "__main__":
    raise SystemExit(main())
