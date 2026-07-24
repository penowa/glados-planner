# 📚 Meu Assistente de Notas - MAN

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?logo=arch-linux&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Fiz esse sistema para gerenciar minha carga de leitura na faculdade**

*Organize uma biblioteca, agenda, anotações, e gráficos*

</div>

## Features Ferramentas

- **Gestão de carga de Leituras** - 
- **Agenda** - Calendário integrado
- **Integração Obsidian** - Gerenciador de notas .md
- **Estatísticas** - Analytics de produtividade com base em um diário

## 🚀 Como instalar

### Pré-requisitos
- Até hoje só usei no Arch Linux (otimizado para Hyprland/Wayland)
- Python 3.11+
- Obsidian (opcional, mas recomendo)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/philosophy-planner.git
cd glados-planner

# Configure o ambiente
chmod +x setup.sh
./setup.sh

# Ative o ambiente virtual
source venv/bin/activate  # bash/zsh
# ou
source venv/bin/activate.fish  # fish

# Tem alguns scripts com algumas ferramentas úteis
cd scripts/


# Configure seu ambiente
cp .env.example .env
# Edite .env com suas configurações

# Inicialize o banco de dados
python -m src.cli.init_db
