# scripts/init_database.py
#!/usr/bin/env python3
"""
Script para inicializar o banco de dados.
"""

import sys
from pathlib import Path
from sqlalchemy import text  # Adicionar esta importação

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database.base import init_db, engine
from src.core.config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Inicializa o banco de dados."""
    logger.info("Inicializando banco de dados...")
    
    # Garante que o diretório existe
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        init_db()
        logger.info(f"Banco de dados criado em: {settings.database_url}")
        
        # Testa a conexão - CORRIGIDO: usar text() para queries SQL
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))  # Adicionar text()
            row = result.fetchone()
            if row and row[0] == 1:
                logger.info("Conexão com banco de dados testada com sucesso!")
            else:
                logger.warning("Teste de conexão retornou resultado inesperado")
            
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
