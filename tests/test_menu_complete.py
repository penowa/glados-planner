# tests/test_menu_complete.py
#!/usr/bin/env python3
"""
Teste completo do sistema de menus GLaDOS com caminhos corrigidos
"""

import time
import sys
import os
from pathlib import Path

# Configura caminhos corretos
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
sys.path.insert(0, str(src_dir))

# Agora importa com os caminhos corretos
from cli.interactive.menu import Menu, MenuItem, MultiLevelMenu, MenuStyle
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
                  action=lambda: theme.print("Sistema verificado!", style="success"))
    menu.add_item("Executar Diagnóstico", icon=Icon.WARNING,
                  action=lambda: theme.print("Diagnóstico em execução...", style="warning"))
    menu.add_item("Calibrar Sensores", icon=Icon.COMPLETE,
                  action=lambda: theme.print("Sensores calibrados.", style="success"))
    menu.add_item("Testar Portal", icon=Icon.PORTAL,
                  action=lambda: theme.print("Portal ativado! (Não se preocupe com os paradoxos)", style="accent"))
    menu.add_item("Bolo", icon=Icon.CAKE,
                  action=lambda: theme.print("O bolo é uma mentira.", style="warning"))
    menu.add_item("Item Desabilitado", icon=Icon.ERROR,
                  enabled=False)
    
    # Executa menu
    return menu.run()

def test_hierarchical_menu():
    """Teste de menu hierárquico (multi-nível)"""
    theme.clear()
    theme.rule(" Teste 2: Menu Hierárquico ", style="accent")
    
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
                       action=lambda: theme.print("Teste de unidade executado.", style="success"))
    test_menu.add_item("Teste de Integração", icon=Icon.WARNING,
                       action=lambda: theme.print("Teste de integração em andamento...", style="warning"))
    test_menu.add_item("Teste de Stress", icon=Icon.ERROR,
                       action=lambda: theme.print("Aplicando stress ao sistema...", style="error"))
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
                          action=lambda: theme.print("Exportando dados...", style="info"))
    reports_menu.add_item("← Voltar", icon=Icon.BACK,
                          action=lambda: None)
    
    return reports_menu.run()

def generate_report(type_report):
    """Gera relatório"""
    theme.print(f"\n{Icon.INFO} Gerando relatório {type_report}...", style="info")
    time.sleep(1)
    theme.print(f"{Icon.SUCCESS} Relatório {type_report} gerado com sucesso!", style="success")
    time.sleep(1)

def test_dashboard_simulation():
    """Simulação de dashboard GLaDOS"""
    theme.clear()
    theme.rule(" Teste 3: Dashboard Simulado ", style="accent")
    
    # Dados simulados
    dashboard_data = {
        'metas_dia': [
            {'descricao': 'Leitura: 25/50 páginas', 'concluida': False, 'icone': Icon.BOOK},
            {'descricao': 'Escrita: 500/1000 palavras', 'concluida': False, 'icone': Icon.EDIT},
            {'descricao': 'Revisão: 10/15 flashcards', 'concluida': True, 'icone': Icon.FLASHCARD},
            {'descricao': 'Exercícios: 30 minutos', 'concluida': False, 'icone': Icon.TIMER},
        ],
        'compromissos': [
            {'hora': '09:00-11:00', 'titulo': 'A República - Platão', 'local': 'Biblioteca'},
            {'hora': '14:00-16:00', 'titulo': 'Aula: Ética', 'local': 'Sala 12'},
            {'hora': '19:00-20:00', 'titulo': 'Paper: Virtude', 'local': 'Home Office'},
        ],
        'alertas': [
            'Prova de Lógica em 3 dias. Prepare-se para o fracasso inevitável.',
            'Entrega do paper em 7 dias. Não me culpe quando você falhar.',
            'Você está 15% atrasado no cronograma. Surpresa, surpresa.',
        ]
    }
    
    # Exibe dashboard
    theme.print(f"{Icon.INFO} Dashboard GLaDOS - {time.strftime('%d/%m/%Y')}\n", style="primary")
    
    # Metas do dia
    theme.print(f"{Icon.TASK} METAS DO DIA", style="accent")
    for meta in dashboard_data['metas_dia']:
        status = "✅" if meta['concluida'] else "□"
        theme.print(f"  {status} {meta['icone']} {meta['descricao']}", style="info")
    
    theme.print()  # Linha vazia
    
    # Compromissos
    theme.print(f"{Icon.CALENDAR} PRÓXIMOS COMPROMISSOS", style="accent")
    for comp in dashboard_data['compromissos']:
        theme.print(f"  {comp['hora']}  {comp['titulo']}", style="primary")
        theme.print(f"     📍 {comp['local']}", style="dim")
    
    theme.print()  # Linha vazia
    
    # Alertas
    theme.print(f"{Icon.ALERT} ALERTAS GLaDOS", style="error")
    for alerta in dashboard_data['alertas']:
        theme.print(f"  • {alerta}", style="warning")
    
    theme.print()  # Linha vazia
    
    # Menu de ações
    menu = Menu("Ações Disponíveis", show_help=False)
    menu.add_item("Iniciar Sessão de Trabalho", icon=Icon.TIMER,
                  action=lambda: theme.print("Iniciando sessão Pomodoro...", style="success"))
    menu.add_item("Atualizar Progresso", icon=Icon.EDIT,
                  action=lambda: theme.print("Atualizando progresso...", style="info"))
    menu.add_item("Reagendar Tarefas", icon=Icon.CALENDAR,
                  action=lambda: theme.print("Reagendando tarefas...", style="warning"))
    menu.add_item("Consultar GLaDOS", icon=Icon.GLADOS,
                  action=lambda: theme.print("GLaDOS: 'Isso é realmente necessário?'", style="warning"))
    menu.add_item("Sair do Dashboard", icon=Icon.EXIT,
                  action=lambda: None)
    
    return menu.run()

def test_complete_demo():
    """Demonstração completa de todos os sistemas"""
    theme.clear()
    theme.rule(" DEMONSTRAÇÃO COMPLETA - Sistema GLaDOS ", style="accent")
    theme.print("Selecione uma demonstração:", style="primary")
    
    menu = Menu("Demonstrações")
    
    menu.add_item("1. Menu Simples", icon=Icon.ARROW_RIGHT,
                  action=test_simple_menu)
    menu.add_item("2. Menu Hierárquico", icon=Icon.ARROW_DOWN,
                  action=test_hierarchical_menu)
    menu.add_item("3. Dashboard Simulado", icon=Icon.TASK,
                  action=test_dashboard_simulation)
    menu.add_item("4. Todas as Demonstrações", icon=Icon.GLADOS,
                  action=run_all_demos)
    menu.add_item("Sair", icon=Icon.EXIT,
                  action=lambda: theme.print("Encerrando demonstração...", style="warning"))
    
    return menu.run()

def run_all_demos():
    """Executa todas as demonstrações em sequência"""
    demos = [
        ("Menu Simples", test_simple_menu),
        ("Menu Hierárquico", test_hierarchical_menu),
        ("Dashboard Simulado", test_dashboard_simulation),
    ]
    
    for name, demo in demos:
        theme.clear()
        theme.rule(f" Demonstração: {name} ", style="accent")
        demo()
        
        if name != demos[-1][0]:  # Não pergunta após a última
            theme.print("\nPressione qualquer tecla para continuar...", style="info")
            
            from cli.interactive.input.keyboard_handler import KeyboardHandler
            handler = KeyboardHandler()
            handler.wait_for_input()
    
    theme.print("\n🎉 Todas demonstrações concluídas!", style="success")

if __name__ == "__main__":
    # Executa demonstração completa
    test_complete_demo()
    
    theme.print("\n" + "="*50, style="primary")
    theme.print("Testes do sistema de menu concluídos!", style="success")
    theme.print("="*50, style="primary")
