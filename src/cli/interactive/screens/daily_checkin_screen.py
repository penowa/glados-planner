# src/cli/interactive/screens/daily_checkin_screen.py
"""
Tela de check-in diário com formulário multi-passo.
Integra com DailyCheckinSystem.
"""
import datetime
from .base_screen import BaseScreen
from cli.integration.backend_integration import backend
from cli.theme import theme
from cli.icons import Icon, icon_text

class DailyCheckinScreen(BaseScreen):
    """Tela de check-in diário."""
    
    def __init__(self):
        super().__init__()
        self.title = "Check-in Diário"
        self.checkin_data = {}
    
    def show(self):
        theme.clear()
        theme.rule(f"[{self.title}]")
        
        today = datetime.datetime.now().strftime("%d/%m/%Y")
        theme.print(f"\n📅 Check-in do dia: {today}", style="primary")
        theme.print("=" * 50, style="dim")
        
        # Passo 1: Humor
        theme.print(f"\n{icon_text(Icon.INFO, '1. Como você está se sentindo hoje?')}", style="info")
        theme.print("  1) 😊 Excelente")
        theme.print("  2) 🙂 Bem")
        theme.print("  3) 😐 Normal")
        theme.print("  4) 😔 Cansado")
        theme.print("  5) 😞 Mal")
        
        mood = input("\nEscolha (1-5): ").strip()
        mood_map = {'1': 'excellent', '2': 'good', '3': 'normal', '4': 'tired', '5': 'bad'}
        self.checkin_data['mood'] = mood_map.get(mood, 'normal')
        
        # Passo 2: Qualidade do sono
        theme.print(f"\n{icon_text(Icon.INFO, '2. Qualidade do sono:')}", style="info")
        sleep_hours = input("Quantas horas dormiu? ").strip()
        sleep_quality = input("Qualidade (1-10): ").strip()
        
        self.checkin_data['sleep_hours'] = float(sleep_hours) if sleep_hours.replace('.', '').isdigit() else 0
        self.checkin_data['sleep_quality'] = int(sleep_quality) if sleep_quality.isdigit() else 5
        
        # Passo 3: Metas do dia
        theme.print(f"\n{icon_text(Icon.TASK, '3. Metas para hoje:')}", style="info")
        
        goals = []
        theme.print("Digite suas metas (uma por linha, linha vazia para terminar):", style="dim")
        
        for i in range(1, 6):
            goal = input(f"  Meta {i}: ").strip()
            if not goal:
                break
            goals.append(goal)
        
        self.checkin_data['goals'] = goals
        
        # Passo 4: Desafios esperados
        theme.print(f"\n{icon_text(Icon.WARNING, '4. Desafios ou obstáculos esperados:')}", style="info")
        challenges = input("(opcional): ").strip()
        if challenges:
            self.checkin_data['challenges'] = challenges
        
        # Passo 5: Energia e foco
        theme.print(f"\n{icon_text(Icon.INFO, '5. Níveis de energia e foco:')}", style="info")
        energy = input("Energia (1-10): ").strip()
        focus = input("Foco (1-10): ").strip()
        
        self.checkin_data['energy'] = int(energy) if energy.isdigit() else 5
        self.checkin_data['focus'] = int(focus) if focus.isdigit() else 5
        
        # Revisão e confirmação
        theme.print(f"\n{icon_text(Icon.INFO, 'Revisão do check-in:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        for key, value in self.checkin_data.items():
            if key == 'goals':
                theme.print(f"  Metas: {len(value)} definidas", style="info")
            else:
                theme.print(f"  {key.replace('_', ' ').title()}: {value}", style="info")
        
        # Confirmar
        theme.print(f"\n{icon_text(Icon.QUESTION, 'Confirmar check-in?')}", style="warning")
        confirm = input("(S/n): ").strip().lower()
        
        if confirm in ['s', 'sim', '']:
            try:
                result = backend.perform_daily_checkin(self.checkin_data)
                
                if result.get('success', False):
                    theme.print(f"\n✅ {icon_text(Icon.SUCCESS, 'Check-in registrado com sucesso!')}", style="success")
                    
                    # Mostrar feedback do sistema
                    feedback = result.get('feedback', '')
                    if feedback:
                        theme.print(f"\n{icon_text(Icon.GLADOS, 'GLaDOS diz:')}", style="accent")
                        theme.print(f"  {feedback}", style="info")
                    
                    # Mostrar estatísticas se disponíveis
                    stats = result.get('stats', {})
                    if stats:
                        theme.print(f"\n{icon_text(Icon.INFO, 'Estatísticas:')}", style="info")
                        for stat_key, stat_value in stats.items():
                            theme.print(f"  {stat_key}: {stat_value}", style="dim")
                
                else:
                    theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Falha ao registrar check-in:')}", style="error")
                    theme.print(f"  {result.get('error', 'Erro desconhecido')}", style="error")
                    
            except Exception as e:
                theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Erro:')}", style="error")
                theme.print(f"  {str(e)}", style="error")
        
        else:
            theme.print(f"\n{icon_text(Icon.INFO, 'Check-in cancelado.')}", style="warning")
        
        self.wait_for_exit()
