# tests/test_menu_system.py
#!/usr/bin/env python3
"""
Teste completo do sistema de menus GLaDOS
Demonstra navegação, hierarquia e ações personalizadas
"""

import time
import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli.interactive.menu import Menu, MenuItem, MultiLevelMenu, MenuStyle
from cli.interactive.input.input_manager import InputManager, TextInput
from cli.theme import theme
from cli.icons import Icon, icon_text

def test_simple_menu():
    """Teste básico de menu vertical"""
    theme.clear()
    theme.rule(" Teste 1: Menu Simples ", style="accent")
    
    # Cria menu
    menu = Menu(
        title="Sistema de Testes GLaDOS",
        show_help=True
    )
    
    # Adiciona itens
    menu.add_item("Verificar Sistema", icon=Icon.INFO, 
                  action=lambda: print("Sistema verificado!"))
    menu.add_item("Executar Diagnóstico", icon=Icon.WARNING,
                  action=lambda: print("Diagnóstico em execução..."))
    menu.add_item("Calibrar Sensores", icon=Icon.COMPLETE,
                  action=lambda: print("Sensores calibrados."))
    menu.add_item("Testar Portal", icon=Icon.PORTAL,
                  action=lambda: print("Portal ativado! (Não se preocupe com os paradoxos)"))
    menu.add_item("Bolo", icon=Icon.CAKE,
                  action=lambda: print("O bolo é uma mentira."))
    menu.add_item("Item Desabilitado", icon=Icon.ERROR,
                  enabled=False)
    
    # Executa menu
    return menu.run()

def test_menu_with_input():
    """Teste com campo de entrada de texto"""
    theme.clear()
    theme.rule(" Teste 2: Menu com Input ", style="accent")
    
    def get_name(name):
        theme.print(f"\nOlá, {name}! Bem-vindo ao teste.", style="success")
        time.sleep(1)
        return name
    
    menu = Menu("Teste de Input")
    
    # Campo de texto
    text_input = TextInput(prompt="Seu nome: ", default="Teste")
    
    menu.add_item("Inserir Nome", icon=Icon.EDIT,
                  action=lambda: run_text_input(text_input, get_name))
    menu.add_item("Ver Resultado", icon=Icon.INFO,
                  action=lambda: print(f"Nome atual: {text_input.value}"))
    menu.add_item("Limpar", icon=Icon.DELETE,
                  action=lambda: setattr(text_input, 'value', ''))
    
    menu.run()

def run_text_input(input_widget, callback):
    """Executa entrada de texto"""
    theme.print("\nDigite seu nome (Enter para confirmar, ESC para cancelar):", style="info")
    
    input_widget.active = True
    input_widget.value = ""
    
    from cli.interactive.input.keyboard_handler import KeyboardHandler, Key
    handler = KeyboardHandler()
    
    while input_widget.active:
        # Renderiza campo
        theme.clear()
        theme.rule(" Entrada de Texto ", style="primary")
        theme.print(input_widget.render())
        
        # Processa input
        key = handler.wait_for_input()
        
        if key == Key.ESC:
            break
        elif key == Key.ENTER:
            if input_widget.value.strip():
                callback(input_widget.value.strip())
            break
        else:
            # Converte Key para string se necessário
            if isinstance(key, Key):
                key_str = key.value
            else:
                key_str = str(key)
            
            # Mapeia teclas especiais
            key_map = {
                Key.UP.value: 'up',
                Key.DOWN.value: 'down',
                Key.LEFT.value: 'left',
                Key.RIGHT.value: 'right',
                Key.SPACE.value: ' '
            }
            
            if key_str in key_map:
                input_widget.handle_key(key_map[key_str])
            elif len(key_str) == 1:
                input_widget.handle_key(key_str)

def test_hierarchical_menu():
    """Teste de menu hierárquico (multi-nível)"""
    theme.clear()
    theme.rule(" Teste 3: Menu Hierárquico ", style="accent")
    
    system = MultiLevelMenu("Sistema de Controle GLaDOS")
    
    # Menu principal
    main_menu = system.create_submenu("Menu Principal")
    main_menu.add_item("Testes de Sistema", icon=Icon.INFO,
                       action=lambda: open_test_submenu(system))
    main_menu.add_item("Configurações", icon=Icon.EDIT,
                       action=lambda: open_settings_menu(system))
    main_menu.add_item("Relatórios", icon=Icon.BOOK,
                       action=lambda: open_reports_menu(system))
    main_menu.add_item("Sair", icon=Icon.EXIT,
                       action=lambda: theme.print("Saindo...", style="warning"))
    
    # Executa sistema
    return system.run()

def open_test_submenu(system):
    """Abre submenu de testes"""
    test_menu = system.create_submenu("Testes de Sistema")
    
    test_menu.add_item("Teste de Unidade", icon=Icon.COMPLETE,
                       action=lambda: print("Teste de unidade executado."))
    test_menu.add_item("Teste de Integração", icon=Icon.WARNING,
                       action=lambda: print("Teste de integração em andamento..."))
    test_menu.add_item("Teste de Stress", icon=Icon.ERROR,
                       action=lambda: print("Aplicando stress ao sistema..."))
    test_menu.add_item("← Voltar", icon=Icon.BACK,
                       action=lambda: None)  # None faz voltar
    
    return test_menu.run()

def open_settings_menu(system):
    """Abre menu de configurações"""
    settings_menu = system.create_submenu("Configurações")
    
    settings = {
        "notificações": True,
        "som": False,
        "tema escuro": True,
        "auto-save": True
    }
    
    for key, value in settings.items():
        toggle_text = "ON" if value else "OFF"
        settings_menu.add_item(
            f"{key.title()}: [{toggle_text}]", 
            icon=Icon.EDIT,
            action=lambda k=key, v=value: toggle_setting(k, not v, settings_menu)
        )
    
    settings_menu.add_item("← Voltar", icon=Icon.BACK,
                           action=lambda: None)
    
    return settings_menu.run()

def toggle_setting(key, new_value, menu):
    """Alterna configuração e atualiza menu"""
    # Em implementação real, salvaria no arquivo de configuração
    theme.print(f"{Icon.SUCCESS} Configuração '{key}' alterada para {'ON' if new_value else 'OFF'}", 
                style="success")
    
    # Atualiza texto do item
    for i, item in enumerate(menu.items):
        if key in item.label.lower():
            toggle_text = "ON" if new_value else "OFF"
            menu.items[i].label = f"{key.title()}: [{toggle_text}]"
            break

def open_reports_menu(system):
    """Abre menu de relatórios"""
    reports_menu = system.create_submenu("Relatórios")
    
    reports_menu.add_item("Relatório Diário", icon=Icon.CALENDAR,
                          action=lambda: generate_report("diário"))
    reports_menu.add_item("Relatório Semanal", icon=Icon.BOOK,
                          action=lambda: generate_report("semanal"))
    reports_menu.add_item("Relatório de Performance", icon=Icon.INFO,
                          action=lambda: generate_report("performance"))
    reports_menu.add_item("Exportar Dados", icon=Icon.EDIT,
                          action=lambda: print("Exportando dados..."))
    reports_menu.add_item("← Voltar", icon=Icon.BACK,
                          action=lambda: None)
    
    return reports_menu.run()

def generate_report(type_report):
    """Gera relatório"""
    theme.print(f"\n{Icon.INFO} Gerando relatório {type_report}...", style="info")
    time.sleep(1)
    theme.print(f"{Icon.SUCCESS} Relatório {type_report} gerado com sucesso!", style="success")
    time.sleep(1)

def test_grid_menu():
    """Teste de menu em grade (grid)"""
    theme.clear()
    theme.rule(" Teste 4: Menu Grid ", style="accent")
    
    # Cria grade 3x3
    menu = Menu("Grade de Opções", style=MenuStyle.GRID)
    
    icons = [Icon.BOOK, Icon.CALENDAR, Icon.TASK, 
             Icon.NOTE, Icon.FLASHCARD, Icon.TIMER,
             Icon.ALERT, Icon.HOME, Icon.COMPANION_CUBE]
    
    for i in range(9):
        menu.add_item(f"Opção {i+1}", icon=icons[i],
                      action=lambda idx=i: print(f"Selecionado: Opção {idx+1}"))
    
    return menu.run()

def test_input_manager():
    """Teste do InputManager avançado"""
    theme.clear()
    theme.rule(" Teste 5: Input Manager ", style="accent")
    
    input_manager = InputManager()
    
    def on_input(event):
        theme.print(f"[{event.timestamp:.3f}] Modo: {input_manager.mode.value} | Tecla: {event.key} | Raw: {repr(event.raw)}", 
                    style="info")
    
    input_manager.add_listener(on_input)
    
    theme.print("InputManager iniciado. Pressione teclas para testar:", style="info")
    theme.print("Modos: i (insert), Esc (normal), : (command), / (search)", style="info")
    theme.print("Navegação: h (←), j (↓), k (↑), l (→)", style="info")
    theme.print("Ctrl+C para sair", style="warning")
    
    input_manager.start()
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        input_manager.stop()

def demo_completa():
    """Demonstração completa de todos os sistemas"""
    theme.clear()
    theme.rule(" DEMONSTRAÇÃO COMPLETA - Sistema GLaDOS ", style="accent")
    theme.print("Selecione uma demonstração:", style="primary")
    
    menu = Menu("Demonstrações")
    
    menu.add_item("1. Menu Simples", icon=Icon.ARROW_RIGHT,
                  action=test_simple_menu)
    menu.add_item("2. Menu com Input", icon=Icon.EDIT,
                  action=test_menu_with_input)
    menu.add_item("3. Menu Hierárquico", icon=Icon.ARROW_DOWN,
                  action=test_hierarchical_menu)
    menu.add_item("4. Menu Grid", icon=Icon.TASK,
                  action=test_grid_menu)
    menu.add_item("5. Input Manager", icon=Icon.INFO,
                  action=test_input_manager)
    menu.add_item("6. Todas as Demonstrações", icon=Icon.GLADOS,
                  action=run_all_demos)
    menu.add_item("Sair", icon=Icon.EXIT,
                  action=lambda: theme.print("Encerrando demonstração...", style="warning"))
    
    return menu.run()

def run_all_demos():
    """Executa todas as demonstrações em sequência"""
    demos = [
        ("Menu Simples", test_simple_menu),
        ("Menu com Input", test_menu_with_input),
        ("Menu Hierárquico", test_hierarchical_menu),
        ("Menu Grid", test_grid_menu),
        ("Input Manager", test_input_manager),
    ]
    
    for name, demo in demos:
        theme.clear()
        theme.rule(f" Demonstração: {name} ", style="accent")
        demo()
        theme.print("\nPressione qualquer tecla para continuar...", style="info")
        
        from cli.interactive.input.keyboard_handler import KeyboardHandler
        handler = KeyboardHandler()
        handler.wait_for_input()
    
    theme.print("\n🎉 Todas demonstrações concluídas!", style="success")

if __name__ == "__main__":
    # Executa demonstração completa
    demo_completa()
    
    theme.print("\n" + "="*50, style="primary")
    theme.print("Testes do sistema de menu concluídos!", style="success")
    theme.print("="*50, style="primary")
