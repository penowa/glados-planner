"""
Sistema de check-in diário para feedback contínuo
"""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
from pathlib import Path
import uuid


@dataclass
class CheckinData:
    """Dados de um check-in diário"""
    id: str
    date: str
    time: str
    mood_score: float  # 1.0-5.0
    energy_level: float  # 1.0-5.0
    focus_score: float  # 1.0-5.0
    achievements: List[str] = field(default_factory=list)
    challenges: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    goals_tomorrow: List[str] = field(default_factory=list)
    notes: str = ""
    productivity_score: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "date": self.date,
            "time": self.time,
            "mood_score": self.mood_score,
            "energy_level": self.energy_level,
            "focus_score": self.focus_score,
            "achievements": self.achievements,
            "challenges": self.challenges,
            "insights": self.insights,
            "goals_tomorrow": self.goals_tomorrow,
            "notes": self.notes,
            "productivity_score": self.productivity_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CheckinData':
        return cls(
            id=data["id"],
            date=data["date"],
            time=data["time"],
            mood_score=data["mood_score"],
            energy_level=data["energy_level"],
            focus_score=data["focus_score"],
            achievements=data.get("achievements", []),
            challenges=data.get("challenges", []),
            insights=data.get("insights", []),
            goals_tomorrow=data.get("goals_tomorrow", []),
            notes=data.get("notes", ""),
            productivity_score=data.get("productivity_score", 0.0)
        )


class DailyCheckinSystem:
    def __init__(self, vault_path: str, user_id: str = "default"):
        """
        Inicializa o sistema de check-in diário
        
        Args:
            vault_path: Caminho para o vault do Obsidian
            user_id: ID do usuário para personalização
        """
        self.vault_path = Path(vault_path).expanduser()
        self.user_id = user_id
        
        # Arquivo de check-ins
        self.checkin_file = self.vault_path / "06-RECURSOS" / "daily_checkins.json"
        
        # Carrega check-ins existentes
        self.checkins = self._load_checkins()
        
        # Histórico
        self.history = []
    
    def _load_checkins(self) -> Dict[str, CheckinData]:
        """Carrega check-ins do arquivo"""
        checkins = {}
        
        if self.checkin_file.exists():
            try:
                with open(self.checkin_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for checkin_id, checkin_data in data.items():
                    checkins[checkin_id] = CheckinData.from_dict(checkin_data)
            except Exception as e:
                print(f"Erro ao carregar check-ins: {e}")
        
        return checkins
    
    def _save_checkins(self):
        """Salva check-ins no arquivo"""
        try:
            data = {checkin_id: checkin.to_dict() 
                   for checkin_id, checkin in self.checkins.items()}
            
            self.checkin_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.checkin_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar check-ins: {e}")
    
    def morning_routine(self, energy_level: float = 3.0, 
                       focus_score: float = 3.0,
                       goals_today: List[str] = None) -> Dict:
        """
        Rotina matinal automatizada
        
        Args:
            energy_level: Nível de energia (1.0-5.0)
            focus_score: Nível de foco (1.0-5.0)
            goals_today: Metas para o dia
            
        Returns:
            Dicionário com rotina criada
        """
        if goals_today is None:
            goals_today = []
        
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        
        # Cria check-in matinal
        checkin = CheckinData(
            id=str(uuid.uuid4()),
            date=date_str,
            time=time_str,
            mood_score=3.0,  # padrão neutro
            energy_level=energy_level,
            focus_score=focus_score,
            achievements=[],
            challenges=[],
            insights=[],
            goals_tomorrow=[],
            notes=f"Check-in matinal automático",
            productivity_score=0.0
        )
        
        # Adiciona à coleção
        self.checkins[checkin.id] = checkin
        
        # Salva
        self._save_checkins()
        
        # Rotina sugerida
        routine = {
            "checkin_id": checkin.id,
            "time": time_str,
            "suggested_activities": [
                {"time": "07:30-08:00", "activity": "Revisão rápida da agenda do dia"},
                {"time": "08:00-08:15", "activity": "Definição de 3 metas principais"},
                {"time": "08:15-08:30", "activity": "Pequena sessão de leitura (10-15p)"},
                {"time": "08:30-09:00", "activity": "Planejamento de blocos de trabalho"}
            ],
            "personalized_tip": self._get_morning_tip(energy_level, focus_score),
            "goals_today": goals_today
        }
        
        # Registra no histórico
        self.history.append({
            "date": date_str,
            "time": time_str,
            "type": "morning",
            "energy_level": energy_level,
            "focus_score": focus_score
        })
        
        return routine
    
    def evening_checkin(self, mood_score: float = 3.0,
                       achievements: List[str] = None,
                       challenges: List[str] = None,
                       insights: List[str] = None) -> Dict:
        """
        Check-in noturno
        
        Args:
            mood_score: Humor (1.0-5.0)
            achievements: Conquistas do dia
            challenges: Desafios enfrentados
            insights: Insights/reflexões
            
        Returns:
            Análise do dia
        """
        if achievements is None:
            achievements = []
        if challenges is None:
            challenges = []
        if insights is None:
            insights = []
        
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        
        # Calcula produtividade
        productivity_score = self.calculate_productivity_score(date_str)
        
        # Cria check-in noturno
        checkin = CheckinData(
            id=str(uuid.uuid4()),
            date=date_str,
            time=time_str,
            mood_score=mood_score,
            energy_level=2.0,  # geralmente mais baixo à noite
            focus_score=2.0,
            achievements=achievements,
            challenges=challenges,
            insights=insights,
            goals_tomorrow=[],
            notes=f"Check-in noturno automático",
            productivity_score=productivity_score
        )
        
        # Adiciona à coleção
        self.checkins[checkin.id] = checkin
        
        # Salva
        self._save_checkins()
        
        # Análise do dia
        analysis = {
            "checkin_id": checkin.id,
            "time": time_str,
            "mood_score": mood_score,
            "productivity_score": productivity_score,
            "achievement_count": len(achievements),
            "challenge_count": len(challenges),
            "insight_count": len(insights),
            "summary": self._generate_daily_summary(achievements, challenges, insights),
            "suggestions_tomorrow": self._get_tomorrow_suggestions(productivity_score, mood_score)
        }
        
        # Registra no histórico
        self.history.append({
            "date": date_str,
            "time": time_str,
            "type": "evening",
            "mood_score": mood_score,
            "productivity_score": productivity_score
        })
        
        return analysis
    
    def calculate_productivity_score(self, date_str: str) -> float:
        """
        Calcula produtividade do dia (simplificado)
        
        Args:
            date_str: Data no formato YYYY-MM-DD
            
        Returns:
            Score de produtividade (0.0-10.0)
        """
        # Esta é uma implementação simplificada
        # Na implementação real, você integraria com o AgendaManager
        
        # Fatores de produtividade
        base_score = 5.0  # neutro
        
        # Verifica se há check-ins para este dia
        day_checkins = []
        for checkin in self.checkins.values():
            if checkin.date == date_str:
                day_checkins.append(checkin)
        
        if not day_checkins:
            return base_score
        
        # Calcula médias
        avg_mood = sum(c.mood_score for c in day_checkins) / len(day_checkins)
        avg_energy = sum(c.energy_level for c in day_checkins) / len(day_checkins)
        avg_focus = sum(c.focus_score for c in day_checkins) / len(day_checkins)
        
        # Conquistas (cada uma vale +0.5)
        total_achievements = sum(len(c.achievements) for c in day_checkins)
        
        # Fórmula de produtividade
        productivity = (
            avg_mood * 0.3 +
            avg_energy * 0.3 +
            avg_focus * 0.4 +
            (total_achievements * 0.5)
        )
        
        # Normaliza para 0-10
        return min(max(productivity, 0.0), 10.0)
    
    def _get_morning_tip(self, energy_level: float, focus_score: float) -> str:
        """Retorna dica personalizada para a manhã"""
        if energy_level < 2.5 and focus_score < 2.5:
            return "Energia e foco baixos. Comece com tarefas simples para criar momentum."
        elif energy_level > 3.5 and focus_score > 3.5:
            return "Energia e foco altos. Ótimo momento para tarefas complexas ou leitura densa."
        elif energy_level > 3.5 and focus_score < 2.5:
            return "Energia alta mas foco baixo. Tarefas físicas ou organização podem ser boas."
        else:
            return "Níveis medianos. Sugiro começar com revisão e planejamento antes de tarefas complexas."
    
    def _generate_daily_summary(self, achievements: List[str], 
                               challenges: List[str], 
                               insights: List[str]) -> str:
        """Gera um resumo automático do dia"""
        if not achievements and not challenges and not insights:
            return "Dia sem registros significativos."
        
        parts = []
        
        if achievements:
            parts.append(f"Concluiu {len(achievements)} conquistas.")
        
        if challenges:
            parts.append(f"Enfrentou {len(challenges)} desafios.")
        
        if insights:
            parts.append(f"Teve {len(insights)} insights importantes.")
        
        return " ".join(parts)
    
    def _get_tomorrow_suggestions(self, productivity_score: float, 
                                 mood_score: float) -> List[str]:
        """Gera sugestões para o próximo dia"""
        suggestions = []
        
        if productivity_score < 4.0:
            suggestions.append("Comece com pequenas vitórias para construir confiança.")
            suggestions.append("Considere ajustar metas para serem mais realistas.")
        
        if mood_score < 2.5:
            suggestions.append("Inclua uma atividade prazerosa no planejamento.")
            suggestions.append("Pratique mindfulness por 5-10 minutos pela manhã.")
        
        if productivity_score > 7.0:
            suggestions.append("Mantenha o ritmo, mas não esqueça de pausas.")
            suggestions.append("Considere abordar projetos mais desafiadores.")
        
        if not suggestions:
            suggestions.append("Continue com a rotina atual, está funcionando bem.")
        
        return suggestions
    
    def get_recent_checkins(self, days: int = 7) -> List[Dict]:
        """
        Retorna check-ins recentes
        
        Args:
            days: Número de dias para trás
            
        Returns:
            Lista de check-ins ordenados por data
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        recent = []
        for checkin in self.checkins.values():
            checkin_date = datetime.strptime(checkin.date, "%Y-%m-%d").date()
            if checkin_date >= cutoff_date:
                recent.append({
                    "date": checkin.date,
                    "time": checkin.time,
                    "mood_score": checkin.mood_score,
                    "energy_level": checkin.energy_level,
                    "productivity_score": checkin.productivity_score,
                    "achievements": checkin.achievements
                })
        
        # Ordena por data (mais recente primeiro)
        recent.sort(key=lambda x: x["date"], reverse=True)
        
        return recent
    
    def get_trends(self, days: int = 30) -> Dict:
        """
        Analisa tendências nos check-ins
        
        Args:
            days: Número de dias para análise
            
        Returns:
            Análise de tendências
        """
        recent_checkins = self.get_recent_checkins(days)
        
        if not recent_checkins:
            return {"message": "Dados insuficientes para análise"}
        
        # Calcula médias
        avg_mood = sum(c["mood_score"] for c in recent_checkins) / len(recent_checkins)
        avg_energy = sum(c["energy_level"] for c in recent_checkins) / len(recent_checkins)
        avg_productivity = sum(c["productivity_score"] for c in recent_checkins) / len(recent_checkins)
        
        # Identifica padrões
        patterns = []
        
        if avg_mood < 2.5:
            patterns.append("Humor consistentemente baixo")
        elif avg_mood > 4.0:
            patterns.append("Humor consistentemente alto")
        
        if avg_energy < 2.5:
            patterns.append("Energia consistentemente baixa")
        
        if avg_productivity > 7.0:
            patterns.append("Produtividade consistentemente alta")
        elif avg_productivity < 4.0:
            patterns.append("Produtividade consistentemente baixa")
        
        # Recomendações baseadas em padrões
        recommendations = []
        
        if "Humor consistentemente baixo" in patterns:
            recommendations.append("Considere incluir mais atividades de autocuidado")
        
        if "Produtividade consistentemente baixa" in patterns:
            recommendations.append("Experimente diferentes técnicas de pomodoro ou planejamento")
        
        if not patterns:
            recommendations.append("Padrões consistentes, continue o bom trabalho")
        
        return {
            "analysis_period_days": days,
            "total_checkins_analyzed": len(recent_checkins),
            "averages": {
                "mood": round(avg_mood, 2),
                "energy": round(avg_energy, 2),
                "productivity": round(avg_productivity, 2)
            },
            "detected_patterns": patterns,
            "recommendations": recommendations
        }
