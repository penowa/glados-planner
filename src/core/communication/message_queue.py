"""
Sistema de fila de mensagens para comunicação ordenada
"""
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QMutex, QMutexLocker
from typing import Any, Dict, List, Optional, Callable
import time
import heapq
import logging

logger = logging.getLogger(__name__)

class Message:
    """Classe para representar uma mensagem na fila"""
    
    def __init__(self, id: str, type: str, data: Any, 
                 priority: int = 0, timestamp: Optional[float] = None,
                 ttl: Optional[float] = None, retries: int = 0):
        self.id = id
        self.type = type
        self.data = data
        self.priority = priority  # Menor número = maior prioridade
        self.timestamp = timestamp or time.time()
        self.ttl = ttl  # Time to live em segundos
        self.retries = retries
        self.delivered = False
        self.attempts = 0
        
    def __lt__(self, other):
        # Para heap: primeiro prioridade, depois timestamp
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp
    
    def is_expired(self) -> bool:
        """Verifica se mensagem expirou"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

class MessageQueue(QObject):
    """Fila de mensagens com prioridade e TTL"""
    
    message_ready = pyqtSignal(Message)
    queue_empty = pyqtSignal()
    
    def __init__(self, max_size: int = 1000, parent=None):
        super().__init__(parent)
        self.max_size = max_size
        self.queue = []  # Heap min
        self.mutex = QMutex()
        self.message_map = {}  # id -> Message
        self.handlers = {}
        self.processing_timer = QTimer()
        self.processing_timer.timeout.connect(self._process_next)
        
        # Configurações
        self.processing_interval = 10  # ms
        self.max_retries = 3
        self.processing_enabled = True
        
        logger.info(f"MessageQueue inicializada (max_size={max_size})")
    
    def enqueue(self, type: str, data: Any, priority: int = 0, 
                message_id: Optional[str] = None, ttl: Optional[float] = None) -> str:
        """
        Adiciona mensagem à fila
        
        Returns:
            str: ID da mensagem
        """
        with QMutexLocker(self.mutex):
            # Gerar ID se não fornecido
            if message_id is None:
                message_id = f"msg_{int(time.time() * 1000)}_{len(self.queue)}"
            
            # Verificar se fila está cheia
            if len(self.queue) >= self.max_size:
                # Remover mensagem de menor prioridade
                self._remove_lowest_priority()
            
            # Criar mensagem
            msg = Message(message_id, type, data, priority, ttl=ttl)
            
            # Adicionar à heap
            heapq.heappush(self.queue, msg)
            self.message_map[message_id] = msg
            
            logger.debug(f"Mensagem enfileirada: {type} (id={message_id}, priority={priority})")
            
            # Iniciar processamento se não estiver ativo
            if not self.processing_timer.isActive() and self.processing_enabled:
                self.processing_timer.start(self.processing_interval)
            
            return message_id
    
    def dequeue(self) -> Optional[Message]:
        """Remove e retorna a próxima mensagem"""
        with QMutexLocker(self.mutex):
            if not self.queue:
                return None
            
            # Remover mensagens expiradas
            self._remove_expired()
            
            if not self.queue:
                return None
            
            # Pegar próxima mensagem (maior prioridade)
            msg = heapq.heappop(self.queue)
            
            # Remover do mapa
            if msg.id in self.message_map:
                del self.message_map[msg.id]
            
            return msg
    
    def register_handler(self, message_type: str, handler: Callable):
        """Registra handler para tipo de mensagem específico"""
        self.handlers[message_type] = handler
        logger.info(f"Handler registrado para tipo: {message_type}")
    
    def unregister_handler(self, message_type: str):
        """Remove handler para tipo de mensagem"""
        if message_type in self.handlers:
            del self.handlers[message_type]
            logger.info(f"Handler removido para tipo: {message_type}")
    
    def _process_next(self):
        """Processa próxima mensagem na fila"""
        msg = self.dequeue()
        
        if msg is None:
            # Fila vazia, parar timer
            self.processing_timer.stop()
            self.queue_empty.emit()
            return
        
        # Verificar se mensagem expirou
        if msg.is_expired():
            logger.debug(f"Mensagem expirada ignorada: {msg.id}")
            return
        
        # Tentar processar
        try:
            # Emitir sinal
            self.message_ready.emit(msg)
            
            # Chamar handler específico se registrado
            if msg.type in self.handlers:
                self.handlers[msg.type](msg.data)
            
            msg.delivered = True
            logger.debug(f"Mensagem processada: {msg.type} (id={msg.id})")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem {msg.id}: {e}")
            
            # Tentar novamente se ainda houver tentativas
            msg.attempts += 1
            if msg.attempts < self.max_retries:
                msg.retries += 1
                # Re-enfileirar com prioridade reduzida
                self.enqueue(msg.type, msg.data, msg.priority + 1, msg.id, msg.ttl)
            else:
                logger.error(f"Mensagem {msg.id} falhou após {msg.attempts} tentativas")
    
    def _remove_expired(self):
        """Remove mensagens expiradas da fila"""
        current_time = time.time()
        expired_ids = []
        
        # Encontrar mensagens expiradas
        for msg in self.queue:
            if msg.ttl is not None and current_time - msg.timestamp > msg.ttl:
                expired_ids.append(msg.id)
        
        # Remover mensagens expiradas
        if expired_ids:
            # Reconstruir heap sem mensagens expiradas
            new_queue = []
            for msg in self.queue:
                if msg.id not in expired_ids:
                    new_queue.append(msg)
                else:
                    if msg.id in self.message_map:
                        del self.message_map[msg.id]
            
            heapq.heapify(new_queue)
            self.queue = new_queue
            
            logger.debug(f"Removidas {len(expired_ids)} mensagens expiradas")
    
    def _remove_lowest_priority(self):
        """Remove mensagem de menor prioridade (maior número)"""
        if not self.queue:
            return
        
        # Encontrar mensagem com maior valor de prioridade
        lowest_priority_msg = max(self.queue, key=lambda x: x.priority)
        
        # Remover
        self.queue.remove(lowest_priority_msg)
        heapq.heapify(self.queue)
        
        if lowest_priority_msg.id in self.message_map:
            del self.message_map[lowest_priority_msg.id]
        
        logger.warning(f"Mensagem removida por overflow: {lowest_priority_msg.id}")
    
    def get_message(self, message_id: str) -> Optional[Message]:
        """Retorna mensagem pelo ID"""
        with QMutexLocker(self.mutex):
            return self.message_map.get(message_id)
    
    def remove_message(self, message_id: str) -> bool:
        """Remove mensagem específica da fila"""
        with QMutexLocker(self.mutex):
            if message_id not in self.message_map:
                return False
            
            msg = self.message_map[message_id]
            
            # Remover da heap
            if msg in self.queue:
                self.queue.remove(msg)
                heapq.heapify(self.queue)
            
            # Remover do mapa
            del self.message_map[message_id]
            
            return True
    
    def clear(self):
        """Limpa toda a fila"""
        with QMutexLocker(self.mutex):
            self.queue.clear()
            self.message_map.clear()
            logger.info("Fila de mensagens limpa")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da fila"""
        with QMutexLocker(self.mutex):
            total = len(self.queue)
            
            # Contar por tipo
            type_counts = {}
            for msg in self.queue:
                type_counts[msg.type] = type_counts.get(msg.type, 0) + 1
            
            # Contar por prioridade
            priority_counts = {}
            for msg in self.queue:
                priority_counts[msg.priority] = priority_counts.get(msg.priority, 0) + 1
            
            return {
                "total_messages": total,
                "type_distribution": type_counts,
                "priority_distribution": priority_counts,
                "max_size": self.max_size,
                "handlers_registered": len(self.handlers)
            }
    
    def start_processing(self):
        """Inicia processamento da fila"""
        self.processing_enabled = True
        if self.queue and not self.processing_timer.isActive():
            self.processing_timer.start(self.processing_interval)
        logger.info("Processamento da fila iniciado")
    
    def stop_processing(self):
        """Para processamento da fila"""
        self.processing_enabled = False
        self.processing_timer.stop()
        logger.info("Processamento da fila parado")
    
    def set_processing_interval(self, interval_ms: int):
        """Define intervalo de processamento"""
        self.processing_interval = interval_ms
        if self.processing_timer.isActive():
            self.processing_timer.stop()
            self.processing_timer.start(interval_ms)