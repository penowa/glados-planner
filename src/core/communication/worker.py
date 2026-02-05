"""
Worker para executar operações pesadas em thread separada
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
import time
import inspect
import logging

logger = logging.getLogger(__name__)

class BackendWorker(QObject):
    """Worker para executar operações pesadas em thread separada"""
    
    # Sinais
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal()
    
    def __init__(self, backend_instance, method_name: str, *args, **kwargs):
        super().__init__()
        self.backend = backend_instance
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs
        self.is_cancelled = False
        self.start_time = time.time()
        
        logger.debug(f"Worker criado para {method_name}")
    
    def cancel(self):
        """Marca worker para cancelamento"""
        self.is_cancelled = True
        logger.info(f"Worker {self.method_name} marcado para cancelamento")
    
    @pyqtSlot()
    def run(self):
        """Executa operação na thread do worker"""
        logger.info(f"Iniciando worker: {self.method_name}")
        
        try:
            # Verificar se método existe
            if not hasattr(self.backend, self.method_name):
                error_msg = f"Método '{self.method_name}' não encontrado no backend"
                raise AttributeError(error_msg)
            
            method = getattr(self.backend, self.method_name)
            
            # Verificar se método aceita callback de progresso
            sig = inspect.signature(method)
            
            if 'progress_callback' in sig.parameters:
                # Método suporta callback de progresso
                result = method(
                    *self.args,
                    progress_callback=self._progress_callback,
                    **self.kwargs
                )
            else:
                # Método normal
                result = method(*self.args, **self.kwargs)
            
            # Verificar cancelamento
            if self.is_cancelled:
                logger.info(f"Worker {self.method_name} cancelado durante execução")
                self.finished.emit()
                return
                
            # Log de sucesso
            duration = time.time() - self.start_time
            logger.info(f"Worker {self.method_name} concluído em {duration:.2f}s")
            
            # Emitir resultado
            self.result_ready.emit(result)
            
        except Exception as e:
            # Log de erro
            duration = time.time() - self.start_time
            logger.error(f"Erro no worker {self.method_name} após {duration:.2f}s: {e}")
            
            # Emitir erro
            self.error_occurred.emit(str(e))
            
        finally:
            # Sinalizar conclusão
            self.finished.emit()
    
    def _progress_callback(self, percent: int, message: str) -> bool:
        """
        Callback para atualizar progresso
        
        Returns:
            bool: True para continuar, False para parar
        """
        # Verificar cancelamento
        if self.is_cancelled:
            return False
        
        # Limitar frequência de atualizações (máximo 10 por segundo)
        current_time = time.time()
        if hasattr(self, '_last_progress_time'):
            if current_time - self._last_progress_time < 0.1:  # 100ms
                return True
        
        self._last_progress_time = current_time
        
        # Emitir progresso
        try:
            self.progress_updated.emit(percent, message)
        except Exception as e:
            logger.error(f"Erro ao emitir progresso: {e}")
        
        return True
    
    def get_info(self) -> dict:
        """Retorna informações sobre o worker"""
        return {
            "method": self.method_name,
            "args_count": len(self.args),
            "kwargs_keys": list(self.kwargs.keys()),
            "is_cancelled": self.is_cancelled,
            "running_time": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }