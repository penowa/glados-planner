"""
Monitor de performance do sistema
"""
import time
import psutil
import logging
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from collections import deque

logger = logging.getLogger('GLaDOS.Performance')


@dataclass
class PerformanceMetrics:
    cpu_percent: float
    memory_mb: float
    disk_io_read: float
    disk_io_write: float
    network_sent: float
    network_recv: float
    process_count: int
    timestamp: float


class PerformanceMonitor:
    """Monitora performance do sistema em tempo real"""
    
    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.metrics_history = deque(maxlen=history_size)
        self.start_time = time.time()
        self.peak_memory = 0
        self.peak_cpu = 0
        
        # Inicializar contadores do psutil
        self.last_disk_io = psutil.disk_io_counters()
        self.last_network_io = psutil.net_io_counters()
        self.last_check_time = time.time()
        
        logger.info("PerformanceMonitor inicializado")
    
    def collect_metrics(self) -> PerformanceMetrics:
        """Coleta métricas atuais do sistema"""
        current_time = time.time()
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memória
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # Atualizar picos
        self.peak_memory = max(self.peak_memory, memory_mb)
        self.peak_cpu = max(self.peak_cpu, cpu_percent)
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        time_diff = current_time - self.last_check_time
        
        if self.last_disk_io and time_diff > 0:
            read_bytes_per_sec = (disk_io.read_bytes - self.last_disk_io.read_bytes) / time_diff
            write_bytes_per_sec = (disk_io.write_bytes - self.last_disk_io.write_bytes) / time_diff
        else:
            read_bytes_per_sec = 0
            write_bytes_per_sec = 0
        
        self.last_disk_io = disk_io
        
        # Network I/O
        network_io = psutil.net_io_counters()
        
        if self.last_network_io and time_diff > 0:
            sent_bytes_per_sec = (network_io.bytes_sent - self.last_network_io.bytes_sent) / time_diff
            recv_bytes_per_sec = (network_io.bytes_recv - self.last_network_io.bytes_recv) / time_diff
        else:
            sent_bytes_per_sec = 0
            recv_bytes_per_sec = 0
        
        self.last_network_io = network_io
        self.last_check_time = current_time
        
        # Process count
        process_count = len(psutil.pids())
        
        metrics = PerformanceMetrics(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            disk_io_read=read_bytes_per_sec,
            disk_io_write=write_bytes_per_sec,
            network_sent=sent_bytes_per_sec,
            network_recv=recv_bytes_per_sec,
            process_count=process_count,
            timestamp=current_time
        )
        
        # Adicionar ao histórico
        self.metrics_history.append(metrics)
        
        return metrics
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Retorna métricas atuais em formato dicionário"""
        metrics = self.collect_metrics()
        return asdict(metrics)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status geral do sistema"""
        metrics = self.get_current_metrics()
        
        status = {
            'cpu': {
                'current': metrics['cpu_percent'],
                'peak': self.peak_cpu,
                'status': 'normal' if metrics['cpu_percent'] < 80 else 'high'
            },
            'memory': {
                'current_mb': metrics['memory_mb'],
                'peak_mb': self.peak_memory,
                'status': 'normal' if metrics['memory_mb'] < 500 else 'high'
            },
            'disk': {
                'read_mbps': metrics['disk_io_read'] / 1024 / 1024,
                'write_mbps': metrics['disk_io_write'] / 1024 / 1024,
                'status': 'normal'
            },
            'network': {
                'sent_mbps': metrics['network_sent'] / 1024 / 1024,
                'recv_mbps': metrics['network_recv'] / 1024 / 1024,
                'status': 'normal'
            },
            'uptime': time.time() - self.start_time,
            'processes': metrics['process_count'],
            'health_score': self._calculate_health_score(metrics)
        }
        
        return status
    
    def _calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """Calcula score de saúde do sistema (0-100)"""
        cpu_score = max(0, 100 - metrics['cpu_percent'])
        memory_score = max(0, 100 - (metrics['memory_mb'] / 10))  # 10MB = 1 ponto
        
        # Normalizar I/O scores
        disk_read_score = max(0, 100 - (metrics['disk_io_read'] / 1024 / 1024))  # 1MB/s = 1 ponto
        disk_write_score = max(0, 100 - (metrics['disk_io_write'] / 1024 / 1024))
        
        disk_score = (disk_read_score + disk_write_score) / 2
        
        # Score final
        weights = {
            'cpu': 0.3,
            'memory': 0.4,
            'disk': 0.2,
            'process': 0.1
        }
        
        process_score = max(0, 100 - (metrics['process_count'] / 10))  # 10 processos = 1 ponto
        
        final_score = (
            cpu_score * weights['cpu'] +
            memory_score * weights['memory'] +
            disk_score * weights['disk'] +
            process_score * weights['process']
        )
        
        return round(final_score, 1)
    
    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """Retorna histórico de métricas"""
        if limit:
            recent = list(self.metrics_history)[-limit:]
        else:
            recent = list(self.metrics_history)
        
        return [asdict(m) for m in recent]
    
    def check_for_anomalies(self) -> List[Dict[str, Any]]:
        """Verifica anomalias no sistema"""
        anomalies = []
        
        metrics = self.get_current_metrics()
        
        # Verificar CPU
        if metrics['cpu_percent'] > 90:
            anomalies.append({
                'type': 'high_cpu',
                'value': metrics['cpu_percent'],
                'threshold': 90,
                'severity': 'high'
            })
        
        # Verificar memória
        if metrics['memory_mb'] > 1000:  # 1GB
            anomalies.append({
                'type': 'high_memory',
                'value': metrics['memory_mb'],
                'threshold': 1000,
                'severity': 'medium'
            })
        
        # Verificar disk I/O
        if metrics['disk_io_read'] > 50 * 1024 * 1024:  # 50MB/s
            anomalies.append({
                'type': 'high_disk_read',
                'value': metrics['disk_io_read'] / 1024 / 1024,
                'threshold': 50,
                'severity': 'low'
            })
        
        return anomalies
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Gera relatório completo de performance"""
        status = self.get_system_status()
        anomalies = self.check_for_anomalies()
        history = self.get_history(10)  # Últimas 10 medições
        
        return {
            'current_status': status,
            'anomalies': anomalies,
            'recent_history': history,
            'uptime_hours': (time.time() - self.start_time) / 3600,
            'peak_memory_mb': self.peak_memory,
            'peak_cpu_percent': self.peak_cpu,
            'timestamp': time.time()
        }