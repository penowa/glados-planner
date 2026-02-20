# 📚 Planner Glados

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?logo=arch-linux&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Um sistema integrado de gestão acadêmica para estudantes**

*Organize leituras, agenda, anotações e análises com IA local*

</div>

##  Features

-  **Gestão Inteligente de Leituras** - Cronograma, progresso, revisão espaçada
-  **Agenda** - Calendário acadêmico integrado
-  **Assistente LLM Local** - Análise de textos com modelos privados
-  **Integração Obsidian** - Sincronia bidirecional com seu vault
-  **Pomodoro** - Foco com citações inspiradoras
-  **Tradução & Glossário** - Termos técnicos em grego/alemão
-  **Estatísticas** - Analytics de produtividade e aprendizado

## Quick Start

### Pré-requisitos
- Arch Linux (otimizado para Hyprland/Wayland)
- Python 3.11+
- Obsidian (opcional, mas recomendado)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/penowa/glados-planner.git
cd glados-planner

# Configure o ambiente
chmod +x setup.sh
./setup.sh

# Ative o ambiente virtual
source venv/bin/activate  # bash/zsh
# ou
source venv/bin/activate.fish  # fish

# Instale dependências
pip install -r requirements.txt

# (Opcional) Stack de embeddings/NLP pesado
pip install -r requirements-nlp.txt

# Configure seu ambiente
cp .env.example .env
# Edite .env com suas configurações

# Inicialize o banco de dados
python -m src.cli.init_db
```

### LLM local na GPU (GTX 750 Ti)

```bash
source venv/bin/activate
./scripts/install_llama_cpp_gpu.sh vulkan
```

- Para GTX 750 Ti, use `vulkan` por padrão.
- `cuda` só funciona com toolkit que ainda suporte `compute_50` (CUDA 13+ não suporta).
- Mantenha `llm.n_gpu_layers` em `config/settings.yaml` maior que `0` para offload de camadas.

## Build de Release (PyInstaller)

```bash
# Instale dependências para empacotamento
pip install -r requirements-release.txt

# Gere o executável (formato onedir)
./scripts/build_release.sh

# Gere artefato .tar.gz + checksum para GitHub Release
./scripts/package_release_artifacts.sh v1.0.0
```

Artefato de saída: `dist/glados-planner/`
