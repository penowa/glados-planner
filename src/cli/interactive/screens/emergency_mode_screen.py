# src/cli/interactive/screens/emergency_mode_screen.py
"""
Tela de modo emergência para reorganização automática.
Integra com AgendaManager.emergency_mode().
"""
from .base_screen import BaseScreen
from cli.integration.backend_integration import backend
from cli.theme import theme
from cli.icons import Icon, icon_text

class EmergencyModeScreen(BaseScreen):
    """Tela de modo emergência."""
    
    def __init__(self):
        super().__init__()
        self.title = "Modo Emergência"
    
    def show(self):
        theme.clear()
        theme.rule(f"[{self.title}]", style="error")
        
        theme.print(f"\n{icon_text(Icon.ALERT, 'ATENÇÃO: MODO EMERGÊNCIA')}", style="error")
        theme.print("=" * 60, style="error")
        
        theme.print("\nEste modo irá:", style="warning")
        theme.print("  1. 🚨 Reorganizar completamente sua agenda", style="warning")
        theme.print("  2. 📋 Priorizar tarefas críticas e urgentes", style="warning")
        theme.print("  3. 📅 Adiar compromissos não essenciais", style="warning")
        theme.print("  4. 🎯 Criar blocos focados de trabalho", style="warning")
        theme.print("  5. ⚠️  Cancelar eventos de baixa prioridade", style="warning")
        
        theme.print("\n" + "=" * 60, style="dim")
        
        # Motivo da emergência
        theme.print(f"\n{icon_text(Icon.QUESTION, 'Motivo da emergência:')}", style="info")
        theme.print("  1) 📝 Prova/Exame próximo")
        theme.print("  2) ⏰ Prazo de entrega curto")
        theme.print("  3) 🚨 Emergência pessoal")
        theme.print("  4) 🔧 Sistema fora do ar")
        theme.print("  5) 🎯 Outro")
        
        reason = input("\nEscolha (1-5): ").strip()
        reason_map = {
            '1': 'exam', '2': 'deadline', '3': 'personal', 
            '4': 'system', '5': 'other'
        }
        
        emergency_reason = reason_map.get(reason, 'other')
        
        # Duração da emergência
        theme.print(f"\n{icon_text(Icon.TIMER, 'Duração da emergência:')}", style="info")
        duration = input("Dias (1-7, padrão=3): ").strip()
        duration_days = int(duration) if duration.isdigit() and 1 <= int(duration) <= 7 else 3
        
        # Nível de emergência
        theme.print(f"\n{icon_text(Icon.WARNING, 'Nível de emergência:')}", style="info")
        theme.print("  1) 🟢 Moderado (reorganiza, mas mantém essenciais)")
        theme.print("  2) 🟡 Alto (cancela não-essenciais)")
        theme.print("  3) 🔴 Crítico (foco total, cancela tudo não-crítico)")
        
        level = input("\nEscolha (1-3): ").strip()
        level_map = {'1': 'moderate', '2': 'high', '3': 'critical'}
        emergency_level = level_map.get(level, 'moderate')
        
        # Tarefas críticas
        theme.print(f"\n{icon_text(Icon.TASK, 'Tarefas críticas (uma por linha):')}", style="info")
        critical_tasks = []
        
        for i in range(1, 6):
            task = input(f"  Tarefa crítica {i}: ").strip()
            if not task:
                break
            critical_tasks.append(task)
        
        # Confirmação final
        theme.print(f"\n{icon_text(Icon.ALERT, 'CONFIRMAÇÃO FINAL')}", style="error")
        theme.print("=" * 60, style="error")
        
        theme.print(f"\nVocê está prestes a ativar o modo emergência:", style="warning")
        theme.print(f"  • Motivo: {emergency_reason}", style="info")
        theme.print(f"  • Duração: {duration_days} dias", style="info")
        theme.print(f"  • Nível: {emergency_level}", style="info")
        theme.print(f"  • Tarefas críticas: {len(critical_tasks)}", style="info")
        
        theme.print(f"\n{icon_text(Icon.WARNING, 'ISSO NÃO PODE SER DESFEITO FACILMENTE!')}", style="error")
        
        confirm = input("\nDigite 'EMERGENCIA' para confirmar: ").strip()
        
        if confirm == 'EMERGENCIA':
            theme.print(f"\n{icon_text(Icon.LOADING, 'Ativando modo emergência...')}", style="info")
            
            try:
                # Usar backend para ativar modo emergência
                result = backend.activate_emergency_mode({
                    'reason': emergency_reason,
                    'duration_days': duration_days,
                    'level': emergency_level,
                    'critical_tasks': critical_tasks
                })
                
                if result.get('success', False):
                    theme.print(f"\n✅ {icon_text(Icon.SUCCESS, 'Modo emergência ativado!')}", style="success")
                    
                    # Mostrar resumo das mudanças
                    changes = result.get('changes', {})
                    
                    if changes:
                        theme.print(f"\n{icon_text(Icon.INFO, 'Mudanças aplicadas:')}", style="info")
                        
                        if 'canceled' in changes:
                            theme.print(f"  📋 Eventos cancelados: {changes['canceled']}", style="warning")
                        
                        if 'rescheduled' in changes:
                            theme.print(f"  📅 Eventos reagendados: {changes['rescheduled']}", style="info")
                        
                        if 'created' in changes:
                            theme.print(f"  🎯 Novos blocos criados: {changes['created']}", style="success")
                    
                    # Mostrar nova agenda
                    theme.print(f"\n{icon_text(Icon.CALENDAR, 'Nova agenda emergencial:')}", style="primary")
                    # TODO: Mostrar agenda reorganizada
                
                else:
                    theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Falha ao ativar modo emergência:')}", style="error")
                    theme.print(f"  {result.get('error', 'Erro desconhecido')}", style="error")
                    
            except Exception as e:
                theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Erro crítico:')}", style="error")
                theme.print(f"  {str(e)}", style="error")
        
        else:
            theme.print(f"\n{icon_text(Icon.INFO, 'Modo emergência cancelado.')}", style="warning")
        
        self.wait_for_exit("Pressione qualquer tecla para voltar ao dashboard...")
