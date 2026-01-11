# src/cli/interactive/screens/new_book_screen.py
"""
Tela para adicionar novo livro ao sistema.
Integra com BookProcessor e ReadingManager.
"""
import os
from .base_screen import BaseScreen
from cli.integration.backend_integration import backend
from cli.theme import theme
from cli.icons import Icon, icon_text

class NewBookScreen(BaseScreen):
    """Tela para adicionar novo livro."""
    
    def __init__(self):
        super().__init__()
        self.title = "Adicionar Novo Livro"
    
    def show(self):
        self.should_exit = False
        
        while not self.should_exit:
            theme.clear()
            theme.rule(f"[{self.title}]")
            
            theme.print("\n📚 Adicionar um novo livro ao sistema", style="primary")
            theme.print("=" * 50, style="dim")
            
            # Formulário de entrada
            theme.print("\n1. Caminho do arquivo (PDF/EPUB/TXT):", style="info")
            file_path = input("> ").strip()
            
            if not file_path:
                theme.print("Operação cancelada.", style="warning")
                self.wait_for_exit()
                break
            
            if not os.path.exists(file_path):
                theme.print(f"❌ Arquivo não encontrado: {file_path}", style="error")
                self.wait_for_exit()
                continue
            
            # Extrair metadados básicos
            theme.print("\n2. Metadados do livro (opcional):", style="info")
            title = input("Título (deixe vazio para detectar automaticamente): ").strip()
            author = input("Autor (deixe vazio para detectar automaticamente): ").strip()
            
            # Configurações de processamento
            theme.print("\n3. Configurações de processamento:", style="info")
            theme.print("Qualidade de processamento:", style="dim")
            theme.print("  1) Rápido (apenas metadados)")
            theme.print("  2) Normal (texto completo)")
            theme.print("  3) Completo (texto + análise)")
            
            quality_choice = input("Escolha (1-3, padrão=2): ").strip()
            quality_map = {'1': 'fast', '2': 'normal', '3': 'complete'}
            quality = quality_map.get(quality_choice, 'normal')
            
            # Configurações de agenda
            theme.print("\n4. Configurações de leitura:", style="info")
            deadline = input("Prazo em dias (deixe vazio para sem prazo): ").strip()
            daily_pages = input("Páginas por dia (deixe vazio para calcular automaticamente): ").strip()
            
            # Processar livro
            theme.print(f"\n{icon_text(Icon.LOADING, 'Processando livro...')}", style="info")
            
            try:
                # Usar backend para processar
                result = backend.add_book_from_file(
                    file_path=file_path,
                    title=title if title else None,
                    author=author if author else None,
                    processing_quality=quality,
                    deadline_days=int(deadline) if deadline.isdigit() else None,
                    daily_pages=int(daily_pages) if daily_pages.isdigit() else None
                )
                
                if result.get('success', False):
                    theme.print(f"\n✅ {icon_text(Icon.SUCCESS, 'Livro adicionado com sucesso!')}", style="success")
                    
                    book_info = result.get('book', {})
                    if book_info:
                        theme.print(f"\n📖 Título: {book_info.get('title', 'N/A')}", style="info")
                        theme.print(f"👤 Autor: {book_info.get('author', 'N/A')}", style="info")
                        theme.print(f"📄 Páginas: {book_info.get('total_pages', 'N/A')}", style="info")
                        theme.print(f"📁 Local: {book_info.get('vault_path', 'N/A')}", style="info")
                    
                    # Sugerir sessão de leitura
                    theme.print(f"\n{icon_text(Icon.INFO, 'Deseja iniciar uma sessão de leitura agora?')}", style="info")
                    start_session = input("(s/N): ").strip().lower()
                    
                    if start_session == 's':
                        # Redirecionar para sessão de leitura
                        from .reading_session_screen import ReadingSessionScreen
                        session_screen = ReadingSessionScreen()
                        session_screen.set_book(book_info.get('id'))
                        session_screen.show()
                
                else:
                    theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Falha ao processar livro:')}", style="error")
                    theme.print(f"   {result.get('error', 'Erro desconhecido')}", style="error")
                    
            except Exception as e:
                theme.print(f"\n❌ {icon_text(Icon.ERROR, 'Erro durante o processamento:')}", style="error")
                theme.print(f"   {str(e)}", style="error")
            
            self.wait_for_exit("\nPressione qualquer tecla para voltar...")
            self.should_exit = True
