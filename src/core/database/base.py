# src/core/database/base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator

from ..config.settings import settings

# Cria diretório do banco de dados se não existir
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "database").mkdir(parents=True, exist_ok=True)

# Engine e Session
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
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
