#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="${1:-v1.0.0}"
BUILD_DIR="dist/glados-planner"
ARTIFACT_BASENAME="glados-planner-${VERSION}-linux-x86_64"
ARTIFACT_TAR="dist/${ARTIFACT_BASENAME}.tar.gz"
CHECKSUM_FILE="${ARTIFACT_TAR}.sha256"

./scripts/build_release.sh

echo "Empacotando artefato em ${ARTIFACT_TAR}..."
tar -C dist -czf "$ARTIFACT_TAR" "glados-planner"

echo "Gerando checksum SHA256..."
sha256sum "$ARTIFACT_TAR" | tee "$CHECKSUM_FILE"

echo
echo "Release pronta:"
echo " - ${ARTIFACT_TAR}"
echo " - ${CHECKSUM_FILE}"
