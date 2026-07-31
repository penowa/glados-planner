#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${PROJECT_DIR}/venv/bin/python"
VENV_PIP="${PROJECT_DIR}/venv/bin/pip"

BACKEND="${1:-${LLAMA_BACKEND:-vulkan}}"
CUDA_ARCH="${CUDA_ARCH:-50}"
ARCH_SPIRV_HEADERS_HINT="sudo pacman -S spirv-headers"

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

if [[ "${BACKEND}" == "vulkan" ]] && command -v pacman >/dev/null 2>&1; then
  if ! pacman -Qq spirv-headers >/dev/null 2>&1; then
    echo "Aviso: o pacote 'spirv-headers' não está instalado."
    echo "No Arch, instale com: ${ARCH_SPIRV_HEADERS_HINT}"
    echo "Sem isso, o backend Vulkan do llama-cpp-python não compila."
  fi
fi

echo "Instalando llama-cpp-python com backend: ${BACKEND}"
if [[ -n "${CMAKE_ARGS_VALUE}" ]]; then
  GGML_VK_PREFER_HOST_MEMORY=1 CMAKE_ARGS="${CMAKE_ARGS_VALUE}" FORCE_CMAKE=1 \
    "${VENV_PIP}" install --upgrade --force-reinstall --no-cache-dir --no-binary llama-cpp-python llama-cpp-python
else
  GGML_VK_PREFER_HOST_MEMORY=1 "${VENV_PIP}" install --upgrade --force-reinstall --no-cache-dir llama-cpp-python
fi

VERIFY_OUTPUT="$("${VENV_PYTHON}" - <<'PY'
import os
import platform
import sys
import llama_cpp
print("version=" + str(getattr(llama_cpp, "__version__", "unknown")))
print("gpu_offload=" + str(bool(llama_cpp.llama_supports_gpu_offload())))
print("prefer_host_memory=" + str(os.environ.get("GGML_VK_PREFER_HOST_MEMORY", "")))
print("python=" + sys.version.replace("\n", " "))
print("platform=" + platform.platform())
print("module=" + str(getattr(llama_cpp, "__file__", "unknown")))
print("cuda_visible_devices=" + str(os.environ.get("CUDA_VISIBLE_DEVICES", "")))
PY
)"

echo "${VERIFY_OUTPUT}"

if ! grep -q '^gpu_offload=True$' <<< "${VERIFY_OUTPUT}"; then
  cat <<EOF
Erro: o build do llama-cpp-python não ficou com offload GPU ativo.
Diagnóstico:
- backend solicitado: ${BACKEND}
- CMAKE_ARGS: ${CMAKE_ARGS_VALUE:-<vazio>}
- Saída: $(printf '%s' "${VERIFY_OUTPUT}" | tr '\n' ' ' | sed 's/  */ /g')

Próximos passos sugeridos:
1. Remova o wheel atual: ${VENV_PIP} uninstall -y llama-cpp-python
2. Garanta dependências de build/Vulkan no sistema
   - No Arch: ${ARCH_SPIRV_HEADERS_HINT}
3. Reexecute: ./scripts/install_llama_cpp_gpu.sh vulkan
EOF
  exit 3
fi

echo "Concluído. GPU offload verificado com sucesso."
