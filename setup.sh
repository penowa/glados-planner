#!/bin/bash
# setup.sh

set -e  # Exit on error

echo "🚀 Configurando Philosophy Planner..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Arch Linux
if ! grep -q "Arch Linux" /etc/os-release 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Aviso: Este setup foi otimizado para Arch Linux${NC}"
fi

# Create directory structure
echo -e "${GREEN}📁 Criando estrutura de diretórios...${NC}"
mkdir -p src/core/{models,database,llm,modules,utils}
mkdir -p src/{api,cli}
mkdir -p config/templates
mkdir -p data/{database,models,exports,cache}
mkdir -p tests/{unit,integration}
mkdir -p docs/{api,guides,examples}
mkdir -p scripts/{deployment,maintenance}
mkdir -p .github/{workflows,ISSUE_TEMPLATE}

# Create essential files
echo -e "${GREEN}📄 Criando arquivos essenciais...${NC}"

# __init__.py files
find src -type d -exec touch {}/__init__.py \;

# Create config files
cat > config/settings.yaml << 'EOF'
# Philosophy Planner - Configuration

app:
  name: "Philosophy Planner"
  version: "0.1.0"
  debug: true
  log_level: "INFO"

paths:
  vault: "~/Documents/Obsidian/Philosophy_Vault"  # Update this path
  data_dir: "./data"
  models_dir: "./data/models"
  exports_dir: "./data/exports"

database:
  url: "sqlite:///data/database/philosophy.db"
  echo: false

llm:
  model_path: "./data/models/philosophy-llama-7b.Q4_K_M.gguf"
  n_ctx: 2048
  n_gpu_layers: 0  # Set based on your GPU
  temperature: 0.7
  top_p: 0.95

obsidian:
  templates_dir: "./config/templates"
  auto_sync: true
  sync_interval: 300  # seconds

pomodoro:
  work_duration: 25
  short_break: 5
  long_break: 15
  sessions_before_long_break: 4

features:
  enable_llm: true
  enable_obsidian_sync: true
  enable_pomodoro: true
  enable_translation: false
EOF

# Create .env.example
cat > .env.example << 'EOF'
# Environment Variables for Philosophy Planner

# App
APP_ENV=development
SECRET_KEY=your-secret-key-here-change-in-production

# Paths
OBSIDIAN_VAULT_PATH=~/Documents/Obsidian/Philosophy_Vault

# LLM
LLM_MODEL_PATH=./data/models/llama-2-7b.Q4_K_M.gguf
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=512

# Database
DATABASE_URL=sqlite:///data/database/philosophy.db

# Optional APIs (for future features)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
GOOGLE_TRANSLATE_KEY=your-key-here
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environments
venv/
env/
.benv/
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project Specific
data/database/*.db
data/exports/*
data/cache/*
!data/database/.keep
!data/exports/.keep
!data/cache/.keep

# Models (large files)
data/models/*
!data/models/.keep
!data/models/README.md

# Environment variables
.env
!.env.example

# Logs
logs/
*.log

# Test coverage
.coverage
htmlcov/
.pytest_cache/

# Jupyter
.ipynb_checkpoints

# Obsidian vault (user specific)
*.obsidian/
EOF

# Create .keep files for git
touch data/database/.keep
touch data/exports/.keep
touch data/cache/.keep
touch data/models/.keep
touch config/templates/.keep

# Create initial README
cat > README.md << 'EOF'
# 📚 Philosophy Planner

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?logo=arch-linux&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Um sistema integrado de gestão acadêmica para estudantes de filosofia**

*Organize leituras, agenda, anotações e análises com IA local*

</div>

## ✨ Features

- 📖 **Gestão Inteligente de Leituras** - Cronograma, progresso, revisão espaçada
- 🗓️ **Agenda Filosófica** - Calendário acadêmico integrado
- 🧠 **Assistente LLM Local** - Análise de textos com modelos privados
- 📝 **Integração Obsidian** - Sincronia bidirecional com seu vault
- ⏱️ **Pomodoro Filosófico** - Foco com citações inspiradoras
- 🌐 **Tradução & Glossário** - Termos técnicos em grego/alemão
- 📊 **Estatísticas** - Analytics de produtividade e aprendizado

## 🚀 Quick Start

### Pré-requisitos
- Arch Linux (otimizado para Hyprland/Wayland)
- Python 3.11+
- Obsidian (opcional, mas recomendado)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/philosophy-planner.git
cd philosophy-planner

# Configure o ambiente
chmod +x setup.sh
./setup.sh

# Ative o ambiente virtual
source venv/bin/activate  # bash/zsh
# ou
source venv/bin/activate.fish  # fish

# Instale dependências
pip install -r requirements.txt

# Configure seu ambiente
cp .env.example .env
# Edite .env com suas configurações

# Inicialize o banco de dados
python -m src.cli.init_db
