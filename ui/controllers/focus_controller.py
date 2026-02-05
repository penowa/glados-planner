"""
Controller para módulo de Foco
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from core.communication.base_controller import BackendController
import logging

logger = logging.getLogger('GLaDOS.UI.FocusController')


class FocusController(BackendController):
    """Controller para sessões de foco"""
    
    # Sinais
    session_started = pyqtSignal(dict)
    session_updated = pyqtSignal(dict)
    session_completed = pyqtSignal(dict)
    session_stats_updated = pyqtSignal(dict)
    
    def __init__(self, focus_manager=None):
        super().__init__(focus_manager, "FocusController")
        self.current_session = None
        self.session_history = []
        
    def start_session(self, session_type='focus', duration=25):
        """Inicia nova sessão de foco"""
        session_data = {
            'type': session_type,
            'duration': duration,
            'start_time': self.get_timestamp(),
            'status': 'active'
        }
        
        self.current_session = session_data
        self.session_started.emit(session_data)
        
        logger.info(f"Sessão de {session_type} iniciada ({duration}min)")
    
    def pause_session(self):
        """Pausa sessão atual"""
        if self.current_session:
            self.current_session['status'] = 'paused'
            self.session_updated.emit(self.current_session)
            
            logger.info("Sessão pausada")
    
    def resume_session(self):
        """Retoma sessão pausada"""
        if self.current_session:
            self.current_session['status'] = 'active'
            self.session_updated.emit(self.current_session)
            
            logger.info("Sessão retomada")
    
    def complete_session(self):
        """Completa sessão atual"""
        if self.current_session:
            self.current_session.update({
                'status': 'completed',
                'end_time': self.get_timestamp(),
                'productive': True  # Implementar lógica real
            })
            
            self.session_history.append(self.current_session.copy())
            self.session_completed.emit(self.current_session)
            
            # Atualizar estatísticas
            self.update_stats()
            
            self.current_session = None
            logger.info("Sessão completada")
    
    def update_stats(self):
        """Atualiza estatísticas de sessões"""
        stats = self.get_session_stats()
        self.session_stats_updated.emit(stats)
    
    def get_session_stats(self):
        """Retorna estatísticas das sessões"""
        if not self.session_history:
            return {
                'sessions_today': 0,
                'total_time': 0,
                'productivity': 100,
                'avg_focus_time': 0
            }
        
        # Calcular estatísticas básicas
        total_sessions = len(self.session_history)
        total_time = sum(s.get('duration', 25) for s in self.session_history)
        
        return {
            'sessions_today': total_sessions,
            'total_time': total_time,
            'productivity': 85,  # Placeholder
            'avg_focus_time': total_time / total_sessions if total_sessions > 0 else 0
        }
    
    def get_timestamp(self):
        """Retorna timestamp atual"""
        from datetime import datetime
        return datetime.now().isoformat()