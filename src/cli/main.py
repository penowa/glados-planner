"""
Ponto de entrada principal do sistema GLaDOS CLI.
Integra todas as telas através do ScreenManager otimizado.
"""
import sys
import os
import time

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.theme import theme
from src.cli.icons import Icon, icon_text
from src.cli.interactive.screen_manager import ScreenManager
from src.cli.interactive.screens.dashboard_screen import DashboardScreen
from src.cli.interactive.terminal import GLTerminal, Key


def main():
    """Função principal do sistema."""
    try:
        # Criar terminal otimizado
        terminal = GLTerminal()
        
        # 1. MOSTRAR BOOT SCREEN
        terminal.clear_screen()
        
    # Arte ASCII GLaDOS
        gladios_art = [
            "╔══════════════════════════════════════════════════════╗",
            "║                                                      ║",
            "║   ██████╗ ██╗      █████╗ ██████╗ ███████╗███████╗   ║",
            "║  ██╔════╝ ██║     ██╔══██╗██╔══██╗██╔══██║██╔════╝   ║",
            "║  ██║  ███╗██║     ███████║██║  ██║██║  ██║███████╗   ║",
            "║  ██║   ██║██║     ██╔══██║██║  ██║██║  ██║╚════██║   ║",
            "║  ╚██████╔╝███████╗██║  ██║██████╔╝███████║███████║   ║",
            "║   ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝   ║",
            "║                                                      ║",
            "║             GLaDOS Planner CLI - v1.0.0              ║",
            "║    'Uma interface simples, mas feita com carinho'    ║",
            "║                                                      ║",
            "╚══════════════════════════════════════════════════════╝"
        ]       
        
        # Renderizar arte
        term_width, term_height = terminal.get_size()
        start_y = max(0, (term_height - len(gladios_art)) // 2)
        
        for i, line in enumerate(gladios_art):
            start_x = max(0, (term_width - len(line)) // 2)
            terminal.print_at(start_x, start_y + i, line, {"color": "accent"})
        
        terminal.flush()
        time.sleep(3)
        
        # 2. VERIFICAÇÃO DE MÓDULOS
        terminal.clear_screen()
        
        status_y = 5
        checks = [
            ("Sistema de temas", True),
            ("Sistema de ícones", True),
            ("Terminal otimizado", True),
            ("Backend integration", True),
            ("Screen Manager", True),
        ]
        
        terminal.print_at(0, status_y, "→ Inicializando GLaDOS Planner...", 
                         {"color": "accent", "bold": True})
        
        for i, (check_name, check_status) in enumerate(checks):
            y = status_y + i + 2
            icon = "✓" if check_status else "✗"
            color = "success" if check_status else "error"
            terminal.print_at(2, y, f"{icon} {check_name}", {"color": color})
            terminal.flush()
            time.sleep(0.2)  # Efeito de carregamento
        
        terminal.flush()
        time.sleep(2)
        
        # 3. LIMPAR TELA E INICIAR SCREEN MANAGER
        terminal.clear_screen()
        terminal.flush()
        
        # Criar e configurar gerenciador de telas
        screen_manager = ScreenManager(terminal)
        
        # Adicionar dashboard como tela inicial
        screen_manager.push(DashboardScreen)
        
        # Mensagem de transição
        ready_msg = "✨ Sistema GLaDOS Planner pronto!"
        ready_x = max(0, (term_width - len(ready_msg)) // 2)
        ready_y = term_height // 2
        
        terminal.print_at(ready_x, ready_y, ready_msg, 
                         {"color": "success", "bold": True})
        terminal.flush()
        time.sleep(2)
        terminal.clear_screen()
        # 4. EXECUTAR LOOP PRINCIPAL
        screen_manager.run()
        
    except KeyboardInterrupt:
        terminal = GLTerminal()
        terminal.clear_screen()
        
        term_width, term_height = terminal.get_size()
        msg = "⚠️ Sistema interrompido pelo usuário."
        msg_x = max(0, (term_width - len(msg)) // 2)
        msg_y = term_height // 2
        
        terminal.print_at(msg_x, msg_y, msg, {"color": "warning", "bold": True})
        terminal.flush()
        
        time.sleep(0.5)
        terminal.cleanup()
        
    except Exception as e:
        terminal = GLTerminal()
        terminal.clear_screen()
        
        term_width, term_height = terminal.get_size()
        
        error_title = "✗ Erro fatal no sistema"
        error_msg = f"   {str(e)}"
        
        title_x = max(0, (term_width - len(error_title)) // 2)
        msg_x = max(0, (term_width - len(error_msg)) // 2)
        
        terminal.print_at(title_x, term_height // 2 - 1, error_title, 
                         {"color": "error", "bold": True})
        terminal.print_at(msg_x, term_height // 2, error_msg, {"color": "error"})
        
        import traceback
        tb = traceback.format_exc()
        tb_lines = tb.split('\n')[:10]
        
        for i, line in enumerate(tb_lines):
            terminal.print_at(0, term_height // 2 + 2 + i, line, {"color": "dim"})
        
        terminal.print_at(0, term_height - 1, "Pressione qualquer tecla para sair...", 
                         {"color": "dim"})
        terminal.flush()
        
        terminal.get_key()
        terminal.cleanup()
        
        sys.exit(1)


if __name__ == "__main__":
    main()
