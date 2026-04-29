#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VENV_DIR="${PROJECT_ROOT}/venv"
INSTALL_DEV=0
INSTALL_NLP=0
INSTALL_RELEASE=0
SKIP_SYSTEM=0
SKIP_PYTHON=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    printf "%b%s%b\n" "${GREEN}" "$1" "${NC}"
}

info() {
    printf "%b%s%b\n" "${BLUE}" "$1" "${NC}"
}

warn() {
    printf "%b%s%b\n" "${YELLOW}" "$1" "${NC}"
}

error() {
    printf "%b%s%b\n" "${RED}" "$1" "${NC}" >&2
}

usage() {
    cat <<EOF
Uso: ./scripts/install_dependencies.sh [opcoes]

Opcoes:
  --with-dev       Instala requirements-dev.txt
  --with-nlp       Instala requirements-nlp.txt
  --with-release   Instala requirements-release.txt
  --skip-system    Nao instala dependencias de sistema
  --skip-python    Nao cria venv nem instala pacotes Python
  -h, --help       Mostra esta ajuda

Exemplos:
  ./scripts/install_dependencies.sh
  ./scripts/install_dependencies.sh --with-dev --with-nlp
  ./scripts/install_dependencies.sh --skip-system
EOF
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

run_as_root() {
    if [ "${EUID}" -eq 0 ]; then
        "$@"
    elif command_exists sudo; then
        sudo "$@"
    else
        error "Este passo precisa de privilegios de administrador e o comando 'sudo' nao foi encontrado."
        exit 1
    fi
}

detect_package_manager() {
    if command_exists pacman; then
        echo "pacman"
    elif command_exists apt-get; then
        echo "apt"
    elif command_exists dnf; then
        echo "dnf"
    else
        echo ""
    fi
}

package_exists() {
    local manager="$1"
    local package="$2"

    case "${manager}" in
        pacman)
            pacman -Si "${package}" >/dev/null 2>&1
            ;;
        apt)
            apt-cache show "${package}" >/dev/null 2>&1
            ;;
        dnf)
            dnf list --available "${package}" >/dev/null 2>&1
            ;;
        *)
            return 1
            ;;
    esac
}

filter_available_packages() {
    local manager="$1"
    shift
    local package

    for package in "$@"; do
        if package_exists "${manager}" "${package}"; then
            printf "%s\n" "${package}"
        else
            warn "Pacote indisponivel no gerenciador atual: ${package}"
        fi
    done
}

install_packages() {
    local manager="$1"
    shift
    local packages=("$@")

    if [ "${#packages[@]}" -eq 0 ]; then
        return 0
    fi

    case "${manager}" in
        pacman)
            run_as_root pacman -Sy --needed "${packages[@]}"
            ;;
        apt)
            run_as_root apt-get install -y "${packages[@]}"
            ;;
        dnf)
            run_as_root dnf install -y "${packages[@]}"
            ;;
        *)
            error "Gerenciador de pacotes nao suportado: ${manager}"
            exit 1
            ;;
    esac
}

install_obsidian_flatpak() {
    if command_exists obsidian; then
        info "Obsidian ja esta disponivel no sistema."
        return 0
    fi

    if ! command_exists flatpak; then
        warn "Flatpak nao encontrado. O Obsidian precisara ser instalado manualmente."
        return 0
    fi

    info "Instalando Obsidian via Flatpak..."
    run_as_root flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    run_as_root flatpak install -y flathub md.obsidian.Obsidian
}

install_system_dependencies() {
    local manager
    manager="$(detect_package_manager)"

    if [ -z "${manager}" ]; then
        warn "Nenhum gerenciador de pacotes suportado foi detectado. Pulando dependencias de sistema."
        return 0
    fi

    log "Instalando dependencias de sistema via ${manager}..."

    local base_packages=()
    local obsidian_packages=()
    local zathura_packages=()
    local available_packages=()
    local package

    case "${manager}" in
        pacman)
            base_packages=(
                python
                python-pip
                python-virtualenv
                base-devel
                sqlite
                tesseract
                tesseract-data-eng
                tesseract-data-por
                poppler
                qt6-base
                wl-clipboard
                xclip
            )
            obsidian_packages=(obsidian)
            zathura_packages=(
                zathura
                zathura-pdf-poppler
                zathura-djvu
                zathura-ps
            )
            run_as_root pacman -Sy
            ;;
        apt)
            base_packages=(
                python3
                python3-pip
                python3-venv
                python3-dev
                build-essential
                sqlite3
                libsqlite3-dev
                tesseract-ocr
                tesseract-ocr-eng
                tesseract-ocr-por
                poppler-utils
                libgl1
                libegl1
                libfontconfig1
                libxkbcommon-x11-0
                libdbus-1-3
                libxrender1
                libxi6
                libxcomposite1
                libxdamage1
                libxrandr2
                libxtst6
                libxcb-cursor0
                wl-clipboard
                xclip
                flatpak
            )
            zathura_packages=(
                zathura
                zathura-pdf-poppler
                zathura-djvu
                zathura-ps
            )
            run_as_root apt-get update
            ;;
        dnf)
            base_packages=(
                python3
                python3-pip
                python3-virtualenv
                python3-devel
                gcc
                gcc-c++
                make
                sqlite
                tesseract
                tesseract-langpack-eng
                tesseract-langpack-por
                poppler-utils
                qt6-qtbase
                wl-clipboard
                xclip
                flatpak
            )
            zathura_packages=(
                zathura
                zathura-pdf-poppler
                zathura-djvu
                zathura-ps
            )
            ;;
    esac

    while IFS= read -r package; do
        available_packages+=("${package}")
    done < <(filter_available_packages "${manager}" "${base_packages[@]}" "${obsidian_packages[@]}" "${zathura_packages[@]}")

    install_packages "${manager}" "${available_packages[@]}"

    if [ "${manager}" != "pacman" ]; then
        install_obsidian_flatpak
    elif ! command_exists obsidian; then
        warn "Obsidian nao ficou disponivel via pacote nativo. Tentando fallback com Flatpak."
        install_obsidian_flatpak
    fi
}

install_python_requirements() {
    local python_bin=""

    if command_exists python3; then
        python_bin="python3"
    elif command_exists python; then
        python_bin="python"
    else
        error "Python nao encontrado. Rode novamente sem --skip-system ou instale o Python manualmente."
        exit 1
    fi

    log "Criando ambiente virtual em ${VENV_DIR}..."
    "${python_bin}" -m venv "${VENV_DIR}"

    local pip_bin="${VENV_DIR}/bin/pip"
    local requirements=(
        "${PROJECT_ROOT}/requirements.txt"
    )

    if [ "${INSTALL_DEV}" -eq 1 ]; then
        requirements+=("${PROJECT_ROOT}/requirements-dev.txt")
    fi

    if [ "${INSTALL_NLP}" -eq 1 ]; then
        requirements+=("${PROJECT_ROOT}/requirements-nlp.txt")
    fi

    if [ "${INSTALL_RELEASE}" -eq 1 ]; then
        requirements+=("${PROJECT_ROOT}/requirements-release.txt")
    fi

    info "Atualizando pip, setuptools e wheel..."
    "${pip_bin}" install --upgrade pip setuptools wheel

    local requirement_file
    for requirement_file in "${requirements[@]}"; do
        if [ -f "${requirement_file}" ]; then
            info "Instalando $(basename "${requirement_file}")..."
            "${pip_bin}" install -r "${requirement_file}"
        else
            warn "Arquivo de dependencias nao encontrado: ${requirement_file}"
        fi
    done
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --with-dev)
            INSTALL_DEV=1
            ;;
        --with-nlp)
            INSTALL_NLP=1
            ;;
        --with-release)
            INSTALL_RELEASE=1
            ;;
        --skip-system)
            SKIP_SYSTEM=1
            ;;
        --skip-python)
            SKIP_PYTHON=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Opcao desconhecida: $1"
            usage
            exit 1
            ;;
    esac
    shift
done

cd "${PROJECT_ROOT}"

log "Preparando dependencias do glados-planner..."

if [ "${SKIP_SYSTEM}" -eq 0 ]; then
    install_system_dependencies
else
    warn "Pulando dependencias de sistema por solicitacao."
fi

if [ "${SKIP_PYTHON}" -eq 0 ]; then
    install_python_requirements
else
    warn "Pulando instalacao de dependencias Python por solicitacao."
fi

log "Instalacao concluida."
printf "Ative o ambiente virtual com: source %s/bin/activate\n" "${VENV_DIR}"
