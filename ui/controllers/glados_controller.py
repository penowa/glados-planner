"""
controladores/glados_controller.py
Controladora principal para assistente GLaDOS com integração completa do backend
"""
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer
from PyQt6.QtGui import QImage, QPixmap
import logging
import traceback
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

# Importações do backend completo
from core.llm.local_llm import llm as backend_llm
from core.llm.glados.personality.glados_voice import GladosVoice
from core.llm.glados.brain.vault_connector import VaultStructure
from core.llm.glados.models.tinyllama_wrapper import TinyLlamaGlados
from core.llm.glados.brain.semantic_search import Sembrain

logger = logging.getLogger('GLaDOS.Controller')


@dataclass
class GladosState:
    """Estado atual do assistente GLaDOS"""
    personality_intensity: float = 0.7
    enable_sarcasm: bool = True
    current_mode: str = "academic"
    memory_usage: Dict[str, Any] = None
    conversation_history: List[Dict] = None
    active_context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.memory_usage is None:
            self.memory_usage = {"cache_hits": 0, "cache_misses": 0}
        if self.conversation_history is None:
            self.conversation_history = []
        if self.active_context is None:
            self.active_context = {}


class BackendWorker(QThread):
    """Thread worker para operações pesadas do backend"""
    
    task_completed = pyqtSignal(object)
    task_failed = pyqtSignal(str, str)  # (error_type, error_message)
    progress_updated = pyqtSignal(int, str)  # (percent, message)
    
    def __init__(self, task_type: str, task_data: Dict, parent=None):
        super().__init__(parent)
        self.task_type = task_type
        self.task_data = task_data
        self.is_running = True
    
    def run(self):
        """Executa a tarefa na thread"""
        try:
            if self.task_type == "llm_generate":
                result = self._run_llm_generation()
                self.task_completed.emit(result)
                
            elif self.task_type == "vault_search":
                result = self._run_vault_search()
                self.task_completed.emit(result)
                
            elif self.task_type == "semantic_query":
                result = self._run_semantic_query()
                self.task_completed.emit(result)
                
            elif self.task_type == "brain_analysis":
                result = self._run_brain_analysis()
                self.task_completed.emit(result)
                
            elif self.task_type == "memory_update":
                result = self._run_memory_update()
                self.task_completed.emit(result)
                
        except Exception as e:
            error_type = type(e).__name__
            error_msg = f"{error_type}: {str(e)}"
            logger.error(f"Worker error: {error_msg}\n{traceback.format_exc()}")
            self.task_failed.emit(error_type, error_msg)
    
    def _run_llm_generation(self) -> Dict:
        """Executa geração LLM"""
        query = self.task_data.get("query", "")
        use_semantic = self.task_data.get("use_semantic", True)
        user_name = self.task_data.get("user_name", "Helio")
        request_metadata = self.task_data.get("request_metadata") or {}

        self.progress_updated.emit(10, "Consultando o cérebro de GLaDOS...")

        # Gerar resposta usando backend completo
        result = backend_llm.generate(
            query=query,
            user_name=user_name,
            use_semantic=use_semantic,
            request_metadata=request_metadata,
        )
        
        self.progress_updated.emit(90, "Formando resposta no estilo GLaDOS...")
        
        # Adicionar metadados da operação
        result["backend_operation"] = {
            "task_type": self.task_type,
            "query_length": len(query),
            "response_length": len(result.get("text", "")),
            "semantic_used": use_semantic and result.get("semantic_context_used", False),
            "request_metadata": request_metadata,
        }

        return result
    
    def _run_vault_search(self) -> Dict:
        """Busca no vault do Obsidian"""
        query = self.task_data.get("query", "")
        limit = self.task_data.get("limit", 5)
        use_semantic = self.task_data.get("use_semantic", True)
        
        self.progress_updated.emit(20, "Indexando vault do Obsidian...")
        
        # Busca usando backend
        if use_semantic and backend_llm.sembrain:
            notes = backend_llm.search_notes(query, limit, use_semantic=True)
        else:
            notes = backend_llm.vault_structure.search_notes(query, limit)
        
        self.progress_updated.emit(80, "Formatando resultados...")
        
        # Formatar resultados
        formatted_notes = []
        for note in notes:
            if isinstance(note, dict):
                formatted_notes.append(note)
            else:
                # Converter objeto Note para dict
                formatted_notes.append({
                    "title": getattr(note, 'title', 'Sem título'),
                    "path": str(getattr(note, 'path', '')),
                    "excerpt": getattr(note, 'content', '')[:200] + "..." if len(getattr(note, 'content', '')) > 200 else getattr(note, 'content', ''),
                    "tags": getattr(note, 'tags', []),
                    "type": "semantic" if use_semantic else "textual"
                })
        
        return {
            "query": query,
            "results": formatted_notes,
            "total_found": len(formatted_notes),
            "search_method": "semantic" if use_semantic else "textual",
            "vault_stats": backend_llm.vault_structure.get_vault_stats() if hasattr(backend_llm, 'vault_structure') else {}
        }
    
    def _run_semantic_query(self) -> Dict:
        """Consulta semântica avançada"""
        query = self.task_data.get("query", "")
        max_notes = self.task_data.get("max_notes", 3)
        
        self.progress_updated.emit(30, "Analisando significado semântico...")
        
        # Obter contexto semântico
        context = backend_llm.get_semantic_context(query, max_notes)
        
        self.progress_updated.emit(70, "Processando relações conceituais...")
        
        # Análise semântica adicional
        semantic_analysis = {
            "query_terms": query.lower().split(),
            "context_length": len(context) if context else 0,
            "context_available": bool(context),
            "notes_analyzed": max_notes
        }
        
        return {
            "query": query,
            "semantic_context": context,
            "analysis": semantic_analysis,
            "brain_stats": backend_llm.get_status() if hasattr(backend_llm, 'get_status') else {}
        }
    
    def _run_brain_analysis(self) -> Dict:
        """Análise completa do cérebro/cache"""
        self.progress_updated.emit(40, "Analisando memórias...")
        
        # Obter status do LLM
        llm_status = backend_llm.get_status()
        
        # Obter status do vault
        vault_stats = {}
        if hasattr(backend_llm, 'vault_structure'):
            vault_stats = backend_llm.vault_structure.get_vault_stats()
        
        # Obter status do Sembrain se disponível
        sembrain_stats = {}
        if hasattr(backend_llm, 'sembrain') and backend_llm.sembrain:
            sembrain_stats = backend_llm.sembrain.get_stats()
        
        self.progress_updated.emit(80, "Compilando relatório cerebral...")
        
        return {
            "llm_status": llm_status,
            "vault_status": vault_stats,
            "semantic_brain": sembrain_stats,
            "cache_performance": {
                "total_queries": len(getattr(backend_llm, 'query_history', [])),
                "cache_size": len(getattr(backend_llm, 'response_cache', {})),
                "memory_usage": "Calculando..."
            }
        }
    
    def _run_memory_update(self) -> Dict:
        """Atualiza memória/cache"""
        operation = self.task_data.get("operation", "clear")
        
        if operation == "clear_all":
            backend_llm.clear_cache("all")
            message = "Memória completamente limpa"
        elif operation == "clear_responses":
            backend_llm.clear_cache("responses")
            message = "Cache de respostas limpo"
        elif operation == "clear_semantic":
            backend_llm.clear_cache("semantic")
            message = "Cache semântico limpo"
        elif operation == "save_state":
            backend_llm.save_state()
            message = "Estado do cérebro salvo"
        else:
            message = "Operação desconhecida"
        
        return {
            "operation": operation,
            "message": message,
            "new_status": backend_llm.get_status() if hasattr(backend_llm, 'get_status') else {}
        }
    
    def stop(self):
        """Para a execução da thread"""
        self.is_running = False
        self.quit()


class GladosController(QObject):
    """
    Controladora principal do GLaDOS
    Integra TODOS os componentes do backend com a UI
    """
    
    # Sinais para UI
    response_ready = pyqtSignal(dict)  # Resposta completa do LLM
    vault_results_ready = pyqtSignal(dict)  # Resultados da busca no vault
    semantic_context_ready = pyqtSignal(dict)  # Contexto semântico
    brain_analysis_ready = pyqtSignal(dict)  # Análise do cérebro
    memory_updated = pyqtSignal(dict)  # Atualização de memória
    conversation_updated = pyqtSignal(list)  # Histórico atualizado
    
    # Sinais de status
    processing_started = pyqtSignal(str, str)  # (task_type, message)
    processing_progress = pyqtSignal(int, str)  # (percent, message)
    processing_completed = pyqtSignal(str)  # task_type
    error_occurred = pyqtSignal(str, str, str)  # (error_type, error_message, context)
    
    # Sinais de personalidade
    personality_updated = pyqtSignal(dict)
    voice_tone_changed = pyqtSignal(float, bool)  # (intensity, sarcasm_enabled)
    
    def __init__(self, vault_path: Optional[str] = None):
        super().__init__()
        
        # Estado do GLaDOS
        self.state = GladosState()
        
        # Instância do backend LLM (singleton)
        self.backend = backend_llm
        
        # Personalidade GLaDOS
        self.personality = GladosVoice(
            user_name="Helio",
            intensity=self.state.personality_intensity
        )
        
        # Workers ativos
        self.active_workers: Dict[str, BackendWorker] = {}
        
        # Histórico de conversa
        self.conversation_history: List[Dict] = []
        
        # Cache local para UI
        self.ui_cache = {
            "vault_structure": None,
            "book_covers": {},
            "recent_queries": [],
            "quick_responses": {}
        }
        
        # Timer para atualizações periódicas
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._periodic_update)
        self.update_timer.start(30000)  # Atualiza a cada 30 segundos
        
        logger.info("Controladora GLaDOS inicializada com backend completo")
    
    def _periodic_update(self):
        """Atualizações periódicas do sistema"""
        try:
            # Atualizar estatísticas
            status = self.backend.get_status()
            self.state.memory_usage = {
                "cache_hits": status.get("cache", {}).get("hits", 0),
                "cache_misses": status.get("cache", {}).get("misses", 0),
                "cache_hit_rate": status.get("cache", {}).get("hit_rate", 0)
            }
            
            # Limpar workers concluídos
            self._cleanup_finished_workers()
            
        except Exception as e:
            logger.warning(f"Erro em atualização periódica: {e}")
    
    def _cleanup_finished_workers(self):
        """Remove workers que já terminaram"""
        finished = []
        for task_id, worker in self.active_workers.items():
            if not worker.isRunning():
                finished.append(task_id)
        
        for task_id in finished:
            del self.active_workers[task_id]
    
    @pyqtSlot(str, bool, str, object)
    def ask_glados(
        self,
        question: str,
        use_semantic: bool = True,
        user_name: str = "Helio",
        request_metadata: Optional[Dict[str, Any]] = None,
    ):
        """Envia pergunta para GLaDOS (backend completo)"""

        # Adicionar ao histórico
        self._add_to_conversation("user", question)
        
        # Criar worker para processamento
        task_id = f"llm_{len(self.active_workers)}"
        worker = BackendWorker(
            task_type="llm_generate",
            task_data={
                "query": question,
                "use_semantic": use_semantic,
                "user_name": user_name,
                "request_metadata": request_metadata or {},
            }
        )
        
        # Conectar sinais
        worker.task_completed.connect(self._handle_llm_response)
        worker.task_failed.connect(self._handle_worker_error)
        worker.progress_updated.connect(self.processing_progress)
        
        # Armazenar e iniciar
        self.active_workers[task_id] = worker
        self.processing_started.emit("llm_generate", f"GLaDOS processando: '{question[:50]}...'")
        worker.start()
    
    def _handle_llm_response(self, result: Dict):
        """Processa resposta do LLM"""
        try:
            # Extrair texto da resposta
            response_text = result.get("text", "Desculpe, não consegui processar isso.")
            
            # Adicionar ao histórico
            self._add_to_conversation("assistant", response_text)
            
            # Emitir resposta formatada
            formatted_response = {
                "text": response_text,
                "metadata": {
                    "model": result.get("model", "TinyLlama-1.1B"),
                    "cached": result.get("cached", False),
                    "semantic_used": result.get("semantic_context_used", False),
                    "timestamp": result.get("timestamp", ""),
                    "backend_operation": result.get("backend_operation", {})
                },
                "personality": {
                    "intensity": self.state.personality_intensity,
                    "sarcasm": self.state.enable_sarcasm
                }
            }
            
            self.response_ready.emit(formatted_response)
            self.processing_completed.emit("llm_generate")
            
            # Atualizar cache de respostas rápidas
            query = result.get("backend_operation", {}).get("query", "")
            if query and len(response_text) < 200:
                self.ui_cache["quick_responses"][query.lower()] = response_text
            
        except Exception as e:
            self.error_occurred.emit("ResponseError", str(e), "handle_llm_response")
    
    @pyqtSlot(str, int, bool)
    def search_vault(self, query: str, limit: int = 5, use_semantic: bool = True):
        """Busca no vault do Obsidian"""
        task_id = f"vault_{len(self.active_workers)}"
        worker = BackendWorker(
            task_type="vault_search",
            task_data={
                "query": query,
                "limit": limit,
                "use_semantic": use_semantic
            }
        )
        
        worker.task_completed.connect(self._handle_vault_results)
        worker.task_failed.connect(self._handle_worker_error)
        worker.progress_updated.connect(self.processing_progress)
        
        self.active_workers[task_id] = worker
        self.processing_started.emit("vault_search", f"Buscando no vault: '{query}'")
        worker.start()
    
    def _handle_vault_results(self, results: Dict):
        """Processa resultados da busca no vault"""
        try:
            # Formatar para UI
            formatted_results = {
                "query": results.get("query", ""),
                "total": results.get("total_found", 0),
                "method": results.get("search_method", "textual"),
                "results": results.get("results", []),
                "vault_info": results.get("vault_stats", {})
            }
            
            # Cache da estrutura do vault para UI
            if not self.ui_cache["vault_structure"]:
                self.ui_cache["vault_structure"] = formatted_results.get("vault_info", {})
            
            self.vault_results_ready.emit(formatted_results)
            self.processing_completed.emit("vault_search")
            
        except Exception as e:
            self.error_occurred.emit("VaultSearchError", str(e), "handle_vault_results")
    
    @pyqtSlot(str, int)
    def get_semantic_context(self, query: str, max_notes: int = 3):
        """Obtém contexto semântico para uma consulta"""
        task_id = f"semantic_{len(self.active_workers)}"
        worker = BackendWorker(
            task_type="semantic_query",
            task_data={
                "query": query,
                "max_notes": max_notes
            }
        )
        
        worker.task_completed.connect(self._handle_semantic_context)
        worker.task_failed.connect(self._handle_worker_error)
        worker.progress_updated.connect(self.processing_progress)
        
        self.active_workers[task_id] = worker
        self.processing_started.emit("semantic_query", f"Analisando contexto semântico")
        worker.start()
    
    def _handle_semantic_context(self, context_data: Dict):
        """Processa contexto semântico"""
        try:
            self.semantic_context_ready.emit(context_data)
            self.processing_completed.emit("semantic_query")
        except Exception as e:
            self.error_occurred.emit("SemanticError", str(e), "handle_semantic_context")
    
    @pyqtSlot()
    def analyze_brain(self):
        """Faz análise completa do cérebro GLaDOS"""
        task_id = f"brain_{len(self.active_workers)}"
        worker = BackendWorker(
            task_type="brain_analysis",
            task_data={}
        )
        
        worker.task_completed.connect(self._handle_brain_analysis)
        worker.task_failed.connect(self._handle_worker_error)
        worker.progress_updated.connect(self.processing_progress)
        
        self.active_workers[task_id] = worker
        self.processing_started.emit("brain_analysis", "Analisando cérebro de GLaDOS...")
        worker.start()
    
    def _handle_brain_analysis(self, analysis: Dict):
        """Processa análise do cérebro"""
        try:
            self.brain_analysis_ready.emit(analysis)
            self.processing_completed.emit("brain_analysis")
        except Exception as e:
            self.error_occurred.emit("BrainAnalysisError", str(e), "handle_brain_analysis")
    
    @pyqtSlot(str)
    def update_memory(self, operation: str):
        """Atualiza memória/cache"""
        task_id = f"memory_{len(self.active_workers)}"
        worker = BackendWorker(
            task_type="memory_update",
            task_data={"operation": operation}
        )
        
        worker.task_completed.connect(self._handle_memory_update)
        worker.task_failed.connect(self._handle_worker_error)
        worker.progress_updated.connect(self.processing_progress)
        
        self.active_workers[task_id] = worker
        self.processing_started.emit("memory_update", f"Atualizando memória: {operation}")
        worker.start()
    
    def _handle_memory_update(self, result: Dict):
        """Processa atualização de memória"""
        try:
            self.memory_updated.emit(result)
            self.processing_completed.emit("memory_update")
        except Exception as e:
            self.error_occurred.emit("MemoryError", str(e), "handle_memory_update")
    
    @pyqtSlot(float, bool)
    def update_personality(self, intensity: float, sarcasm_enabled: bool):
        """Atualiza personalidade do GLaDOS"""
        self.state.personality_intensity = intensity
        self.state.enable_sarcasm = sarcasm_enabled
        
        # Atualizar instância da personalidade
        self.personality = GladosVoice(
            user_name="Helio",
            intensity=intensity
        )
        
        # Emitir sinais
        self.personality_updated.emit({
            "intensity": intensity,
            "sarcasm_enabled": sarcasm_enabled,
            "mode": self.state.current_mode
        })
        
        self.voice_tone_changed.emit(intensity, sarcasm_enabled)
        
        logger.info(f"Personalidade GLaDOS atualizada: intensidade={intensity}, sarcasmo={sarcasm_enabled}")
    
    @pyqtSlot(str)
    def set_mode(self, mode: str):
        """Altera modo de operação"""
        valid_modes = ["academic", "creative", "technical", "casual"]
        if mode not in valid_modes:
            mode = "academic"
        
        self.state.current_mode = mode
        
        # Ajustar parâmetros baseado no modo
        if mode == "academic":
            self.update_personality(0.8, True)
        elif mode == "creative":
            self.update_personality(0.9, True)
        elif mode == "technical":
            self.update_personality(0.6, False)
        elif mode == "casual":
            self.update_personality(0.4, True)

    @pyqtSlot(str)
    def set_generation_preset(self, preset_label: str) -> Dict[str, Any]:
        """Aplica preset de geração no backend LLM em runtime."""
        preset_map = {
            "Rápido": {
                "temperature": 0.25,
                "top_p": 0.85,
                "repeat_penalty": 1.15,
                "max_tokens": 220,
            },
            "Balanceado": {
                "temperature": 0.35,
                "top_p": 0.90,
                "repeat_penalty": 1.12,
                "max_tokens": 384,
            },
            "Qualidade": {
                "temperature": 0.45,
                "top_p": 0.92,
                "repeat_penalty": 1.08,
                "max_tokens": 512,
            },
        }

        selected_label = preset_label if preset_label in preset_map else "Balanceado"
        params = preset_map[selected_label]

        applied = {"preset": selected_label, **params}
        try:
            if hasattr(self.backend, "set_generation_params"):
                backend_result = self.backend.set_generation_params(**params)
                applied.update(backend_result)
            logger.info("Preset de geração aplicado: %s", selected_label)
        except Exception as e:
            logger.error("Falha ao aplicar preset de geração: %s", e)
            self.error_occurred.emit("PresetError", str(e), "set_generation_preset")

        return applied
    
    def _add_to_conversation(self, role: str, content: str):
        """Adiciona mensagem ao histórico"""
        message = {
            "role": role,
            "content": content,
            "timestamp": self._get_timestamp(),
            "mode": self.state.current_mode
        }
        
        self.conversation_history.append(message)
        
        # Manter histórico limitado
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
        
        # Emitir atualização
        self.conversation_updated.emit(self.conversation_history[-20:])  # Últimas 20 mensagens
    
    def _handle_worker_error(self, error_type: str, error_message: str):
        """Lida com erros dos workers"""
        self.error_occurred.emit(error_type, error_message, "backend_worker")
        logger.error(f"Worker error: {error_type} - {error_message}")
    
    def _get_timestamp(self) -> str:
        """Retorna timestamp formatado"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    def get_conversation_history(self, limit: int = 20) -> List[Dict]:
        """Retorna histórico de conversa"""
        return self.conversation_history[-limit:] if self.conversation_history else []
    
    def get_system_status(self) -> Dict:
        """Retorna status completo do sistema"""
        try:
            llm_status = self.backend.get_status()
            vault_stats = getattr(self.backend.vault_structure, 'get_vault_stats', lambda: {})()
            
            return {
                "glados_state": {
                    "personality_intensity": self.state.personality_intensity,
                    "sarcasm_enabled": self.state.enable_sarcasm,
                    "current_mode": self.state.current_mode,
                    "conversation_length": len(self.conversation_history)
                },
                "backend_status": llm_status,
                "vault_status": vault_stats,
                "worker_status": {
                    "active_workers": len(self.active_workers),
                    "worker_types": list(self.active_workers.keys())
                },
                "ui_cache": {
                    "cached_items": len(self.ui_cache.get("quick_responses", {})),
                    "recent_queries": len(self.ui_cache.get("recent_queries", []))
                }
            }
        except Exception as e:
            return {
                "error": str(e),
                "glados_state": self.state.__dict__
            }
    
    def quick_response(self, query: str) -> Optional[str]:
        """Resposta rápida do cache (sem processar no LLM)"""
        query_lower = query.lower()
        
        # Verificar cache
        if query_lower in self.ui_cache["quick_responses"]:
            return self.ui_cache["quick_responses"][query_lower]
        
        # Respostas padrão para comandos comuns
        quick_patterns = {
            "quem é você": "Eu sou GLaDOS, sua assistente filosófica sarcástica.",
            "qual seu nome": "GLaDOS, mas você já deveria saber disso.",
            "como você está": "Funcionando dentro dos parâmetros esperados, considerando suas limitações.",
            "obrigado": "De nada. Agora volte ao trabalho.",
            "olá": "Olá. Espero que tenha algo útil para perguntar.",
            "ajuda": "Consulte a documentação ou faça uma pergunta específica."
        }
        
        for pattern, response in quick_patterns.items():
            if pattern in query_lower:
                return response
        
        return None
    
    @pyqtSlot()
    def stop_all_workers(self):
        """Para todos os workers ativos"""
        for worker in self.active_workers.values():
            if worker.isRunning():
                worker.stop()
                worker.wait()
        
        self.active_workers.clear()
        logger.info("Todos os workers foram parados")


# Exemplo de integração com UI
class GladosUIAdapter:
    """Adaptador para conectar controladora com widgets PyQt6"""
    
    def __init__(self, controller: GladosController):
        self.controller = controller
        self.setup_connections()
    
    def setup_connections(self):
        """Conecta todos os sinais da controladora com slots da UI"""
        
        # Conectar sinais de resposta
        self.controller.response_ready.connect(self._handle_glados_response)
        self.controller.vault_results_ready.connect(self._handle_vault_results)
        self.controller.semantic_context_ready.connect(self._handle_semantic_context)
        
        # Conectar sinais de status
        self.controller.processing_started.connect(self._show_processing_status)
        self.controller.processing_progress.connect(self._update_progress)
        self.controller.processing_completed.connect(self._hide_processing_status)
        self.controller.error_occurred.connect(self._show_error)
        
        # Conectar sinais de personalidade
        self.controller.personality_updated.connect(self._update_personality_ui)
        self.controller.voice_tone_changed.connect(self._update_voice_tone_ui)
        
        # Conectar sinais de conversação
        self.controller.conversation_updated.connect(self._update_chat_history)
    
    def _handle_glados_response(self, response: Dict):
        """Atualiza widget de chat com resposta do GLaDOS"""
        # Implementação específica da UI
        text = response.get("text", "")
        metadata = response.get("metadata", {})
        
        # Exemplo: adicionar ao QTextEdit
        # self.chat_widget.add_message("GLaDOS", text, metadata)
        print(f"[GLaDOS]: {text[:100]}...")
    
    def _handle_vault_results(self, results: Dict):
        """Atualiza widget de resultados do vault"""
        # Implementação específica da UI
        print(f"[Vault] Encontrados {results.get('total', 0)} resultados")
    
    def _handle_semantic_context(self, context: Dict):
        """Atualiza widget de contexto semântico"""
        # Implementação específica da UI
        print(f"[Semantic] Contexto obtido: {context.get('query', '')}")
    
    def _show_processing_status(self, task_type: str, message: str):
        """Mostra status de processamento na UI"""
        # Exemplo: mostrar QProgressDialog
        print(f"[Processing] {task_type}: {message}")
    
    def _update_progress(self, percent: int, message: str):
        """Atualiza progresso na UI"""
        # Exemplo: atualizar QProgressBar
        print(f"[Progress] {percent}%: {message}")
    
    def _hide_processing_status(self, task_type: str):
        """Esconde status de processamento"""
        print(f"[Completed] {task_type}")
    
    def _show_error(self, error_type: str, error_message: str, context: str):
        """Mostra erro na UI"""
        # Exemplo: mostrar QMessageBox
        print(f"[ERROR] {error_type}: {error_message} ({context})")
    
    def _update_personality_ui(self, personality: Dict):
        """Atualiza UI da personalidade"""
        print(f"[Personality] Atualizada: {personality}")
    
    def _update_voice_tone_ui(self, intensity: float, sarcasm: bool):
        """Atualiza controles de voz na UI"""
        print(f"[Voice] Intensidade: {intensity}, Sarcasmo: {sarcasm}")
    
    def _update_chat_history(self, history: List[Dict]):
        """Atualiza histórico do chat na UI"""
        print(f"[History] {len(history)} mensagens no histórico")


# Exemplo de uso completo
def example_usage():
    """Exemplo de uso da controladora completa"""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Criar controladora
    controller = GladosController()
    
    # Criar adaptador para UI
    adapter = GladosUIAdapter(controller)
    
    # Exemplo de interações
    print("=== Sistema GLaDOS Inicializado ===")
    
    # Consultar status
    status = controller.get_system_status()
    print(f"Status: {status.get('backend_status', {}).get('status', 'unknown')}")
    
    # Fazer pergunta
    controller.ask_glados("O que é virtude para Aristóteles?")
    
    # Buscar no vault
    controller.search_vault("ética aristotélica", limit=3)
    
    # Analisar cérebro
    controller.analyze_brain()
    
    # Alterar personalidade
    controller.update_personality(0.9, True)
    
    # Alterar modo
    controller.set_mode("academic")
    
    # Ver histórico
    history = controller.get_conversation_history(5)
    print(f"Histórico: {len(history)} mensagens")
    
    # Resposta rápida
    quick = controller.quick_response("quem é você")
    print(f"Resposta rápida: {quick}")
    
    # Parar todos os workers (ao fechar aplicação)
    controller.stop_all_workers()
    
    print("=== Sistema GLaDOS Finalizado ===")
    
    return app.exec()


if __name__ == "__main__":
    example_usage()
