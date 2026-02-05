# ui/utils/responsive.py
from PyQt6.QtCore import QObject, QRect, pyqtSignal
from PyQt6.QtWidgets import QApplication

class ResponsiveManager(QObject):
    """Gerencia responsividade da interface"""
    
    breakpoint_changed = pyqtSignal(str)  # mobile, tablet, desktop, wide
    
    BREAKPOINTS = {
        'mobile': 600,
        'tablet': 900,
        'desktop': 1200,
        'wide': 1800
    }
    
    _instance = None  # Variável de classe para armazenar a instância singleton
    
    @classmethod
    def instance(cls):
        """Método singleton para obter a instância única"""
        if cls._instance is None:
            cls._instance = ResponsiveManager()
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self.current_breakpoint = 'desktop'
        self.screen = QApplication.primaryScreen()
        self.registered_windows = []
        
    def get_current_breakpoint(self, width: int = None) -> str:
        """Determinar breakpoint atual"""
        if width is None:
            width = self.screen.availableGeometry().width()
        
        for breakpoint_name, max_width in self.BREAKPOINTS.items():
            if width <= max_width:
                return breakpoint_name
        return 'wide'
    
    def update_breakpoint(self):
        """Atualizar e emitir breakpoint se mudou"""
        new_breakpoint = self.get_current_breakpoint()
        
        if new_breakpoint != self.current_breakpoint:
            self.current_breakpoint = new_breakpoint
            self.breakpoint_changed.emit(new_breakpoint)
    
    def register_window(self, window):
        """Registra uma janela para gerenciamento responsivo"""
        self.registered_windows.append(window)
        
        # Conectar sinal de redimensionamento
        window.resizeEvent = self.create_resize_handler(window.resizeEvent)
        
    def create_resize_handler(self, original_resize_event):
        """Cria um handler para eventos de redimensionamento"""
        def resize_handler(event):
            # Executar handler original se existir
            if original_resize_event:
                original_resize_event(event)
            
            # Atualizar breakpoint
            self.update_breakpoint()
            
            # Emitir evento personalizado
            for window in self.registered_windows:
                if hasattr(window, 'on_window_resized'):
                    window.on_window_resized(event.size().width(), event.size().height())
                    
        return resize_handler