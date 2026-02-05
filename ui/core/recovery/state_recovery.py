"""
Gerenciador de recuperação de estado do sistema
"""
import json
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pickle

logger = logging.getLogger('GLaDOS.Recovery')


class RecoveryAction:
    """Representa uma ação de recuperação"""
    
    def __init__(self, action_type: str, params: Dict[str, Any], priority: int = 1):
        self.action_type = action_type
        self.params = params
        self.priority = priority  # 1=baixo, 5=alto
        self.status = 'pending'  # pending, executing, completed, failed
        self.created_at = datetime.now()
        self.completed_at = None
        self.result = None
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Executa a ação de recuperação"""
        self.status = 'executing'
        
        try:
            if self.action_type == 'retry_operation':
                result = self._retry_operation(context)
            elif self.action_type == 'use_fallback':
                result = self._use_fallback(context)
            elif self.action_type == 'emergency_save':
                result = self._emergency_save(context)
            elif self.action_type == 'restart_module':
                result = self._restart_module(context)
            elif self.action_type == 'rollback_state':
                result = self._rollback_state(context)
            else:
                result = {'success': False, 'error': f'Ação desconhecida: {self.action_type}'}
            
            self.status = 'completed' if result.get('success') else 'failed'
            self.result = result
            
        except Exception as e:
            self.status = 'failed'
            self.result = {'success': False, 'error': str(e)}
        
        self.completed_at = datetime.now()
        return self.result
    
    def _retry_operation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Tenta operação novamente"""
        attempts = self.params.get('attempts', 3)
        delay = self.params.get('delay', 1)
        
        operation = context.get('operation')
        if not operation:
            return {'success': False, 'error': 'Operação não especificada'}
        
        import time
        for attempt in range(attempts):
            try:
                result = operation()
                return {'success': True, 'attempts': attempt + 1, 'result': result}
            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                if attempt < attempts - 1:
                    time.sleep(delay)
        
        return {'success': False, 'error': f'Falha após {attempts} tentativas'}
    
    def _use_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Usa recurso fallback"""
        resource_type = self.params.get('resource', 'data')
        
        if resource_type == 'data':
            # Tenta carregar dados de cache
            cache_path = context.get('cache_path')
            if cache_path and os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r') as f:
                        data = json.load(f)
                    return {'success': True, 'source': 'cache', 'data': data}
                except:
                    pass
        
        return {'success': False, 'error': 'Nenhum fallback disponível'}
    
    def _emergency_save(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Salva estado atual de emergência"""
        state = context.get('current_state')
        if not state:
            return {'success': False, 'error': 'Estado não disponível para salvamento'}
        
        try:
            backup_dir = os.path.join(os.getcwd(), 'recovery_backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'emergency_backup_{timestamp}.pkl')
            
            with open(backup_file, 'wb') as f:
                pickle.dump(state, f)
            
            logger.info(f"Estado salvo em: {backup_file}")
            return {'success': True, 'backup_file': backup_file}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _restart_module(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reinicia um módulo"""
        module_name = self.params.get('module')
        module = context.get('modules', {}).get(module_name)
        
        if not module:
            return {'success': False, 'error': f'Módulo {module_name} não encontrado'}
        
        try:
            # Tenta reinicializar o módulo
            if hasattr(module, 'cleanup'):
                module.cleanup()
            
            if hasattr(module, 'initialize'):
                module.initialize()
            
            logger.info(f"Módulo {module_name} reiniciado")
            return {'success': True, 'module': module_name}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _rollback_state(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reverte para estado anterior"""
        backup_id = self.params.get('backup_id', 'latest')
        
        backup_dir = os.path.join(os.getcwd(), 'recovery_backups')
        if not os.path.exists(backup_dir):
            return {'success': False, 'error': 'Nenhum backup disponível'}
        
        # Buscar backup mais recente
        backups = []
        for file in os.listdir(backup_dir):
            if file.startswith('emergency_backup_') and file.endswith('.pkl'):
                file_path = os.path.join(backup_dir, file)
                mtime = os.path.getmtime(file_path)
                backups.append((mtime, file_path))
        
        if not backups:
            return {'success': False, 'error': 'Nenhum backup encontrado'}
        
        # Ordenar por data (mais recente primeiro)
        backups.sort(reverse=True)
        
        if backup_id == 'latest':
            backup_file = backups[0][1]
        else:
            # Implementar busca por ID específico
            backup_file = None
            for mtime, file_path in backups:
                if backup_id in file_path:
                    backup_file = file_path
                    break
        
        if not backup_file:
            return {'success': False, 'error': f'Backup {backup_id} não encontrado'}
        
        try:
            with open(backup_file, 'rb') as f:
                state = pickle.load(f)
            
            return {'success': True, 'state': state, 'backup_file': backup_file}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


class StateRecoveryManager:
    """Gerencia recuperação de estado do sistema"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.recovery_queue = []
        self.completed_actions = []
        self.recovery_state = {
            'last_recovery': None,
            'success_count': 0,
            'failure_count': 0,
            'active': False
        }
        
        # Criar diretório de backups
        self.backup_dir = os.path.join(os.getcwd(), 'recovery_backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logger.info("StateRecoveryManager inicializado")
    
    def schedule_recovery(self, issue_type: str, context: Dict[str, Any]) -> RecoveryAction:
        """
        Agenda uma ação de recuperação
        
        Args:
            issue_type: Tipo de problema (ex: 'system_check', 'module_error')
            context: Contexto para a recuperação
            
        Returns:
            Ação de recuperação agendada
        """
        # Determinar ação baseada no tipo de problema
        if issue_type == 'system_check':
            action = RecoveryAction('restart_module', {'module': context.get('module', 'unknown')}, priority=3)
        elif issue_type == 'module_error':
            action = RecoveryAction('retry_operation', {'attempts': 3, 'delay': 2}, priority=4)
        elif issue_type == 'data_loss':
            action = RecoveryAction('use_fallback', {'resource': 'data'}, priority=5)
        elif issue_type == 'critical_error':
            action = RecoveryAction('emergency_save', {}, priority=5)
        else:
            action = RecoveryAction('retry_operation', {'attempts': 2, 'delay': 1}, priority=2)
        
        # Adicionar à fila
        self.recovery_queue.append(action)
        
        # Ordenar por prioridade (maior primeiro)
        self.recovery_queue.sort(key=lambda a: a.priority, reverse=True)
        
        logger.info(f"Ação de recuperação agendada: {action.action_type} (prioridade: {action.priority})")
        return action
    
    def execute_recovery(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa as ações de recuperação pendentes"""
        if not self.recovery_queue:
            return {'success': True, 'message': 'Nenhuma ação pendente'}
        
        self.recovery_state['active'] = True
        results = []
        context = context or {}
        
        logger.info(f"Executando recuperação: {len(self.recovery_queue)} ações pendentes")
        
        for action in list(self.recovery_queue):  # Copia da lista
            try:
                result = action.execute(context)
                results.append({
                    'action': action.action_type,
                    'success': result['success'],
                    'result': result
                })
                
                # Mover para completadas
                self.recovery_queue.remove(action)
                self.completed_actions.append(action)
                
                # Atualizar estatísticas
                if result.get('success'):
                    self.recovery_state['success_count'] += 1
                else:
                    self.recovery_state['failure_count'] += 1
                
            except Exception as e:
                logger.error(f"Erro ao executar ação {action.action_type}: {e}")
                results.append({
                    'action': action.action_type,
                    'success': False,
                    'error': str(e)
                })
        
        self.recovery_state['active'] = False
        self.recovery_state['last_recovery'] = datetime.now().isoformat()
        
        # Resumo
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        summary = {
            'total_actions': total_count,
            'successful_actions': success_count,
            'failed_actions': total_count - success_count,
            'results': results,
            'timestamp': self.recovery_state['last_recovery']
        }
        
        logger.info(f"Recuperação concluída: {success_count}/{total_count} ações bem-sucedidas")
        
        return summary
    
    def create_state_backup(self, state_data: Dict[str, Any], tag: str = '') -> str:
        """Cria um backup do estado atual"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            tag_suffix = f'_{tag}' if tag else ''
            backup_file = os.path.join(self.backup_dir, f'state_backup{tag_suffix}_{timestamp}.json')
            
            # Adicionar metadados
            backup_data = {
                'state': state_data,
                'metadata': {
                    'created_at': timestamp,
                    'tag': tag,
                    'system': 'GLaDOS Philosophy Planner',
                    'version': '1.0.0'
                }
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Backup de estado criado: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            return None
    
    def restore_state_backup(self, backup_file: str = None) -> Optional[Dict[str, Any]]:
        """Restaura estado a partir de backup"""
        try:
            if not backup_file:
                # Usar backup mais recente
                backups = []
                for file in os.listdir(self.backup_dir):
                    if file.endswith('.json'):
                        file_path = os.path.join(self.backup_dir, file)
                        mtime = os.path.getmtime(file_path)
                        backups.append((mtime, file_path))
                
                if not backups:
                    return None
                
                backups.sort(reverse=True)
                backup_file = backups[0][1]
            
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            logger.info(f"Estado restaurado de: {backup_file}")
            return backup_data.get('state')
            
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}")
            return None
    
    def get_recovery_status(self) -> Dict[str, Any]:
        """Retorna status atual do sistema de recuperação"""
        return {
            'queue_size': len(self.recovery_queue),
            'completed_count': len(self.completed_actions),
            'state': self.recovery_state,
            'backup_count': len(os.listdir(self.backup_dir)) if os.path.exists(self.backup_dir) else 0,
            'last_actions': [{
                'type': a.action_type,
                'status': a.status,
                'created': a.created_at.isoformat() if hasattr(a.created_at, 'isoformat') else str(a.created_at),
                'priority': a.priority
            } for a in self.completed_actions[-5:]]  # Últimas 5 ações
        }
    
    def cleanup_old_backups(self, max_age_days: int = 7):
        """Remove backups antigos"""
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        
        if not os.path.exists(self.backup_dir):
            return
        
        removed_count = 0
        for file in os.listdir(self.backup_dir):
            file_path = os.path.join(self.backup_dir, file)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_time < cutoff_time:
                try:
                    os.remove(file_path)
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao remover backup antigo {file}: {e}")
        
        if removed_count > 0:
            logger.info(f"Removidos {removed_count} backups antigos")