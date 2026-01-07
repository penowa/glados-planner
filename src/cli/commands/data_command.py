# [file name]: src/cli/commands/data_commands.py
"""
Comandos CLI para os novos módulos do GLaDOS
"""
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from typing import Optional
import json
from pathlib import Path

from src.core.llm.local_llm import PhilosophyLLM
from src.core.database.obsidian_sync import VaultManager
from src.core.modules.reading_manager import ReadingManager
from src.core.modules.agenda_manager import AgendaManager
from src.core.modules.translation_module import TranslationAssistant
from src.core.modules.pomodoro_timer import PomodoroTimer
from src.core.modules.writing_assistant import WritingAssistant
from src.core.modules.review_system import ReviewSystem

app = typer.Typer(name="data", help="Comandos de dados e módulos avançados")
console = Console()

# Inicializa módulos com base nas configurações
def _get_module(module_name: str):
    """Obtém instância de um módulo"""
    from src.core.config.settings import settings
    
    vault_path = settings.paths.vault
    
    modules = {
        "philosophy_llm": lambda: PhilosophyLLM(None),  # Precisa de LLM base
        "vault_manager": lambda: VaultManager(vault_path),
        "reading_manager": lambda: ReadingManager(vault_path),
        "agenda_manager": lambda: AgendaManager(vault_path),
        "translation": lambda: TranslationAssistant(vault_path),
        "pomodoro": lambda: PomodoroTimer(vault_path),
        "writing": lambda: WritingAssistant(vault_path),
        "review": lambda: ReviewSystem(vault_path)
    }
    
    return modules.get(module_name)()

@app.command(name="leituras")
def gerenciar_leituras(
    comando: str = typer.Argument("status", help="Comando: status, atualizar, cronograma"),
    livro: Optional[str] = typer.Option(None, "--livro", "-l", help="ID do livro"),
    pagina: Optional[int] = typer.Option(None, "--pagina", "-p", help="Página atual"),
    notas: Optional[str] = typer.Option(None, "--notas", "-n", help="Notas sobre a leitura")
):
    """Gerencia leituras filosóficas"""
    manager = _get_module("reading_manager")
    
    if comando == "status":
        if livro:
            progresso = manager.get_reading_progress(livro)
            if progresso:
                console.print(Panel.fit(
                    f"[bold]Progresso de Leitura[/bold]\n"
                    f"Livro: {progresso.get('title', livro)}\n"
                    f"Progresso: {progresso.get('progress', '0/0')}\n"
                    f"Conclusão: {progresso.get('percentage', 0):.1f}%\n"
                    f"Velocidade: {progresso.get('reading_speed', 0):.1f} páginas/dia\n"
                    f"Estimativa: {progresso.get('estimated_completion', 'N/A')}",
                    border_style="blue"
                ))
            else:
                console.print(f"[yellow]Livro '{livro}' não encontrado.[/yellow]")
        else:
            todos = manager.get_reading_progress()
            if todos:
                table = Table(title="Progresso de Leitura", show_header=True, header_style="bold blue")
                table.add_column("Livro", style="cyan")
                table.add_column("Progresso", justify="center")
                table.add_column("%", justify="right")
                table.add_column("Velocidade", justify="right")
                table.add_column("Estimativa", style="green")
                
                for livro_id, progresso in todos.items():
                    if progresso:
                        table.add_row(
                            progresso.get('title', livro_id),
                            progresso.get('progress', '0/0'),
                            f"{progresso.get('percentage', 0):.1f}%",
                            f"{progresso.get('reading_speed', 0):.1f}/dia",
                            progresso.get('estimated_completion', 'N/A')
                        )
                
                console.print(table)
            else:
                console.print("[yellow]Nenhuma leitura registrada.[/yellow]")
    
    elif comando == "atualizar" and livro and pagina is not None:
        sucesso = manager.update_progress(livro, pagina, notas or "")
        if sucesso:
            console.print(f"[green]Progresso atualizado: {livro} página {pagina}[/green]")
        else:
            console.print(f"[red]Erro ao atualizar progresso.[/red]")
    
    elif comando == "cronograma" and livro:
        cronograma = manager.generate_schedule(livro)
        if "error" not in cronograma:
            console.print(Panel.fit(
                f"[bold]Cronograma de Leitura[/bold]\n"
                f"Livro: {cronograma.get('book', livro)}\n"
                f"Páginas restantes: {cronograma.get('pages_remaining', 0)}\n"
                f"Dias restantes: {cronograma.get('days_remaining', 0)}\n"
                f"Páginas/dia: {cronograma.get('pages_per_day', 0)}\n"
                f"Conclusão prevista: {cronograma.get('target_completion', 'N/A')}",
                border_style="green"
            ))
            
            # Mostra primeiros dias do cronograma
            if cronograma.get('daily_schedule'):
                table = Table(title="Primeiros Dias", show_header=True)
                table.add_column("Dia", style="cyan")
                table.add_column("Data")
                table.add_column("Páginas Alvo", justify="right")
                table.add_column("A Ler", justify="right")
                
                for dia in cronograma['daily_schedule'][:7]:
                    table.add_row(
                        str(dia['day']),
                        dia['date'],
                        str(dia['target_pages']),
                        str(dia['pages_to_read'])
                    )
                
                console.print(table)
        else:
            console.print(f"[red]{cronograma.get('error')}[/red]")

@app.command(name="agenda")
def gerenciar_agenda(
    comando: str = typer.Argument("hoje", help="Comando: hoje, adicionar, pendentes, estatisticas"),
    titulo: Optional[str] = typer.Option(None, "--titulo", "-t", help="Título do evento"),
    data: Optional[str] = typer.Option(None, "--data", "-d", help="Data (YYYY-MM-DD ou YYYY-MM-DD HH:MM)"),
    tipo: Optional[str] = typer.Option("outro", "--tipo", help="Tipo: aula, prova, entrega, reuniao"),
    disciplina: Optional[str] = typer.Option("", "--disciplina", "-m", help="Disciplina relacionada")
):
    """Gerencia agenda acadêmica"""
    manager = _get_module("agenda_manager")
    
    if comando == "hoje":
        resumo = manager.get_daily_summary()
        
        console.print(Panel.fit(
            f"[bold]Agenda para {resumo['date']}[/bold]\n"
            f"Eventos: {resumo['total_events']} | "
            f"Concluídos: {resumo['completed_events']} | "
            f"Taxa: {resumo['completion_rate']:.1f}%",
            border_style="yellow"
        ))
        
        if resumo['events']:
            table = Table(show_header=True, header_style="bold yellow")
            table.add_column("Hora", style="cyan")
            table.add_column("Evento")
            table.add_column("Tipo")
            table.add_column("Status", justify="center")
            
            for evento in resumo['events']:
                status = "✅" if evento['completed'] else "⏳"
                table.add_row(
                    evento['time'],
                    evento['title'],
                    evento['type'],
                    status
                )
            
            console.print(table)
        else:
            console.print("[green]Nenhum evento agendado para hoje.[/green]")
    
    elif comando == "adicionar" and titulo and data:
        evento_id = manager.add_event(titulo, data, event_type=tipo, discipline=disciplina)
        console.print(f"[green]Evento adicionado com ID: {evento_id}[/green]")
    
    elif comando == "pendentes":
        pendentes = manager.get_overdue_tasks()
        
        if pendentes:
            console.print(Panel.fit(
                f"[bold red]Tarefas Atrasadas: {len(pendentes)}[/bold red]",
                border_style="red"
            ))
            
            table = Table(show_header=True, header_style="bold red")
            table.add_column("Tarefa")
            table.add_column("Disciplina")
            table.add_column("Dias Atraso", justify="right")
            table.add_column("Prioridade")
            
            for tarefa in pendentes:
                table.add_row(
                    tarefa['title'],
                    tarefa['discipline'],
                    str(tarefa['days_late']),
                    tarefa['priority']
                )
            
            console.print(table)
        else:
            console.print("[green]Nenhuma tarefa atrasada![/green]")
    
    elif comando == "estatisticas":
        stats = manager.get_statistics()
        
        console.print(Panel.fit(
            "[bold]Estatísticas da Agenda[/bold]",
            border_style="magenta"
        ))
        
        console.print(f"📊 Total de eventos: {stats['total_events']}")
        console.print(f"✅ Concluídos: {stats['completed_events']}")
        console.print(f"🎯 Taxa de conclusão: {stats['completion_rate']:.1f}%")
        console.print(f"⚠️  Atrasados: {stats['overdue_tasks']}")
        console.print(f"📅 Próximos (7 dias): {stats['upcoming_events']}")
        
        if stats['by_type']:
            console.print("\n[bold]Por Tipo:[/bold]")
            for tipo, count in stats['by_type'].items():
                console.print(f"  {tipo}: {count}")

@app.command(name="traduzir")
def traduzir_termo(
    termo: str = typer.Argument(..., help="Termo filosófico para traduzir"),
    idioma: str = typer.Option("português", "--idioma", "-l", help="Idioma de destino"),
    pronuncia: bool = typer.Option(False, "--pronuncia", "-p", help="Mostrar pronúncia")
):
    """Traduz termos filosóficos"""
    translator = _get_module("translation")
    
    if pronuncia:
        resultado = translator.get_pronunciation(termo, idioma)
        
        console.print(Panel.fit(
            f"[bold]Pronúncia de '{termo}'[/bold]\n"
            f"Idioma: {resultado['idioma']}\n"
            f"Pronúncia: {resultado['pronúncia']}\n"
            f"Dica: {resultado['dica']}",
            border_style="cyan"
        ))
        
        if resultado['guia']:
            console.print("\n[bold]Guia de Pronúncia:[/bold]")
            for simbolo, explicacao in resultado['guia'].items():
                console.print(f"  {simbolo}: {explicacao}")
    else:
        resultado = translator.translate_term(termo, target_lang=idioma)
        
        if resultado.get('encontrado_no_glossario', False):
            console.print(Panel.fit(
                f"[bold]Tradução de '{termo}'[/bold]\n"
                f"Termo: {resultado['termo']}\n"
                f"Original ({resultado['idioma_original']}): {resultado['original']}\n"
                f"Tradução: {resultado['tradução']}",
                border_style="green"
            ))
            
            console.print(f"\n[bold]Definição:[/bold] {resultado['definição']}")
            
            if resultado.get('exemplos'):
                console.print("\n[bold]Exemplos:[/bold]")
                for exemplo in resultado['exemplos'][:3]:
                    console.print(f"  • {exemplo}")
        else:
            console.print(Panel.fit(
                f"[bold]Termo não encontrado no glossário[/bold]\n"
                f"Termo: {termo}\n"
                f"Tradução sugerida: {resultado['tradução']}",
                border_style="yellow"
            ))
            
            if resultado.get('notas_encontradas'):
                console.print(f"\n[bold]Menções encontradas no vault ({len(resultado['notas_encontradas'])}):[/bold]")
                for i, nota in enumerate(resultado['notas_encontradas'][:3]):
                    console.print(f"\n{i+1}. Arquivo: {nota['arquivo']}")
                    console.print(f"   Contexto: {nota['contexto'][:200]}...")

@app.command(name="pomodoro")
def temporizador_pomodoro(
    comando: str = typer.Argument("iniciar", help="Comando: iniciar, pausar, retomar, parar, estatisticas"),
    tipo: str = typer.Option("trabalho", "--tipo", "-t", help="Tipo: trabalho, pausa_curta, pausa_longa"),
    disciplina: Optional[str] = typer.Option(None, "--disciplina", "-d", help="Disciplina relacionada")
):
    """Gerencia temporizador Pomodoro"""
    timer = _get_module("pomodoro")
    
    tipo_map = {
        "trabalho": "work",
        "pausa_curta": "short_break",
        "pausa_longa": "long_break"
    }
    
    session_type = tipo_map.get(tipo, "work")
    
    if comando == "iniciar":
        sucesso = timer.start(session_type, disciplina)
        if sucesso:
            duracao = timer._get_duration_for_type(session_type) // 60
            console.print(f"[green]Sessão {tipo} iniciada ({duracao} minutos)[/green]")
        else:
            console.print("[red]Já existe uma sessão em andamento.[/red]")
    
    elif comando == "pausar":
        if timer.pause():
            console.print("[yellow]Sessão pausada[/yellow]")
        else:
            console.print("[red]Não há sessão ativa para pausar.[/red]")
    
    elif comando == "retomar":
        if timer.resume():
            console.print("[green]Sessão retomada[/green]")
        else:
            console.print("[red]Não há sessão pausada para retomar.[/red]")
    
    elif comando == "parar":
        sessao = timer.stop()
        if sessao:
            duracao = sessao.get('actual_duration', 0) // 60
            console.print(f"[green]Sessão finalizada ({duracao:.1f} minutos)[/green]")
        else:
            console.print("[yellow]Nenhuma sessão ativa.[/yellow]")
    
    elif comando == "estatisticas":
        stats = timer.get_stats()
        
        console.print(Panel.fit(
            "[bold]Estatísticas Pomodoro[/bold]",
            border_style="blue"
        ))
        
        console.print(f"📊 Total de sessões: {stats['total_sessions']}")
        console.print(f"💼 Sessões de trabalho: {stats['work_sessions']}")
        console.print(f"⏱️  Tempo total de trabalho: {stats['total_work_time_formatted']}")
        console.print(f"☕ Pausas: {stats['short_breaks'] + stats['long_breaks']}")
        console.print(f"🔥 Sequência atual: {stats['streak_days']} dias")
        console.print(f"🎯 Precisão hoje: {stats.get('today', {}).get('work_sessions', 0)} sessões")
        
        if stats.get('current_session'):
            sessao = stats['current_session']
            console.print(f"\n[bold]Sessão Atual ({sessao['type']}):[/bold]")
            console.print(f"  Decorrido: {sessao['elapsed']}")
            console.print(f"  Restante: {sessao['remaining']}")
            console.print(f"  Progresso: {sessao['progress']:.1f}%")
        
        # Recomendações
        recom = timer.get_recommendations()
        if recom['recommendations']:
            console.print("\n[bold]Recomendações:[/bold]")
            for rec in recom['recommendations'][:3]:
                icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                console.print(f"  {icon} {rec['message']}")

@app.command(name="escrever")
def assistente_escrita(
    comando: str = typer.Argument("estruturar", help="Comando: estruturar, verificar, analisar, exportar"),
    titulo: Optional[str] = typer.Option(None, "--titulo", "-t", help="Título do trabalho"),
    arquivo: Optional[str] = typer.Option(None, "--arquivo", "-a", help="Caminho do arquivo no vault"),
    template: str = typer.Option("ensaio_filosofico", "--template", help="Template: ensaio_filosofico, paper_academico, resenha_critica"),
    formato: str = typer.Option("pdf", "--formato", "-f", help="Formato: pdf, docx, html")
):
    """Assistente de escrita acadêmica"""
    assistant = _get_module("writing")
    
    if comando == "estruturar" and titulo:
        estrutura = assistant.structure_paper(titulo, template)
        
        console.print(Panel.fit(
            f"[bold]Estrutura Gerada: {titulo}[/bold]\n"
            f"Template: {template}\n"
            f"Seções: {len(estrutura.sections)}\n"
                    f"Meta de palavras: {estrutura.word_count_target}\n"
            f"Norma: {estrutura.style_guide}",
            border_style="green"
        ))
        
        table = Table(title="Seções", show_header=True, header_style="bold green")
        table.add_column("#", style="cyan")
        table.add_column("Título")
        table.add_column("Descrição")
        table.add_column("Palavras", justify="right")
        
        for i, secao in enumerate(estrutura.sections, 1):
            table.add_row(
                str(i),
                secao['title'],
                secao['description'][:50] + "...",
                str(secao['word_target'])
            )
        
        console.print(table)
        
        console.print(f"\n[dim]Arquivo criado no vault com a estrutura proposta.[/dim]")
    
    elif comando == "verificar" and arquivo:
        relatorio = assistant.check_norms(arquivo)
        
        console.print(Panel.fit(
            f"[bold]Verificação de Normas[/bold]\n"
            f"Arquivo: {relatorio['file']}\n"
            f"Norma: {relatorio['style_guide']}\n"
            f"Pontuação: {relatorio['score']}/100",
            border_style="green" if relatorio['score'] >= 70 else "yellow" if relatorio['score'] >= 50 else "red"
        ))
        
        if relatorio['checks_performed']:
            console.print("\n[bold]Verificações:[/bold]")
            for check in relatorio['checks_performed']:
                status_icon = "✅" if check['status'] == 'pass' else "⚠️" if check['status'] == 'warning' else "❌"
                console.print(f"  {status_icon} {check['check']}: {check['message']}")
        
        if relatorio['suggestions']:
            console.print("\n[bold]Sugestões:[/bold]")
            for sugestao in relatorio['suggestions']:
                console.print(f"  • {sugestao}")
    
    elif comando == "analisar" and arquivo:
        analise = assistant.analyze_writing_style(arquivo)
        
        console.print(Panel.fit(
            f"[bold]Análise de Estilo[/bold]\n"
            f"Arquivo: {analise['file']}",
            border_style="blue"
        ))
        
        if analise.get('basic_stats'):
            stats = analise['basic_stats']
            console.print(f"\n📊 [bold]Estatísticas Básicas:[/bold]")
            console.print(f"  Palavras: {stats['word_count']}")
            console.print(f"  Frases: {stats['sentence_count']}")
            console.print(f"  Média palavras/frase: {stats['average_sentence_length']:.1f}")
            console.print(f"  Média letras/palavra: {stats['average_word_length']:.1f}")
        
        if analise.get('readability'):
            leg = analise['readability']
            console.print(f"\n📖 [bold]Legibilidade:[/bold]")
            console.print(f"  Nível: {leg.get('level', 'N/A')}")
            if 'flesch_score' in leg:
                console.print(f"  Índice Flesch: {leg['flesch_score']:.1f}")
        
        if analise.get('vocabulary'):
            voc = analise['vocabulary']
            console.print(f"\n📚 [bold]Vocabulário:[/bold]")
            console.print(f"  Palavras únicas: {voc['unique_words']}")
            console.print(f"  Diversidade lexical: {voc['lexical_diversity']:.2%}")
        
        if analise.get('suggestions'):
            console.print(f"\n💡 [bold]Sugestões:[/bold]")
            for sugestao in analise['suggestions']:
                console.print(f"  • {sugestao}")
    
    elif comando == "exportar" and arquivo:
        caminho = assistant.export_document(arquivo, formato)
        console.print(f"[green]Documento exportado para: {caminho}[/green]")

@app.command(name="revisar")
def sistema_revisao(
    comando: str = typer.Argument("cartoes", help="Comando: cartoes, quiz, revisar, estatisticas"),
    topico: Optional[str] = typer.Option(None, "--topico", "-t", help="Tópico para filtrar"),
    quantidade: int = typer.Option(10, "--quantidade", "-q", help="Quantidade de itens")
):
    """Sistema de revisão espaçada"""
    review = _get_module("review")
    
    if comando == "cartoes":
        if topico == "gerar":
            novos = review.generate_flashcards(limit=quantidade)
            console.print(f"[green]Gerados {len(novos)} novos flashcards[/green]")
        else:
            cartoes = review.spaced_repetition(topico, quantidade)
            
            if cartoes:
                console.print(Panel.fit(
                    f"[bold]Cartões para Revisão[/bold]\n"
                    f"Total: {len(cartoes)}\n"
                    f"Tópico: {topico or 'Todos'}",
                    border_style="cyan"
                ))
                
                for i, cartao in enumerate(cartoes, 1):
                    console.print(f"\n{i}. [bold]{cartao.front}[/bold]")
                    console.print(f"   Tags: {', '.join(cartao.tags[:3])}")
                    console.print(f"   Próxima revisão: {cartao.next_review[:10]}")
                    console.print(f"   Intervalo: {cartao.interval} dias")
            else:
                console.print("[green]Nenhum cartão para revisar no momento![/green]")
    
    elif comando == "quiz":
        quiz = review.create_quiz(topico, quantidade)
        
        console.print(Panel.fit(
            f"[bold]Quiz: {quiz['title']}[/bold]\n"
            f"Questões: {len(quiz['questions'])}\n"
            f"Dificuldade: {quiz['difficulty']}\n"
            f"Criado: {quiz['created'][:10]}",
            border_style="yellow"
        ))
        
        for i, questao in enumerate(quiz['questions'], 1):
            console.print(f"\n{i}. {questao['question']}")
            for j, opcao in enumerate(questao['options']):
                console.print(f"   {chr(65+j)}) {opcao}")
            console.print(f"   [dim]Dificuldade: {questao['difficulty']}[/dim]")
    
    elif comando == "estatisticas":
        stats = review.get_review_stats()
        
        console.print(Panel.fit(
            "[bold]Estatísticas de Revisão[/bold]",
            border_style="magenta"
        ))
        
        console.print(f"📊 Total de revisões: {stats['total_reviews']}")
        console.print(f"✅ Respostas corretas: {stats['correct_answers']}")
        console.print(f"❌ Respostas incorretas: {stats['incorrect_answers']}")
        console.print(f"🎯 Precisão: {stats['accuracy']:.1f}%")
        console.print(f"🔥 Sequência: {stats['streak_days']} dias")
        console.print(f"📚 Flashcards: {stats['total_flashcards']}")
        console.print(f"❓ Quizzes: {stats['total_quizzes']}")
        console.print(f"⏰ Para revisar hoje: {stats['due_today']}")
        console.print(f"⏱️  Tempo estimado: {stats['estimated_review_time_minutes']} min")
        
        if stats.get('quiz_difficulty'):
            console.print("\n[bold]Dificuldade dos Quizzes:[/bold]")
            for dificuldade, count in stats['quiz_difficulty'].items():
                console.print(f"  {dificuldade}: {count}")

@app.command(name="sincronizar")
def sincronizar_vault(
    direcao: str = typer.Argument("ambos", help="Direção: para_obsidian, do_obsidian, ambos"),
    forcar: bool = typer.Option(False, "--forcar", "-f", help="Forçar sincronização completa")
):
    """Sincroniza vault com banco de dados"""
    sync = _get_module("vault_manager")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Sincronizando...", total=100)
        
        if direcao in ["do_obsidian", "ambos"]:
            progress.update(task, advance=25, description="[cyan]Sincronizando do Obsidian...")
            stats_from = sync.sync_from_obsidian(forcar)
            progress.update(task, advance=25)
            
            console.print(f"\n📥 [bold]Do Obsidian:[/bold]")
            console.print(f"   Notas escaneadas: {stats_from['notes_scanned']}")
            console.print(f"   Notas atualizadas: {stats_from['notes_updated']}")
            console.print(f"   Notas ignoradas: {stats_from['notes_skipped']}")
            console.print(f"   Erros: {stats_from['errors']}")
        
        if direcao in ["para_obsidian", "ambos"]:
            progress.update(task, advance=25, description="[cyan]Sincronizando para Obsidian...")
            # Nota: Para sincronizar para o Obsidian, precisaria de dados
            progress.update(task, advance=25)
            console.print("\n📤 [yellow]Sincronização para Obsidian requer dados específicos.[/yellow]")
        
        progress.update(task, advance=25, description="[green]Concluído!")
    
    status = sync.get_sync_status()
    console.print(f"\n📊 [bold]Status da Sincronização:[/bold]")
    console.print(f"   Total de sincronizações: {status['total_syncs']}")
    console.print(f"   Notas no banco: {status['total_notes']}")
    
    if status['recent_syncs']:
        console.print(f"\n[bold]Últimas sincronizações:[/bold]")
        for sync_item in status['recent_syncs'][:5]:
            icon = "✅" if sync_item['status'] == 'success' else "❌"
            console.print(f"   {icon} {sync_item['note']} ({sync_item['direction']})")
