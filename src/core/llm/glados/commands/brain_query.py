"""
Comandos CLI para interagir com o cérebro da GLaDOS
"""
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.markdown import Markdown
import time
from typing import Optional

from src.core.llm.glados.brain.vault_connector import VaultStructure
from src.core.llm.glados.personality.glados_voice import GladosVoice
from src.core.llm.glados.models.tinyllama_wrapper import TinyLlamaGlados, LlamaConfig

app = typer.Typer(name="glados", help="Sistema GLaDOS - Cérebro Filosófico")
console = Console()

def _get_glados_system():
    """Inicializa o sistema GLaDOS"""
    from src.core.config.settings import settings
    
    # Configurações
    vault = VaultStructure(settings.paths.vault)
    
    glados_voice = GladosVoice(
        user_name=settings.llm.glados.user_name,
        intensity=settings.llm.glados.personality_intensity
    )
    
    llama_config = LlamaConfig(
        model_path=settings.llm.model_path,
        n_ctx=settings.llm.n_ctx,
        n_gpu_layers=settings.llm.n_gpu_layers,
        temperature=settings.llm.temperature,
        top_p=settings.llm.top_p,
        repeat_penalty=settings.llm.repeat_penalty,
        max_tokens=settings.llm.max_tokens,
        n_threads=settings.llm.cpu.threads
    )
    
    llm = TinyLlamaGlados(llama_config, vault, glados_voice)
    
    return {
        "vault": vault,
        "voice": glados_voice,
        "llm": llm,
        "settings": settings
    }

@app.command(name="consultar")
def consultar_cerebro(
    pergunta: str = typer.Argument(..., help="Pergunta para o cérebro de GLaDOS"),
    area: Optional[str] = typer.Option(None, "--area", "-a", help="Área específica (conceitos, leituras, etc)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mostrar detalhes do processo"),
    raw: bool = typer.Option(False, "--raw", help="Mostrar resposta sem formatação Rich")
):
    """
    Consulta o cérebro de GLaDOS (vault do Obsidian)
    """
    system = _get_glados_system()
    
    # Cabeçalho
    if not raw:
        console.print(Panel.fit(
            f"[bold magenta]GLaDOS[/bold magenta] - Consulta Cerebral\n"
            f"[dim]Usuário: {system['settings'].llm.glados.user_name} | "
            f"Vault: {system['settings'].paths.vault}[/dim]",
            border_style="magenta"
        ))
    
    # Processamento com barra de progresso
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
        disable=raw
    ) as progress:
        
        task1 = progress.add_task("[cyan]Ativando neurônios...", total=100)
        for i in range(10):
            progress.update(task1, advance=10)
            time.sleep(0.05)
        
        task2 = progress.add_task("[cyan]Consultando memórias...", total=100)
        vault_stats = system['vault'].get_vault_stats()
        for i in range(10):
            progress.update(task2, advance=10)
            time.sleep(0.05)
        
        task3 = progress.add_task("[cyan]Processando com TinyLlama...", total=100)
        resposta = system['llm'].generate_response(pergunta, system['settings'].llm.glados.user_name)
        for i in range(10):
            progress.update(task3, advance=10)
            time.sleep(0.1)
    
    # Mostra resultados
    if verbose:
        console.print("\n[bold]Estatísticas do Vault:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Pasta", style="cyan")
        table.add_column("Notas", justify="right")
        table.add_column("Função Cerebral", style="green")
        
        for folder, count in vault_stats["notes_by_folder"].items():
            brain_region = system['settings'].obsidian.brain_regions.get(folder, "desconhecida")
            table.add_row(folder, str(count), brain_region.replace("_", " ").title())
        
        console.print(table)
        
        # Estatísticas do LLM
        llm_stats = system['llm'].get_stats()
        console.print(f"\n[bold]Estatísticas GLaDOS:[/bold]")
        console.print(f"• Modelo carregado: {'✅' if llm_stats['model_loaded'] else '❌'}")
        console.print(f"• Taxa de cache: {llm_stats['cache_hit_rate']:.1%}")
        console.print(f"• Tamanho do cache: {llm_stats['cache_size']} respostas")
    
    # Resposta final
    if raw:
        console.print(resposta)
    else:
        console.print(Panel.fit(
            Markdown(resposta),
            title="[bold magenta]Resposta de GLaDOS[/bold magenta]",
            border_style="magenta",
            padding=(1, 2)
        ))
        
        # Rodapé
        console.print(f"\n[dim]Consulta processada. Memórias ativadas: {vault_stats['total_notes']}[/dim]")

@app.command(name="estrutura")
def mostrar_estrutura(
    detalhado: bool = typer.Option(False, "--detalhado", "-d", help="Mostrar estrutura detalhada")
):
    """Mostra a estrutura do cérebro (vault) de GLaDOS"""
    system = _get_glados_system()
    vault_stats = system['vault'].get_vault_stats()
    
    console.print(Panel.fit(
        "[bold magenta]Estrutura do Cérebro de GLaDOS[/bold magenta]\n"
        f"[dim]Vault: {system['settings'].paths.vault}[/dim]",
        border_style="magenta"
    ))
    
    if detalhado:
        # Estrutura detalhada
        for folder, description in system['vault'].STRUCTURE.items():
            notes = system['vault'].get_notes_by_folder(folder)
            brain_region = system['settings'].obsidian.brain_regions.get(folder, "desconhecida")
            
            console.print(f"\n[bold cyan]{folder}[/bold cyan] - {description}")
            console.print(f"  [dim]Função cerebral: {brain_region.replace('_', ' ').title()}[/dim]")
            console.print(f"  [dim]Notas: {len(notes)}[/dim]")
            
            # Mostra algumas notas de exemplo
            if notes and len(notes) > 0:
                for note in notes[:3]:
                    console.print(f"    • {note.title}")
                if len(notes) > 3:
                    console.print(f"    [dim]... e mais {len(notes) - 3} notas[/dim]")
    else:
        # Visão geral
        table = Table(title="Estrutura do Vault", show_header=True, header_style="bold magenta")
        table.add_column("Pasta", style="cyan")
        table.add_column("Descrição", style="white")
        table.add_column("Notas", justify="right")
        table.add_column("Função Cerebral", style="green")
        
        for folder, description in system['vault'].STRUCTURE.items():
            notes_count = vault_stats["notes_by_folder"].get(folder, 0)
            brain_region = system['settings'].obsidian.brain_regions.get(folder, "desconhecida")
            table.add_row(folder, description, str(notes_count), brain_region.replace("_", " ").title())
        
        console.print(table)
    
    console.print(f"\n[dim]Total de memórias: {vault_stats['total_notes']} notas[/dim]")

@app.command(name="chamar")
def chamar_glados():
    """Chama GLaDOS pelo nome"""
    system = _get_glados_system()
    resposta = system['voice'].respond_to_name()
    
    console.print(Panel.fit(
        resposta,
        title="[bold magenta]GLaDOS[/bold magenta]",
        border_style="magenta"
    ))

@app.command(name="estatisticas")
def mostrar_estatisticas():
    """Mostra estatísticas do sistema GLaDOS"""
    system = _get_glados_system()
    
    # Estatísticas do vault
    vault_stats = system['vault'].get_vault_stats()
    
    # Estatísticas do LLM
    llm_stats = system['llm'].get_stats()
    
    console.print(Panel.fit(
        "[bold magenta]Estatísticas do Sistema GLaDOS[/bold magenta]",
        border_style="magenta"
    ))
    
    console.print("\n[bold]📊 Cérebro (Vault):[/bold]")
    console.print(f"  • Total de memórias: {vault_stats['total_notes']} notas")
    console.print(f"  • Estrutura validada: {'✅' if system['vault']._validate_structure() else '❌'}")
    
    console.print("\n[bold]🤖 Inteligência (LLM):[/bold]")
    console.print(f"  • Modelo: {llm_stats['config']['model']}")
    console.print(f"  • Carregado: {'✅' if llm_stats['model_loaded'] else '❌ (modo simulado)'}")
    console.print(f"  • Contexto: {llm_stats['config']['context_size']} tokens")
    console.print(f"  • Cache: {llm_stats['cache_size']} respostas")
    console.print(f"  • Taxa de acerto no cache: {llm_stats['cache_hit_rate']:.1%}")
    
    console.print("\n[bold]👤 Personalidade:[/bold]")
    console.print(f"  • Usuário: {system['settings'].llm.glados.user_name}")
    console.print(f"  • Intensidade: {system['settings'].llm.glados.personality_intensity}")
    console.print(f"  • Interações: {system['voice'].user_context.interaction_count}")
    
    console.print("\n[dim]Sistema GLaDOS operacional. Pronto para consultas filosóficas.[/dim]")

@app.command(name="buscar")
def buscar_no_vault(
    termo: str = typer.Argument(..., help="Termo para buscar no vault"),
    limite: int = typer.Option(10, "--limite", "-l", help="Número máximo de resultados")
):
    """Busca direta no vault do Obsidian"""
    system = _get_glados_system()
    
    console.print(f"[bold]Buscando '{termo}' no cérebro de GLaDOS...[/bold]\n")
    
    results = system['vault'].search_notes(termo, limit=limite)
    
    if not results:
        console.print("[yellow]Nenhuma nota encontrada.[/yellow]")
        return
    
    table = Table(title=f"Resultados para '{termo}'", show_header=True, header_style="bold cyan")
    table.add_column("Nota", style="green")
    table.add_column("Pasta", style="cyan")
    table.add_column("Tags", style="yellow")
    table.add_column("Tamanho", justify="right")
    
    for note in results:
        relative_path = note.path.relative_to(system['vault'].vault_path)
        folder = str(relative_path).split('/')[0] if '/' in str(relative_path) else "raiz"
        tags = ", ".join(note.tags[:3]) if note.tags else ""
        if len(note.tags) > 3:
            tags += "..."
        
        size = f"{len(note.content)} chars"
        
        table.add_row(note.title, folder, tags, size)
    
    console.print(table)
    console.print(f"\n[dim]Encontradas {len(results)} notas.[/dim]")

@app.command(name="diagnostico")
def diagnostico_sistema():
    """Faz diagnóstico completo do sistema GLaDOS"""
    from pathlib import Path
    
    system = _get_glados_system()
    settings = system['settings']
    
    console.print(Panel.fit(
        "[bold red]DIAGNÓSTICO DO SISTEMA GLaDOS[/bold red]",
        border_style="red"
    ))
    
    checks = []
    
    # 1. Verifica vault
    vault_path = Path(settings.paths.vault).expanduser()
    if vault_path.exists():
        checks.append(("✅", "Vault encontrado", str(vault_path)))
    else:
        checks.append(("❌", "Vault NÃO encontrado", str(vault_path)))
    
    # 2. Verifica modelo
    model_path = Path(settings.llm.model_path)
    if model_path.exists():
        checks.append(("✅", "Modelo encontrado", model_path.name))
    else:
        checks.append(("❌", "Modelo NÃO encontrado", str(model_path)))
    
    # 3. Verifica estrutura do vault
    structure_ok = system['vault']._validate_structure()
    checks.append(("✅" if structure_ok else "⚠️", 
                  "Estrutura do vault", 
                  "Válida" if structure_ok else "Incompleta"))
    
    # 4. Verifica LLM
    llm_loaded = system['llm'].llm is not None
    checks.append(("✅" if llm_loaded else "⚠️", 
                  "Modelo LLM", 
                  "Carregado" if llm_loaded else "Modo simulado"))
    
    # 5. Verifica cache
    cache_dir = Path(settings.paths.cache_dir)
    if cache_dir.exists():
        checks.append(("✅", "Diretório de cache", "OK"))
    else:
        checks.append(("⚠️", "Diretório de cache", "Não existe"))
    
    # Mostra resultados
    console.print("\n[bold]Verificações do Sistema:[/bold]")
    for icon, check, detail in checks:
        console.print(f"  {icon} {check}: [dim]{detail}[/dim]")
    
    # Estatísticas
    vault_stats = system['vault'].get_vault_stats()
    console.print(f"\n[bold]Estatísticas:[/bold]")
    console.print(f"  • Notas no vault: {vault_stats['total_notes']}")
    console.print(f"  • Interações GLaDOS: {system['voice'].user_context.interaction_count}")
    
    # Recomendações
    console.print("\n[bold]Recomendações:[/bold]")
    if not llm_loaded:
        console.print("  • Instale llama-cpp-python: pip install llama-cpp-python")
    if not structure_ok:
        console.print("  • Verifique a estrutura do vault na documentação")
    if vault_stats['total_notes'] == 0:
        console.print("  • Adicione notas ao vault para melhorar as consultas")
    
    console.print("\n[green]Diagnóstico completo. Sistema GLaDOS pronto.[/green]")
