"""
Gerenciador centralizado de erros para o sistema
"""
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger('GLaDOS.Errors')


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorManager:
    """Gerencia e trata erros de forma centralizada"""
    
    def __init__(self):
        self.error_history = []
        self.error_handlers = {}
        
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Processa um erro e retorna ações de recuperação
        
        Args:
            error: Exceção a ser tratada
            
        Returns:
            Dict com ações de recuperação
        """
        error_data = {
            'type': type(error).__name__,
            'message': str(error),
            'severity': self._determine_severity(error),
            'timestamp': self._get_timestamp(),
        }
        
        # Log do erro
        self._log_error(error_data)
        
        # Adicionar ao histórico
        self.error_history.append(error_data)
        
        # Determinar ações de recuperação
        recovery_actions = self._determine_recovery_actions(error_data)
        
        return {
            'error_data': error_data,
            'recovery_actions': recovery_actions,
            'notify_user': error_data['severity'] in ['high', 'critical'],
            'urgency': error_data['severity']
        }
    
    def _determine_severity(self, error: Exception) -> str:
        """Determina a severidade do erro"""
        error_type = type(error).__name__
        
        severity_map = {
            'FileNotFoundError': ErrorSeverity.MEDIUM,
            'ConnectionError': ErrorSeverity.HIGH,
            'MemoryError': ErrorSeverity.CRITICAL,
            'TimeoutError': ErrorSeverity.HIGH,
            'PermissionError': ErrorSeverity.MEDIUM,
            'ValueError': ErrorSeverity.LOW,
            'KeyError': ErrorSeverity.LOW,
            'ModuleError': ErrorSeverity.MEDIUM,
        }
        
        return severity_map.get(error_type, ErrorSeverity.MEDIUM).value
    
    def _log_error(self, error_data: Dict[str, Any]):
        """Registra o erro no log apropriado"""
        log_methods = {
            'low': logger.debug,
            'medium': logger.warning,
            'high': logger.error,
            'critical': logger.critical
        }
        
        log_method = log_methods.get(error_data['severity'], logger.error)
        log_method(f"Erro {error_data['type']}: {error_data['message']}")
    
    def _determine_recovery_actions(self, error_data: Dict[str, Any]) -> list:
        """Determina ações de recuperação baseadas no erro"""
        actions = []
        
        if error_data['type'] == 'FileNotFoundError':
            actions = [
                {'action': 'check_file_path', 'params': {'path': error_data.get('path')}},
                {'action': 'use_fallback', 'params': {'resource': 'file'}}
            ]
        elif error_data['type'] == 'ConnectionError':
            actions = [
                {'action': 'retry_connection', 'params': {'attempts': 3, 'delay': 5}},
                {'action': 'use_cached_data', 'params': {}}
            ]
        elif error_data['severity'] == 'critical':
            actions = [
                {'action': 'emergency_save', 'params': {}},
                {'action': 'restart_module', 'params': {}}
            ]
        
        return actions
    
    def _get_timestamp(self) -> str:
        """Retorna timestamp formatado"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def register_handler(self, error_type: str, handler):
        """Registra um handler customizado para um tipo de erro"""
        self.error_handlers[error_type] = handler
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de erros"""
        if not self.error_history:
            return {'total': 0, 'by_severity': {}, 'recent': []}
        
        by_severity = {}
        for error in self.error_history:
            severity = error['severity']
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            'total': len(self.error_history),
            'by_severity': by_severity,
            'recent': self.error_history[-10:],  # Últimos 10 erros
            'critical_count': len([e for e in self.error_history if e['severity'] == 'critical'])
        }