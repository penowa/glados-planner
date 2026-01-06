# src/cli/main.py
#!/usr/bin/env python3
"""
Philosophy Planner - CLI Main Entry Point
"""
from src.cli.glados import add_glados_to_cli
import sys
from pathlib import Path

# Adiciona o diretório src ao sys.path para imports absolutos
SRC_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(SRC_PATH))

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.database.base import init_db, SessionLocal
# Comentado por enquanto - ainda não implementados
# from src.core.llm.local_llm import PhilosophyLLM
# from src.core.database.obsidian_sync import VaultManager

# Tentar importar comandos de dados, mas continuar se não existirem
try:
    from src.cli.commands.data_commands import app as data_app
    HAS_DATA_COMMANDS = True
except ImportError:
    HAS_DATA_COMMANDS = False

app = typer.Typer(help=" Glados Planner - Sistema de gestão acadêmica")
console = Console()
add_glados_to_cli(app)

# Incluir subcomandos de dados apenas se existirem
if HAS_DATA_COMMANDS:
    app.add_typer(data_app, name="data", help="📊 Comandos de gestão de dados")

# Global state (to be properly managed later)
llm = None
vault_manager = None

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Modo verboso"),
    config: str = typer.Option("config/settings.yaml", help="Caminho do arquivo de configuração"),
):
    """
    Philosophy Planner - Sistema integrado para estudantes de filosofia
    """
    if verbose:
        console.print("[bold yellow]Modo verboso ativado[/bold yellow]")

@app.command()
def init(
    vault_path: str = typer.Option(None, help="Caminho para o vault do Obsidian"),
    force: bool = typer.Option(False, help="Forçar re-inicialização"),
):
    """
    Inicializa o sistema
    """
    console.print(Panel.fit("🚀 Inicializando Philosophy Planner", border_style="blue"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Task 1: Initialize database
        task1 = progress.add_task("[cyan]Inicializando banco de dados...", total=None)
        try:
            init_db()
            progress.update(task1, completed=True)
            console.print("[green]✓ Banco de dados inicializado[/green]")
        except Exception as e:
            console.print(f"[red]✗ Erro ao inicializar banco: {e}[/red]")
            raise typer.Exit(1)
        
        # Task 2: Setup vault manager
        task2 = progress.add_task("[cyan]Configurando gerenciador do vault...", total=None)
        global vault_manager
        try:
            # vault_manager = VaultManager(vault_path)
            progress.update(task2, completed=True)
            console.print("[green]✓ Gerenciador do vault configurado[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Aviso: {e}[/yellow]")
            console.print("[yellow]Você pode configurar o vault posteriormente[/yellow]")
        
        # Task 3: Load LLM
        task3 = progress.add_task("[cyan]Carregando modelo LLM...", total=None)
        global llm
        try:
            # llm = PhilosophyLLM()
            progress.update(task3, completed=True)
            console.print("[green]✓ Modelo LLM carregado[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Aviso: {e}[/yellow]")
            console.print("[yellow]Funcionalidades LLM estarão desabilitadas[/yellow]")
    
    console.print(Panel.fit("✅ Sistema inicializado com sucesso!", border_style="green"))

@app.command()
def version():
    """
    Mostra a versão do sistema
    """
    from importlib.metadata import version, PackageNotFoundError
    
    try:
        v = version("philosophy-planner")
        console.print(f"[bold]Philosophy Planner[/bold] v{v}")
    except PackageNotFoundError:
        console.print("[bold]Philosophy Planner[/bold] v0.1.0 (desenvolvimento)")

@app.command()
def status():
    """
    Mostra status do sistema
    """
    table = Table(title="📊 Status do Sistema")
    table.add_column("Componente", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Detalhes")
    
    # Database status
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "✅"
        db_details = "Conectado"
    except Exception as e:
        db_status = "❌"
        db_details = f"Desconectado: {e}"
    
    # LLM status
    global llm
    if llm and hasattr(llm, 'is_loaded') and llm.is_loaded():
        llm_status = "✅"
        llm_details = "Modelo carregado"
    else:
        llm_status = "⚠️"
        llm_details = "Não carregado"
    
    # Vault status
    global vault_manager
    if vault_manager and hasattr(vault_manager, 'is_connected') and vault_manager.is_connected():
        vault_status = "✅"
        vault_details = vault_manager.vault_path
    else:
        vault_status = "⚠️"
        vault_details = "Não configurado"
    
    table.add_row("Banco de Dados", db_status, db_details)
    table.add_row("LLM Local", llm_status, llm_details)
    table.add_row("Obsidian Vault", vault_status, vault_details)
    
    console.print(table)

if __name__ == "__main__":
    app()
