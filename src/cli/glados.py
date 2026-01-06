"""
Integração do módulo GLaDOS com o CLI principal
"""
import typer
from rich.console import Console

# Importa os comandos do módulo GLaDOS
from src.core.llm.glados.commands.brain_query import app as glados_app

console = Console()

def add_glados_to_cli(main_app: typer.Typer):
    """
    Adiciona todos os comandos GLaDOS ao CLI principal
    
    Args:
        main_app: A instância principal do Typer
    """
    main_app.add_typer(
        glados_app,
        name="glados",
        help="🤖 Sistema GLaDOS - Cérebro filosófico com personalidade sarcástica"
    )
    
    console.print("[dim]✓ Módulo GLaDOS carregado[/dim]")

# Comandos diretos (opcional)
app = typer.Typer()

@app.command()
def versao():
    """Mostra versão do módulo GLaDOS"""
    console.print("[bold magenta]GLaDOS v0.4.0[/bold magenta]")
    console.print("[dim]Sistema de inteligência filosófica com personalidade[/dim]")

if __name__ == "__main__":
    app()
