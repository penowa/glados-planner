#!/usr/bin/env python3
"""
Glados Planner - CLI Main Entry Point
"""
import sys
from pathlib import Path

# Adiciona o diretório src ao sys.path para imports absolutos
SRC_PATH = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_PATH))

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Importações básicas que devem sempre existir
from src.core.database.base import init_db, SessionLocal
from src.core.vault.manager import VaultManager

# Tentar importar comandos do GLaDOS, mas continuar se não existirem
try:
    from src.cli.commands.brain_query import app as glados_app
    HAS_GLADOS = True
except ImportError:
    HAS_GLADOS = False

# Tentar importar comandos de dados, mas continuar se não existirem
try:
    from src.cli.commands.data_commands import app as data_app
    HAS_DATA_COMMANDS = True
except ImportError:
    HAS_DATA_COMMANDS = False

app = typer.Typer(help="GLaDOS Planner - Sistema de gestão acadêmica filosófica")
console = Console()

# Incluir subcomandos apenas se existirem
if HAS_GLADOS:
    app.add_typer(glados_app, name="glados", help="🤖 Comandos do cérebro GLaDOS")

if HAS_DATA_COMMANDS:
    app.add_typer(data_app, name="data", help="📊 Comandos de gestão de dados")

# Global state (to be properly managed later)
vault_manager = None

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Modo verboso"),
):
    """
    GLaDOS Planner - Sistema integrado para estudantes de filosofia
    """
    if verbose:
        console.print("[bold yellow]Modo verboso ativado[/bold yellow]")

@app.command()
def init(
    vault_path: str = typer.Option(None, help="Caminho para o vault do Obsidian"),
    force: bool = typer.Option(False, help="Forçar re-inicialização"),
):
    """
    Inicializa o sistema GLaDOS Planner
    """
    from src.core.config.settings import settings
    
    console.print(Panel.fit("🚀 Inicializando GLaDOS Planner", border_style="blue"))
    
    # Usa o caminho do vault das configurações se não fornecido
    if not vault_path:
        vault_path = settings.paths.vault
    
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
            vault_manager = VaultManager(vault_path)
            if force or not vault_manager.is_connected():
                vault_manager.create_structure()
            progress.update(task2, completed=True)
            console.print(f"[green]✓ Gerenciador do vault configurado em: {vault_path}[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Aviso: {e}[/yellow]")
            console.print("[yellow]Você pode configurar o vault posteriormente[/yellow]")
        
        # Task 3: Verificar módulos
        task3 = progress.add_task("[cyan]Verificando módulos...", total=None)
        progress.update(task3, completed=True)
        
        # Verificar quais módulos estão disponíveis
        modules_status = []
        
        try:
            from src.core.llm.local_llm import PhilosophyLLM
            modules_status.append(("PhilosophyLLM", "✅"))
        except:
            modules_status.append(("PhilosophyLLM", "⚠️"))
        
        try:
            from src.core.modules.reading_manager import ReadingManager
            modules_status.append(("ReadingManager", "✅"))
        except:
            modules_status.append(("ReadingManager", "⚠️"))
        
        try:
            from src.core.modules.agenda_manager import AgendaManager
            modules_status.append(("AgendaManager", "✅"))
        except:
            modules_status.append(("AgendaManager", "⚠️"))
    
    console.print("\n[bold]Status dos Módulos:[/bold]")
    for module, status in modules_status:
        console.print(f"  {status} {module}")
    
    console.print(Panel.fit("✅ Sistema GLaDOS Planner inicializado com sucesso!", border_style="green"))
    
    console.print("\n[bold]Próximos passos:[/bold]")
    console.print("1. Use 'glados consultar' para testar o cérebro da GLaDOS")
    console.print("2. Explore 'data leituras', 'data agenda' para funcionalidades avançadas")
    console.print("3. Configure seu vault do Obsidian em ~/Documentos/Obsidian/Philosophy_Vault")

@app.command()
def version():
    """
    Mostra a versão do sistema
    """
    from importlib.metadata import version, PackageNotFoundError
    from src.core.config.settings import settings
    
    try:
        v = version("glados-planner")
        console.print(f"[bold]GLaDOS Planner[/bold] v{v}")
    except PackageNotFoundError:
        console.print(f"[bold]GLaDOS Planner[/bold] v{settings.app.version} (desenvolvimento)")
    
    console.print(f"[dim]Ambiente: {settings.app.environment}[/dim]")

@app.command()
def status():
    """
    Mostra status do sistema
    """
    from src.core.config.settings import settings
    
    table = Table(title="📊 Status do Sistema GLaDOS Planner")
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
        db_details = f"Desconectado: {str(e)[:50]}"
    
    # Vault status
    try:
        vault_manager = VaultManager(settings.paths.vault)
        if vault_manager.is_connected():
            vault_status = "✅"
            vault_details = str(vault_manager.vault_path)
        else:
            vault_status = "⚠️"
            vault_details = "Não conectado"
    except Exception as e:
        vault_status = "❌"
        vault_details = f"Erro: {str(e)[:50]}"
    
    # GLaDOS status
    if HAS_GLADOS:
        glados_status = "✅"
        glados_details = "Comandos disponíveis"
    else:
        glados_status = "⚠️"
        glados_details = "Módulo não encontrado"
    
    # Data commands status
    if HAS_DATA_COMMANDS:
        data_status = "✅"
        data_details = "Comandos disponíveis"
    else:
        data_status = "⚠️"
        data_details = "Módulo não encontrado"
    
    table.add_row("Banco de Dados", db_status, db_details)
    table.add_row("Obsidian Vault", vault_status, vault_details)
    table.add_row("Cérebro GLaDOS", glados_status, glados_details)
    table.add_row("Módulos de Dados", data_status, data_details)
    
    console.print(table)
    
    # Mostrar informações do sistema
    console.print(f"\n[bold]Configurações:[/bold]")
    console.print(f"  • Versão: {settings.app.version}")
    console.print(f"  • Ambiente: {settings.app.environment}")
    console.print(f"  • Vault: {settings.paths.vault}")
    
    if HAS_GLADOS:
        console.print(f"  • Usuário GLaDOS: {settings.llm.glados.user_name}")

@app.command()
def modules():
    """
    Lista todos os módulos disponíveis
    """
    console.print(Panel.fit("📦 Módulos do GLaDOS Planner", border_style="cyan"))
    
    # Lista de módulos principais
    core_modules = [
        ("🤖 Cérebro GLaDOS", "Sistema de IA com personalidade GLaDOS", "glados"),
        ("📚 Gerenciador de Leituras", "Acompanha progresso de leituras", "data leituras"),
        ("📅 Agenda Acadêmica", "Gerencia prazos e eventos", "data agenda"),
        ("🌐 Tradutor Filosófico", "Traduz termos filosóficos", "data traduzir"),
        ("⏱️  Pomodoro Timer", "Técnica Pomodoro para estudos", "data pomodoro"),
        ("✍️  Assistente de Escrita", "Auxilia na escrita acadêmica", "data escrever"),
        ("🔄 Sistema de Revisão", "Revisão espaçada com flashcards", "data revisar"),
        ("🔄 Sincronização", "Sincroniza com vault do Obsidian", "data sincronizar")
    ]
    
    for name, description, command in core_modules:
        console.print(f"[bold]{name}[/bold]")
        console.print(f"  {description}")
        console.print(f"  [dim]Comando: {command}[/dim]\n")
    
    # Verificar disponibilidade
    console.print("[bold]Disponibilidade:[/bold]")
    if HAS_GLADOS:
        console.print("  ✅ Módulo GLaDOS disponível")
    else:
        console.print("  ❌ Módulo GLaDOS não encontrado")
    
    if HAS_DATA_COMMANDS:
        console.print("  ✅ Módulos de dados disponíveis")
    else:
        console.print("  ❌ Módulos de dados não encontrados")

@app.command()
def setup_vault(
    vault_path: str = typer.Option(..., "--path", "-p", help="Caminho para o vault do Obsidian"),
    template: str = typer.Option("default", "--template", "-t", help="Template a usar"),
):
    """
    Configura um novo vault do Obsidian
    """
    console.print(Panel.fit("⚙️ Configurando vault do Obsidian", border_style="blue"))
    
    try:
        vault_manager = VaultManager(vault_path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task1 = progress.add_task("[cyan]Criando estrutura...", total=None)
            result = vault_manager.create_structure()
            progress.update(task1, completed=True)
            
            task2 = progress.add_task("[cyan]Aplicando template...", total=None)
            # Aqui poderíamos aplicar templates específicos
            progress.update(task2, completed=True)
        
        if result:
            console.print(f"[green]✅ Vault configurado em: {vault_path}[/green]")
            console.print("\n[bold]Estrutura criada:[/bold]")
            for folder in vault_manager.expected_folders:
                console.print(f"  📁 {folder}")
        else:
            console.print("[yellow]⚠️  Vault já existe ou houve erro na criação[/yellow]")
    
    except Exception as e:
        console.print(f"[red]❌ Erro ao configurar vault: {e}[/red]")

@app.command()
def backup(
    output_path: str = typer.Option(None, "--output", "-o", help="Caminho para backup"),
    include_database: bool = typer.Option(True, "--db/--no-db", help="Incluir banco de dados"),
):
    """
    Cria backup do sistema
    """
    from datetime import datetime
    import shutil
    from pathlib import Path
    
    console.print(Panel.fit("💾 Criando backup do sistema", border_style="yellow"))
    
    # Define caminho padrão para backup
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"./backups/glados_backup_{timestamp}"
    
    backup_dir = Path(output_path)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Criando backup...", total=100)
        
        # Backup do vault
        try:
            from src.core.config.settings import settings
            vault_path = Path(settings.paths.vault).expanduser()
            if vault_path.exists():
                vault_backup = backup_dir / "vault"
                progress.update(task, advance=30, description="[cyan]Copiando vault...")
                shutil.copytree(vault_path, vault_backup)
            else:
                console.print("[yellow]⚠️  Vault não encontrado, pulando...[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Erro ao copiar vault: {e}[/yellow]")
        
        # Backup do banco de dados
        if include_database:
            try:
                db_path = Path("data/database/philosophy.db")
                if db_path.exists():
                    db_backup = backup_dir / "database"
                    db_backup.mkdir(exist_ok=True)
                    progress.update(task, advance=30, description="[cyan]Copiando banco de dados...")
                    shutil.copy2(db_path, db_backup / "philosophy.db")
            except Exception as e:
                console.print(f"[yellow]⚠️  Erro ao copiar banco de dados: {e}[/yellow]")
        
        # Backup das configurações
        try:
            config_backup = backup_dir / "config"
            config_backup.mkdir(exist_ok=True)
            progress.update(task, advance=20, description="[cyan]Copiando configurações...")
            shutil.copytree("config", config_backup, dirs_exist_ok=True)
        except Exception as e:
            console.print(f"[yellow]⚠️  Erro ao copiar configurações: {e}[/yellow]")
        
        # Criar arquivo de metadados
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "version": "0.4.0",
            "components": ["vault", "database", "config"],
            "notes": "Backup automático do GLaDOS Planner"
        }
        
        import json
        with open(backup_dir / "backup_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        progress.update(task, advance=20, description="[green]Backup concluído!")
    
    console.print(f"[green]✅ Backup criado em: {output_path}[/green]")
    console.print(f"[dim]Tamanho total: {sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file()) / (1024*1024):.2f} MB[/dim]")

if __name__ == "__main__":
    app()
