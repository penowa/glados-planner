# src/cli/interactive/screens/reading_session_screen.py
"""
Tela de sessão de leitura com timer e acompanhamento de progresso.
Integra com ReadingManager.
"""
import time
from .base_screen import BaseScreen
from cli.integration.backend_integration import backend
from cli.theme import theme
from cli.icons import Icon, icon_text

class ReadingSessionScreen(BaseScreen):
    """Tela de sessão de leitura."""
    
    def __init__(self, book_id=None):
        super().__init__()
        self.title = "Sessão de Leitura"
        self.book_id = book_id
        self.current_book = None
        self.duration = 60 * 60  # 60 minutos padrão
        self.is_running = False
        self.pages_read = 0
    
    def show(self):
        # Selecionar livro se não fornecido
        if not self.book_id:
            self._select_book()
        
        if not self.current_book:
            theme.print("❌ Nenhum livro selecionado.", style="error")
            self.wait_for_exit()
            return
        
        # Configurar sessão
        self._setup_session()
        
        # Iniciar sessão
        self._start_session()
        
        # Mostrar tela de leitura
        self._show_reading_session()
        
        # Finalizar sessão
        self._finish_session()
    
    def set_book(self, book_id):
        """Define o livro para a sessão."""
        self.book_id = book_id
        self._load_book()
    
    def _select_book(self):
        """Seleciona um livro para leitura."""
        try:
            books = backend.get_active_books()
            
            if not books:
                theme.print("❌ Nenhum livro ativo encontrado.", style="error")
                return
            
            theme.clear()
            theme.rule("[Selecionar Livro para Leitura]")
            
            theme.print(f"\n{icon_text(Icon.BOOK, 'Livros ativos:')}", style="primary")
            
            for i, book in enumerate(books, 1):
                progress = book.get('progress', 0)
                theme.print(f"{i}. {book.get('title', 'Sem título')} - {progress}%", style="info")
            
            choice = input("\nEscolha um livro (número): ").strip()
            
            if choice.isdigit() and 1 <= int(choice) <= len(books):
                self.book_id = books[int(choice)-1].get('id')
                self._load_book()
            else:
                theme.print("❌ Seleção inválida.", style="error")
                
        except Exception as e:
            theme.print(f"❌ Erro ao carregar livros: {e}", style="error")
    
    def _load_book(self):
        """Carrega informações do livro."""
        if not self.book_id:
            return
        
        try:
            # TODO: Implementar método específico para obter livro por ID
            books = backend.get_active_books()
            for book in books:
                if book.get('id') == self.book_id:
                    self.current_book = book
                    break
        except:
            self.current_book = {
                'id': self.book_id,
                'title': 'Livro Desconhecido',
                'author': 'Autor Desconhecido',
                'current_page': 1,
                'total_pages': 100
            }
    
    def _setup_session(self):
        """Configura a sessão de leitura."""
        if not self.current_book:
            return
        
        theme.clear()
        theme.rule("[Configurar Sessão de Leitura]")
        
        theme.print(f"\n{icon_text(Icon.BOOK, 'Livro selecionado:')}", style="primary")
        theme.print(f"  📖 {self.current_book.get('title', 'Sem título')}", style="info")
        theme.print(f"  👤 {self.current_book.get('author', 'Autor desconhecido')}", style="dim")
        theme.print(f"  📄 Página atual: {self.current_book.get('current_page', 1)}/{self.current_book.get('total_pages', '?')}", style="dim")
        theme.print(f"  📊 Progresso: {self.current_book.get('progress', 0)}%", style="dim")
        
        # Configurar duração
        theme.print(f"\n{icon_text(Icon.TIMER, 'Duração da sessão:')}", style="info")
        duration = input("Minutos (padrão=60): ").strip()
        
        if duration.isdigit():
            self.duration = int(duration) * 60
        else:
            self.duration = 60 * 60
        
        # Meta de páginas
        theme.print(f"\n{icon_text(Icon.TARGET, 'Meta de páginas (opcional):')}", style="info")
        pages_goal = input("Quantas páginas deseja ler?: ").strip()
        
        self.pages_goal = int(pages_goal) if pages_goal.isdigit() else None
        
        # Notas
        theme.print(f"\n{icon_text(Icon.NOTE, 'Notas para esta sessão (opcional):')}", style="info")
        self.session_notes = input(": ").strip()
    
    def _start_session(self):
        """Inicia a sessão de leitura."""
        self.is_running = True
        self.start_time = time.time()
        self.remaining_time = self.duration
        self.start_page = self.current_book.get('current_page', 1)
        
        # Registrar início no backend
        try:
            backend.start_reading_session({
                'book_id': self.book_id,
                'start_page': self.start_page,
                'duration': self.duration,
                'pages_goal': self.pages_goal,
                'notes': self.session_notes
            })
        except:
            pass
    
    def _show_reading_session(self):
        """Mostra a interface da sessão de leitura."""
        reading_tips = [
            "Mantenha uma postura errada para melhor concentração. Brincadeira. Mantenha uma postura ereta.",
            "Anote pontos importantes. Ou não anote. Eu não sou sua professora.",
            "Faça pausas a cada 20-30 minutos. A menos que esteja quase terminando um capítulo.",
            "Leia ativamente, questionando o texto. Ou leia passivamente. Sua escolha.",
            "Use um marca-texto para passagens importantes. Mas não exagere.",
            "Resuma o que leu a cada capítulo. Ou não. Eu só estou dando sugestões."
        ]
        
        current_tip = 0
        
        while self.is_running and self.remaining_time > 0:
            theme.clear()
            theme.rule("[Sessão de Leitura em Andamento]", style="accent")
            
            # Informações do livro
            theme.print(f"\n{icon_text(Icon.BOOK, 'Lendo:')}", style="primary")
            theme.print(f"  {self.current_book.get('title', 'Sem título')}", style="info")
            
            # Timer
            minutes = self.remaining_time // 60
            seconds = self.remaining_time % 60
            
            theme.print(f"\n{icon_text(Icon.TIMER, 'Tempo restante:')}", style="primary")
            theme.print(f"  ⏰ {minutes:02d}:{seconds:02d}", style="accent")
            
            # Progresso
            current_page = self.current_book.get('current_page', self.start_page)
            total_pages = self.current_book.get('total_pages', 100)
            
            if total_pages > 0:
                book_progress = (current_page / total_pages) * 100
                session_progress = 1 - (self.remaining_time / self.duration)
                
                theme.print(f"\n{icon_text(Icon.CHART, 'Progresso:')}", style="info")
                theme.print(f"  📖 Páginas: {current_page}/{total_pages} ({book_progress:.1f}%)", style="dim")
                
                # Barra de progresso da sessão
                bar_length = 30
                filled = int(bar_length * session_progress)
                bar = '█' * filled + '░' * (bar_length - filled)
                theme.print(f"  ⏱️  Sessão: [{bar}] {session_progress*100:.1f}%", style="dim")
            
            # Dica de leitura
            theme.print(f"\n{icon_text(Icon.INFO, 'Dica de leitura:')}", style="accent")
            theme.print(f"  {reading_tips[current_tip % len(reading_tips)]}", style="dim")
            
            # Controle de páginas
            theme.print(f"\n{icon_text(Icon.EDIT, 'Controles:')}", style="info")
            theme.print("  +) Adicionar página lida", style="dim")
            theme.print("  -) Remover página lida", style="dim")
            theme.print("  S) Salvar e continuar", style="dim")
            theme.print("  X) Finalizar sessão", style="dim")
            
            # Atualizar timer
            time.sleep(1)
            self.remaining_time -= 1
            
            # Verificar entrada
            key = self.keyboard_handler.get_key()
            
            if key == Key.PLUS or key == Key.ADD:
                self._add_page()
            elif key == Key.MINUS or key == Key.SUBTRACT:
                self._remove_page()
            elif key == Key.S:
                self._save_progress()
            elif key in [Key.X, Key.ESC]:
                self._handle_early_exit()
                break
            
            # Mudar dica a cada 2 minutos
            if self.remaining_time % 120 == 0:
                current_tip += 1
        
        # Sessão completada por tempo
        if self.remaining_time <= 0:
            self._save_progress()
    
    def _add_page(self):
        """Adiciona uma página lida."""
        if 'current_page' in self.current_book:
            self.current_book['current_page'] += 1
            self.pages_read += 1
            
            # Atualizar progresso
            total_pages = self.current_book.get('total_pages', 100)
            if total_pages > 0:
                progress = (self.current_book['current_page'] / total_pages) * 100
                self.current_book['progress'] = progress
    
    def _remove_page(self):
        """Remove uma página lida."""
        if 'current_page' in self.current_book and self.current_book['current_page'] > 1:
            self.current_book['current_page'] -= 1
            self.pages_read = max(0, self.pages_read - 1)
    
    def _save_progress(self):
        """Salva o progresso atual no backend."""
        if not self.current_book or not self.book_id:
            return
        
        try:
            backend.update_reading_progress(
                book_id=self.book_id,
                current_page=self.current_book.get('current_page', self.start_page),
                pages_read=self.pages_read,
                session_duration=self.duration - self.remaining_time
            )
            
            theme.print(f"\n✅ Progresso salvo: Página {self.current_book.get('current_page', self.start_page)}", style="success")
            time.sleep(1)
            
        except Exception as e:
            theme.print(f"\n❌ Erro ao salvar progresso: {e}", style="error")
    
    def _handle_early_exit(self):
        """Lida com saída antecipada da sessão."""
        theme.print(f"\n{icon_text(Icon.QUESTION, 'Finalizar sessão antecipadamente?')}", style="warning")
        theme.print("  S) Salvar progresso e sair", style="info")
        theme.print("  X) Descartar e sair", style="error")
        theme.print("  C) Continuar sessão", style="info")
        
        while True:
            key = self.keyboard_handler.wait_for_input()
            
            if key == Key.S:
                self._save_progress()
                self.is_running = False
                break
            elif key == Key.X:
                self.is_running = False
                break
            elif key == Key.C:
                # Continuar sessão
                break
    
    def _finish_session(self):
        """Finaliza a sessão e mostra resumo."""
        theme.clear()
        theme.rule("[Sessão de Leitura Concluída]", style="success")
        
        theme.print(f"\n{icon_text(Icon.SUCCESS, 'Sessão de leitura concluída!')}", style="success")
        theme.print("=" * 50, style="dim")
        
        # Estatísticas
        theme.print(f"\n{icon_text(Icon.BOOK, 'Resumo da sessão:')}", style="primary")
        
        session_minutes = (self.duration - self.remaining_time) // 60
        theme.print(f"  ⏱️  Duração: {session_minutes} minutos", style="info")
        theme.print(f"  📖 Páginas lidas: {self.pages_read}", style="info")
        
        if self.pages_read > 0 and session_minutes > 0:
            pages_per_minute = self.pages_read / session_minutes
            theme.print(f"  📊 Velocidade: {pages_per_minute:.1f} páginas/minuto", style="info")
        
        # Progresso do livro
        current_page = self.current_book.get('current_page', self.start_page)
        total_pages = self.current_book.get('total_pages', 100)
        
        if total_pages > 0:
            progress = (current_page / total_pages) * 100
            pages_remaining = total_pages - current_page
            
            theme.print(f"\n{icon_text(Icon.CHART, 'Progresso do livro:')}", style="primary")
            theme.print(f"  📖 Página atual: {current_page}/{total_pages}", style="info")
            theme.print(f"  📊 Progresso total: {progress:.1f}%", style="info")
            
            if pages_remaining > 0 and self.pages_read > 0:
                estimated_sessions = pages_remaining / self.pages_read
                theme.print(f"  ⏳ Estimativa: {estimated_sessions:.1f} sessões restantes", style="dim")
        
        # Meta
        if self.pages_goal:
            goal_percentage = (self.pages_read / self.pages_goal) * 100
            theme.print(f"\n{icon_text(Icon.TARGET, 'Meta da sessão:')}", style="primary")
            theme.print(f"  🎯 {self.pages_read}/{self.pages_goal} páginas ({goal_percentage:.1f}%)", 
                       style="success" if goal_percentage >= 100 else "warning")
        
        self.wait_for_exit("\nPressione qualquer tecla para voltar...")
