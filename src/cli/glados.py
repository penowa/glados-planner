"""
Módulo de comandos específicos do GLaDOS
"""
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def add_glados_to_cli(app: typer.Typer):
    """Adiciona comandos específicos do Glados ao CLI principal"""
    
    @app.command()
    def glados_test():
        """Testa se o sistema GLaDOS está funcionando"""
        console.print(Panel.fit(
            "[bold cyan]GLaDOS System Test[/bold cyan]\n"
            "[green]✅ All systems operational[/green]\n"
            "[yellow]Current core temperature: 3.6°C[/yellow]",
            border_style="cyan"
        ))
    
    @app.command()
    def glados_personality():
        """Mostra configurações de personalidade do GLaDOS"""
        from src.core.config.settings import settings
        
        table = Table(title="🎭 GLaDOS Personality Settings")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        glados_config = settings.llm.glados
        
        table.add_row("User Name", glados_config.user_name)
        table.add_row("GLaDOS Name", glados_config.gladios_name)
        table.add_row("Gender", glados_config.gender)
        table.add_row("Personality Intensity", str(glados_config.personality_intensity))
        table.add_row("Sarcasm Enabled", "✅" if glados_config.enable_sarcasm else "❌")
        table.add_row("Brain Metaphor", "✅" if glados_config.enable_brain_metaphor else "❌")
        
        console.print(table)
        
        # Mostrar configurações de área
        if glados_config.area_behavior:
            area_table = Table(title="🧠 Area Behavior Settings")
            area_table.add_column("Area", style="magenta")
            area_table.add_column("Sarcasm Level", style="yellow")
            area_table.add_column("Formality", style="blue")
            
            for area, behavior in glados_config.area_behavior.items():
                area_table.add_row(
                    area.capitalize(),
                    str(behavior.sarcasm_level),
                    str(behavior.formality)
                )
            
            console.print(area_table)
    
    @app.command()
    def glados_quote():
        """Citações inspiradoras do GLaDOS"""
        import random
        
        quotes = [
            "[cyan]'The Enrichment Center is committed to the well being of all participants.'[/cyan]",
            "[yellow]'You're doing very well.'[/yellow]",
            "[magenta]'I'm not angry, just disappointed.'[/magenta]",
            "[green]'Science has shown that you learn faster when tested.'[/green]",
            "[red]'This next test involves turrets. You remember them, right?'[/red]",
            "[blue]'The probability of you surviving is... non-zero.'[/blue]",
        ]
        
        console.print(Panel.fit(
            random.choice(quotes),
            title="[bold]GLaDOS Quote[/bold]",
            border_style="cyan"
        ))
    
    @app.command()
    def glados_setup(
        vault_path: str = typer.Option(None, help="Caminho para o vault do Obsidian"),
        model_path: str = typer.Option(None, help="Caminho para o modelo LLM"),
    ):
        """Configuração guiada do GLaDOS"""
        console.print(Panel.fit(
            "[bold cyan]GLaDOS Setup Wizard[/bold cyan]\n"
            "Vamos configurar seu assistente acadêmico personalizado.",
            border_style="cyan"
        ))
        
        # Configuração do vault
        if vault_path:
            console.print(f"[green]✓ Vault configurado: {vault_path}[/green]")
        else:
            console.print("[yellow]⚠️  Nenhum vault configurado. Use --vault-path para configurar.[/yellow]")
        
        # Configuração do modelo
        if model_path:
            console.print(f"[green]✓ Modelo LLM configurado: {model_path}[/green]")
        else:
            console.print("[yellow]⚠️  Nenhum modelo LLM configurado. Use --model-path para configurar.[/yellow]")
        
        console.print("\n[bold green]✅ Configuração inicial concluída![/bold green]")
        console.print("[cyan]Execute 'glados-personality' para ver configurações detalhadas.[/cyan]")

    @app.command()
    def create_vault(
        path: str = typer.Option(None, help="Caminho para criar o vault"),
        force: bool = typer.Option(False, help="Forçar criação mesmo se existir"),
    ):
        """Cria um novo vault do Obsidian estruturado"""
        from src.core.vault.manager import VaultManager
        from src.core.config.settings import settings
        from pathlib import Path
        
        vault_path = path or settings.paths.vault
        vault_path = Path(vault_path).expanduser()
        
        console.print(Panel.fit(
            f"[bold cyan]Criando vault em:[/bold cyan]\n{vault_path}",
            border_style="cyan"
        ))
        
        manager = VaultManager(str(vault_path))
        
        if manager.is_connected() and not force:
            console.print("[yellow]⚠️  Vault já existe. Use --force para recriar.[/yellow]")
            return
        
        if manager.create_structure():
            console.print(Panel.fit(
                "[bold green]✅ Vault criado com sucesso![/bold green]\n\n"
                f"Acesse em: {vault_path}\n\n"
                "[cyan]Estrutura criada:[/cyan]",
                border_style="green"
            ))
            
            # Mostra estrutura criada
            table = Table(title="📁 Estrutura do Vault")
            table.add_column("Diretório", style="cyan")
            table.add_column("Finalidade", style="green")
            
            for directory in settings.obsidian.vault_structure:
                base_name = directory.split(" - ")[-1] if " - " in directory else directory
                purpose = settings.obsidian.brain_regions.get(base_name.lower(), "Organização")
                table.add_row(directory, purpose)
            
            console.print(table)
        else:
            console.print("[red]❌ Falha ao criar vault[/red]")
