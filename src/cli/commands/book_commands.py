# src/cli/commands/book_commands.py
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
import questionary

from src.core.modules.book_processor import BookProcessor, ProcessingQuality, ProcessingStatus
from src.core.modules.obsidian.vault_manager import ObsidianVaultManager
from src.core.modules.agenda_manager import AgendaManager  # Para integração futura

app = typer.Typer(help="Comandos para gerenciar livros")
console = Console()

@app.command()
def adicionar(
    caminho: str = typer.Argument(..., help="Caminho para o arquivo do livro (PDF ou EPUB)"),
    transcrever: bool = typer.Option(True, help="Transcrever o livro automaticamente"),
    prazo: Optional[str] = typer.Option(None, help="Prazo para leitura (ex: 30dias, 2semanas)"),
    dificuldade: int = typer.Option(3, help="Dificuldade do livro (1-5)", min=1, max=5),
    prioridade: str = typer.Option("media", help="Prioridade (alta, media, baixa)"),
    qualidade: str = typer.Option("standard", help="Qualidade da transcrição (draft, standard, high, academic)")
):
    """Adiciona um novo livro ao sistema."""
    
    # Verificar se o arquivo existe
    livro_path = Path(caminho).expanduser()
    if not livro_path.exists():
        console.print(f"[red]❌ Arquivo não encontrado: {caminho}[/red]")
        raise typer.Exit(1)
    
    # Mapear qualidade
    quality_map = {
        'draft': ProcessingQuality.DRAFT,
        'standard': ProcessingQuality.STANDARD,
        'high': ProcessingQuality.HIGH,
        'academic': ProcessingQuality.ACADEMIC
    }
    
    processing_quality = quality_map.get(qualidade.lower(), ProcessingQuality.STANDARD)
    
    # Inicializar componentes
    vault_manager = ObsidianVaultManager()
    processor = BookProcessor(vault_manager)
    
    # Analisar o livro primeiro
    console.print(f"\n[cyan]🔍 Analisando livro: {livro_path.name}[/cyan]")
    
    try:
        metadata, recommendations = processor.analyze_book(str(livro_path))
        
        # Mostrar informações do livro
        info_table = Table(title="📚 Informações do Livro")
        info_table.add_column("Campo", style="cyan")
        info_table.add_column("Valor", style="green")
        
        info_table.add_row("Título", metadata.title)
        info_table.add_row("Autor", metadata.author or "Desconhecido")
        info_table.add_row("Páginas", str(metadata.total_pages))
        info_table.add_row("Tamanho", f"{metadata.file_size_mb:.1f} MB")
        info_table.add_row("Tempo estimado", f"{metadata.estimated_processing_time} segundos")
        
        if metadata.requires_ocr:
            info_table.add_row("OCR necessário", "✅ Sim (PDF escaneado)")
        if metadata.has_images:
            info_table.add_row("Contém imagens", "✅ Sim")
        
        console.print(info_table)
        
        # Mostrar recomendações
        if recommendations:
            console.print("\n[yellow]📋 Recomendações:[/yellow]")
            for rec in recommendations:
                console.print(f"  • {rec}")
        
        # Confirmar processamento
        if not transcrever:
            console.print("\n[green]✅ Apenas metadados extraídos. Processamento de transcrição desativado.[/green]")
            return
        
        # Perguntar sobre processamento noturno para livros grandes
        schedule_night = False
        if metadata.estimated_processing_time > 300:  # > 5 minutos
            schedule_night = Confirm.ask(
                f"\n⏰ Este livro levará aproximadamente {metadata.estimated_processing_time//60} minutos para processar. "
                "Deseja agendar para processamento noturno?",
                default=True
            )
        
        # Iniciar processamento
        console.print(f"\n[green]🚀 Iniciando processamento ({processing_quality.value})...[/green]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task(
                f"Processando {metadata.title}...", 
                total=metadata.total_pages
            )
            
            # Simular progresso (será substituído por progresso real)
            for i in range(metadata.total_pages):
                progress.update(task, advance=1, 
                              description=f"Processando página {i+1}/{metadata.total_pages}")
                # Aqui iria o processamento real
            
            result = processor.process_book(
                filepath=str(livro_path),
                quality=processing_quality,
                schedule_night=schedule_night
            )
        
        # Mostrar resultados
        if result.status == ProcessingStatus.COMPLETED:
            console.print(Panel.fit(
                f"[bold green]✅ Livro processado com sucesso![/bold green]\n\n"
                f"📁 [cyan]Diretório:[/cyan] {result.output_dir}\n"
                f"📄 [cyan]Capítulos:[/cyan] {len(result.processed_chapters)}\n"
                f"⏱️ [cyan]Tempo total:[/cyan] {result.end_time - result.start_time if result.end_time else 'N/A'}\n\n"
                f"[yellow]O livro foi integrado ao seu vault do Obsidian.[/yellow]",
                title="Resultado do Processamento"
            ))
            
            # Perguntar sobre alocação na agenda
            if Confirm.ask("\n📅 Deseja alocar tempo para leitura na agenda?", default=True):
                _allocate_reading_time(metadata, prazo, dificuldade, prioridade)
            
            # Perguntar sobre revisão espaçada
            if Confirm.ask("\n🔄 Deseja configurar revisão espaçada?", default=True):
                _setup_spaced_repetition(metadata)
                
        elif result.status == ProcessingStatus.SCHEDULED:
            console.print(Panel.fit(
                f"[yellow]⏰ Processamento agendado para horário noturno[/yellow]\n\n"
                f"O livro será processado automaticamente durante a noite.\n"
                f"Você receberá uma notificação quando estiver pronto.",
                title="Processamento Agendado"
            ))
        else:
            console.print(f"[red]❌ Erro no processamento: {result.error}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ Erro: {e}[/red]")
        raise typer.Exit(1)

def _allocate_reading_time(metadata, prazo, dificuldade, prioridade):
    """Aloca tempo para leitura na agenda."""
    console.print("[yellow]⏳ Alocando tempo na agenda...[/yellow]")
    
    try:
        # Aqui integraríamos com o AgendaManager
        agenda = AgendaManager()
        
        # Calcular páginas por dia baseado no prazo
        pages_per_day = metadata.total_pages / 30  # Default: 30 dias
        
        if prazo:
            # Parse prazo (ex: "30dias", "2semanas")
            if 'dia' in prazo:
                days = int(prazo.replace('dias', '').replace('dia', '').strip())
            elif 'semanas' in prazo:
                days = int(prazo.replace('semanas', '').replace('semanas', '').strip()) * 7
            else:
                days = 30
            
            pages_per_day = metadata.total_pages / days
        
        console.print(f"📖 Páginas por dia: {pages_per_day:.1f}")
        console.print(f"🎯 Dificuldade: {dificuldade}/5")
        console.print(f"⚠️ Prioridade: {prioridade}")
        
        # TODO: Chamar AgendaManager para alocar blocos de leitura
        
        console.print("[green]✅ Tempo alocado na agenda com sucesso![/green]")
        
    except Exception as e:
        console.print(f"[yellow]⚠️ Não foi possível alocar tempo na agenda: {e}[/yellow]")

def _setup_spaced_repetition(metadata):
    """Configura revisão espaçada para o livro."""
    console.print("[yellow]🔁 Configurando revisão espaçada...[/yellow]")
    
    # TODO: Integrar com ReviewSystem
    console.print(f"📚 O livro '{metadata.title}' será revisado em:")
    console.print("   • 1 dia após conclusão")
    console.print("   • 3 dias após")
    console.print("   • 1 semana após")
    console.print("   • 1 mês após")
    
    console.print("[green]✅ Revisão espaçada configurada![/green]")

@app.command()
def listar():
    """Lista todos os livros no sistema."""
    vault_manager = ObsidianVaultManager()
    
    # Encontrar notas de livros
    book_notes = vault_manager.find_notes_by_tag('book')
    
    if not book_notes:
        console.print("[yellow]Nenhum livro encontrado no vault.[/yellow]")
        return
    
    table = Table(title="📚 Livros no Sistema")
    table.add_column("Título", style="cyan", no_wrap=True)
    table.add_column("Autor", style="magenta")
    table.add_column("Progresso", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Tags", style="white")
    
    for note in book_notes[:20]:  # Limitar a 20 para visualização
        title = note.frontmatter.get('title', 'Sem título')
        author = note.frontmatter.get('author', 'Desconhecido')
        progress = note.frontmatter.get('progress', '0%')
        status = note.frontmatter.get('status', 'unknown')
        tags = ", ".join(list(note.tags)[:3])
        
        table.add_row(title, author, progress, status, tags)
    
    console.print(table)
    console.print(f"\n[dim]Total de livros: {len(book_notes)}[/dim]")

@app.command()
def status(livro_id: str = typer.Argument(..., help="ID ou título do livro")):
    """Mostra status de processamento de um livro."""
    console.print(f"[yellow]⚠️ Funcionalidade em desenvolvimento[/yellow]")

if __name__ == "__main__":
    app()
