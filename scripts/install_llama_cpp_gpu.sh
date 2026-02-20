#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python"
VENV_PIP="${PROJECT_DIR}/venv/bin/pip"

BACKEND="${1:-${LLAMA_BACKEND:-vulkan}}"
CUDA_ARCH="${CUDA_ARCH:-50}"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Erro: ambiente virtual não encontrado em ${PROJECT_DIR}/venv"
  echo "Crie/ative o venv antes: python -m venv venv"
  exit 1
fi

# Alguns ambientes ficam com scripts de pip sem o pacote instalado.
"${VENV_PYTHON}" -m ensurepip --upgrade >/dev/null

case "${BACKEND}" in
  vulkan)
    CMAKE_ARGS_VALUE="-DGGML_VULKAN=ON"
    ;;
  cuda)
    if command -v nvcc >/dev/null 2>&1; then
      CUDA_MAJOR="$(nvcc --version | sed -n 's/.*release \([0-9][0-9]*\)\..*/\1/p' | head -n 1)"
      if [[ -n "${CUDA_MAJOR}" && "${CUDA_MAJOR}" -ge 13 && "${CUDA_ARCH}" -le 50 ]]; then
        echo "Erro: CUDA ${CUDA_MAJOR} não suporta compute_${CUDA_ARCH} (GTX 750 Ti)."
        echo "Use backend Vulkan: ./scripts/install_llama_cpp_gpu.sh vulkan"
        exit 2
      fi
    fi
    CMAKE_ARGS_VALUE="-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCH}"
    ;;
  cpu)
    CMAKE_ARGS_VALUE=""
    ;;
  *)
    echo "Uso: ./scripts/install_llama_cpp_gpu.sh [vulkan|cuda|cpu]"
    exit 1
    ;;
esac

echo "Instalando llama-cpp-python com backend: ${BACKEND}"
if [[ -n "${CMAKE_ARGS_VALUE}" ]]; then
  CMAKE_ARGS="${CMAKE_ARGS_VALUE}" FORCE_CMAKE=1 \
    "${VENV_PIP}" install --upgrade --no-cache-dir llama-cpp-python
else
  "${VENV_PIP}" install --upgrade --no-cache-dir llama-cpp-python
fi

"${VENV_PYTHON}" - <<'PY'
import llama_cpp
print("llama-cpp-python:", getattr(llama_cpp, "__version__", "unknown"))
print("gpu_offload:", llama_cpp.llama_supports_gpu_offload())
PY

echo "Concluído."
