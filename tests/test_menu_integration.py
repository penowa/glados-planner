# tests/test_menu_integration.py
#!/usr/bin/env python3
"""
Teste de integração do menu com backend
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli.interactive.menu import Menu, MenuItem
from cli.interactive.integration.backend_integration import init_backend
from cli.theme import theme
from cli.icons import Icon

def test_menu_with_real_backend():
    """Teste usando dados reais do backend"""
    theme.clear()
    theme.rule(" Teste de Integração Backend ", style="accent")
    
    # Inicializa backend
    theme.print("Inicializando backend...", style="info")
    backend = init_backend()
    
    if not backend.is_ready():
        theme.print("Backend não disponível. Usando modo mock.", style="warning")
    
    # Cria menu com dados reais
    menu = Menu("Dashboard GLaDOS - Dados em Tempo Real")
    
    # Adiciona itens dinâmicos baseados no backend
    menu.add_item("Ver Agenda Hoje", icon=Icon.CALENDAR,
                  action=lambda: show_today_agenda(backend))
    
    menu.add_item("Meus Livros Ativos", icon=Icon.BOOK,
                  action=lambda: show_active_books(backend))
    
    menu.add_item("Estatísticas do Dia", icon=Icon.INFO,
                  action=lambda: show_daily_stats(backend))
    
    menu.add_item("Fazer Check-in", icon=Icon.COMPLETE,
                  action=lambda: do_daily_checkin(backend))
    
    menu.add_item("Consultar GLaDOS", icon=Icon.GLADOS,
                  action=lambda: ask_glados_question(backend))
    
    menu.add_item("Sair", icon=Icon.EXIT,
                  action=lambda: None)
    
    # Executa menu
    return menu.run()

def show_today_agenda(backend):
    """Mostra agenda do dia"""
    theme.clear()
    theme.rule(" Agenda de Hoje ", style="primary")
    
    try:
        agenda = backend.get_today_agenda()
        if agenda:
            for event in agenda:
                status = "✅" if event.get('completed') else "□"
                theme.print(f"{status} {event.get('time', '')} - {event.get('title', '')}", 
                          style="info")
        else:
            theme.print("Nenhum evento agendado para hoje.", style="dim")
    except Exception as e:
        theme.print(f"Erro ao buscar agenda: {e}", style="error")
    
    input("\nPressione Enter para continuar...")

def show_active_books(backend):
    """Mostra livros ativos"""
    theme.clear()
    theme.rule(" Livros Ativos ", style="primary")
    
    try:
        books = backend.get_active_books()
        if books:
            for book in books:
                progress = book.get('progress', 0)
                theme.print(f"📚 {book.get('title', '')}", style="primary")
                theme.print(f"   📖 {book.get('current_page', 0)}/{book.get('total_pages', 0)} páginas", style="info")
                theme.print(f"   📊 {progress}% concluído", style="success")
                theme.print()  # Linha vazia
        else:
            theme.print("Nenhum livro ativo no momento.", style="dim")
    except Exception as e:
        theme.print(f"Erro ao buscar livros: {e}", style="error")
    
    input("\nPressione Enter para continuar...")

def show_daily_stats(backend):
    """Mostra estatísticas do dia"""
    theme.clear()
    theme.rule(" Estatísticas do Dia ", style="primary")
    
    try:
        dashboard = backend.get_dashboard_data()
        stats = dashboard.get('daily_stats', {})
        
        if stats:
            theme.print(f"📚 Leitura: {stats.get('pages_read', 0)} páginas", style="info")
            theme.print(f"✍️  Escrita: {stats.get('words_written', 0)} palavras", style="info")
            theme.print(f"🔁 Revisões: {stats.get('reviews_done', 0)} concluídas", style="info")
            theme.print(f"🎯 Tarefas: {stats.get('tasks_completed', 0)}/{stats.get('total_tasks', 0)}", style="info")
            theme.print(f"⏱️  Pomodoros: {stats.get('pomodoros_completed', 0)} sessões", style="info")
        else:
            theme.print("Nenhuma estatística disponível.", style="dim")
    except Exception as e:
        theme.print(f"Erro ao buscar estatísticas: {e}", style="error")
    
    input("\nPressione Enter para continuar...")

def do_daily_checkin(backend):
    """Realiza check-in diário"""
    theme.clear()
    theme.rule(" Check-in Diário ", style="primary")
    
    # Simula formulário de check-in
    checkin_menu = Menu("Como você está se sentindo?")
    
    checkin_options = [
        ("😊 Produtivo", "Ótimo. Aproveite enquanto dura."),
        ("😐 Normal", "Como esperado de um desempenho mediano."),
        ("😟 Distraído", "Concentração é um conceito difícil, não é?"),
        ("😡 Frustrado", "Mais uma falha para adicionar à coleção."),
        ("🎯 Focado", "Finalmente fazendo algo útil.")
    ]
    
    for emoji, response in checkin_options:
        checkin_menu.add_item(emoji, 
                             action=lambda r=response: process_checkin(backend, r))
    
    checkin_menu.run()

def process_checkin(backend, response):
    """Processa resposta do check-in"""
    try:
        result = backend.perform_daily_checkin(checkin_type="mood", notes=response)
        theme.print(f"\n{Icon.SUCCESS} Check-in registrado.", style="success")
        theme.print(f"GLaDOS: {response}", style="info")
    except Exception as e:
        theme.print(f"Erro ao registrar check-in: {e}", style="error")
    
    time.sleep(2)

def ask_glados_question(backend):
    """Consulta GLaDOS"""
    theme.clear()
    theme.rule(" Consultar GLaDOS ", style="primary")
    
    theme.print("Digite sua pergunta (ou Enter para cancelar):", style="info")
    question = input("> ").strip()
    
    if question:
        theme.print("\n🔍 Processando...", style="info")
        try:
            response = backend.ask_glados(question)
            theme.print(f"\n🤖 GLaDOS: {response}", style="warning")
        except Exception as e:
            theme.print(f"Erro na consulta: {e}", style="error")
            theme.print("(Resposta mock: 'Isso parece uma pergunta trivial. Tente algo mais desafiador.')", 
                       style="dim")
    else:
        theme.print("Consulta cancelada.", style="dim")
    
    input("\nPressione Enter para continuar...")

if __name__ == "__main__":
    import time
    test_menu_with_real_backend()
