# src/cli/commands/obsidian_commands.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import json

from src.core.modules.obsidian import ObsidianVaultManager

console = Console()
app = typer.Typer(help="🔗 Comandos de integração com Obsidian")

# Instância do gerenciador de vault
vault_manager = None

@app.callback()
def init_vault_manager(vault_path: str = typer.Option(None, help="Caminho para o vault do Obsidian")):
    """Inicializa o gerenciador do vault."""
    global vault_manager
    try:
        vault_manager = ObsidianVaultManager(vault_path)
        console.print(f"[green]✅ Vault conectado: {vault_manager.vault_path}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Erro ao conectar ao vault: {e}[/red]")
        console.print("[yellow]Use --vault-path para especificar o caminho[/yellow]")

@app.command()
def vault_status():
    """Mostra status do vault do Obsidian."""
    if not vault_manager or not vault_manager.is_connected():
        console.print("[red]❌ Vault não conectado[/red]")
        return
    
    stats = vault_manager.get_vault_stats()
    
    console.print(Panel.fit("📊 Status do Vault Obsidian", border_style="blue"))
    
    # Tabela de estatísticas básicas
    table = Table(show_header=False, box=None)
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    
    table.add_row("Total de notas", f"{stats['total_notes']}")
    table.add_row("Total de links", f"{stats['total_links']}")
    table.add_row("Tamanho do vault", f"{stats['vault_size_mb']:.2f} MB")
    table.add_row("Caminho", f"{vault_manager.vault_path}")
    
    console.print(table)
    
    # Top tags
    if stats['tag_counts']:
        console.print("\n[bold]🏷️  Top Tags:[/bold]")
        tag_table = Table()
        tag_table.add_column("Tag", style="cyan")
        tag_table.add_column("Quantidade", style="green", justify="right")
        
        for tag, count in stats['tag_counts'].items():
            tag_table.add_row(tag, str(count))
        
        console.print(tag_table)
    
    # Tipos de notas
    if stats['type_counts']:
        console.print("\n[bold]📂 Tipos de Notas:[/bold]")
        type_table = Table()
        type_table.add_column("Tipo", style="magenta")
        type_table.add_column("Quantidade", style="green", justify="right")
        
        for note_type, count in stats['type_counts'].items():
            type_table.add_row(note_type, str(count))
        
        console.print(type_table)

@app.command()
def list_notes(
    tag: str = typer.Option(None, help="Filtrar por tag"),
    search: str = typer.Option(None, help="Buscar no conteúdo"),
    limit: int = typer.Option(20, help="Limite de resultados"),
):
    """Lista notas do vault do Obsidian."""
    if not vault_manager:
        console.print("[red]❌ Vault não conectado[/red]")
        return
    
    notes = []
    
    if tag:
        notes = vault_manager.find_notes_by_tag(tag)
        title = f"📝 Notas com tag: #{tag}"
    elif search:
        notes = vault_manager.find_notes_by_content(search)
        title = f"🔍 Notas contendo: '{search}'"
    else:
        notes = vault_manager.get_all_notes()
        title = "📝 Todas as Notas"
    
    # Ordenar por data de modificação (mais recentes primeiro)
    notes.sort(key=lambda x: x.modified or x.created or datetime.min, reverse=True)
    
    if not notes:
        console.print(f"[yellow]Nenhuma nota encontrada.[/yellow]")
        return
    
    # Limitar resultados
    notes = notes[:limit]
    
    table = Table(title=title)
    table.add_column("Caminho", style="cyan")
    table.add_column("Tags", style="blue")
    table.add_column("Links", style="magenta", justify="right")
    table.add_column("Modificado", style="yellow")
    
    for note in notes:
        # Formatar tags
        tags_str = ", ".join(list(note.tags)[:3])
        if len(note.tags) > 3:
            tags_str += f" (+{len(note.tags) - 3})"
        
        # Formatar data
        date_str = note.modified.strftime("%d/%m %H:%M") if note.modified else "N/A"
        
        table.add_row(
            str(note.path),
            tags_str,
            str(len(note.links)),
            date_str
        )
    
    console.print(table)
    console.print(f"[dim]Mostrando {len(notes)} de {len(vault_manager.get_all_notes())} notas[/dim]")

@app.command()
def sync_from_obsidian(
    force: bool = typer.Option(False, help="Forçar sincronização completa"),
    dry_run: bool = typer.Option(False, help="Apenas mostrar o que seria feito"),
):
    """Sincroniza dados do Obsidian para o Philosophy Planner."""
    if not vault_manager:
        console.print("[red]❌ Vault não conectado[/red]")
        return
    
    console.print(Panel.fit("🔄 Sincronizando do Obsidian", border_style="blue"))
    
    if dry_run:
        console.print("[yellow]🧪 Modo dry-run: apenas simulação[/yellow]")
        
        # Contar notas que seriam processadas
        notes = vault_manager.get_all_notes()
        book_notes = vault_manager.find_notes_by_tag('book')
        
        console.print(f"\n[bold]📊 Estatísticas estimadas:[/bold]")
        console.print(f"  📚 Notas de livros: {len(book_notes)}")
        console.print(f"  📝 Total de notas: {len(notes)}")
        console.print(f"  🔄 Notas a processar: {len(notes) - len(book_notes)}")
        
        # Mostrar algumas notas que seriam importadas
        if notes:
            console.print(f"\n[bold]📋 Exemplo de notas que seriam importadas:[/bold]")
            for i, note in enumerate(notes[:5]):
                console.print(f"  {i+1}. {note.path} ({len(note.tags)} tags)")
        
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Sincronizando do Obsidian...", total=None)
        
        try:
            stats = vault_manager.sync_from_obsidian()
            progress.update(task, completed=True)
            
            console.print(Panel.fit(
                f"[green]✅ Sincronização concluída![/green]\n\n"
                f"[bold]📚 Livros:[/bold]\n"
                f"  Encontrados: {stats['books_found']}\n"
                f"  Criados: {stats['books_created']}\n"
                f"  Atualizados: {stats['books_updated']}\n\n"
                f"[bold]📝 Anotações:[/bold]\n"
                f"  Encontradas: {stats['notes_found']}\n"
                f"  Criadas: {stats['notes_created']}\n"
                f"  Atualizadas: {stats['notes_updated']}",
                title="📊 Resultado da Sincronização",
                border_style="green"
            ))
            
        except Exception as e:
            console.print(f"[red]❌ Erro durante sincronização: {e}[/red]")

@app.command()
def sync_to_obsidian(
    book_id: int = typer.Option(None, help="ID do livro específico para sincronizar"),
    all_books: bool = typer.Option(False, help="Sincronizar todos os livros"),
):
    """Sincroniza dados do Philosophy Planner para o Obsidian."""
    if not vault_manager:
        console.print("[red]❌ Vault não conectado[/red]")
        return
    
    if not all_books and book_id is None:
        console.print("[yellow]⚠️  Use --book-id ou --all-books para especificar o que sincronizar[/yellow]")
        return
    
    console.print(Panel.fit("🔄 Sincronizando para o Obsidian", border_style="blue"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Sincronizando para o Obsidian...", total=None)
        
        try:
            stats = vault_manager.sync_to_obsidian(book_id)
            progress.update(task, completed=True)
            
            console.print(Panel.fit(
                f"[green]✅ Sincronização concluída![/green]\n\n"
                f"[bold]📊 Estatísticas:[/bold]\n"
                f"  📚 Livros sincronizados: {stats['books_synced']}\n"
                f"  📝 Anotações sincronizadas: {stats['notes_synced']}\n"
                f"  📄 Arquivos criados: {stats['files_created']}\n"
                f"  🔄 Arquivos atualizados: {stats['files_updated']}",
                title="📊 Resultado da Sincronização",
                border_style="green"
            ))
            
        except Exception as e:
            console.print(f"[red]❌ Erro durante sincronização: {e}[/red]")

@app.command()
def create_book_note(
    book_id: int = typer.Option(..., help="ID do livro"),
    template: str = typer.Option("metadata", help="Template a usar (metadata, summary, concept)"),
):
    """Cria uma nota no Obsidian para um livro específico."""
    if not vault_manager:
        console.print("[red]❌ Vault não conectado[/red]")
        return
    
    from src.core.repositories import BookRepository
    from src.core.database.base import SessionLocal
    from datetime import datetime
    
    db = SessionLocal()
    
    try:
        book_repo = BookRepository(db)
        book = book_repo.get(book_id)
        
        if not book:
            console.print(f"[red]❌ Livro com ID {book_id} não encontrado[/red]")
            return
        
        console.print(f"[cyan]Criando nota para: {book.title} por {book.author}[/cyan]")
        
        # Calcular páginas por dia se houver prazo
        pages_per_day = 0
        days_remaining = None
        if book.deadline:
            from datetime import date
            days_remaining = (book.deadline - date.today()).days
            if days_remaining > 0:
                pages_per_day = (book.total_pages - book.current_page) // days_remaining
        
        # Preparar dados para o template
        template_data = {
            'title': book.title,
            'author': book.author,
            'status': book.status.value.replace('_', ' ').title(),
            'progress': f"{book.progress_percentage():.1f}",
            'current_page': book.current_page,
            'total_pages': book.total_pages,
            'discipline': book.discipline or "Filosofia",
            'discipline_lower': (book.discipline or "filosofia").lower(),
            'publisher': book.publisher or "Desconhecida",
            'year': book.year or "Desconhecido",
            'isbn': book.isbn or "N/A",
            'date': datetime.now().strftime("%Y-%m-%d"),
            'start_date': book.start_date.strftime("%d/%m/%Y") if book.start_date else "Não iniciado",
            'deadline': book.deadline.strftime("%d/%m/%Y") if book.deadline else "Sem prazo",
            'finish_date': book.finish_date.strftime("%d/%m/%Y") if book.finish_date else "Não concluído",
            'pages_per_day': pages_per_day,
            'days_remaining': days_remaining or "N/A"
        }
        
        # Escolher template
        from src.core.modules.obsidian.templates import book_template
        
        if template == "summary":
            template_content = book_template.BOOK_SUMMARY_TEMPLATE
            note_path = f"01-LEITURAS/{book.author}/{book.title}/📖 Resumo.md"
        elif template == "concept":
            template_content = book_template.CONCEPT_TEMPLATE
            note_path = f"01-LEITURAS/{book.author}/{book.title}/🧠 Conceitos.md"
        else:  # metadata
            template_content = book_template.BOOK_METADATA_TEMPLATE
            note_path = f"01-LEITURAS/{book.author}/{book.title}/📖 Metadados.md"
        
        # Aplicar template
        content = template_content.format(**template_data)
        
        # Criar nota
        note = vault_manager.create_note(
            note_path,
            content=content,
            tags=["book", book.discipline.lower() if book.discipline else "filosofia"]
        )
        
        console.print(Panel.fit(
            f"[green]✅ Nota criada com sucesso![/green]\n\n"
            f"[bold]Caminho:[/bold] {note.path}\n"
            f"[bold]Template:[/bold] {template}\n"
            f"[bold]Tamanho:[/bold] {len(content)} caracteres",
            title="📄 Nova Nota no Obsidian",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"[red]❌ Erro ao criar nota: {e}[/red]")
    finally:
        db.close()

@app.command()
def search_backlinks(
    note_path: str = typer.Option(..., help="Caminho da nota (relativo ao vault)"),
):
    """Busca backlinks para uma nota específica."""
    if not vault_manager:
        console.print("[red]❌ Vault não conectado[/red]")
        return
    
    note_name = Path(note_path).stem
    all_notes = vault_manager.get_all_notes()
    
    backlinks = []
    for note in all_notes:
        # Verificar se a nota menciona a nota alvo
        if f"[[{note_name}]]" in note.content or f"[[{note_path}]]" in note.content:
            backlinks.append(note)
    
    if not backlinks:
        console.print(f"[yellow]Nenhum backlink encontrado para {note_path}[/yellow]")
        return
    
    console.print(Panel.fit(f"🔗 Backlinks para: {note_path}", border_style="blue"))
    
    table = Table()
    table.add_column("Nota", style="cyan")
    table.add_column("Tags", style="blue")
    table.add_column("Mencionado em", style="yellow")
    
    for note in backlinks:
        tags_str = ", ".join(list(note.tags)[:3])
        table.add_row(str(note.path), tags_str, str(note.modified.strftime("%d/%m %H:%M")))
    
    console.print(table)
    console.print(f"[dim]Total de backlinks: {len(backlinks)}[/dim]")
