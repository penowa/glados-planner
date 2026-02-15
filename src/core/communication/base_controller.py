"""
Controller base para integração backend-frontend
Gerencia workers assíncronos e adapta dados para a UI
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
import time
import logging
from typing import Any, Callable, Dict, Optional

from .event_bus import GlobalEventBus
from .worker import BackendWorker

logger = logging.getLogger(__name__)

class BackendController(QObject):
    """Controlador base que adapta backend para frontend"""
    
    # Sinais padrão
    operation_started = pyqtSignal(str, dict)  # (operation, context)
    operation_completed = pyqtSignal(str, dict)  # (operation, result)
    operation_failed = pyqtSignal(str, str, dict)  # (operation, error, context)
    progress_updated = pyqtSignal(str, int, str, dict)  # (operation, %, msg, data)
    data_changed = pyqtSignal(str, dict)  # (data_type, data)
    
    def __init__(self, backend_module: Any, name: str):
        super().__init__()
        self.backend = backend_module
        self.name = name
        self.workers = []  # Lista de workers ativos
        self.event_bus = GlobalEventBus.instance()
        
        # Configurar conexões automáticas
        self._setup_automatic_connections()
        
        logger.info(f"Controller {name} inicializado")
    
    def _setup_automatic_connections(self):
        """Conecta automaticamente ao EventBus para eventos comuns"""
        # Notifica quando controlador está pronto
        self.event_bus.module_ready.emit(self.name, {"status": "initialized"})
        
        # Propaga progresso para EventBus
        self.progress_updated.connect(
            lambda op, pct, msg, data: self.event_bus.progress_updated.emit(
                f"{self.name}.{op}", pct, msg
            )
        )
        
        # Propaga erros para EventBus
        self.operation_failed.connect(
            lambda op, err, ctx: self.event_bus.module_error.emit(
                self.name, f"{op}: {err}"
            )
        )
        
        # Propaga dados para EventBus
        self.data_changed.connect(
            lambda dtype, data: self.event_bus.data_updated.emit(dtype, data)
        )
    
    def execute_async(self, operation: str, *args, callback: Optional[Callable] = None, 
                     error_callback: Optional[Callable] = None, **kwargs) -> QThread:
        """
        Executa operação do backend de forma assíncrona
        
        Args:
            operation: Nome do método do backend
            callback: Função chamada quando completar (opcional)
            error_callback: Função chamada em erro (opcional)
            
        Returns:
            QThread: Thread do worker
        """
        # Criar worker para operação
        worker = BackendWorker(self.backend, operation, *args, **kwargs)
        worker_thread = QThread()
        
        # Mover worker para thread
        worker.moveToThread(worker_thread)
        
        # Conectar sinais
        worker.result_ready.connect(
            lambda result: self._handle_result(operation, result, callback)
        )
        worker.error_occurred.connect(
            lambda error: self._handle_error(operation, error, error_callback)
        )
        worker.progress_updated.connect(
            lambda pct, msg: self.progress_updated.emit(operation, pct, msg, {})
        )
        
        # Conectar início/fim da thread
        worker_thread.started.connect(worker.run)
        worker.finished.connect(worker_thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker_thread.finished.connect(worker_thread.deleteLater)
        worker_thread.finished.connect(
            lambda: self._on_worker_thread_finished(worker_thread, worker)
        )
        
        # Armazenar referência
        self.workers.append((worker_thread, worker))
        
        # Emitir evento de início
        self.operation_started.emit(operation, {
            "args": args,
            "kwargs": kwargs,
            "timestamp": time.time(),
            "controller": self.name
        })
        
        # Iniciar thread
        worker_thread.start()
        
        return worker_thread

    def _on_worker_thread_finished(self, worker_thread: QThread, worker: BackendWorker):
        """Remove referências de workers finalizados para evitar retenção em memória."""
        try:
            self.workers = [
                (thread, w)
                for thread, w in self.workers
                if thread is not worker_thread and w is not worker
            ]
        except Exception as e:
            logger.debug(f"Falha ao limpar worker finalizado em {self.name}: {e}")
    
    def _handle_result(self, operation: str, result: Any, callback: Optional[Callable]):
        """Processa resultado bem-sucedido"""
        self.operation_completed.emit(operation, {
            "result": result,
            "timestamp": time.time()
        })
        
        # Se resultado contém dados, emitir evento de dados
        if isinstance(result, dict) and 'data_type' in result:
            self.data_changed.emit(result['data_type'], result)
        
        # Chamar callback se fornecido
        if callback:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in callback for operation {operation}: {e}")
    
    def _handle_error(self, operation: str, error: str, error_callback: Optional[Callable]):
        """Processa erro"""
        error_data = {
            "timestamp": time.time(),
            "module": self.name,
            "operation": operation,
            "error": error
        }
        
        self.operation_failed.emit(operation, error, error_data)
        
        # Chamar error_callback se fornecido
        if error_callback:
            try:
                error_callback(error)
            except Exception as e:
                logger.error(f"Error in error_callback for operation {operation}: {e}")
    
    def execute_sync(self, operation: str, *args, timeout: float = 30.0, **kwargs) -> Any:
        """
        Executa operação de forma síncrona (bloqueante)
        Útil para operações rápidas
        
        Args:
            operation: Nome do método do backend
            timeout: Timeout em segundos
            
        Returns:
            Resultado da operação
            
        Raises:
            TimeoutError: Se operação exceder timeout
            Exception: Se operação falhar
        """
        if not hasattr(self.backend, operation):
            raise AttributeError(f"Método '{operation}' não encontrado no backend")
        
        import threading
        import queue
        
        result_queue = queue.Queue()
        error_queue = queue.Queue()
        
        def worker():
            try:
                method = getattr(self.backend, operation)
                result = method(*args, **kwargs)
                result_queue.put(result)
            except Exception as e:
                error_queue.put(e)
        
        # Executar em thread separada
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Operação {operation} excedeu timeout de {timeout}s")
        
        # Verificar se houve erro
        if not error_queue.empty():
            raise error_queue.get()
        
        return result_queue.get()
    
    def cancel_all_operations(self):
        """Cancela todas as operações pendentes"""
        for thread, worker in self.workers:
            if hasattr(worker, 'cancel'):
                worker.cancel()
            
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)  # Esperar 1 segundo
        
        self.workers.clear()
        logger.info(f"Todas as operações canceladas no controller {self.name}")
    
    def cleanup(self):
        """Limpa todos os workers ativos"""
        self.cancel_all_operations()
        
        # Limpar conexões
        try:
            self.disconnect()
        except:
            pass
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do controller"""
        return {
            "name": self.name,
            "active_workers": len([t for t, _ in self.workers if t.isRunning()]),
            "total_operations": len(self.workers),
            "backend_type": type(self.backend).__name__
        }
