"""
Controller para integração do dashboard com backend real
"""
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from datetime import datetime
import logging

logger = logging.getLogger('GLaDOS.Controller.Dashboard')

class DashboardController(QObject):
    """Controller que centraliza dados do dashboard"""
    
    # Sinais
    reading_updated = pyqtSignal(dict)  # Livro atual
    agenda_updated = pyqtSignal(list)   # Agenda do dia
    stats_updated = pyqtSignal(dict)    # Estatísticas
    glados_updated = pyqtSignal(str)    # Mensagens GLaDOS
    
    def __init__(self, backend_modules):
        super().__init__()
        
        # Backend modules
        self.book_processor = backend_modules.get('book_processor')
        self.reading_manager = backend_modules.get('reading_manager')
        self.agenda_manager = backend_modules.get('agenda_manager')
        self.llm_module = backend_modules.get('llm_module')
        
        # Cache de dados
        self.cached_reading = None
        self.cached_agenda = []
        self.cached_stats = {}
        
        # Timer para atualizações
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.fetch_updates)
        self.update_timer.start(30000)  # 30 segundos
        
        logger.info("DashboardController initialized")
    
    def fetch_updates(self):
        """Busca atualizações de todos os módulos"""
        self.fetch_current_reading()
        self.fetch_today_agenda()
        self.fetch_daily_stats()
    
    def fetch_current_reading(self):
        """Busca livro atual em leitura"""
        try:
            if self.reading_manager:
                # O método get_reading_progress retorna um dicionário, não um objeto
                reading_data = self.reading_manager.get_reading_progress()
                
                if not reading_data:
                    self.cached_reading = None
                    return
                
                # Se for dicionário de dicionários, pega o primeiro
                if isinstance(reading_data, dict) and len(reading_data) > 0:
                    # Tenta encontrar um livro em progresso
                    current_book = None
                    for book_id, book_data in reading_data.items():
                        if isinstance(book_data, dict):
                            # Verifica se não está concluído
                            percentage = book_data.get('percentage', 0)
                            if percentage < 100:
                                current_book = book_data
                                current_book['id'] = book_id
                                break
                    
                    # Se não encontrou livro em progresso, pega o primeiro
                    if not current_book:
                        first_key = next(iter(reading_data))
                        current_book = reading_data[first_key]
                        current_book['id'] = first_key
                
                # Se já é um dicionário único
                elif isinstance(reading_data, dict):
                    current_book = reading_data
                    if 'book_id' in current_book:
                        current_book['id'] = current_book['book_id']
                
                if current_book and current_book != self.cached_reading:
                    self.cached_reading = current_book
                    
                    # Formatar para UI
                    ui_data = {
                        'id': current_book.get('id', current_book.get('book_id', '')),
                        'title': current_book.get('title', 'Sem título'),
                        'author': current_book.get('author', 'Autor desconhecido'),
                        'progress': current_book.get('percentage', 0),
                        'current_page': current_book.get('current_page', 0),
                        'total_pages': current_book.get('total_pages', 0),
                        'cover_color': self._generate_color(current_book.get('title', ''))
                    }
                    
                    self.reading_updated.emit(ui_data)
                    
        except Exception as e:
            logger.error(f"Error fetching current reading: {e}")
    
    def fetch_today_agenda(self):
        """Busca agenda do dia"""
        try:
            if self.agenda_manager:
                agenda = self.agenda_manager.get_day_events()
                
                if agenda != self.cached_agenda:
                    self.cached_agenda = agenda
                    
                    # Formatar para UI
                    ui_agenda = []
                    for event in agenda:
                        # AgendaEvent usa 'title', não 'description'
                        ui_agenda.append({
                            'id': event.id,
                            'description': event.title,  # Corrigido: usar title
                            'time': event.start.strftime('%H:%M') if hasattr(event.start, 'strftime') else '--:--',
                            'priority': event.priority.name if hasattr(event.priority, 'name') else str(event.priority),
                            'completed': event.completed
                        })
                    
                    self.agenda_updated.emit(ui_agenda)
                    
        except Exception as e:
            logger.error(f"Error fetching agenda: {e}")
    
    def fetch_daily_stats(self):
        """Busca estatísticas do dia"""
        try:
            if self.reading_manager:
                # O método stats retorna um dicionário
                stats = self.reading_manager.stats()
                
                if stats != self.cached_stats:
                    self.cached_stats = stats
                    
                    # Formatar para UI - usar as chaves reais do dicionário
                    ui_stats = {
                        'total_books': stats.get('total_books', 0),
                        'completed_books': stats.get('completed_books', 0),
                        'books_in_progress': stats.get('books_in_progress', 0),
                        'total_pages_read': stats.get('total_pages_read', 0),
                        'completion_percentage': stats.get('completion_percentage', 0),
                        'average_reading_speed': stats.get('average_reading_speed', 0),
                        'pages_last_week': stats.get('pages_last_week', 0)
                    }
                    
                    self.stats_updated.emit(ui_stats)
                    
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
    
    def _generate_color(self, text):
        """Gera cor baseada no título do livro"""
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hex_color = hash_obj.hexdigest()[:6]
        return f"#{hex_color}"