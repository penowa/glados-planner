# src/cli/main.py (atualizado)
"""
Ponto de entrada principal do sistema GLaDOS CLI.
Integra todas as telas através do ScreenManager.
"""
import sys
import os

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli.theme import theme
from cli.icons import Icon, icon_text
from cli.interactive.screen_manager import ScreenManager
from cli.interactive.screens.dashboard_screen import DashboardScreen

def main():
    """Função principal do sistema."""
    try:
        # Mostrar tela de inicialização
        theme.clear()
        theme.rule("[GLaDOS Planner CLI]", style="accent")
        
        theme.print(f"\n{icon_text(Icon.GLADOS, 'Inicializando sistema...')}", style="info")
        theme.print("=" * 60, style="dim")
        
        # Verificar dependências
        theme.print("✓ Sistema de temas", style="success")
        theme.print("✓ Sistema de ícones", style="success")
        theme.print("✓ Gerenciador de telas", style="success")
        theme.print("✓ Backend integration", style="success")
        
        # Criar e configurar gerenciador de telas
        theme.print(f"\n{icon_text(Icon.LOADING, 'Carregando interface...')}", style="info")
        
        screen_manager = ScreenManager()
        
        # Adicionar dashboard como tela inicial
        dashboard = DashboardScreen()
        screen_manager.push(dashboard)
        
        # Iniciar sistema
        theme.print(f"\n{icon_text(Icon.SUCCESS, 'Sistema pronto!')}", style="success")
        theme.print("Pressione qualquer tecla para continuar...", style="dim")
        
        import readchar
        readchar.readkey()
        
        # Executar loop principal
        screen_manager.run()
        
    except KeyboardInterrupt:
        theme.print(f"\n\n{icon_text(Icon.EXIT, 'Sistema interrompido.')}", style="warning")
        
    except Exception as e:
        theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Erro fatal:')}", style="error")
        theme.print(f"   {str(e)}", style="error")
        
        import traceback
        theme.print(traceback.format_exc(), style="error")
        
        theme.print("\nPressione qualquer tecla para sair...", style="dim")
        import readchar
        readchar.readkey()
        
        sys.exit(1)

if __name__ == "__main__":
    main()
