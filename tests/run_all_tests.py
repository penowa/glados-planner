# tests/run_all_tests.py
#!/usr/bin/env python3
"""
Script principal para executar todos os testes do sistema
"""

import sys
import os
from pathlib import Path

# Configura caminhos corretos
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from cli.theme import theme
from cli.icons import Icon

def main():
    """Função principal para execução de testes"""
    theme.clear()
    theme.rule(" SISTEMA DE TESTES GLaDOS CLI ", style="accent")
    
    # Menu de testes
    from cli.interactive.menu import Menu
    
    menu = Menu("Selecione o conjunto de testes")
    
    # Adiciona opções
    menu.add_item("1. Testes de Sistema (Menu Básico)", 
                  icon=Icon.INFO,
                  action=lambda: run_menu_tests())
    
    menu.add_item("2. Teste de Integração (Backend)", 
                  icon=Icon.GLADOS,
                  action=lambda: run_backend_tests())
    
    menu.add_item("3. Teste Completo (Todos)", 
                  icon=Icon.COMPLETE,
                  action=lambda: run_all_tests())
    
    menu.add_item("4. Verificar Instalação", 
                  icon=Icon.WARNING,
                  action=lambda: check_installation())
    
    menu.add_item("5. Sair", 
                  icon=Icon.EXIT,
                  action=lambda: None)
    
    # Executa menu
    result = menu.run()
    
    theme.print("\n" + "="*60, style="primary")
    theme.print("Testes concluídos. Obrigado por testar o GLaDOS CLI!", style="success")
    theme.print("="*60 + "\n", style="primary")

def run_menu_tests():
    """Executa testes do sistema de menu"""
    import tests.test_menu_complete as menu_tests
    menu_tests.test_complete_demo()

def run_backend_tests():
    """Executa testes de integração com backend"""
    import tests.test_menu_backend_integration as backend_tests
    backend_tests.test_menu_with_backend()

def run_all_tests():
    """Executa todos os testes em sequência"""
    theme.clear()
    theme.rule(" EXECUTANDO TODOS OS TESTES ", style="accent")
    
    tests_to_run = [
        ("Testes de Sistema", run_menu_tests),
        ("Testes de Integração", run_backend_tests),
    ]
    
    for test_name, test_func in tests_to_run:
        theme.print(f"\n▶ Executando: {test_name}", style="accent")
        try:
            test_func()
            theme.print(f"✅ {test_name} - CONCLUÍDO", style="success")
        except Exception as e:
            theme.print(f"❌ {test_name} - FALHOU: {e}", style="error")
        
        # Pausa entre testes (exceto no último)
        if test_name != tests_to_run[-1][0]:
            theme.print("\nPressione qualquer tecla para continuar...", style="info")
            
            from cli.interactive.input.keyboard_handler import KeyboardHandler
            handler = KeyboardHandler()
            handler.wait_for_input()

def check_installation():
    """Verifica se todas as dependências estão instaladas"""
    theme.clear()
    theme.rule(" VERIFICAÇÃO DE INSTALAÇÃO ", style="accent")
    
    dependencies = [
        ("rich", "Sistema de temas e formatação"),
        ("readchar", "Captura de teclado"),
        ("cli.theme", "Sistema de temas GLaDOS"),
        ("cli.icons", "Sistema de ícones"),
        ("cli.interactive.menu", "Sistema de menus"),
        ("cli.integration.backend_integration", "Integração com backend"),
    ]
    
    all_ok = True
    
    for module_name, description in dependencies:
        try:
            if module_name.startswith("cli."):
                # Para módulos internos
                module_path = module_name.replace(".", "/") + ".py"
                if os.path.exists(f"src/{module_path}"):
                    theme.print(f"✅ {module_name}: {description}", style="success")
                else:
                    theme.print(f"❌ {module_name}: Arquivo não encontrado", style="error")
                    all_ok = False
            else:
                # Para pacotes externos
                __import__(module_name)
                theme.print(f"✅ {module_name}: {description}", style="success")
        except ImportError:
            theme.print(f"❌ {module_name}: Não instalado", style="error")
            all_ok = False
        except Exception as e:
            theme.print(f"⚠️  {module_name}: Erro: {e}", style="warning")
            all_ok = False
    
    theme.print("\n" + "="*50, style="primary")
    
    if all_ok:
        theme.print("✅ Todas as dependências estão OK!", style="success")
    else:
        theme.print("⚠️  Algumas dependências estão faltando", style="warning")
        theme.print("\nExecute: pip install rich readchar", style="info")
    
    input("\nPressione Enter para continuar...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        theme.print("\n\n❌ Interrompido pelo usuário", style="warning")
    except Exception as e:
        theme.print(f"\n❌ Erro inesperado: {e}", style="error")
        import traceback
        traceback.print_exc()
