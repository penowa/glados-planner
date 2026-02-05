"""
Controller para integração do dashboard com backend real
"""
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
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
                reading = self.reading_manager.get_current_reading()
                
                if reading and reading != self.cached_reading:
                    self.cached_reading = reading
                    
                    # Formatar para UI
                    ui_data = {
                        'id': reading.id,
                        'title': reading.title,
                        'author': reading.author or 'Autor desconhecido',
                        'progress': reading.progress_percentage,
                        'current_page': reading.current_page,
                        'total_pages': reading.total_pages,
                        'cover_color': self._generate_color(reading.title)
                    }
                    
                    self.reading_updated.emit(ui_data)
                    
        except Exception as e:
            logger.error(f"Error fetching current reading: {e}")
    
    def fetch_today_agenda(self):
        """Busca agenda do dia"""
        try:
            if self.agenda_manager:
                agenda = self.agenda_manager.get_today_tasks()
                
                if agenda != self.cached_agenda:
                    self.cached_agenda = agenda
                    
                    # Formatar para UI
                    ui_agenda = []
                    for task in agenda:
                        ui_agenda.append({
                            'id': task.id,
                            'description': task.description,
                            'time': task.scheduled_time.strftime('%H:%M') if task.scheduled_time else '--:--',
                            'priority': task.priority,
                            'completed': task.completed
                        })
                    
                    self.agenda_updated.emit(ui_agenda)
                    
        except Exception as e:
            logger.error(f"Error fetching agenda: {e}")
    
    def fetch_daily_stats(self):
        """Busca estatísticas do dia"""
        try:
            if self.reading_manager:
                stats = self.reading_manager.get_daily_statistics()
                
                if stats != self.cached_stats:
                    self.cached_stats = stats
                    
                    # Formatar para UI
                    ui_stats = {
                        'reading_time_minutes': stats.get('total_reading_minutes', 0),
                        'pomodoros_completed': stats.get('completed_sessions', 0),
                        'notes_created': stats.get('notes_created', 0),
                        'pages_read': stats.get('pages_read', 0),
                        'books_started': stats.get('books_started', 0),
                        'concepts_created': stats.get('concepts_created', 0)
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