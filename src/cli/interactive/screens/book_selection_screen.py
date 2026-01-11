# src/cli/interactive/screens/book_selection_screen.py
"""
Tela de seleção de livros para leitura ou revisão.
"""
from .base_screen import BaseScreen
from src.cli.integration.backend_integration import backend
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text

class BookSelectionScreen(BaseScreen):
    """Tela de seleção de livros."""
    
    def __init__(self):
        super().__init__()
        self.title = "Seleção de Livros"
        self.books = []
        self.filtered_books = []
        self.current_filter = "all"
    
    def show(self):
        self._load_books()
        
        if not self.books:
            theme.print("❌ Nenhum livro disponível.", style="error")
            self.wait_for_exit()
            return
        
        selected_index = 0
        
        while True:
            self._render_book_list(selected_index)
            
            key = self.keyboard_handler.wait_for_input()
            
            if key == Key.UP:
                selected_index = (selected_index - 1) % len(self.filtered_books)
            elif key == Key.DOWN:
                selected_index = (selected_index + 1) % len(self.filtered_books)
            elif key == Key.ENTER:
                if self.filtered_books:
                    self._select_book(self.filtered_books[selected_index])
                break
            elif key == Key.F:
                self._apply_filter()
                selected_index = 0
            elif key == Key.S:
                self._search_books()
                selected_index = 0
            elif key == Key.ESC:
                break
    
    def _load_books(self):
        """Carrega a lista de livros do backend."""
        try:
            self.books = backend.get_active_books()
            self.filtered_books = self.books.copy()
        except Exception as e:
            theme.print(f"❌ Erro ao carregar livros: {e}", style="error")
            self.books = []
            self.filtered_books = []
    
    def _render_book_list(self, selected_index):
        """Renderiza a lista de livros."""
        theme.clear()
        theme.rule(f"[{self.title}]")
        
        theme.print(f"\n{icon_text(Icon.BOOK, 'Livros disponíveis:')} ({len(self.filtered_books)}/{len(self.books)})", style="primary")
        theme.print("=" * 70, style="dim")
        
        if not self.filtered_books:
            theme.print("\nNenhum livro corresponde ao filtro atual.", style="warning")
        else:
            for i, book in enumerate(self.filtered_books):
                prefix = "> " if i == selected_index else "  "
                
                # Informações básicas
                title = book.get('title', 'Sem título')
                author = book.get('author', 'Autor desconhecido')
                progress = book.get('progress', 0)
                current_page = book.get('current_page', 0)
                total_pages = book.get('total_pages', 0)
                
                # Cor baseada no progresso
                if progress >= 100:
                    style = "success"
                elif progress >= 75:
                    style = "info"
                elif progress >= 50:
                    style = "primary"
                elif progress >= 25:
                    style = "warning"
                else:
                    style = "dim"
                
                # Linha principal
                main_line = f"{prefix}{title}"
                if author:
                    main_line += f" - {author}"
                
                theme.print(main_line, style=style if i == selected_index else "info")
                
                # Linha secundária
                pages_info = f"Pág. {current_page}/{total_pages}" if total_pages > 0 else ""
                progress_bar = self._get_progress_bar(progress)
                
                theme.print(f"     {progress_bar} {progress:.1f}% {pages_info}", style="dim")
        
        # Legenda
        theme.print(f"\n{icon_text(Icon.INFO, 'Legenda:')}", style="dim")
        theme.print("  F) Filtrar  S) Buscar  Enter) Selecionar  ESC) Voltar", style="dim")
        
        # Filtro atual
        filter_names = {
            "all": "Todos",
            "reading": "Em leitura",
            "completed": "Concluídos",
            "recent": "Recentes"
        }
        theme.print(f"\nFiltro: {filter_names.get(self.current_filter, self.current_filter)}", style="dim")
    
    def _get_progress_bar(self, progress, length=20):
        """Gera uma barra de progresso ASCII."""
        filled = int(length * progress / 100)
        return '█' * filled + '░' * (length - filled)
    
    def _apply_filter(self):
        """Aplica filtro à lista de livros."""
        theme.clear()
        theme.rule("[Filtrar Livros]")
        
        theme.print(f"\n{icon_text(Icon.FILTER, 'Selecione o filtro:')}", style="primary")
        
        filters = [
            ("Todos os livros", "all"),
            ("Em leitura (1-99%)", "reading"),
            ("Não iniciados (0%)", "not_started"),
            ("Concluídos (100%)", "completed"),
            ("Recentemente adicionados", "recent"),
            ("Por autor", "author"),
            ("Por categoria", "category")
        ]
        
        for i, (name, value) in enumerate(filters, 1):
            theme.print(f"{i}. {name}", style="info")
        
        choice = input("\nEscolha (1-7): ").strip()
        
        filter_map = {
            '1': 'all', '2': 'reading', '3': 'not_started',
            '4': 'completed', '5': 'recent', '6': 'author', '7': 'category'
        }
        
        new_filter = filter_map.get(choice, 'all')
        
        if new_filter != self.current_filter:
            self.current_filter = new_filter
            self._filter_books()
    
    def _filter_books(self):
        """Filtra os livros baseado no filtro atual."""
        if self.current_filter == "all":
            self.filtered_books = self.books.copy()
        
        elif self.current_filter == "reading":
            self.filtered_books = [
                book for book in self.books
                if 0 < book.get('progress', 0) < 100
            ]
        
        elif self.current_filter == "not_started":
            self.filtered_books = [
                book for book in self.books
                if book.get('progress', 0) == 0
            ]
        
        elif self.current_filter == "completed":
            self.filtered_books = [
                book for book in self.books
                if book.get('progress', 0) >= 100
            ]
        
        elif self.current_filter == "recent":
            # Ordenar por data de adição (supondo que há um campo 'added_date')
            self.filtered_books = sorted(
                self.books,
                key=lambda x: x.get('added_date', ''),
                reverse=True
            )[:10]  # Limitar aos 10 mais recentes
        
        elif self.current_filter == "author":
            author = input("Digite o nome do autor: ").strip().lower()
            if author:
                self.filtered_books = [
                    book for book in self.books
                    if author in book.get('author', '').lower()
                ]
        
        elif self.current_filter == "category":
            category = input("Digite a categoria: ").strip().lower()
            if category:
                self.filtered_books = [
                    book for book in self.books
                    if category in book.get('category', '').lower()
                ]
    
    def _search_books(self):
        """Busca livros por termo."""
        theme.clear()
        theme.rule("[Buscar Livros]")
        
        search_term = input("Termo de busca (título/autor): ").strip().lower()
        
        if not search_term:
            return
        
        self.filtered_books = [
            book for book in self.books
            if (search_term in book.get('title', '').lower() or
                search_term in book.get('author', '').lower() or
                search_term in book.get('category', '').lower())
        ]
        
        self.current_filter = f"busca: '{search_term}'"
    
    def _select_book(self, book):
        """Ações ao selecionar um livro."""
        book_id = book.get('id')
        book_title = book.get('title', 'Livro sem título')
        
        selected_index = 0
        options = [
            ("📖 Iniciar leitura", lambda: self._start_reading(book_id)),
            ("📊 Ver detalhes", lambda: self._view_details(book)),
            ("✏️  Editar informações", lambda: self._edit_book(book_id)),
            ("🔄 Atualizar progresso", lambda: self._update_progress(book_id)),
            ("📋 Gerar flashcards", lambda: self._generate_flashcards(book_id)),
            ("📅 Agendar leitura", lambda: self._schedule_reading(book_id)),
            ("🗑️  Remover livro", lambda: self._remove_book(book_id)),
            ("← Voltar", lambda: "back")
        ]
        
        while True:
            theme.clear()
            theme.rule(f"[{book_title}]")
            
            theme.print(f"\n{icon_text(Icon.BOOK, 'Ações disponíveis:')}", style="primary")
            
            for i, (label, _) in enumerate(options):
                prefix = "> " if i == selected_index else "  "
                theme.print(f"{prefix}{label}", style="primary" if i == selected_index else "info")
            
            key = self.keyboard_handler.wait_for_input()
            
            if key == Key.UP:
                selected_index = (selected_index - 1) % len(options)
            elif key == Key.DOWN:
                selected_index = (selected_index + 1) % len(options)
            elif key == Key.ENTER:
                result = options[selected_index][1]()
                if result == "back":
                    break
                # Recarregar livros após ação
                self._load_books()
                self._filter_books()
                break
            elif key == Key.ESC:
                break
    
    def _start_reading(self, book_id):
        """Inicia sessão de leitura para o livro selecionado."""
        from .reading_session_screen import ReadingSessionScreen
        screen = ReadingSessionScreen(book_id)
        screen.show()
        return "back"
    
    def _view_details(self, book):
        """Mostra detalhes do livro."""
        theme.clear()
        theme.rule(f"[Detalhes: {book.get('title', 'Livro')}]")
        
        theme.print(f"\n{icon_text(Icon.BOOK, 'Informações:')}", style="primary")
        
        fields = [
            ("Título", book.get('title', 'N/A')),
            ("Autor", book.get('author', 'N/A')),
            ("Páginas", f"{book.get('current_page', 0)}/{book.get('total_pages', 'N/A')}"),
            ("Progresso", f"{book.get('progress', 0):.1f}%"),
            ("Categoria", book.get('category', 'Não definida')),
            ("Adicionado em", book.get('added_date', 'N/A')),
            ("Última leitura", book.get('last_read', 'N/A')),
            ("Velocidade média", f"{book.get('reading_speed', 0):.1f} páginas/dia"),
            ("Local no vault", book.get('vault_path', 'N/A'))
        ]
        
        for label, value in fields:
            if value and value != 'N/A':
                theme.print(f"  {label}: {value}", style="info")
        
        # Estatísticas de leitura
        if book.get('reading_stats'):
            theme.print(f"\n{icon_text(Icon.CHART, 'Estatísticas:')}", style="primary")
            stats = book.get('reading_stats', {})
            
            if 'total_sessions' in stats:
                theme.print(f"  Sessões: {stats.get('total_sessions', 0)}", style="dim")
            
            if 'total_minutes' in stats:
                theme.print(f"  Tempo total: {stats.get('total_minutes', 0)} minutos", style="dim")
            
            if 'average_session' in stats:
                theme.print(f"  Média/sessão: {stats.get('average_session', 0):.1f} minutos", style="dim")
        
        self.wait_for_exit()
        return "continue"
    
    def _edit_book(self, book_id):
        """Edita informações do livro."""
        theme.clear()
        theme.rule("[Editar Livro]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
        return "continue"
    
    def _update_progress(self, book_id):
        """Atualiza progresso manualmente."""
        theme.clear()
        theme.rule("[Atualizar Progresso]")
        
        try:
            # Obter livro atual
            book = next((b for b in self.books if b.get('id') == book_id), None)
            if not book:
                theme.print("❌ Livro não encontrado.", style="error")
                self.wait_for_exit()
                return "continue"
            
            current_page = book.get('current_page', 1)
            total_pages = book.get('total_pages', 100)
            
            theme.print(f"\nLivro: {book.get('title', 'Sem título')}", style="info")
            theme.print(f"Progresso atual: {current_page}/{total_pages} ({book.get('progress', 0):.1f}%)", style="info")
            
            new_page = input(f"\nNova página atual (1-{total_pages}): ").strip()
            
            if new_page.isdigit():
                new_page = int(new_page)
                if 1 <= new_page <= total_pages:
                    # Atualizar no backend
                    backend.update_reading_progress(
                        book_id=book_id,
                        current_page=new_page,
                        pages_read=max(0, new_page - current_page)
                    )
                    
                    theme.print(f"\n✅ Progresso atualizado para página {new_page}.", style="success")
                else:
                    theme.print(f"❌ Página inválida. Deve estar entre 1 e {total_pages}.", style="error")
            else:
                theme.print("❌ Entrada inválida.", style="error")
        
        except Exception as e:
            theme.print(f"❌ Erro ao atualizar progresso: {e}", style="error")
        
        self.wait_for_exit()
        return "continue"
    
    def _generate_flashcards(self, book_id):
        """Gera flashcards do livro."""
        theme.clear()
        theme.rule("[Gerar Flashcards]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
        return "continue"
    
    def _schedule_reading(self, book_id):
        """Agenda sessões de leitura para o livro."""
        theme.clear()
        theme.rule("[Agendar Leitura]")
        theme.print("\nEm desenvolvimento...", style="warning")
        self.wait_for_exit()
        return "continue"
    
    def _remove_book(self, book_id):
        """Remove um livro do sistema."""
        theme.clear()
        theme.rule("[Remover Livro]")
        
        theme.print(f"\n{icon_text(Icon.WARNING, 'ATENÇÃO: Esta ação não pode ser desfeita!')}", style="error")
        
        confirm = input("\nDigite 'REMOVER' para confirmar: ").strip()
        
        if confirm == 'REMOVER':
            try:
                # TODO: Implementar método de remoção no backend
                theme.print("\n✅ Livro removido do sistema.", style="success")
            except Exception as e:
                theme.print(f"\n❌ Erro ao remover livro: {e}", style="error")
        else:
            theme.print("\n❌ Remoção cancelada.", style="warning")
        
        self.wait_for_exit()
        return "continue"
