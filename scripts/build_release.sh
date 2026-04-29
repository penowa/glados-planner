#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BUILD_TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/glados-build.XXXXXX")"
cleanup() {
  rm -rf "${BUILD_TMP_DIR}"
}
trap cleanup EXIT

# Keep the release build deterministic in offline/headless environments.
export MPLCONFIGDIR="${BUILD_TMP_DIR}/mplconfig"
mkdir -p "${MPLCONFIGDIR}"
export LITELLM_LOCAL_MODEL_COST_MAP="${LITELLM_LOCAL_MODEL_COST_MAP:-true}"

SYNC_DEPS=1
VERIFY_ARCHIVE=1
for arg in "$@"; do
  case "$arg" in
    --skip-deps)
      SYNC_DEPS=0
      ;;
    --skip-verify)
      VERIFY_ARCHIVE=0
      ;;
    *)
      echo "Parametro invalido: $arg"
      echo "Uso: ./scripts/build_release.sh [--skip-deps] [--skip-verify]"
      exit 2
      ;;
  esac
done

if [[ -x "${ROOT_DIR}/venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
else
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "Python nao encontrado."
  exit 1
fi

if [[ "$SYNC_DEPS" -eq 1 ]]; then
  echo "Sincronizando dependencias de release..."
  "${PYTHON_BIN}" -m pip install --upgrade pip
  "${PYTHON_BIN}" -m pip install -r requirements-release.txt
fi

echo "Validando dependencias de build (PyInstaller + Cloud LLM)..."
"${PYTHON_BIN}" - <<'PY'
import importlib
import sys

required = {
    "PyInstaller": "PyInstaller",
    "litellm": "litellm",
    "openai": "openai",
    "backoff": "backoff",
    "multipart": "python-multipart",
    "yaml": "PyYAML",
    "PyQt6": "PyQt6",
}
missing = []
for module_name, display_name in required.items():
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        missing.append(f"- {display_name} ({module_name}): {exc}")

if missing:
    print("Dependencias ausentes para build:")
    print("\n".join(missing))
    print("Execute: python -m pip install -r requirements-release.txt")
    sys.exit(1)

print("Dependencias OK.")
PY

echo "Gerando build de release (onedir)..."
"${PYTHON_BIN}" -m PyInstaller --noconfirm --clean glados.spec

if [[ "$VERIFY_ARCHIVE" -eq 1 ]]; then
  echo "Verificando empacotamento do backend cloud (litellm)..."
  ARCHIVE_LIST_FILE="$(mktemp)"
  "${PYTHON_BIN}" -m PyInstaller.utils.cliutils.archive_viewer -r dist/glados-planner/glados-planner \
    > "${ARCHIVE_LIST_FILE}"
  if ! grep -q "litellm" "${ARCHIVE_LIST_FILE}"; then
    rm -f "${ARCHIVE_LIST_FILE}"
    echo "ERRO: litellm nao foi encontrado no executavel empacotado."
    exit 1
  fi
  if ! grep -q "litellm.litellm_core_utils.tokenizers" "${ARCHIVE_LIST_FILE}"; then
    rm -f "${ARCHIVE_LIST_FILE}"
    echo "ERRO: pacote interno do LiteLLM (litellm.litellm_core_utils.tokenizers) nao foi empacotado."
    exit 1
  fi
  rm -f "${ARCHIVE_LIST_FILE}"
  if [[ ! -f "dist/glados-planner/_internal/litellm/model_prices_and_context_window_backup.json" ]]; then
    echo "ERRO: arquivo de dados do LiteLLM nao foi empacotado."
    exit 1
  fi
  if [[ ! -d "dist/glados-planner/_internal/litellm/litellm_core_utils/tokenizers" ]]; then
    echo "ERRO: arquivos de tokenizer do LiteLLM nao foram empacotados."
    exit 1
  fi
fi

echo
echo "Build finalizado em: dist/glados-planner/"
