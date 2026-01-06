# Glados Planner

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?logo=arch-linux&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Um sistema integrado de gestão acadêmica para estudantes**

*Organize leituras, agenda, anotações e análises com LLM local*

</div>

## ✨ Features

- **Gestão Inteligente de Leituras** - Cronograma, progresso, revisão espaçada
- **Agenda Filosófica** - Calendário acadêmico integrado
- **Assistente LLM Local** - Análise de textos com modelos privados
- **Integração Obsidian** - Sincronia bidirecional com seu vault
- **Pomodoro** - Foco com citações inspiradoras
- **Tradução & Glossário** - Termos técnicos em grego/alemão
- **Estatísticas** - Analytics de produtividade e aprendizado

## 🚀 Quick Start

### Pré-requisitos
- Arch Linux (otimizado para Hyprland/Wayland)
- Python 3.11+
- Obsidian (opcional)

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
