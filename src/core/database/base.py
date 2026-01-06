# src/core/database/base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from pathlib import Path

from ..config.settings import settings

# CORREÇÃO: Usar settings.paths.data_dir em vez de settings.data_dir
data_dir = Path(settings.paths.data_dir)
database_dir = data_dir / "database"

# Cria diretório do banco de dados se não existir
data_dir.mkdir(parents=True, exist_ok=True)
database_dir.mkdir(parents=True, exist_ok=True)

# Engine e Session
engine = create_engine(
    # CORREÇÃO: Usar settings.database.url em vez de settings.database_url
    settings.database.url,
    # CORREÇÃO: Usar settings.database.echo em vez de settings.database_echo
    echo=settings.database.echo,
    connect_args={"check_same_thread": False}  # Para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dependency para obter sessão do banco de dados."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """Inicializa o banco de dados (cria tabelas)."""
    Base.metadata.create_all(bind=engine)
