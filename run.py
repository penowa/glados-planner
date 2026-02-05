#!/usr/bin/env python3
"""
Script principal para executar o GLaDOS Philosophy Planner
"""
import sys
import os

# Adiciona o diretório atual ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Agora importa e executa a aplicação
from ui.main import main

if __name__ == "__main__":
    sys.exit(main())