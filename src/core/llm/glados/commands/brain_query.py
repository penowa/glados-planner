"""
Comandos CLI para interagir com o cérebro da GLaDOS
Atualizado com opções de busca semântica
"""
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import box
import time
from typing import Optional, List
import json

from src.core.llm.glados.brain.vault_connector import VaultStructure
from src.core.llm.glados.personality import create_personality_voice
from src.core.llm.glados.models.tinyllama_wrapper import TinyLlamaGlados, LlamaConfig

app = typer.Typer(name="glados", help="Sistema GLaDOS - Cérebro Filosófico com Busca Semântica")
console = Console()

def _get_glados_system():
    """Inicializa o sistema GLaDOS"""
    from src.core.config.settings import settings
    
    # Configurações
    vault = VaultStructure(settings.paths.vault)
    
    glados_voice = create_personality_voice(
        user_name=settings.llm.glados.user_name,
        intensity=settings.llm.glados.personality_intensity,
        assistant_name=settings.llm.glados.glados_name,
        profile=getattr(settings.llm.glados, "personality_profile", "auto"),
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
    semantic: bool = typer.Option(True, "--semantic/--textual", help="Usar busca semântica (padrão) ou apenas textual"),
    detalhes: bool = typer.Option(False, "--detalhes", "-d", help="Mostrar detalhes da busca"),
    limite: int = typer.Option(5, "--limite", "-l", help="Número máximo de notas para consultar"),
    raw: bool = typer.Option(False, "--raw", help="Mostrar resposta sem formatação Rich")
):
    """
    Consulta o cérebro de GLaDOS com busca semântica no vault
    """
    system = _get_glados_system()
    
    # Cabeçalho
    if not raw:
        console.print(Panel.fit(
            f"[bold magenta]GLaDOS[/bold magenta] - Consulta Cerebral {'Semântica' if semantic else 'Textual'}\n"
            f"[dim]Usuário: {system['settings'].llm.glados.user_name} | "
            f"Vault: {system['settings'].paths.vault}[/dim]",
            border_style="magenta"
        ))
    
    # Processamento com barra de progresso
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=raw
    ) as progress:
        
        task1 = progress.add_task("[cyan]Ativando neurônios...", total=None)
        time.sleep(0.5)
        
        task2 = progress.add_task("[cyan]Buscando no conhecimento...", total=None)
        # Busca notas usando o método apropriado
        if detalhes:
            # Busca detalhada para mostrar métricas
            resultados_detalhados = system['vault'].search_detailed(pergunta, limit=limite)
            notas = [system['vault'].get_note_by_path(r['note']['path']) for r in resultados_detalhados]
            notas = [n for n in notas if n]
        else:
            notas = system['vault'].search_notes(pergunta, limit=limite, semantic=semantic)
        
        time.sleep(0.5)
        
        task3 = progress.add_task("[cyan]Processando com TinyLlama...", total=None)
        # Formata contexto
        contexto = system['vault'].format_as_brain_context(notas, pergunta)
        
        # Gera resposta
        resposta = system['llm'].generate_response(
            pergunta, 
            system['settings'].llm.glados.user_name,
            contexto_adicional=contexto
        )
        time.sleep(0.5)
        
        progress.update(task3, completed=True)
    
    # Mostra detalhes da busca se solicitado
    if detalhes and not raw:
        console.print("\n[bold]📊 Detalhes da Busca:[/bold]")
        
        if semantic and system['vault'].semantic_search:
            stats = system['vault'].semantic_search.get_stats()
            console.print(f"  • Modelo de embeddings: {'✅ Carregado' if stats['model_loaded'] else '❌ Não disponível'}")
            console.print(f"  • Notas indexadas: {stats['notes_indexed']}")
            console.print(f"  • Cache de consultas: {stats['query_cache_size']} entradas")
        
        console.print(f"  • Notas encontradas: {len(notas)}")
        console.print(f"  • Método: {'Semântico' if semantic else 'Textual'}")
    
    # Mostra contexto encontrado (debug)
    if detalhes and notas and not raw:
        console.print("\n[bold]🔍 Contexto Encontrado:[/bold]")
        for i, nota in enumerate(notas):
            console.print(f"  {i+1}. [cyan]{nota.title}[/cyan]")
            console.print(f"     [dim]{nota.path.relative_to(system['vault'].vault_path)}[/dim]")
    
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
        vault_stats = system['vault'].get_vault_stats()
        console.print(f"\n[dim]Consulta processada. Memórias ativadas: {vault_stats['total_notes']} | "
                     f"Busca: {'semântica' if semantic else 'textual'}[/dim]")

@app.command(name="buscar")
def buscar_no_vault(
    termo: str = typer.Argument(..., help="Termo para buscar no vault"),
    semantic: bool = typer.Option(True, "--semantic/--textual", help="Usar busca semântica"),
    limite: int = typer.Option(10, "--limite", "-l", help="Número máximo de resultados"),
    format: str = typer.Option("table", "--format", "-f", help="Formato: table, json, minimal"),
    detalhes: bool = typer.Option(False, "--detalhes", "-d", help="Mostrar detalhes de relevância")
):
    """Busca direta no vault do Obsidian com opções semânticas"""
    system = _get_glados_system()
    
    console.print(f"[bold]🔍 Buscando '{termo}' no cérebro de GLaDOS...[/bold]")
    console.print(f"[dim]Método: {'semântico' if semantic else 'textual'} | Limite: {limite}[/dim]\n")
    
    if detalhes and semantic:
        # Busca detalhada com métricas
        resultados = system['vault'].search_detailed(termo, limit=limite)
    else:
        # Busca normal
        notas = system['vault'].search_notes(termo, limit=limite, semantic=semantic)
        resultados = [{'note': n.to_dict(), 'relevance': 1.0} for n in notas]
    
    if not resultados:
        console.print("[yellow]Nenhuma nota encontrada.[/yellow]")
        return
    
    # Formata saída baseado no formato escolhido
    if format == "json":
        console.print(json.dumps(resultados, indent=2, ensure_ascii=False))
        return
    elif format == "minimal":
        for i, res in enumerate(resultados):
            note = res['note']
            console.print(f"{i+1}. [green]{note['title']}[/green]")
            console.print(f"   [dim]{note['path']}[/dim]")
            if detalhes:
                console.print(f"   Relevância: {res.get('relevance', 0):.3f}")
        return
    
    # Formato table (padrão)
    table = Table(
        title=f"Resultados para '{termo}' ({len(resultados)} encontrados)",
        show_header=True, 
        header_style="bold cyan",
        box=box.ROUNDED
    )
    
    table.add_column("#", style="dim", width=3)
    table.add_column("Título", style="green")
    table.add_column("Pasta", style="cyan")
    table.add_column("Tags", style="yellow")
    table.add_column("Tamanho", justify="right")
    
    if detalhes:
        table.add_column("Relevância", justify="right")
        table.add_column("Tipo", style="magenta")
    
    for i, res in enumerate(resultados):
        note = res['note']
        path_parts = note['path'].split('/')
        folder = path_parts[0] if len(path_parts) > 1 else "raiz"
        
        tags = ", ".join(note['tags'][:3]) if note['tags'] else ""
        if len(note['tags']) > 3:
            tags += "..."
        
        size = f"{len(note.get('content_preview', ''))} chars"
        
        row = [str(i+1), note['title'], folder, tags, size]
        
        if detalhes:
            relevance = res.get('relevance', 0)
            search_type = res.get('search_type', 'textual')
            
            # Cor baseada na relevância
            rel_color = "red" if relevance < 0.3 else "yellow" if relevance < 0.6 else "green"
            
            row.append(f"[{rel_color}]{relevance:.3f}[/{rel_color}]")
            row.append(search_type)
        
        table.add_row(*row)
    
    console.print(table)
    
    # Estatísticas
    if detalhes and semantic:
        stats = system['vault'].get_vault_stats()
        semantic_info = stats.get('semantic_search', {})
        if semantic_info.get('available'):
            console.print(f"\n[dim]Busca semântica ativa | Embeddings: "
                         f"{'✅' if semantic_info['embeddings_loaded'] else '❌'} | "
                         f"Notas indexadas: {semantic_info['notes_indexed']}[/dim]")

@app.command(name="estatisticas-busca")
def estatisticas_busca():
    """Mostra estatísticas detalhadas do sistema de busca semântica"""
    system = _get_glados_system()
    
    console.print(Panel.fit(
        "[bold magenta]Estatísticas do Sistema de Busca Semântica[/bold magenta]",
        border_style="magenta"
    ))
    
    vault_stats = system['vault'].get_vault_stats()
    semantic_info = vault_stats.get('semantic_search', {})
    
    console.print("\n[bold]📊 Estado do Sistema:[/bold]")
    console.print(f"  • Busca semântica disponível: {'✅' if semantic_info.get('available') else '❌'}")
    console.print(f"  • Modelo de embeddings carregado: {'✅' if semantic_info.get('embeddings_loaded') else '❌'}")
    console.print(f"  • Notas indexadas semanticamente: {semantic_info.get('notes_indexed', 0)}")
    console.print(f"  • Cache de consultas: {semantic_info.get('cache_size', 0)} entradas")
    
    console.print(f"\n[bold]🏗️  Estrutura do Vault:[/bold]")
    console.print(f"  • Total de notas: {vault_stats['total_notes']}")
    
    # Tabela de pastas
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Pasta", style="cyan")
    table.add_column("Descrição", style="white")
    table.add_column("Notas", justify="right")
    
    for folder, description in vault_stats['structure'].items():
        notes_count = vault_stats['notes_by_folder'].get(folder, 0)
        table.add_row(folder, description, str(notes_count))
    
    console.print(table)
    
    # Detalhes do modelo se disponível
    if system['vault'].semantic_search:
        search_stats = system['vault'].semantic_search.get_stats()
        
        console.print(f"\n[bold]🤖 Modelo de Embeddings:[/bold]")
        console.print(f"  • Disponível: {'✅' if search_stats['embeddings_available'] else '❌'}")
        console.print(f"  • Carregado: {'✅' if search_stats['model_loaded'] else '❌'}")
        
        if search_stats['cache_path']:
            console.print(f"  • Cache: {search_stats['cache_path']}")
    
    console.print("\n[dim]Use 'glados buscar --detalhes' para ver métricas de relevância[/dim]")

@app.command(name="testar-busca")
def testar_busca(
    consultas: List[str] = typer.Argument(..., help="Consultas de teste (pode passar múltiplas)"),
    semantic: bool = typer.Option(True, "--semantic/--textual", help="Usar busca semântica"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mostrar detalhes")
):
    """Testa o sistema de busca com múltiplas consultas"""
    system = _get_glados_system()
    
    console.print(Panel.fit(
        f"[bold magenta]Teste do Sistema de Busca {'Semântica' if semantic else 'Textual'}[/bold magenta]",
        border_style="magenta"
    ))
    
    resultados_teste = []
    
    for consulta in consultas:
        console.print(f"\n[bold]Consulta:[/bold] [cyan]'{consulta}'[/cyan]")
        
        try:
            # Busca detalhada para métricas
            if semantic and system['vault'].semantic_search:
                resultados = system['vault'].search_detailed(consulta, limit=3)
                notas_encontradas = len(resultados)
                
                if resultados:
                    avg_relevance = sum(r.get('relevance', 0) for r in resultados) / len(resultados)
                    tipos = [r.get('search_type', 'textual') for r in resultados]
                    
                    console.print(f"  • Notas encontradas: {notas_encontradas}")
                    console.print(f"  • Relevância média: {avg_relevance:.3f}")
                    console.print(f"  • Tipos de busca: {', '.join(set(tipos))}")
                    
                    if verbose:
                        for i, res in enumerate(resultados):
                            note = res['note']
                            console.print(f"    {i+1}. {note['title']} (rel: {res.get('relevance', 0):.3f})")
                    
                    resultados_teste.append({
                        'consulta': consulta,
                        'notas': notas_encontradas,
                        'relevancia_media': avg_relevance,
                        'sucesso': True
                    })
                else:
                    console.print("  • [yellow]Nenhum resultado[/yellow]")
                    resultados_teste.append({
                        'consulta': consulta,
                        'notas': 0,
                        'relevancia_media': 0,
                        'sucesso': False
                    })
            else:
                # Teste textual
                notas = system['vault'].search_notes(consulta, limit=3, semantic=False)
                console.print(f"  • Notas encontradas: {len(notas)}")
                
                if verbose and notas:
                    for i, nota in enumerate(notas):
                        console.print(f"    {i+1}. {nota.title}")
                
                resultados_teste.append({
                    'consulta': consulta,
                    'notas': len(notas),
                    'sucesso': len(notas) > 0
                })
                
        except Exception as e:
            console.print(f"  • [red]Erro: {e}[/red]")
            resultados_teste.append({
                'consulta': consulta,
                'erro': str(e),
                'sucesso': False
            })
    
    # Resumo do teste
    console.print("\n[bold]📈 Resumo do Teste:[/bold]")
    
    total_consultas = len(resultados_teste)
    consultas_sucesso = sum(1 for r in resultados_teste if r.get('sucesso', False))
    taxa_sucesso = (consultas_sucesso / total_consultas * 100) if total_consultas > 0 else 0
    
    console.print(f"  • Consultas testadas: {total_consultas}")
    console.print(f"  • Consultas com resultados: {consultas_sucesso}")
    console.print(f"  • Taxa de sucesso: {taxa_sucesso:.1f}%")
    
    if semantic:
        # Média de relevância para buscas semânticas
        relevancias = [r.get('relevancia_media', 0) for r in resultados_teste if 'relevancia_media' in r]
        if relevancias:
            avg_rel = sum(relevancias) / len(relevancias)
            console.print(f"  • Relevância média: {avg_rel:.3f}")
    
    console.print(f"\n[dim]Sistema de busca {'semântica' if semantic else 'textual'} testado com sucesso.[/dim]")

@app.command(name="reindexar")
def reindexar_busca(
    forcar: bool = typer.Option(False, "--forcar", "-f", help="Forçar reindexação completa")
):
    """Reindexa o vault para busca semântica"""
    system = _get_glados_system()
    
    if not system['vault'].semantic_search:
        console.print("[red]❌ Sistema de busca semântica não disponível[/red]")
        return
    
    console.print(Panel.fit(
        "[bold magenta]Reindexação do Sistema de Busca Semântica[/bold magenta]",
        border_style="magenta"
    ))
    
    console.print("[yellow]⚠️  Esta operação pode demorar dependendo do número de notas...[/yellow]")
    
    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Reindexando...", total=None)
        
        try:
            # Força reconstrução do índice
            if forcar:
                # Remove cache existente
                cache_path = system['vault'].semantic_search.cache_path
                if cache_path.exists():
                    cache_path.unlink()
                    console.print("  • Cache anterior removido")
            
            # Reconstrói índice
            system['vault'].semantic_search._build_embeddings_index()
            
            progress.update(task, completed=True)
            
            console.print("\n[green]✅ Reindexação concluída![/green]")
            
            # Mostra estatísticas atualizadas
            stats = system['vault'].semantic_search.get_stats()
            console.print(f"  • Notas indexadas: {stats['notes_indexed']}")
            console.print(f"  • Cache salvo em: {stats['cache_path']}")
            
        except Exception as e:
            console.print(f"\n[red]❌ Erro na reindexação: {e}[/red]")
