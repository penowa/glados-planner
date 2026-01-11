# run_glados.py (na raiz do projeto)
"""
Arquivo de inicialização que configura os caminhos de importação.
Execute este arquivo para iniciar o sistema.
"""
import sys
import os

# Adiciona o diretório src ao sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Agora podemos importar o sistema
from cli.interactive.screen_manager import ScreenManager
from cli.interactive.screens.dashboard_screen import DashboardScreen

def main():
    """Função principal do sistema."""
    try:
        print("🚀 Inicializando GLaDOS Planner CLI...")
        
        # Criar gerenciador de telas
        screen_manager = ScreenManager()
        
        # Adicionar dashboard como tela inicial
        dashboard = DashboardScreen()
        screen_manager.push(dashboard)
        
        # Executar sistema
        screen_manager.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 Sistema encerrado pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
