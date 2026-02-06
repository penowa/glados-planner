# [file name]: src/core/modules/reading_manager.py
"""
Gerenciador de leituras filosóficas
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

@dataclass
class ReadingProgress:
    """Progresso de leitura de um livro"""
    book_id: str
    title: str
    author: str
    total_pages: int
    current_page: int
    start_date: str
    last_read: str
    reading_speed: float  # páginas por dia
    estimated_completion: str
    notes: List[str]

class ReadingManager:
    """Gerencia leituras e progresso"""
    
    def __init__(self, vault_path: str = None):
        """
        Inicializa o gerenciador de leituras
        
        Args:
            vault_path: Caminho para o vault do Obsidian
        """
        from pathlib import Path
        import os
        if vault_path is None:
            try:
                from ...config.settings import settings
                vault_path = settings.paths.vault
            except (ImportError, AttributeError):
                # Fallback para caminho padrão
                vault_path = os.path.expanduser("~/Documentos/Obsidian/Philosophy_Vault")
        self.vault_path = Path(vault_path).expanduser()
        self.progress_file = self.vault_path / "01-LEITURAS" / "progresso_leitura.json"
        
        # Carrega progresso existente - garante que seja um dicionário
        self.readings = self._load_progress()
        if not isinstance(self.readings, dict):
            self.readings = {}
    
    def _load_progress(self) -> Dict[str, ReadingProgress]:
        """Carrega progresso de leitura do arquivo"""
        readings = {}
        
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Garante que data seja um dicionário
                if not isinstance(data, dict):
                    print(f"Formato inválido no arquivo {self.progress_file}. Esperado dicionário.")
                    return {}
                    
                for book_id, book_data in data.items():
                    # Garante que book_data seja um dicionário
                    if isinstance(book_data, dict):
                        readings[book_id] = ReadingProgress(
                            book_id=book_id,
                            title=book_data.get('title', ''),
                            author=book_data.get('author', ''),
                            total_pages=book_data.get('total_pages', 0),
                            current_page=book_data.get('current_page', 0),
                            start_date=book_data.get('start_date', ''),
                            last_read=book_data.get('last_read', ''),
                            reading_speed=book_data.get('reading_speed', 10.0),
                            estimated_completion=book_data.get('estimated_completion', ''),
                            notes=book_data.get('notes', [])
                        )
            except Exception as e:
                print(f"Erro ao carregar progresso: {e}")
        
        return readings
    
    def _save_progress(self):
        """Salva progresso de leitura no arquivo"""
        try:
            data = {}
            for book_id, progress in self.readings.items():
                data[book_id] = {
                    'title': progress.title,
                    'author': progress.author,
                    'total_pages': progress.total_pages,
                    'current_page': progress.current_page,
                    'start_date': progress.start_date,
                    'last_read': progress.last_read,
                    'reading_speed': progress.reading_speed,
                    'estimated_completion': progress.estimated_completion,
                    'notes': progress.notes
                }
            
            # Garante que o diretório existe
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar progresso: {e}")
    
    def get_reading_progress(self, book_id: str = None) -> Dict:
        """
        Obtém progresso de leitura
        
        Args:
            book_id: ID do livro (opcional, retorna todos se None)
            
        Returns:
            Progresso de leitura
        """
        if book_id:
            progress = self.readings.get(book_id)
            if progress:
                return {
                    "id": progress.book_id,
                    "book_id": progress.book_id,
                    "title": progress.title,
                    "progress": f"{progress.current_page}/{progress.total_pages}",
                    "percentage": (progress.current_page / progress.total_pages * 100) if progress.total_pages > 0 else 0,
                    "reading_speed": progress.reading_speed,
                    "estimated_completion": progress.estimated_completion
                }
            return {}
        else:
            result = {}
            for book_id, progress in self.readings.items():
                result[book_id] = {
                    "id": progress.book_id,
                    "book_id": progress.book_id,
                    "title": progress.title,
                    "progress": f"{progress.current_page}/{progress.total_pages}",
                    "percentage": (progress.current_page / progress.total_pages * 100) if progress.total_pages > 0 else 0,
                    "reading_speed": progress.reading_speed,
                    "estimated_completion": progress.estimated_completion
                }
            return result
    
    def update_progress(self, book_id: str, current_page: int, notes: str = "") -> bool:
        """
        Atualiza progresso de leitura
        
        Args:
            book_id: ID do livro
            current_page: Página atual
            notes: Notas sobre a leitura (opcional)
            
        Returns:
            True se atualizado com sucesso
        """
        if book_id not in self.readings:
            # Cria novo registro se não existir
            # Tenta obter informações do vault
            book_info = self._get_book_info_from_vault(book_id)
            if not book_info:
                return False
            
            self.readings[book_id] = ReadingProgress(
                book_id=book_id,
                title=book_info.get('title', 'Desconhecido'),
                author=book_info.get('author', 'Desconhecido'),
                total_pages=book_info.get('total_pages', 300),
                current_page=current_page,
                start_date=datetime.now().isoformat(),
                last_read=datetime.now().isoformat(),
                reading_speed=10.0,  # padrão
                estimated_completion=self._calculate_estimated_completion(book_id, current_page),
                notes=[notes] if notes else []
            )
        else:
            # Atualiza registro existente
            progress = self.readings[book_id]
            progress.current_page = current_page
            progress.last_read = datetime.now().isoformat()
            
            if notes:
                progress.notes.append(f"{datetime.now().strftime('%Y-%m-%d')}: {notes}")
            
            # Recalcula velocidade de leitura
            self._update_reading_speed(book_id)
            
            # Recalcula estimativa de conclusão
            progress.estimated_completion = self._calculate_estimated_completion(book_id, current_page)
        
        # Salva alterações
        self._save_progress()
        return True
    
    def generate_schedule(self, book_id: str, target_date: str = None) -> Dict:
        """
        Gera cronograma de leitura
        
        Args:
            book_id: ID do livro
            target_date: Data alvo para conclusão (opcional)
            
        Returns:
            Cronograma de leitura
        """
        if book_id not in self.readings:
            return {"error": "Livro não encontrado"}
        
        progress = self.readings[book_id]
        pages_remaining = progress.total_pages - progress.current_page
        
        if pages_remaining <= 0:
            return {"message": "Livro já concluído", "pages_remaining": 0}
        
        # Define data alvo
        if target_date:
            try:
                target = datetime.fromisoformat(target_date)
            except:
                target = datetime.now() + timedelta(days=30)  # padrão: 30 dias
        else:
            target = datetime.now() + timedelta(days=30)
        
        # Calcula dias restantes
        days_remaining = (target - datetime.now()).days
        if days_remaining <= 0:
            days_remaining = 1
        
        # Calcula páginas por dia
        pages_per_day = pages_remaining / days_remaining
        
        # Gera cronograma diário
        schedule = []
        current_date = datetime.now()
        cumulative_pages = progress.current_page
        
        for day in range(days_remaining):
            target_pages = progress.current_page + (day + 1) * pages_per_day
            if target_pages > progress.total_pages:
                target_pages = progress.total_pages
            
            schedule.append({
                "day": day + 1,
                "date": (current_date + timedelta(days=day)).strftime("%Y-%m-%d"),
                "target_pages": round(target_pages),
                "pages_to_read": round(target_pages - cumulative_pages)
            })
            cumulative_pages = target_pages
            
            if cumulative_pages >= progress.total_pages:
                break
        
        return {
            "book": progress.title,
            "author": progress.author,
            "current_progress": f"{progress.current_page}/{progress.total_pages}",
            "pages_remaining": pages_remaining,
            "days_remaining": days_remaining,
            "pages_per_day": round(pages_per_day, 1),
            "target_completion": target.strftime("%Y-%m-%d"),
            "daily_schedule": schedule
        }
    
    def _get_book_info_from_vault(self, book_id: str) -> Optional[Dict]:
        """Obtém informações do livro do vault"""
        # Procura arquivo do livro no vault
        book_files = list(self.vault_path.glob(f"**/*{book_id}*.md"))
        
        if book_files:
            try:
                content = book_files[0].read_text(encoding='utf-8')
                
                import re
                # Extrai metadados do frontmatter
                title_match = re.search(r'title:\s*"([^"]+)"', content)
                author_match = re.search(r'author:\s*"([^"]+)"', content)
                pages_match = re.search(r'pages:\s*(\d+)', content)
                
                return {
                    'title': title_match.group(1) if title_match else book_files[0].stem,
                    'author': author_match.group(1) if author_match else 'Desconhecido',
                    'total_pages': int(pages_match.group(1)) if pages_match else 300
                }
            except:
                pass
        
        return None
    
    def _update_reading_speed(self, book_id: str):
        """Atualiza velocidade de leitura baseado no histórico"""
        if book_id not in self.readings:
            return
        
        progress = self.readings[book_id]
        
        # Tenta calcular velocidade baseada no progresso
        try:
            start_date = datetime.fromisoformat(progress.start_date)
            current_date = datetime.now()
            days_elapsed = (current_date - start_date).days + 1  # +1 para evitar divisão por zero
            
            if days_elapsed > 0 and progress.current_page > 0:
                progress.reading_speed = progress.current_page / days_elapsed
        except:
            progress.reading_speed = 10.0  # valor padrão
    
    def _calculate_estimated_completion(self, book_id: str, current_page: int) -> str:
        """Calcula data estimada de conclusão"""
        if book_id not in self.readings:
            return "Desconhecido"
        
        progress = self.readings[book_id]
        pages_remaining = progress.total_pages - current_page
        
        if pages_remaining <= 0:
            return "Concluído"
        
        if progress.reading_speed <= 0:
            return "Indefinido"
        
        days_remaining = pages_remaining / progress.reading_speed
        completion_date = datetime.now() + timedelta(days=days_remaining)
        
        return completion_date.strftime("%Y-%m-%d")
    
    def get_recommended_reading_time(self) -> Dict:
        """
        Calcula tempo de leitura recomendado baseado no progresso
        
        Returns:
            Recomendações de tempo de leitura
        """
        recommendations = {}
        
        for book_id, progress in self.readings.items():
            if progress.current_page < progress.total_pages:
                pages_remaining = progress.total_pages - progress.current_page
                
                # Tempo baseado na velocidade
                if progress.reading_speed > 0:
                    days_needed = pages_remaining / progress.reading_speed
                    daily_minutes = (60 / progress.reading_speed) * 10  # estimativa: 10 páginas/hora
                    
                    recommendations[book_id] = {
                        "title": progress.title,
                        "daily_minutes": round(daily_minutes),
                        "days_to_complete": round(days_needed),
                        "priority": "alta" if days_needed < 7 else "média" if days_needed < 30 else "baixa"
                    }
        
        return recommendations
    
    def add_book(self, title: str, author: str, total_pages: int, book_id: str = None) -> str:
        """
        Adiciona um novo livro ao sistema de leitura
        
        Args:
            title: Título do livro
            author: Autor
            total_pages: Total de páginas
            book_id: ID opcional (gera automaticamente se None)
            
        Returns:
            ID do livro
        """
        if book_id is None:
            # Gera ID baseado no título
            import hashlib
            book_id = hashlib.md5(title.encode()).hexdigest()[:8]
        
        if book_id not in self.readings:
            self.readings[book_id] = ReadingProgress(
                book_id=book_id,
                title=title,
                author=author,
                total_pages=total_pages,
                current_page=0,
                start_date=datetime.now().isoformat(),
                last_read="",
                reading_speed=10.0,
                estimated_completion="",
                notes=[]
            )
            self._save_progress()
        
        return book_id
    
    def list_books(self, include_progress: bool = True) -> List[Dict]:
        """
        Lista todos os livros registrados
        
        Args:
            include_progress: Se True, inclui informações de progresso
            
        Returns:
            Lista de livros
        """
        books = []
        
        for book_id, progress in self.readings.items():
            book_info = {
                "id": book_id,
                "title": progress.title,
                "author": progress.author,
                "total_pages": progress.total_pages
            }
            
            if include_progress:
                book_info.update({
                    "current_page": progress.current_page,
                    "percentage": (progress.current_page / progress.total_pages * 100) if progress.total_pages > 0 else 0,
                    "last_read": progress.last_read,
                    "reading_speed": progress.reading_speed
                })
            
            books.append(book_info)
        
        return books
    
    def stats(self) -> Dict:
        """
        Retorna estatísticas de leitura
        
        Returns:
            Estatísticas detalhadas
        """
        # Garante que self.readings é um dicionário
        if not isinstance(self.readings, dict):
            print(f"Aviso: self.readings não é um dicionário. Tipo: {type(self.readings)}")
            return {"error": "Formato de dados inválido"}
        
        total_books = len(self.readings)
        completed_books = sum(1 for p in self.readings.values() if p.current_page >= p.total_pages)
        in_progress = total_books - completed_books
        
        total_pages_read = sum(p.current_page for p in self.readings.values())
        total_pages = sum(p.total_pages for p in self.readings.values())
        
        avg_speed = sum(p.reading_speed for p in self.readings.values()) / total_books if total_books > 0 else 0
        
        # Estatísticas por tempo
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        recent_pages = 0
        for progress in self.readings.values():
            if progress.last_read >= week_ago:
                recent_pages += progress.current_page
        
        return {
            "total_books": total_books,
            "completed_books": completed_books,
            "books_in_progress": in_progress,
            "total_pages_read": total_pages_read,
            "total_pages": total_pages,
            "completion_percentage": (total_pages_read / total_pages * 100) if total_pages > 0 else 0,
            "average_reading_speed": avg_speed,
            "pages_last_week": recent_pages,
            "estimated_time_to_complete": self._calculate_total_completion_time()
        }
    
    def _calculate_total_completion_time(self) -> str:
        """Calcula tempo total estimado para completar todas as leituras"""
        total_days = 0
        for progress in self.readings.values():
            pages_remaining = progress.total_pages - progress.current_page
            if pages_remaining > 0 and progress.reading_speed > 0:
                total_days += pages_remaining / progress.reading_speed
        
        if total_days <= 0:
            return "Nenhuma leitura pendente"
        
        if total_days < 1:
            return f"{int(total_days * 24)} horas"
        elif total_days < 30:
            return f"{int(total_days)} dias"
        else:
            months = total_days / 30
            return f"{months:.1f} meses"

    def reading_controller(self):
        """Compatibilidade para código legado"""
        return self
    
   
