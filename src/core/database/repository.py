# src/core/database/repository.py
from typing import Type, TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError

from .base import Base, SessionLocal

T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T]):
    """Repositório base para operações CRUD."""
    
    def __init__(self, model: Type[T], session: Session = None):
        self.model = model
        self._owns_session = session is None
        self.session = session or SessionLocal()
    
    def create(self, **kwargs) -> T:
        """Cria um novo registro."""
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
    
    def get(self, id: int) -> Optional[T]:
        """Busca um registro pelo ID."""
        return self.session.get(self.model, id)
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Busca todos os registros com paginação."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = self.session.execute(stmt)
        return result.scalars().all()
    
    def find(self, **filters) -> List[T]:
        """Busca registros por filtros."""
        stmt = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                if value is not None:
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        result = self.session.execute(stmt)
        return result.scalars().all()
    
    def find_one(self, **filters) -> Optional[T]:
        """Busca um único registro por filtros."""
        stmt = select(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                if value is not None:
                    stmt = stmt.where(getattr(self.model, key) == value)
        
        result = self.session.execute(stmt)
        return result.scalars().first()
    
    def update(self, id: int, **kwargs) -> Optional[T]:
        """Atualiza um registro."""
        try:
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(**kwargs)
                .execution_options(synchronize_session="fetch")
            )
            self.session.execute(stmt)
            self.session.commit()
            return self.get(id)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
    
    def delete(self, id: int) -> bool:
        """Remove um registro."""
        try:
            stmt = delete(self.model).where(self.model.id == id)
            self.session.execute(stmt)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
    
    def count(self) -> int:
        """Conta o total de registros."""
        stmt = select(self.model)
        result = self.session.execute(stmt)
        return len(result.scalars().all())
    
    def exists(self, **filters) -> bool:
        """Verifica se existe um registro com os filtros."""
        return self.find_one(**filters) is not None

    def close(self):
        """Fecha sessão local quando o repositório é dono dela."""
        if self._owns_session and self.session is not None:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
