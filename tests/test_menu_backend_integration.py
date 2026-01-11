# tests/test_menu_backend_integration.py
#!/usr/bin/env python3
"""
Teste de integração do menu com backend usando caminhos corretos
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
from cli.interactive.menu import Menu
from cli.integration.backend_integration import init_backend
from cli.theme import theme
from cli.icons import Icon

def test_menu_with_backend():
    """Teste usando dados do backend"""
    theme.clear()
    theme.rule(" Teste de Integração Backend ", style="accent")
    
    # Inicializa backend
    theme.print(f"{Icon.INFO} Inicializando backend...", style="info")
    
    try:
        # Tenta inicializar o backend
        backend = init_backend()
        
        if backend.is_ready():
            theme.print(f"{Icon.SUCCESS} Backend inicializado com sucesso!", style="success")
            theme.print(f"  Módulos disponíveis: {len(backend._modules)}", style="info")
        else:
            theme.print(f"{Icon.WARNING} Backend em modo mock/simulação", style="warning")
        
        # Aguarda um momento
        time.sleep(1)
        
        # Cria menu principal
        menu = Menu("Dashboard GLaDOS - Integração com Backend")
        
        # Adiciona itens dinâmicos
        menu.add_item("Verificar Status do Backend", icon=Icon.INFO,
                      action=lambda: show_backend_status(backend))
        
        menu.add_item("Testar Dashboard Data", icon=Icon.TASK,
                      action=lambda: test_dashboard_data(backend))
        
        menu.add_item("Consultar GLaDOS (Mock)", icon=Icon.GLADOS,
                      action=lambda: test_glados_query(backend))
        
        menu.add_item("Simular Evento do Sistema", icon=Icon.ALERT,
                      action=lambda: simulate_system_event(backend))
        
        menu.add_item("Voltar para Testes", icon=Icon.BACK,
                      action=lambda: "back")
        
        menu.add_item("Sair", icon=Icon.EXIT,
                      action=lambda: None)
        
        # Executa menu
        result = menu.run()
        
        if result == "back":
            return "back"
            
    except Exception as e:
        theme.print(f"{Icon.ERROR} Erro ao inicializar backend: {e}", style="error")
        theme.print("Usando modo de simulação...", style="warning")
        
        # Menu de fallback
        menu = Menu("Modo Simulação - Backend Indisponível")
        menu.add_item("Testar Interface (Simulação)", icon=Icon.INFO,
                      action=lambda: theme.print("Interface funcionando em modo simulação.", style="info"))
        menu.add_item("Voltar", icon=Icon.BACK,
                      action=lambda: "back")
        menu.run()
        
        return "back"

def show_backend_status(backend):
    """Mostra status detalhado do backend"""
    theme.clear()
    theme.rule(" Status do Backend ", style="primary")
    
    try:
        # Informações básicas
        theme.print(f"{Icon.INFO} Status: {'✅ PRONTO' if backend.is_ready() else '⚠️  MOCK'}", 
                   style="success" if backend.is_ready() else "warning")
        
        theme.print(f"{Icon.INFO} Módulos Carregados: {len(backend._modules)}", style="info")
        
        # Lista módulos
        theme.print(f"\n{Icon.BOOK} Módulos Disponíveis:", style="accent")
        for module_name, module_instance in backend._modules.items():
            status = "✅" if not module_name.startswith("Mock") else "🔄"
            theme.print(f"  {status} {module_name}", style="info")
        
        # Cache info
        if hasattr(backend, '_cache'):
            cache_size = len(backend._cache)
            theme.print(f"\n{Icon.INFO} Cache: {cache_size} itens", style="info")
        
        # Últimos eventos
        if hasattr(backend, '_event_history'):
            events = backend._event_history[-5:] if len(backend._event_history) > 5 else backend._event_history
            if events:
                theme.print(f"\n{Icon.ALERT} Últimos Eventos:", style="accent")
                for event in events:
                    theme.print(f"  • {event}", style="dim")
        
    except Exception as e:
        theme.print(f"{Icon.ERROR} Erro ao obter status: {e}", style="error")
    
    input("\nPressione Enter para continuar...")

def test_dashboard_data(backend):
    """Testa obtenção de dados do dashboard"""
    theme.clear()
    theme.rule(" Teste: Dashboard Data ", style="primary")
    
    try:
        theme.print(f"{Icon.INFO} Buscando dados do dashboard...", style="info")
        
        # Obtém dados
        dashboard = backend.get_dashboard_data()
        
        if dashboard:
            theme.print(f"{Icon.SUCCESS} Dados obtidos com sucesso!", style="success")
            
            # Exibe informações básicas
            theme.print(f"\n{Icon.INFO} Estrutura do Dashboard:", style="accent")
            
            for key, value in dashboard.items():
                if isinstance(value, list):
                    theme.print(f"  📊 {key}: {len(value)} itens", style="info")
                elif isinstance(value, dict):
                    theme.print(f"  📊 {key}: {len(value)} campos", style="info")
                else:
                    theme.print(f"  📊 {key}: {value}", style="info")
            
            # Mostra mensagem GLaDOS se disponível
            if 'daily_message' in dashboard and dashboard['daily_message']:
                theme.print(f"\n{Icon.GLADOS} Mensagem do Dia:", style="warning")
                theme.print(f"  \"{dashboard['daily_message']}\"", style="info")
            
        else:
            theme.print(f"{Icon.WARNING} Nenhum dado retornado", style="warning")
        
    except Exception as e:
        theme.print(f"{Icon.ERROR} Erro ao buscar dados: {e}", style="error")
        theme.print("Usando dados de exemplo...", style="info")
        
        # Dados de exemplo
        example_data = {
            'daily_message': 'Bem-vindo ao teste. Por favor, não quebre nada.',
            'daily_stats': {'tarefas': 5, 'concluidas': 2},
            'active_books': ['Livro Teste 1', 'Livro Teste 2'],
            'pending_tasks': ['Tarefa 1', 'Tarefa 2', 'Tarefa 3']
        }
        
        for key, value in example_data.items():
            if isinstance(value, list):
                theme.print(f"  📊 {key}: {len(value)} itens", style="info")
            elif isinstance(value, dict):
                theme.print(f"  📊 {key}: {len(value)} campos", style="info")
            else:
                theme.print(f"  📊 {key}: {value}", style="info")
    
    input("\nPressione Enter para continuar...")

def test_glados_query(backend):
    """Testa consulta à GLaDOS"""
    theme.clear()
    theme.rule(" Consulta GLaDOS ", style="primary")
    
    # Perguntas de exemplo
    questions = [
        "Qual é o sentido da vida?",
        "Como ser mais produtivo?",
        "Recomende um livro",
        "Estou atrasado, o que fazer?",
        "Por que devo continuar?"
    ]
    
    # Menu para selecionar pergunta
    menu = Menu("Selecione uma pergunta para GLaDOS")
    
    for question in questions:
        menu.add_item(question[:40] + "..." if len(question) > 40 else question,
                      icon=Icon.GLADOS,
                      action=lambda q=question: ask_question(backend, q))
    
    menu.add_item("Digitar minha pergunta", icon=Icon.EDIT,
                  action=lambda: custom_question(backend))
    
    menu.add_item("Voltar", icon=Icon.BACK,
                  action=lambda: None)
    
    menu.run()

def ask_question(backend, question):
    """Faz pergunta à GLaDOS"""
    theme.clear()
    theme.rule(" Consultando GLaDOS ", style="primary")
    
    theme.print(f"\n{Icon.INFO} Você perguntou: \"{question}\"", style="info")
    theme.print(f"\n{Icon.GLADOS} GLaDOS está pensando...", style="warning")
    
    # Simula processamento
    time.sleep(1.5)
    
    try:
        # Tenta usar o backend real
        response = backend.ask_glados(question)
        theme.print(f"\n{Icon.GLADOS} Resposta: {response}", style="accent")
    except Exception as e:
        # Fallback para respostas mock
        mock_responses = [
            "Isso parece uma pergunta trivial. Tente algo mais desafiador.",
            "A resposta é 42. Próxima pergunta.",
            "Produtividade é um mito inventado para vender planners.",
            "Leia 'A República' de Platão. Ou não. Provavelmente não.",
            "Atraso é apenas uma perspectiva. Uma perspectiva errada.",
            "Porque desistir seria muito fácil. E nada que é fácil vale a pena."
        ]
        
        import random
        response = random.choice(mock_responses)
        theme.print(f"\n{Icon.GLADOS} Resposta (Mock): {response}", style="accent")
        theme.print(f"\n{Icon.INFO} (Backend real indisponível: {e})", style="dim")
    
    input("\nPressione Enter para continuar...")

def custom_question(backend):
    """Permite digitar pergunta personalizada"""
    theme.clear()
    theme.rule(" Pergunta Personalizada ", style="primary")
    
    theme.print("Digite sua pergunta para GLaDOS:", style="info")
    theme.print("(Pressione Enter para enviar, Ctrl+C para cancelar)", style="dim")
    
    try:
        question = input("\n> ").strip()
        if question:
            ask_question(backend, question)
    except KeyboardInterrupt:
        theme.print("\n❌ Consulta cancelada", style="warning")

def simulate_system_event(backend):
    """Simula um evento do sistema"""
    theme.clear()
    theme.rule(" Simulação de Evento ", style="primary")
    
    # Tipos de evento
    events = [
        ("EVENT_ADDED", "Novo evento na agenda"),
        ("READING_PROGRESS_UPDATED", "Progresso de leitura atualizado"),
        ("CHECKIN_PERFORMED", "Check-in realizado"),
        ("UI_REFRESH_NEEDED", "UI precisa atualizar"),
    ]
    
    menu = Menu("Selecione o tipo de evento")
    
    for event_name, event_desc in events:
        menu.add_item(f"{event_name}: {event_desc}",
                      icon=Icon.ALERT,
                      action=lambda e=event_name: trigger_event(backend, e))
    
    menu.add_item("Voltar", icon=Icon.BACK,
                  action=lambda: None)
    
    menu.run()

def trigger_event(backend, event_name):
    """Dispara evento no sistema"""
    theme.clear()
    theme.rule(f" Disparando Evento: {event_name} ", style="primary")
    
    try:
        # Verifica se o backend tem sistema de eventos
        if hasattr(backend, '_emit_event'):
            from cli.integration.backend_integration import AppEvent
            
            # Mapeia string para enum
            event_enum = None
            for event in AppEvent:
                if event.value == event_name.lower():
                    event_enum = event
                    break
            
            if event_enum:
                backend._emit_event(event_enum, {"test": True, "timestamp": time.time()})
                theme.print(f"{Icon.SUCCESS} Evento '{event_name}' disparado com sucesso!", style="success")
                theme.print(f"{Icon.INFO} Dados: {{'test': True, 'timestamp': ...}}", style="info")
            else:
                theme.print(f"{Icon.WARNING} Evento '{event_name}' não encontrado no enum", style="warning")
        else:
            theme.print(f"{Icon.WARNING} Backend não tem sistema de eventos habilitado", style="warning")
            theme.print("Simulando evento...", style="info")
            
            # Simulação
            theme.print(f"\n[EVENTO SIMULADO] {event_name}", style="accent")
            theme.print("Listeners notificados: 0", style="dim")
    
    except Exception as e:
        theme.print(f"{Icon.ERROR} Erro ao disparar evento: {e}", style="error")
    
    input("\nPressione Enter para continuar...")

if __name__ == "__main__":
    # Executa teste de integração
    test_menu_with_backend()
    
    theme.print("\n" + "="*60, style="primary")
    theme.print("Teste de integração com backend concluído!", style="success")
    theme.print("="*60, style="primary")
