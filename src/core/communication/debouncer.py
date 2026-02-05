"""
Sistema de Debouncing e Throttling para prevenir atualizações excessivas
"""
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
import time
from typing import Callable, Any, Tuple

class Debouncer(QObject):
    """Previne atualizações excessivas da UI com debounce"""
    
    triggered = pyqtSignal()
    
    def __init__(self, delay_ms: int = 100, parent=None):
        super().__init__(parent)
        self.delay = delay_ms
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._execute)
        
        self._callback = None
        self._args = None
        self._kwargs = None
    
    def call(self, callback: Callable, *args, **kwargs):
        """Chama callback com debounce"""
        # Armazenar chamada mais recente
        self._callback = callback
        self._args = args
        self._kwargs = kwargs
        
        # Reiniciar timer
        if self.timer.isActive():
            self.timer.stop()
        
        # Configurar timeout
        self.timer.start(self.delay)
    
    def _execute(self):
        """Executa callback após debounce"""
        if self._callback:
            try:
                self._callback(*self._args, **self._kwargs)
                self.triggered.emit()
            except Exception as e:
                print(f"Error in debounced callback: {e}")
        
        self._reset()
    
    def _reset(self):
        """Reseta estado"""
        self._callback = None
        self._args = None
        self._kwargs = None
    
    def cancel(self):
        """Cancela chamada pendente"""
        if self.timer.isActive():
            self.timer.stop()
        self._reset()

class Throttler(QObject):
    """Limita frequência de chamadas com throttle"""
    
    triggered = pyqtSignal()
    
    def __init__(self, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.interval = interval_ms
        self.last_call = 0
        self.pending_call = None
        
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._execute_pending)
    
    def call(self, callback: Callable, *args, **kwargs):
        """Chama callback com throttle"""
        now = time.time() * 1000  # ms
        
        if now - self.last_call >= self.interval:
            # Pode executar imediatamente
            try:
                callback(*args, **kwargs)
                self.triggered.emit()
            except Exception as e:
                print(f"Error in throttled callback: {e}")
            
            self.last_call = now
        else:
            # Armazena para execução posterior
            self.pending_call = (callback, args, kwargs)
            
            # Agenda execução se não estiver agendado
            if not self.timer.isActive():
                wait_time = self.interval - (now - self.last_call)
                self.timer.start(wait_time)
    
    def _execute_pending(self):
        """Executa chamada pendente"""
        if self.pending_call:
            callback, args, kwargs = self.pending_call
            try:
                callback(*args, **kwargs)
                self.triggered.emit()
            except Exception as e:
                print(f"Error in pending throttled callback: {e}")
            
            self.last_call = time.time() * 1000
            self.pending_call = None
    
    def cancel(self):
        """Cancela chamada pendente"""
        if self.timer.isActive():
            self.timer.stop()
        self.pending_call = None

class AdaptiveThrottler(QObject):
    """Throttler adaptativo que ajusta intervalo baseado na carga"""
    
    def __init__(self, min_interval_ms: int = 100, max_interval_ms: int = 5000, 
                 parent=None):
        super().__init__(parent)
        self.min_interval = min_interval_ms
        self.max_interval = max_interval_ms
        self.current_interval = min_interval_ms
        
        self.call_times = []
        self.max_history = 100
        
        self.throttler = Throttler(self.current_interval, parent)
        self.throttler.triggered.connect(self._on_throttle)
    
    def call(self, callback: Callable, *args, **kwargs):
        """Chama callback com throttle adaptativo"""
        self.call_times.append(time.time())
        
        # Manter histórico limitado
        if len(self.call_times) > self.max_history:
            self.call_times = self.call_times[-self.max_history:]
        
        # Ajustar intervalo baseado na frequência de chamadas
        self._adjust_interval()
        
        # Usar throttler interno
        self.throttler.call(callback, *args, **kwargs)
    
    def _adjust_interval(self):
        """Ajusta intervalo baseado na frequência de chamadas"""
        if len(self.call_times) < 2:
            return
        
        # Calcular frequência atual (chamadas por segundo)
        recent_calls = self.call_times[-10:]  # Últimas 10 chamadas
        if len(recent_calls) >= 2:
            time_span = recent_calls[-1] - recent_calls[0]
            if time_span > 0:
                frequency = len(recent_calls) / time_span
                
                # Ajustar intervalo inversamente proporcional à frequência
                if frequency > 10:  # Muito frequente
                    self.current_interval = min(self.current_interval * 1.5, self.max_interval)
                elif frequency < 2:  # Pouco frequente
                    self.current_interval = max(self.current_interval * 0.8, self.min_interval)
                
                # Atualizar throttler
                self.throttler.interval = self.current_interval
    
    def _on_throttle(self):
        """Callback quando throttler é acionado"""
        # Pode ser usado para monitoramento
        pass
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do throttler"""
        if len(self.call_times) < 2:
            return {"interval": self.current_interval, "frequency": 0}
        
        time_span = self.call_times[-1] - self.call_times[0]
        frequency = len(self.call_times) / time_span if time_span > 0 else 0
        
        return {
            "interval_ms": self.current_interval,
            "call_frequency": frequency,
            "total_calls": len(self.call_times),
            "min_interval": self.min_interval,
            "max_interval": self.max_interval
        }