#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "PyInstaller nao encontrado. Instale com:"
  echo "  pip install -r requirements-release.txt"
  exit 1
fi

echo "Gerando build de release (onedir)..."
pyinstaller --noconfirm --clean glados.spec

echo
echo "Build finalizado em: dist/glados-planner/"
