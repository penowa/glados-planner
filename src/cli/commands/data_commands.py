# src/cli/commands/data_commands.py
import sys
from pathlib import Path

# Adiciona o diretório src ao sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime, date, timedelta
from sqlalchemy import func

from src.core.repositories.book_repository import BookRepository
from src.core.repositories.task_repository import TaskRepository
from src.core.repositories.note_repository import NoteRepository
from src.core.models.book import BookStatus, ReadingPriority
from src.core.models.task import TaskType, TaskPriority
from src.core.models.note import NoteType

console = Console()
app = typer.Typer(help="📊 Comandos de gestão de dados")

# Instâncias dos repositórios (serão inicializadas no callback)
book_repo = None
task_repo = None
note_repo = None

@app.callback()
def init_repositories():
    """Inicializa os repositórios."""
    global book_repo, task_repo, note_repo
    try:
        book_repo = BookRepository()
        task_repo = TaskRepository()
        note_repo = NoteRepository()
    except Exception as e:
        console.print(f"[yellow]⚠️  Aviso ao inicializar repositórios: {e}[/yellow]")
        console.print("[yellow]Alguns comandos podem não funcionar[/yellow]")

@app.command()
def list_books(
    status: str = typer.Option(None, help="Filtrar por status"),
    author: str = typer.Option(None, help="Filtrar por autor"),
    discipline: str = typer.Option(None, help="Filtrar por disciplina"),
):
    """Lista todos os livros."""
    if book_repo is None:
        console.print("[red]❌ Repositório de livros não inicializado[/red]")
        return
    
    filters = {}
    if status:
        try:
            filters["status"] = BookStatus(status)
        except ValueError:
            console.print(f"[red]Status inválido: {status}[/red]")
            console.print(f"Status válidos: {[s.value for s in BookStatus]}")
            return
    
    if author:
        filters["author"] = author
    
    if discipline:
        filters["discipline"] = discipline
    
    books = book_repo.find(**filters)
    
    if not books:
        console.print("[yellow]Nenhum livro encontrado.[/yellow]")
        return
    
    table = Table(title="📚 Livros Cadastrados")
    table.add_column("ID", style="cyan")
    table.add_column("Título", style="green")
    table.add_column("Autor", style="blue")
    table.add_column("Progresso", justify="right")
    table.add_column("Status", style="magenta")
    table.add_column("Prazo", style="yellow")
    
    for book in books:
        progress = book.progress_percentage()
        status_str = book.status.value.replace("_", " ").title()
        
        deadline_str = str(book.deadline) if book.deadline else "Sem prazo"
        
        table.add_row(
            str(book.id),
            book.title[:30] + ("..." if len(book.title) > 30 else ""),
            book.author[:20] + ("..." if len(book.author) > 20 else ""),
            f"{progress:.1f}% ({book.current_page}/{book.total_pages})",
            status_str,
            deadline_str
        )
    
    console.print(table)
    console.print(f"[dim]Total: {len(books)} livros[/dim]")

@app.command()
def add_book(
    title: str = typer.Option(..., prompt=True, help="Título do livro"),
    author: str = typer.Option(..., prompt=True, help="Autor do livro"),
    total_pages: int = typer.Option(..., prompt=True, help="Total de páginas"),
    deadline: str = typer.Option(None, help="Prazo de leitura (YYYY-MM-DD)"),
    discipline: str = typer.Option(None, help="Disciplina (Ética, Metafísica, etc)"),
):
    """Adiciona um novo livro."""
    if book_repo is None:
        console.print("[red]❌ Repositório de livros não inicializado[/red]")
        return
    
    try:
        book_data = {
            "title": title,
            "author": author,
            "total_pages": total_pages,
            "current_page": 0,
            "status": BookStatus.NOT_STARTED,
        }
        
        if deadline:
            book_data["deadline"] = date.fromisoformat(deadline)
        
        if discipline:
            book_data["discipline"] = discipline
        
        book = book_repo.create(**book_data)
        
        console.print(Panel.fit(
            f"[green]✅ Livro adicionado com sucesso![/green]\n\n"
            f"[bold]Título:[/bold] {book.title}\n"
            f"[bold]Autor:[/bold] {book.author}\n"
            f"[bold]Páginas:[/bold] {book.total_pages}\n"
            f"[bold]ID:[/bold] {book.id}",
            title="📖 Novo Livro",
            border_style="green"
        ))
        
    except ValueError as e:
        console.print(f"[red]❌ Formato de data inválido. Use: YYYY-MM-DD[/red]")
    except Exception as e:
        console.print(f"[red]❌ Erro ao adicionar livro: {e}[/red]")

@app.command()
def update_progress(
    book_id: int = typer.Option(..., prompt=True, help="ID do livro"),
    current_page: int = typer.Option(..., prompt=True, help="Página atual"),
):
    """Atualiza o progresso de leitura de um livro."""
    if book_repo is None:
        console.print("[red]❌ Repositório de livros não inicializado[/red]")
        return
    
    book = book_repo.get(book_id)
    
    if not book:
        console.print(f"[red]❌ Livro com ID {book_id} não encontrado.[/red]")
        return
    
    if current_page > book.total_pages:
        console.print(f"[yellow]⚠️  Página atual ({current_page}) maior que total ({book.total_pages}). Ajustando para total.[/yellow]")
        current_page = book.total_pages
    
    try:
        updated_book = book_repo.update_progress(book_id, current_page)
        
        progress = updated_book.progress_percentage()
        status_str = updated_book.status.value.replace("_", " ").title()
        
        console.print(Panel.fit(
            f"[green]✅ Progresso atualizado![/green]\n\n"
            f"[bold]Livro:[/bold] {updated_book.title}\n"
            f"[bold]Progresso:[/bold] {progress:.1f}% ({current_page}/{updated_book.total_pages})\n"
            f"[bold]Status:[/bold] {status_str}",
            title="📈 Atualização de Progresso",
            border_style="green"
        ))
        
        # Sugerir páginas diárias se houver prazo
        if updated_book.deadline and updated_book.status != BookStatus.COMPLETED:
            daily_pages = book_repo.get_recommended_daily_pages(book_id)
            console.print(f"[dim]📅 Para cumprir o prazo: leia {daily_pages} páginas por dia[/dim]")
            
    except Exception as e:
        console.print(f"[red]❌ Erro ao atualizar progresso: {e}[/red]")

@app.command()
def list_tasks(
    today: bool = typer.Option(False, help="Mostrar apenas tarefas de hoje"),
    upcoming: bool = typer.Option(False, help="Mostrar tarefas dos próximos 7 dias"),
    overdue: bool = typer.Option(False, help="Mostrar tarefas atrasadas"),
    completed: bool = typer.Option(False, help="Incluir tarefas completadas"),
):
    """Lista tarefas."""
    if task_repo is None:
        console.print("[red]❌ Repositório de tarefas não inicializado[/red]")
        return
    
    if today:
        tasks = task_repo.find_today_tasks()
        title = "📅 Tarefas de Hoje"
    elif upcoming:
        tasks = task_repo.find_upcoming_tasks(7)
        title = "📅 Tarefas dos Próximos 7 Dias"
    elif overdue:
        tasks = task_repo.find_overdue_tasks()
        title = "⚠️  Tarefas Atrasadas"
    else:
        tasks = task_repo.get_all()
        title = "📝 Todas as Tarefas"
    
    if not completed:
        tasks = [t for t in tasks if not t.completed]
    
    if not tasks:
        console.print(f"[yellow]Nenhuma tarefa encontrada.[/yellow]")
        return
    
    table = Table(title=title)
    table.add_column("ID", style="cyan")
    table.add_column("Título", style="green")
    table.add_column("Tipo", style="blue")
    table.add_column("Início", style="yellow")
    table.add_column("Duração", justify="right")
    table.add_column("Status", style="magenta")
    
    for task in tasks:
        status = "✅" if task.completed else "⏳"
        type_str = task.task_type.value.replace("_", " ").title()
        start_str = task.start_time.strftime("%d/%m %H:%M")
        duration = f"{task.duration_hours():.1f}h"
        
        table.add_row(
            str(task.id),
            task.title[:30] + ("..." if len(task.title) > 30 else ""),
            type_str,
            start_str,
            duration,
            status
        )
    
    console.print(table)
    console.print(f"[dim]Total: {len(tasks)} tarefas[/dim]")

@app.command()
def add_task(
    title: str = typer.Option(..., prompt=True, help="Título da tarefa"),
    task_type: str = typer.Option(..., prompt=True, help=f"Tipo ({[t.value for t in TaskType]})"),
    start_time: str = typer.Option(..., prompt=True, help="Data/hora início (YYYY-MM-DD HH:MM)"),
    end_time: str = typer.Option(..., prompt=True, help="Data/hora fim (YYYY-MM-DD HH:MM)"),
):
    """Adiciona uma nova tarefa."""
    if task_repo is None:
        console.print("[red]❌ Repositório de tarefas não inicializado[/red]")
        return
    
    try:
        # Converter strings para datetime
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
        
        # Validar tipo
        try:
            task_type_enum = TaskType(task_type)
        except ValueError:
            console.print(f"[red]Tipo inválido. Tipos válidos: {[t.value for t in TaskType]}[/red]")
            return
        
        task_data = {
            "title": title,
            "task_type": task_type_enum,
            "start_time": start_dt,
            "end_time": end_dt,
            "priority": TaskPriority.MEDIUM.value,
            "completed": False,
        }
        
        task = task_repo.create(**task_data)
        
        console.print(Panel.fit(
            f"[green]✅ Tarefa adicionada com sucesso![/green]\n\n"
            f"[bold]Título:[/bold] {task.title}\n"
            f"[bold]Tipo:[/bold] {task.task_type.value}\n"
            f"[bold]Início:[/bold] {task.start_time.strftime('%d/%m/%Y %H:%M')}\n"
            f"[bold]Duração:[/bold] {task.duration_hours():.1f} horas\n"
            f"[bold]ID:[/bold] {task.id}",
            title="📝 Nova Tarefa",
            border_style="green"
        ))
        
    except ValueError as e:
        console.print(f"[red]❌ Formato de data inválido. Use: YYYY-MM-DD HH:MM[/red]")
    except Exception as e:
        console.print(f"[red]❌ Erro ao adicionar tarefa: {e}[/red]")

@app.command()
def daily_summary():
    """Mostra resumo do dia."""
    if task_repo is None:
        console.print("[red]❌ Repositório de tarefas não inicializado[/red]")
        return
    
    summary = task_repo.get_daily_summary()
    
    console.print(Panel.fit(
        f"[bold]📅 Data:[/bold] {summary['date']}\n"
        f"[bold]📊 Total de tarefas:[/bold] {summary['total_tasks']}\n"
        f"[bold]✅ Completadas:[/bold] {summary['completed_tasks']}\n"
        f"[bold]⏳ Pendentes:[/bold] {summary['pending_tasks']}\n"
        f"[bold]📈 Taxa de conclusão:[/bold] {summary['completion_rate']}%\n"
        f"[bold]⏱️  Duração total:[/bold] {summary['total_duration_hours']} horas",
        title="📋 Resumo do Dia",
        border_style="blue"
    ))
    
    if summary['tasks_by_type']:
        console.print("\n[bold]📂 Tarefas por tipo:[/bold]")
        for task_type, count in summary['tasks_by_type'].items():
            console.print(f"  {task_type}: {count}")

@app.command()
def stats():
    """Mostra estatísticas gerais."""
    if book_repo is None or task_repo is None or note_repo is None:
        console.print("[red]❌ Repositórios não inicializados[/red]")
        return
    
    console.print(Panel.fit("📊 Estatísticas do Sistema", border_style="cyan"))
    
    # Estatísticas de livros
    try:
        book_stats = book_repo.get_reading_progress()
        total_books = book_repo.count()
        total_tasks = task_repo.count()
        total_notes = note_repo.count()
        
        console.print("\n[bold]📚 Livros:[/bold]")
        console.print(f"  Total: {total_books}")
        console.print(f"  Páginas totais: {book_stats['total_pages']}")
        console.print(f"  Páginas lidas: {book_stats['read_pages']}")
        console.print(f"  Progresso médio: {book_stats['avg_progress']}%")
        
        console.print("\n[bold]📝 Tarefas:[/bold]")
        console.print(f"  Total: {total_tasks}")
        completed_tasks = len(task_repo.find(completed=True))
        console.print(f"  Completadas: {completed_tasks}")
        
        console.print("\n[bold]🗒️  Anotações:[/bold]")
        console.print(f"  Total: {total_notes}")
        note_stats = note_repo.get_stats_by_type()
        if note_stats:
            for note_type, count in note_stats.items():
                console.print(f"  {note_type}: {count}")
    except Exception as e:
        console.print(f"[red]❌ Erro ao calcular estatísticas: {e}[/red]")
