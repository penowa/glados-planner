# src/cli/interactive/screens/glados_query_screen.py
"""
Tela de consulta interativa à GLaDOS.
Integra com LocalLLM.
"""
from .base_screen import BaseScreen
from src.cli.integration.backend_integration import backend
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text

class GladosQueryScreen(BaseScreen):
    """Tela de consulta à GLaDOS."""
    
    def __init__(self):
        super().__init__()
        self.title = "Consulta GLaDOS"
        self.conversation_history = []
    
    def show(self):
        theme.clear()
        theme.rule(f"[{self.title}]")
        
        theme.print(f"\n{icon_text(Icon.GLADOS, 'Olá. Sou a GLaDOS.')}", style="accent")
        theme.print("Como posso ajudá-lo hoje? (Digite 'sair' para voltar)", style="info")
        theme.print("=" * 70, style="dim")
        
        while True:
            # Mostrar histórico da conversa
            self._display_conversation()
            
            # Entrada do usuário
            theme.print(f"\n{icon_text(Icon.INFO, 'Você:')} ", style="primary", end="")
            user_input = input().strip()
            
            if user_input.lower() in ['sair', 'exit', 'quit', 'voltar']:
                break
            
            if not user_input:
                continue
            
            # Adicionar ao histórico
            self.conversation_history.append({
                'role': 'user',
                'content': user_input
            })
            
            # Processar consulta
            theme.print(f"\n{icon_text(Icon.LOADING, 'GLaDOS pensando...')}", style="info")
            
            try:
                # Usar backend para consultar GLaDOS
                response = backend.ask_glados(
                    question=user_input,
                    context=self._get_context(),
                    history=self.conversation_history[-5:]  # Últimas 5 mensagens
                )
                
                # Adicionar resposta ao histórico
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response
                })
                
            except Exception as e:
                error_msg = f"Desculpe, estou tendo problemas técnicos. Erro: {str(e)}"
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': error_msg
                })
        
        theme.print(f"\n{icon_text(Icon.GLADOS, 'Até logo. Volte quando precisar de mais assistência.')}", style="accent")
        self.wait_for_exit()
    
    def _display_conversation(self):
        """Exibe o histórico da conversa."""
        theme.clear()
        theme.rule(f"[{self.title}]")
        
        if not self.conversation_history:
            theme.print(f"\n{icon_text(Icon.GLADOS, 'Digite sua pergunta para começar.')}", style="dim")
            return
        
        for message in self.conversation_history[-10:]:  # Mostrar últimas 10 mensagens
            if message['role'] == 'user':
                theme.print(f"\n{icon_text(Icon.INFO, 'Você:')} {message['content']}", style="primary")
            else:
                theme.print(f"\n{icon_text(Icon.GLADOS, 'GLaDOS:')} ", style="accent", end="")
                
                # Formatar resposta com quebras de linha
                lines = message['content'].split('\n')
                for i, line in enumerate(lines):
                    if i == 0:
                        theme.print(line, style="info")
                    else:
                        theme.print(f"          {line}", style="info")
    
    def _get_context(self):
        """Obtém contexto atual para a consulta."""
        try:
            # Obter dados atuais do sistema
            dashboard_data = backend.get_dashboard_data()
            
            context = {
                'current_tasks': dashboard_data.get('pending_tasks', []),
                'active_books': dashboard_data.get('active_books', []),
                'upcoming_events': dashboard_data.get('upcoming_events', []),
                'daily_stats': dashboard_data.get('daily_stats', {})
            }
            
            return context
            
        except:
            return {}
