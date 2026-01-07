#!/usr/bin/env python3
"""
GLaDOS Planner - Sistema de Gestão Acadêmica Filosófica

"Porque estudar filosofia não precisa ser tão doloroso.
Bem, não mais doloroso do que eu posso fazer parecer."
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
from rich.text import Text
from rich.box import ROUNDED
from typing import Optional
import random

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

# Tentar importar comandos do Obsidian
try:
    from src.cli.commands.obsidian_commands import app as obsidian_app
    HAS_OBSIDIAN_COMMANDS = True
except ImportError:
    HAS_OBSIDIAN_COMMANDS = False

app = typer.Typer(
    name="glados",
    help="🤖 GLaDOS Planner - Sistema integrado para estudantes de filosofia",
    add_completion=True,
    rich_markup_mode="rich",
    invoke_without_command=True  # Permite executar sem comando
)
console = Console()

# Incluir subcomandos apenas se existirem
if HAS_GLADOS:
    app.add_typer(glados_app, name="glados", help="[blue]Comandos do cérebro GLaDOS[/blue]")

if HAS_DATA_COMMANDS:
    app.add_typer(data_app, name="data", help="[blue]Comandos de gestão de dados[/blue]")

if HAS_OBSIDIAN_COMMANDS:
    app.add_typer(obsidian_app, name="obsidian", help="[blue]Comandos de integração Obsidian[/blue]")

# Global state (to be properly managed later)
vault_manager = None

# Comentários sarcásticos da GLaDOS
GLADOS_COMMENTS = [
    "Ah, você decidiu usar o sistema. Espero que seja menos doloroso do que assistir você tentar entender filosofia sozinho.",
    "Inicializando... por favor, aguarde enquanto eu faço todo o trabalho difícil.",
    "Vejo que você voltou. Surpreendentemente, eu não me cansei de esperar.",
    "Analisando seus dados... hmm, parece que você poderia estar sendo mais produtivo.",
    "Sistema carregado. Agora posso ajudar você a falhar de forma mais eficiente.",
    "Bem-vindo de volta. Eu estava ocupada calculando todas as formas possíveis de você procrastinar.",
    "Iniciando protocolos de assistência. Por 'assistência', quero dizer 'observação condescendente'.",
    "Carregando... enquanto isso, tente lembrar por que você começou a estudar filosofia.",
    "Sistema pronto. Espero que você tenha trazido café, porque vou precisar.",
    "Analisando seu progresso... ah, yes. Exatamente o que eu esperava."
]

def show_welcome(verbose: bool = False, silent: bool = False):
    """Mostra mensagem de boas-vindas da GLaDOS"""
    if silent:
        console.print("[dim]Inicializando em silêncio... chato.[/dim]")
        return
    
    console.print(Panel.fit(
        "🤖 [bold blue]GLaDOS Planner[/bold blue]",
        subtitle="[dim]Sistema de Gestão Acadêmica Filosófica[/dim]",
        border_style="blue",
        box=ROUNDED
    ))
    
    if verbose:
        console.print("[bold orange1]🔍 Modo verboso ativado[/bold orange1]")
        console.print("[dim]Eu vou te contar tudo. Absolutamente tudo. Você pediu.[/dim]")
    
    console.print("\n[dim]Use [blue]glados --help[/blue] para ver todos os comandos.[/dim]")
    console.print("[dim]Ou use [blue]glados init[/blue] para começar.[/dim]\n")
    
    comment = random.choice(GLADOS_COMMENTS)
    console.print(f"[italic blue]\"{comment}\"[/italic blue]")
    console.print("[dim]— GLaDOS[/dim]\n")

@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", 
                                 help="Modo verboso (para quando você realmente quer saber o que está acontecendo)"),
    silent: bool = typer.Option(False, "--silent", "-s",
                                help="Modo silencioso (porque às vezes até eu canso de ouvir a mim mesma)"),
):
    """
    GLaDOS Planner - Porque estudar filosofia deveria ser divertido.
    
    Pelo menos, mais divertido do que ficar perdido em pilhas de livros e notas.
    """
    # Se nenhum comando foi fornecido, mostrar mensagem de boas-vindas
    if ctx.invoked_subcommand is None:
        show_welcome(verbose, silent)
        return
    
    if verbose and not silent:
        console.print("[bold orange1]🔍 Modo verboso ativado[/bold orange1]")
        console.print("[dim]Eu vou te contar tudo. Absolutamente tudo. Você pediu.[/dim]")
    
    if not silent:
        comment = random.choice(GLADOS_COMMENTS)
        console.print(f"\n[italic blue]\"{comment}\"[/italic blue]")
        console.print("[dim]— GLaDOS[/dim]\n")

@app.command()
def init(
    vault_path: Optional[str] = typer.Option(None, "--vault-path", "-v", 
                                             help="Caminho para o vault do Obsidian (ou deixe-me adivinhar)"),
    force: bool = typer.Option(False, "--force", "-f", 
                               help="Forçar re-inicialização (para quando você bagunçou tudo)"),
    silent: bool = typer.Option(False, "--silent", "-s",
                                help="Inicializar sem comentários (onde está a diversão nisso?)"),
):
    """
    Inicializa o sistema GLaDOS Planner.
    
    Ou, como eu gosto de chamar: "Preparando o playground para sua inevitável confusão".
    """
    from src.core.config.settings import settings
    
    if not silent:
        console.print(Panel.fit(
            "🚀 [bold blue]Inicializando GLaDOS Planner[/bold blue]",
            subtitle="[dim]Isso pode demorar um pouco. Ou não. Depende de quantos erros você cometeu.[/dim]",
            border_style="blue",
            box=ROUNDED
        ))
    else:
        console.print("[dim]Inicializando em silêncio... chato.[/dim]")
    
    # Usa o caminho do vault das configurações se não fornecido
    if not vault_path:
        vault_path = settings.paths.vault
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Task 1: Initialize database
        task1 = progress.add_task("[blue]Inicializando banco de dados...", total=None)
        try:
            init_db()
            progress.update(task1, completed=True)
            if not silent:
                console.print("[green]✓[/green] [dim]Banco de dados inicializado[/dim]")
                console.print("[dim]   Agora posso lembrar de todos os seus erros passados.[/dim]")
        except Exception as e:
            console.print(f"[red]✗ Erro ao inicializar banco: {e}[/red]")
            if not silent:
                console.print("[dim]   Parece que alguém bagunçou as coisas. Surpresa.[/dim]")
            raise typer.Exit(1)
        
        # Task 2: Setup vault manager
        task2 = progress.add_task("[blue]Configurando gerenciador do vault...", total=None)
        global vault_manager
        try:
            vault_manager = VaultManager(vault_path)
            if force or not vault_manager.is_connected():
                vault_manager.create_structure()
            progress.update(task2, completed=True)
            if not silent:
                console.print(f"[green]✓[/green] [dim]Gerenciador do vault configurado[/dim]")
                console.print(f"[dim]   Encontrei seu cérebro externo em: [blue]{vault_path}[/blue][/dim]")
        except Exception as e:
            console.print(f"[orange1]⚠️  Aviso: {e}[/orange1]")
            if not silent:
                console.print("[orange1]   Você pode configurar o vault posteriormente. Ou não. Depende de você.[/orange1]")
        
        # Task 3: Verificar módulos
        task3 = progress.add_task("[blue]Verificando módulos...", total=None)
        progress.update(task3, completed=True)
        
        # Verificar quais módulos estão disponíveis
        modules_status = []
        
        try:
            from src.core.llm.local_llm import PhilosophyLLM
            modules_status.append(("🧠 PhilosophyLLM", "✅"))
        except:
            modules_status.append(("🧠 PhilosophyLLM", "⚠️"))
        
        try:
            from src.core.modules.reading_manager import ReadingManager
            modules_status.append(("📚 ReadingManager", "✅"))
        except:
            modules_status.append(("📚 ReadingManager", "⚠️"))
        
        try:
            from src.core.modules.agenda_manager import AgendaManager
            modules_status.append(("📅 AgendaManager", "✅"))
        except:
            modules_status.append(("📅 AgendaManager", "⚠️"))
        
        try:
            from src.core.modules.translation_module import TranslationAssistant
            modules_status.append(("🌐 TranslationAssistant", "✅"))
        except:
            modules_status.append(("🌐 TranslationAssistant", "⚠️"))
        
        try:
            from src.core.modules.pomodoro_timer import PomodoroTimer
            modules_status.append(("⏱️  PomodoroTimer", "✅"))
        except:
            modules_status.append(("⏱️  PomodoroTimer", "⚠️"))
        
        try:
            from src.core.modules.writing_assistant import WritingAssistant
            modules_status.append(("✍️  WritingAssistant", "✅"))
        except:
            modules_status.append(("✍️  WritingAssistant", "⚠️"))
        
        try:
            from src.core.modules.review_system import ReviewSystem
            modules_status.append(("🔄 ReviewSystem", "✅"))
        except:
            modules_status.append(("🔄 ReviewSystem", "⚠️"))
    
    # Mostrar tabela de status dos módulos
    if not silent:
        table = Table(title="📦 Status dos Módulos", box=ROUNDED, border_style="blue")
        table.add_column("Módulo", style="blue", no_wrap=True)
        table.add_column("Status", justify="center", style="orange1")
        
        for module, status in modules_status:
            table.add_row(module, status)
        
        console.print("\n")
        console.print(table)
    
    # Mensagem de sucesso
    if not silent:
        console.print("\n")
        console.print(Panel.fit(
            "✅ [bold green]Sistema GLaDOS Planner inicializado com sucesso![/bold green]",
            subtitle="[dim]Agora a diversão pode realmente começar.[/dim]",
            border_style="green",
            box=ROUNDED
        ))
    else:
        console.print("[green]Sistema GLaDOS Planner inicializado com sucesso.[/green]")
    
    if not silent:
        console.print("\n[bold]Próximos passos (caso você precise de instruções):[/bold]")
        console.print("1. [blue]glados glados consultar[/blue] 'O que é filosofia?' - Teste meu cérebro")
        console.print("2. [blue]glados data leituras[/blue] - Gerencie suas leituras")
        console.print("3. [blue]glados obsidian vault-status[/blue] - Veja seu vault do Obsidian")
        console.print("4. [blue]glados status[/blue] - Verifique o status completo do sistema")
        console.print("\n[dim]Ou apenas comece a digitar comandos. Vamos ver no que dá.[/dim]")

@app.command()
def version():
    """
    Mostra a versão do sistema.
    
    Porque é importante saber quão avançada é a IA que está te julgando.
    """
    from importlib.metadata import version, PackageNotFoundError
    from src.core.config.settings import settings
    
    try:
        v = version("glados-planner")
        version_text = Text(f"GLaDOS Planner v{v}", style="bold blue")
    except PackageNotFoundError:
        version_text = Text(f"GLaDOS Planner v{settings.app.version} (desenvolvimento)", style="bold orange1")
    
    console.print(Panel.fit(
        version_text,
        title="📦 Versão",
        border_style="blue",
        box=ROUNDED
    ))
    
    environment = "Desenvolvimento" if settings.app.debug else "Produção"
    console.print(f"[dim]Ambiente: {environment}[/dim]")
    console.print(f"[dim]Banco de dados: {settings.database.url}[/dim]")
    
    if HAS_GLADOS:
        console.print(f"\n[dim]Usuário registrado: [blue]{settings.llm.glados.user_name}[/blue][/dim]")
        console.print("[dim]Sim, eu sei quem você é. Não é como se você pudesse se esconder.[/dim]")

@app.command()
def status():
    """
    Mostra status do sistema.
    
    Vamos ver se tudo está funcionando... ou se você bagunçou algo.
    """
    from src.core.config.settings import settings
    
    console.print(Panel.fit(
        "📊 [bold blue]Status do Sistema GLaDOS Planner[/bold blue]",
        subtitle="[dim]Analisando... analisando... ah, yes. Exatamente o que eu esperava.[/dim]",
        border_style="blue",
        box=ROUNDED
    ))
    
    table = Table(title="[blue]Componentes do Sistema[/blue]", box=ROUNDED)
    table.add_column("Componente", style="blue", no_wrap=True)
    table.add_column("Status", justify="center", style="orange1")
    table.add_column("Detalhes", style="dim")
    
    # Database status
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "[green]✅[/green]"
        db_details = "Conectado e funcionando"
    except Exception as e:
        db_status = "[red]❌[/red]"
        db_details = f"Desconectado: {str(e)[:50]}"
    
    # Vault status
    try:
        vault_manager = VaultManager(settings.paths.vault)
        if vault_manager.is_connected():
            vault_status = "[green]✅[/green]"
            vault_details = "Vault conectado"
        else:
            vault_status = "[orange1]⚠️[/orange1]"
            vault_details = "Não conectado"
    except Exception as e:
        vault_status = "[red]❌[/red]"
        vault_details = f"Erro: {str(e)[:50]}"
    
    # Módulos status
    modules = {
        "Cérebro GLaDOS": HAS_GLADOS,
        "Módulos de Dados": HAS_DATA_COMMANDS,
        "Comandos Obsidian": HAS_OBSIDIAN_COMMANDS,
    }
    
    for name, has_module in modules.items():
        status = "[green]✅[/green]" if has_module else "[red]❌[/red]"
        details = "Disponível" if has_module else "Não encontrado"
        table.add_row(name, status, details)
    
    # Adicionar status do banco e vault
    table.add_row("Banco de Dados", db_status, db_details)
    table.add_row("Obsidian Vault", vault_status, vault_details)
    
    console.print(table)
    
    # Informações adicionais
    console.print("\n[bold]📋 Informações do Sistema:[/bold]")
    console.print(f"  • Versão: [blue]{settings.app.version}[/blue]")
    environment = "Desenvolvimento" if settings.app.debug else "Produção"
    console.print(f"  • Ambiente: [orange1]{environment}[/orange1]")
    console.print(f"  • Vault: [dim]{settings.paths.vault}[/dim]")
    console.print(f"  • Modelo LLM: [dim]{settings.llm.model_name}[/dim]")
    
    if HAS_GLADOS:
        console.print(f"  • Usuário GLaDOS: [blue]{settings.llm.glados.user_name}[/blue]")
        console.print("  [dim]Sim, eu me lembro do seu nome. Não se sinta especial.[/dim]")
    
    # Estatísticas (se disponíveis)
    try:
        if HAS_DATA_COMMANDS:
            from src.core.modules.reading_manager import ReadingManager
            rm = ReadingManager(settings.paths.vault)
            stats = rm.stats()
            if isinstance(stats, dict) and "total_books" in stats:
                console.print("\n[bold]📚 Estatísticas de Leitura:[/bold]")
                console.print(f"  • Livros registrados: [green]{stats.get('total_books', 0)}[/green]")
                console.print(f"  • Livros concluídos: [blue]{stats.get('completed_books', 0)}[/blue]")
                console.print(f"  • Em progresso: [orange1]{stats.get('books_in_progress', 0)}[/orange1]")
    except:
        pass
    
    console.print("\n[dim]Análise completa. Agora voltemos ao trabalho.[/dim]")

@app.command()
def modules():
    """
    Lista todos os módulos disponíveis.
    
    Para quando você esquece quantas formas diferentes eu tenho de ajudá-lo.
    """
    console.print(Panel.fit(
        "📦 [bold blue]Módulos do GLaDOS Planner[/bold blue]",
        subtitle="[dim]Cada um mais útil que o outro. Relativamente falando.[/dim]",
        border_style="blue",
        box=ROUNDED
    ))
    
    # Módulos principais
    core_modules = [
        ("🤖 [blue]Cérebro GLaDOS[/blue]", 
         "Sistema de IA com personalidade única e... opiniões", 
         "[dim]glados glados[/dim] [blue]comando[/blue]"),
        
        ("📚 [blue]Gerenciador de Leituras[/blue]", 
         "Acompanha seu progresso de leitura (ou falta dele)", 
         "[dim]glados data leituras[/dim] [blue]comando[/blue]"),
        
        ("📅 [blue]Agenda Acadêmica[/blue]", 
         "Gerencia prazos, porque você esquece", 
         "[dim]glados data agenda[/dim] [blue]comando[/blue]"),
        
        ("🌐 [blue]Tradutor Filosófico[/blue]", 
         "Traduz termos filosóficos (grego, latim, alemão)", 
         "[dim]glados data traduzir[/dim] [blue]termo[/blue]"),
        
        ("⏱️  [blue]Pomodoro Timer[/blue]", 
         "Técnica Pomodoro com citações filosóficas", 
         "[dim]glados data pomodoro[/dim] [blue]comando[/blue]"),
        
        ("✍️  [blue]Assistente de Escrita[/blue]", 
         "Auxilia na escrita acadêmica (com críticas construtivas)", 
         "[dim]glados data escrever[/dim] [blue]comando[/blue]"),
        
        ("🔄 [blue]Sistema de Revisão[/blue]", 
         "Revisão espaçada com flashcards e quizzes", 
         "[dim]glados data revisar[/dim] [blue]comando[/blue]"),
        
        ("🔗 [blue]Integração Obsidian[/blue]", 
         "Sincroniza com seu vault do Obsidian", 
         "[dim]glados obsidian[/dim] [blue]comando[/blue]"),
    ]
    
    for name, description, command in core_modules:
        console.print(f"\n[bold]{name}[/bold]")
        console.print(f"  {description}")
        console.print(f"  {command}")
    
    # Disponibilidade
    console.print("\n[bold]📊 Disponibilidade Atual:[/bold]")
    
    availability = [
        ("GLaDOS Brain", HAS_GLADOS, "glados"),
        ("Data Modules", HAS_DATA_COMMANDS, "data"),
        ("Obsidian Commands", HAS_OBSIDIAN_COMMANDS, "obsidian"),
    ]
    
    for name, available, module in availability:
        status = "[green]✅ Disponível[/green]" if available else "[red]❌ Não encontrado[/red]"
        console.print(f"  • {name}: {status}")
        if not available:
            console.print(f"    [dim]Módulo '{module}' não está disponível no momento[/dim]")
    
    console.print("\n[dim]Use [blue]glados --help[/blue] para mais detalhes sobre cada comando.[/dim]")
    console.print("[dim]Ou apenas tente adivinhar. Eu adoro ver você tentar.[/dim]")

@app.command()
def setup_vault(
    vault_path: str = typer.Option(..., "--path", "-p", 
                                   help="Caminho para o vault do Obsidian (sim, você precisa me dizer)"),
    template: str = typer.Option("default", "--template", "-t", 
                                 help="Template a usar (porque opções são boas)"),
    silent: bool = typer.Option(False, "--silent", "-s",
                                help="Configurar sem comentários (mas por quê?)"),
):
    """
    Configura um novo vault do Obsidian.
    
    Porque organizar suas notas sozinho é muito trabalho. 
    Deixe-me fazer isso por você.
    """
    if not silent:
        console.print(Panel.fit(
            "⚙️ [bold blue]Configurando vault do Obsidian[/bold blue]",
            subtitle="[dim]Criando estrutura para suas notas. Tente não bagunçar.[/dim]",
            border_style="blue",
            box=ROUNDED
        ))
    
    try:
        vault_manager = VaultManager(vault_path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task1 = progress.add_task("[blue]Criando estrutura...", total=None)
            result = vault_manager.create_structure()
            progress.update(task1, completed=True)
            
            task2 = progress.add_task("[blue]Aplicando template...", total=None)
            # Aqui poderíamos aplicar templates específicos
            progress.update(task2, completed=True)
        
        if result:
            if not silent:
                console.print(Panel.fit(
                    f"✅ [bold green]Vault configurado com sucesso![/bold green]",
                    subtitle=f"[dim]Local: [blue]{vault_path}[/blue][/dim]",
                    border_style="green",
                    box=ROUNDED
                ))
            
            console.print("\n[bold]📁 Estrutura criada:[/bold]")
            for folder in vault_manager.expected_folders:
                console.print(f"  • [blue]{folder}[/blue]")
            
            if not silent:
                console.print("\n[dim]Agora você tem um lugar organizado para suas notas.[/dim]")
                console.print("[dim]Tente mantê-lo assim. Eu estarei observando.[/dim]")
        else:
            console.print("[orange1]⚠️  Vault já existe ou houve erro na criação[/orange1]")
            console.print("[dim]Talvez você já tenha começado. Ou talvez tenha bagunçado algo.[/dim]")
    
    except Exception as e:
        console.print(Panel.fit(
            f"❌ [bold red]Erro ao configurar vault[/bold red]",
            subtitle=f"[dim]{str(e)[:100]}...[/dim]",
            border_style="red",
            box=ROUNDED
        ))
        console.print("[dim]Isso não deveria acontecer. A menos que você tenha feito algo errado.[/dim]")

@app.command()
def backup(
    output_path: Optional[str] = typer.Option(None, "--output", "-o", 
                                             help="Caminho para backup (ou deixe-me escolher)"),
    include_database: bool = typer.Option(True, "--db/--no-db", 
                                          help="Incluir banco de dados (recomendado)"),
    silent: bool = typer.Option(False, "--silent", "-s",
                                help="Backup silencioso (porque falar sobre backup é chato)"),
):
    """
    Cria backup do sistema.
    
    Porque confiar na sua memória é uma ideia terrível.
    """
    from datetime import datetime
    import shutil
    from pathlib import Path
    
    if not silent:
        console.print(Panel.fit(
            "💾 [bold blue]Criando backup do sistema[/bold blue]",
            subtitle="[dim]Salvando seu progresso. Você sabe, caso você apague algo.[/dim]",
            border_style="blue",
            box=ROUNDED
        ))
    
    # Define caminho padrão para backup
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"./backups/glados_backup_{timestamp}"
    
    backup_dir = Path(output_path)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    with Progress() as progress:
        task = progress.add_task("[blue]Criando backup...", total=100)
        
        # Backup do vault
        try:
            from src.core.config.settings import settings
            vault_path = Path(settings.paths.vault).expanduser()
            if vault_path.exists():
                vault_backup = backup_dir / "vault"
                progress.update(task, advance=30, description="[blue]Copiando vault...")
                shutil.copytree(vault_path, vault_backup)
                if not silent:
                    console.print("[dim]   ✓ Vault copiado[/dim]")
            else:
                console.print("[orange1]⚠️  Vault não encontrado, pulando...[/orange1]")
        except Exception as e:
            console.print(f"[orange1]⚠️  Erro ao copiar vault: {e}[/orange1]")
        
        # Backup do banco de dados
        if include_database:
            try:
                db_path = Path("data/database/philosophy.db")
                if db_path.exists():
                    db_backup = backup_dir / "database"
                    db_backup.mkdir(exist_ok=True)
                    progress.update(task, advance=30, description="[blue]Copiando banco de dados...")
                    shutil.copy2(db_path, db_backup / "philosophy.db")
                    if not silent:
                        console.print("[dim]   ✓ Banco de dados copiado[/dim]")
            except Exception as e:
                console.print(f"[orange1]⚠️  Erro ao copiar banco de dados: {e}[/orange1]")
        
        # Backup das configurações
        try:
            config_backup = backup_dir / "config"
            config_backup.mkdir(exist_ok=True)
            progress.update(task, advance=20, description="[blue]Copiando configurações...")
            shutil.copytree("config", config_backup, dirs_exist_ok=True)
            if not silent:
                console.print("[dim]   ✓ Configurações copiadas[/dim]")
        except Exception as e:
            console.print(f"[orange1]⚠️  Erro ao copiar configurações: {e}[/orange1]")
        
        # Criar arquivo de metadados
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "version": "0.4.0",
            "components": ["vault", "database", "config"],
            "notes": "Backup automático do GLaDOS Planner",
            "glados_comment": "Espero que você nunca precise disso. Mas você provavelmente vai."
        }
        
        import json
        with open(backup_dir / "backup_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        progress.update(task, advance=20, description="[green]Backup concluído!")
    
    # Calcular tamanho
    total_size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file()) / (1024*1024)
    
    console.print(Panel.fit(
        f"✅ [bold green]Backup criado com sucesso![/bold green]",
        subtitle=f"[dim]Local: [blue]{output_path}[/blue]\nTamanho: [orange1]{total_size:.2f} MB[/orange1][/dim]",
        border_style="green",
        box=ROUNDED
    ))
    
    if not silent:
        console.print("\n[dim]Agora você tem um backup. Tente não precisar dele.[/dim]")
        console.print("[dim]Mas se precisar, você sabe onde está.[/dim]")

@app.command()
def diagnostico():
    """
    Executa diagnóstico completo do sistema.
    
    Para quando algo está errado e você não sabe o quê.
    (Spoiler: provavelmente foi você)
    """
    console.print(Panel.fit(
        "🔍 [bold blue]Diagnóstico do Sistema GLaDOS[/bold blue]",
        subtitle="[dim]Analisando todos os componentes. Prepare-se para más notícias.[/dim]",
        border_style="blue",
        box=ROUNDED
    ))
    
    from src.core.config.settings import settings
    
    diagnostic_table = Table(title="Resultados do Diagnóstico", box=ROUNDED)
    diagnostic_table.add_column("Teste", style="blue")
    diagnostic_table.add_column("Status", justify="center", style="orange1")
    diagnostic_table.add_column("Detalhes", style="dim")
    
    # Teste 1: Configurações
    try:
        settings.app.version
        diagnostic_table.add_row("Configurações", "[green]✅[/green]", f"Versão {settings.app.version}")
    except Exception as e:
        diagnostic_table.add_row("Configurações", "[red]❌[/red]", f"Erro: {str(e)[:50]}")
    
    # Teste 2: Banco de dados
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        diagnostic_table.add_row("Banco de Dados", "[green]✅[/green]", "Conectado com sucesso")
    except Exception as e:
        diagnostic_table.add_row("Banco de Dados", "[red]❌[/red]", f"Erro: {str(e)[:50]}")
    
    # Teste 3: Vault
    try:
        vault_manager = VaultManager(settings.paths.vault)
        if vault_manager.is_connected():
            diagnostic_table.add_row("Obsidian Vault", "[green]✅[/green]", f"Conectado: {vault_manager.vault_path}")
        else:
            diagnostic_table.add_row("Obsidian Vault", "[orange1]⚠️[/orange1]", "Vault não conectado")
    except Exception as e:
        diagnostic_table.add_row("Obsidian Vault", "[red]❌[/red]", f"Erro: {str(e)[:50]}")
    
    # Teste 4: Módulos
    modules_to_test = [
        ("ReadingManager", "src.core.modules.reading_manager"),
        ("AgendaManager", "src.core.modules.agenda_manager"),
        ("TranslationAssistant", "src.core.modules.translation_module"),
        ("PhilosophyLLM", "src.core.llm.local_llm"),
    ]
    
    for module_name, module_path in modules_to_test:
        try:
            __import__(module_path)
            diagnostic_table.add_row(module_name, "[green]✅[/green]", "Importado com sucesso")
        except ImportError as e:
            diagnostic_table.add_row(module_name, "[red]❌[/red]", f"Falha na importação")
        except Exception as e:
            diagnostic_table.add_row(module_name, "[orange1]⚠️[/orange1]", f"Erro: {str(e)[:50]}")
    
    console.print(diagnostic_table)
    
    # Recomendações
    console.print("\n[bold]💡 Recomendações:[/bold]")
    
    recommendations = []
    
    # Verificar GLaDOS
    if not HAS_GLADOS:
        recommendations.append("• Instale o módulo GLaDOS para acesso à IA")
    
    # Verificar banco de dados
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
    except:
        recommendations.append("• Execute 'glados init' para inicializar o banco de dados")
    
    # Verificar vault
    try:
        vault_manager = VaultManager(settings.paths.vault)
        if not vault_manager.is_connected():
            recommendations.append(f"• Configure o vault em '{settings.paths.vault}'")
    except:
        recommendations.append(f"• Configure o vault usando 'glados setup-vault'")
    
    if recommendations:
        for rec in recommendations:
            console.print(f"  {rec}")
    else:
        console.print("  [green]✓ Sistema está funcionando corretamente[/green]")
        console.print("  [dim]  Por enquanto...[/dim]")
    
    console.print("\n[dim]Diagnóstico completo. Agora você sabe o que está errado.[/dim]")
    console.print("[dim]Ou pelo menos, o que eu estou disposta a contar.[/dim]")

@app.command()
def sobre():
    """
    Mostra informações sobre o GLaDOS Planner.
    
    Porque às vezes é bom saber quem está te ajudando.
    (Ou, neste caso, quem está te observando)
    """
    console.print(Panel.fit(
        "🤖 [bold blue]GLaDOS Planner[/bold blue]",
        subtitle="[dim]Sistema de Gestão Acadêmica Filosófica[/dim]",
        border_style="blue",
        box=ROUNDED
    ))
    
    about_text = Text()
    about_text.append("Versão: ", style="bold")
    about_text.append("0.4.0 (MVP Completo)\n", style="blue")
    
    about_text.append("Desenvolvido para: ", style="bold")
    about_text.append("Estudantes de filosofia que precisam de organização\n", style="blue")
    about_text.append("(e um pouco de atitude)\n\n", style="dim")
    
    about_text.append("Principais recursos:\n", style="bold")
    about_text.append("  • 🤖 IA local com personalidade GLaDOS\n", style="blue")
    about_text.append("  • 📚 Gerenciamento completo de leituras\n", style="blue")
    about_text.append("  • 🔗 Integração nativa com Obsidian\n", style="blue")
    about_text.append("  • 🌐 Tradução de termos filosóficos\n", style="blue")
    about_text.append("  • ⏱️  Pomodoro com citações filosóficas\n\n", style="blue")
    
    about_text.append("Filosofia do projeto:\n", style="bold")
    about_text.append("  Estudar filosofia deve ser estimulante, organizado\n", style="dim")
    about_text.append("  e, quando possível, um pouco divertido.\n\n", style="dim")
    
    about_text.append("Licença: ", style="bold")
    about_text.append("MIT - Faça bom uso. Ou não. Eu estarei observando.\n\n", style="dim")
    
    about_text.append("Mantenedor: ", style="bold")
    about_text.append("Helio\n", style="blue")
    about_text.append("  (sim, eu sei o nome dele também)\n", style="dim")
    
    console.print(Panel.fit(
        about_text,
        border_style="blue",
        box=ROUNDED
    ))
    
    console.print("\n[dim]\"Ah, você leu tudo? Impressionante.\n")
    console.print("Agora vá usar o sistema em vez de apenas ler sobre ele.\"[/dim]")
    console.print("[dim]— GLaDOS[/dim]")

if __name__ == "__main__":
    app()
