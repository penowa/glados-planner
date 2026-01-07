# [file name]: src/core/modules/pomodoro_timer.py
"""
Temporizador Pomodoro para estudos filosóficos
"""
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import threading
import json
from pathlib import Path

class PomodoroTimer:
    """Temporizador Pomodoro para gerenciamento de tempo de estudo"""
    
    def __init__(self, vault_path: str):
        """
        Inicializa o temporizador Pomodoro
        
        Args:
            vault_path: Caminho para o vault do Obsidian
        """
        self.vault_path = Path(vault_path).expanduser()
        self.stats_file = self.vault_path / "06-RECURSOS" / "pomodoro_stats.json"
        
        # Estado do timer
        self.is_running = False
        self.is_paused = False
        self.start_time = None
        self.paused_time = None
        self.elapsed_paused = 0
        self.current_session = None
        
        # Configurações padrão
        self.work_duration = 25 * 60  # 25 minutos em segundos
        self.break_duration = 5 * 60  # 5 minutos em segundos
        self.long_break_duration = 15 * 60  # 15 minutos em segundos
        self.sessions_before_long_break = 4
        
        # Estatísticas
        self.stats = self._load_stats()
        self.current_session_type = "work"  # work, short_break, long_break
        
        # Thread do timer
        self.timer_thread = None
        
        # Callbacks
        self.on_tick = None
        self.on_complete = None
        self.on_phase_change = None
    
    def _load_stats(self) -> Dict:
        """Carrega estatísticas do arquivo"""
        stats = {
            "total_sessions": 0,
            "work_sessions": 0,
            "short_breaks": 0,
            "long_breaks": 0,
            "total_work_time": 0,  # em segundos
            "total_break_time": 0,
            "daily_stats": {},
            "weekly_stats": {},
            "session_history": []
        }
        
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    stats.update(loaded)
            except:
                pass
        
        return stats
    
    def _save_stats(self):
        """Salva estatísticas no arquivo"""
        try:
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar estatísticas: {e}")
    
    def start(self, session_type: str = "work", discipline: str = None) -> bool:
        """
        Inicia uma sessão Pomodoro
        
        Args:
            session_type: Tipo de sessão (work, short_break, long_break)
            discipline: Disciplina relacionada (opcional)
            
        Returns:
            True se iniciado com sucesso
        """
        if self.is_running:
            return False
        
        self.current_session_type = session_type
        self.is_running = True
        self.is_paused = False
        self.start_time = time.time()
        self.elapsed_paused = 0
        
        # Cria registro da sessão
        self.current_session = {
            "type": session_type,
            "discipline": discipline,
            "start_time": datetime.now().isoformat(),
            "planned_duration": self._get_duration_for_type(session_type),
            "notes": ""
        }
        
        # Inicia thread do timer
        self.timer_thread = threading.Thread(target=self._run_timer)
        self.timer_thread.daemon = True
        self.timer_thread.start()
        
        # Chama callback de mudança de fase
        if self.on_phase_change:
            self.on_phase_change(session_type, self._get_duration_for_type(session_type))
        
        return True
    
    def _run_timer(self):
        """Executa o timer em uma thread separada"""
        target_duration = self._get_duration_for_type(self.current_session_type)
        
        while self.is_running:
            if not self.is_paused:
                current_time = time.time()
                elapsed = current_time - self.start_time - self.elapsed_paused
                
                # Chama callback de tick
                if self.on_tick:
                    self.on_tick(elapsed, target_duration - elapsed)
                
                # Verifica se terminou
                if elapsed >= target_duration:
                    self.is_running = False
                    self._complete_session()
                    
                    # Chama callback de conclusão
                    if self.on_complete:
                        self.on_complete(self.current_session_type)
                    
                    break
                
                time.sleep(1)  # Tick a cada segundo
            else:
                time.sleep(0.1)  # Pausa mais curta
    
    def _get_duration_for_type(self, session_type: str) -> int:
        """Obtém duração baseada no tipo de sessão"""
        if session_type == "work":
            return self.work_duration
        elif session_type == "short_break":
            return self.break_duration
        elif session_type == "long_break":
            return self.long_break_duration
        return self.work_duration
    
    def pause(self) -> bool:
        """
        Pausa o timer atual
        
        Returns:
            True se pausado com sucesso
        """
        if not self.is_running or self.is_paused:
            return False
        
        self.is_paused = True
        self.paused_time = time.time()
        return True
    
    def resume(self) -> bool:
        """
        Retoma o timer pausado
        
        Returns:
            True se retomado com sucesso
        """
        if not self.is_running or not self.is_paused:
            return False
        
        self.is_paused = False
        
        # Calcula tempo pausado
        if self.paused_time:
            self.elapsed_paused += time.time() - self.paused_time
            self.paused_time = None
        
        return True
    
    def stop(self, save_stats: bool = True) -> Dict:
        """
        Para o timer atual
        
        Args:
            save_stats: Se True, salva estatísticas
            
        Returns:
            Dados da sessão interrompida
        """
        was_running = self.is_running
        
        self.is_running = False
        self.is_paused = False
        
        if was_running and self.current_session:
            # Calcula duração real
            end_time = time.time()
            actual_duration = end_time - self.start_time - self.elapsed_paused
            
            self.current_session["end_time"] = datetime.now().isoformat()
            self.current_session["actual_duration"] = actual_duration
            self.current_session["completed"] = actual_duration >= self.current_session["planned_duration"] * 0.9
            
            # Se não foi completada, não conta como sessão completa
            if not self.current_session["completed"]:
                was_running = False
            
            if save_stats and was_running:
                self._update_stats(self.current_session)
        
        return self.current_session if self.current_session else {}
    
    def _complete_session(self):
        """Completa uma sessão e atualiza estatísticas"""
        if self.current_session:
            end_time = time.time()
            actual_duration = end_time - self.start_time - self.elapsed_paused
            
            self.current_session["end_time"] = datetime.now().isoformat()
            self.current_session["actual_duration"] = actual_duration
            self.current_session["completed"] = True
            
            self._update_stats(self.current_session)
    
    def _update_stats(self, session: Dict):
        """Atualiza estatísticas com dados da sessão"""
        # Contadores básicos
        self.stats["total_sessions"] += 1
        
        session_type = session["type"]
        if session_type == "work":
            self.stats["work_sessions"] += 1
            self.stats["total_work_time"] += session["actual_duration"]
        elif session_type == "short_break":
            self.stats["short_breaks"] += 1
            self.stats["total_break_time"] += session["actual_duration"]
        elif session_type == "long_break":
            self.stats["long_breaks"] += 1
            self.stats["total_break_time"] += session["actual_duration"]
        
        # Estatísticas diárias
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.stats["daily_stats"]:
            self.stats["daily_stats"][today] = {
                "work_sessions": 0,
                "work_time": 0,
                "breaks": 0,
                "break_time": 0
            }
        
        if session_type == "work":
            self.stats["daily_stats"][today]["work_sessions"] += 1
            self.stats["daily_stats"][today]["work_time"] += session["actual_duration"]
        else:
            self.stats["daily_stats"][today]["breaks"] += 1
            self.stats["daily_stats"][today]["break_time"] += session["actual_duration"]
        
        # Estatísticas semanais
        week_num = datetime.now().strftime("%Y-W%W")
        if week_num not in self.stats["weekly_stats"]:
            self.stats["weekly_stats"][week_num] = {
                "work_sessions": 0,
                "work_time": 0,
                "productivity_score": 0
            }
        
        if session_type == "work":
            self.stats["weekly_stats"][week_num]["work_sessions"] += 1
            self.stats["weekly_stats"][week_num]["work_time"] += session["actual_duration"]
        
        # Histórico de sessões (mantém apenas as últimas 100)
        self.stats["session_history"].append(session)
        if len(self.stats["session_history"]) > 100:
            self.stats["session_history"] = self.stats["session_history"][-100:]
        
        # Salva estatísticas
        self._save_stats()
    
    def get_stats(self) -> Dict:
        """
        Obtém estatísticas do Pomodoro
        
        Returns:
            Estatísticas detalhadas
        """
        # Calcula estatísticas adicionais
        stats = self.stats.copy()
        
        # Tempo total formatado
        stats["total_work_time_formatted"] = self._format_time(stats["total_work_time"])
        stats["total_break_time_formatted"] = self._format_time(stats["total_break_time"])
        
        # Produtividade hoje
        today = datetime.now().strftime("%Y-%m-%d")
        if today in stats["daily_stats"]:
            today_stats = stats["daily_stats"][today]
            stats["today"] = {
                "work_sessions": today_stats["work_sessions"],
                "work_time": self._format_time(today_stats["work_time"]),
                "breaks": today_stats["breaks"],
                "break_time": self._format_time(today_stats["break_time"])
            }
        else:
            stats["today"] = {"work_sessions": 0, "work_time": "0h 0m", "breaks": 0, "break_time": "0h 0m"}
        
        # Estatísticas da semana
        week_num = datetime.now().strftime("%Y-W%W")
        if week_num in stats["weekly_stats"]:
            week_stats = stats["weekly_stats"][week_num]
            stats["this_week"] = {
                "work_sessions": week_stats["work_sessions"],
                "work_time": self._format_time(week_stats["work_time"])
            }
        else:
            stats["this_week"] = {"work_sessions": 0, "work_time": "0h 0m"}
        
        # Sessão atual se estiver rodando
        if self.is_running and self.current_session:
            current_time = time.time()
            elapsed = current_time - self.start_time - self.elapsed_paused
            remaining = self._get_duration_for_type(self.current_session_type) - elapsed
            
            stats["current_session"] = {
                "type": self.current_session_type,
                "elapsed": self._format_time(elapsed),
                "remaining": self._format_time(remaining),
                "progress": (elapsed / self._get_duration_for_type(self.current_session_type)) * 100
            }
        
        return stats
    
    def _format_time(self, seconds: float) -> str:
        """Formata tempo em segundos para string legível"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def get_recommendations(self) -> Dict:
        """
        Obtém recomendações baseadas nas estatísticas
        
        Returns:
            Recomendações personalizadas
        """
        recommendations = []
        
        # Verifica estatísticas de hoje
        today = datetime.now().strftime("%Y-%m-%d")
        if today in self.stats["daily_stats"]:
            today_stats = self.stats["daily_stats"][today]
            
            # Recomendações baseadas no tempo de trabalho
            if today_stats["work_time"] < 2 * 3600:  # Menos de 2 horas
                recommendations.append({
                    "type": "motivation",
                    "message": "Considere fazer mais uma sessão Pomodoro hoje",
                    "priority": "medium"
                })
            elif today_stats["work_time"] > 6 * 3600:  # Mais de 6 horas
                recommendations.append({
                    "type": "health",
                    "message": "Você já trabalhou bastante hoje. Considere descansar.",
                    "priority": "high"
                })
            
            # Verifica proporção trabalho/descanso
            if today_stats["work_time"] > 0:
                work_break_ratio = today_stats["break_time"] / today_stats["work_time"]
                if work_break_ratio < 0.1:  # Menos de 10% de descanso
                    recommendations.append({
                        "type": "balance",
                        "message": "Considere fazer mais pausas para melhor produtividade",
                        "priority": "high"
                    })
        
        # Recomendações gerais
        if self.stats["total_work_time"] < 10 * 3600:  # Menos de 10 horas totais
            recommendations.append({
                "type": "consistency",
                "message": "Tente manter uma rotina diária de Pomodoro",
                "priority": "low"
            })
        
        # Ordena por prioridade
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: priority_order[x["priority"]])
        
        return {
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    
    def configure(self, work_minutes: int = 25, break_minutes: int = 5, 
                  long_break_minutes: int = 15, sessions_before_long_break: int = 4):
        """
        Configura os parâmetros do Pomodoro
        
        Args:
            work_minutes: Minutos de trabalho por sessão
            break_minutes: Minutos de pausa curta
            long_break_minutes: Minutos de pausa longa
            sessions_before_long_break: Sessões de trabalho antes de pausa longa
        """
        self.work_duration = work_minutes * 60
        self.break_duration = break_minutes * 60
        self.long_break_duration = long_break_minutes * 60
        self.sessions_before_long_break = sessions_before_long_break
    
    def get_next_session_type(self) -> str:
        """
        Determina o próximo tipo de sessão baseado no histórico
        
        Returns:
            Tipo da próxima sessão
        """
        # Conta sessões de trabalho consecutivas
        consecutive_work = 0
        for session in reversed(self.stats["session_history"]):
            if session["type"] == "work":
                consecutive_work += 1
            else:
                break
        
        # Decide próximo tipo
        if consecutive_work >= self.sessions_before_long_break:
            return "long_break"
        elif consecutive_work > 0:
            return "short_break"
        else:
            return "work"
