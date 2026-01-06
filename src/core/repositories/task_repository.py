# src/core/repositories/task_repository.py
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, between, select

from ..database.repository import BaseRepository
from ..models.task import Task, TaskType, TaskPriority, RecurrencePattern

class TaskRepository(BaseRepository[Task]):
    """Repositório especializado para operações com tarefas."""
    
    def __init__(self, session=None):
        super().__init__(Task, session)
    
    def find_by_type(self, task_type: TaskType) -> List[Task]:
        """Busca tarefas por tipo."""
        return self.find(task_type=task_type)
    
    def find_by_date_range(self, start_date: date, end_date: date) -> List[Task]:
        """Busca tarefas em um intervalo de datas."""
        stmt = select(self.model).where(
            and_(
                self.model.start_time >= datetime.combine(start_date, datetime.min.time()),
                self.model.start_time <= datetime.combine(end_date, datetime.max.time())
            )
        ).order_by(self.model.start_time)
        
        result = self.session.execute(stmt)
        return result.scalars().all()
    
    def find_today_tasks(self) -> List[Task]:
        """Busca tarefas de hoje."""
        today = date.today()
        return self.find_by_date_range(today, today)
    
    def find_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """Busca tarefas dos próximos dias."""
        today = date.today()
        future = today + timedelta(days=days)
        return self.find_by_date_range(today, future)
    
    def find_overdue_tasks(self) -> List[Task]:
        """Busca tarefas atrasadas."""
        now = datetime.now()
        stmt = select(self.model).where(
            and_(
                self.model.end_time < now,
                self.model.completed == False
            )
        ).order_by(self.model.end_time)
        
        result = self.session.execute(stmt)
        return result.scalars().all()
    
    def find_by_priority(self, priority: int) -> List[Task]:
        """Busca tarefas por prioridade."""
        return self.find(priority=priority)
    
    def complete_task(self, task_id: int) -> Optional[Task]:
        """Marca uma tarefa como completada."""
        return self.update(task_id, 
            completed=True,
            completion_date=datetime.now()
        )
    
    def get_daily_summary(self, target_date: date = None) -> Dict[str, Any]:
        """Retorna resumo das tarefas do dia."""
        if target_date is None:
            target_date = date.today()
        
        tasks = self.find_by_date_range(target_date, target_date)
        
        completed = [t for t in tasks if t.completed]
        pending = [t for t in tasks if not t.completed]
        
        total_duration = sum(t.duration_hours() for t in tasks)
        
        return {
            "date": target_date,
            "total_tasks": len(tasks),
            "completed_tasks": len(completed),
            "pending_tasks": len(pending),
            "completion_rate": round(len(completed) / len(tasks) * 100, 2) if tasks else 0,
            "total_duration_hours": round(total_duration, 2),
            "tasks_by_type": self._group_by_type(tasks)
        }
    
    def _group_by_type(self, tasks: List[Task]) -> Dict[str, int]:
        """Agrupa tarefas por tipo."""
        groups = {}
        for task in tasks:
            type_name = task.task_type.value
            groups[type_name] = groups.get(type_name, 0) + 1
        return groups
