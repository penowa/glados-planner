# Arquivo atual: glados.py (provável estrutura)
# Vamos criar uma versão refatorada em português:

import click
from src.cli.components import GladosComponents
from src.cli.personality import comentario_glados, frase_boas_vindas
import importlib

@click.group()
def glados():
    """GLaDOS Planner - Transformando confusão filosófica em conhecimento aparente."""
    GladosComponents.imprimir_cabecalho()
    print(frase_boas_vindas())

# Comandos principais da agenda
@glados.group(name='agenda', help='Gerencia sua agenda de estudos')
def agenda():
    """Sistema de agenda - Porque claramente você precisa de ajuda para se organizar."""
    pass

@agenda.command(name='listar', help='Lista compromissos')
@click.option('--hoje', is_flag=True, help='Mostra apenas compromissos de hoje')
@click.option('--semana', is_flag=True, help='Mostra compromissos da semana')
def agenda_listar(hoje, semana):
    """Lista seus compromissos agendados."""
    from commands.agenda import listar_compromissos
    GladosComponents.imprimir_titulo("📅 Compromissos Agendados")
    
    if hoje:
        compromissos = listar_compromissos(periodo='hoje')
        print(f"  Hoje: {len(compromissos)} compromissos encontrados.")
    elif semana:
        compromissos = listar_compromissos(periodo='semana')
        print(f"  Esta semana: {len(compromissos)} compromissos.")
    else:
        compromissos = listar_compromissos()
        print(f"  Total: {len(compromissos)} compromissos agendados.")
    
    for comp in compromissos[:10]:  # Limitar a 10 para não poluir
        GladosComponents.imprimir_item(f"{comp['hora']} - {comp['titulo']}")
    
    if len(compromissos) > 10:
        GladosComponents.imprimir_aviso(f"... e mais {len(compromissos)-10} compromissos")
    
    print(comentario_glados("agenda_listar", len(compromissos)))

@agenda.command(name='adicionar', help='Adiciona novo compromisso')
@click.argument('titulo')
@click.option('--data', '-d', help='Data (YYYY-MM-DD)')
@click.option('--hora', '-h', help='Hora (HH:MM)')
@click.option('--duracao', '-t', default='1h', help='Duração (ex: 1h30m)')
def agenda_adicionar(titulo, data, hora, duracao):
    """Adiciona um novo compromisso à sua desorganizada vida."""
    from commands.agenda import adicionar_compromisso
    
    compromisso = {
        'titulo': titulo,
        'data': data,
        'hora': hora,
        'duracao': duracao
    }
    
    resultado = adicionar_compromisso(compromisso)
    
    if resultado['sucesso']:
        GladosComponents.imprimir_sucesso(f"Compromisso adicionado: {titulo}")
        GladosComponents.imprimir_info(f"  Data: {resultado['data_formatada']}")
        GladosComponents.imprimir_info(f"  Hora: {resultado['hora_formatada']}")
    else:
        GladosComponents.imprimir_erro(f"Erro ao adicionar: {resultado['erro']}")
    
    print(comentario_glados("agenda_adicionar", titulo))

# Comandos de livro/leitura
@glados.group(name='livro', help='Gerencia livros e leituras')
def livro():
    """Sistema de gestão de leituras - Para quando você decide 'aprender coisas'."""
    pass

@livro.command(name='processar', help='Processa um novo livro')
@click.argument('arquivo', type=click.Path(exists=True))
@click.option('--qualidade', '-q', default='alta', 
              type=click.Choice(['baixa', 'media', 'alta']),
              help='Qualidade do processamento')
def livro_processar(arquivo, qualidade):
    """Processa um novo livro para estudo."""
    from commands.book_commands import processar_livro
    
    GladosComponents.imprimir_titulo(f"📚 Processando: {arquivo}")
    GladosComponents.imprimir_info(f"Qualidade: {qualidade}")
    
    with GladosComponents.barra_progresso() as progresso:
        tarefa = progresso.add_task("[cyan]Processando...", total=100)
        
        # Simular progresso (substituir pelo processamento real)
        for i in range(10):
            progresso.update(tarefa, advance=10)
            time.sleep(0.1)  # Remover em produção
        
        resultado = processar_livro(arquivo, qualidade)
    
    if resultado['sucesso']:
        GladosComponents.imprimir_sucesso("Livro processado com sucesso!")
        GladosComponents.imprimir_info(f"  Páginas: {resultado['paginas']}")
        GladosComponents.imprimir_info(f"  Conceitos: {resultado['conceitos']}")
    else:
        GladosComponents.imprimir_erro(f"Falha no processamento: {resultado['erro']}")
    
    print(comentario_glados("livro_processar", resultado.get('titulo', 'desconhecido')))

# Comandos de dados
@glados.group(name='dados', help='Gerencia dados e configurações')
def dados():
    """Sistema de dados - Onde suas informações estão (provavelmente) seguras."""
    pass

@dados.command(name='estatisticas', help='Mostra estatísticas de uso')
@click.option('--periodo', '-p', default='mes',
              type=click.Choice(['dia', 'semana', 'mes', 'ano']))
def dados_estatisticas(periodo):
    """Mostra estatísticas do seu (pouco) progresso."""
    from commands.data_commands import obter_estatisticas
    
    stats = obter_estatisticas(periodo)
    
    GladosComponents.imprimir_titulo(f"📊 Estatísticas - Último {periodo}")
    
    # Tabela de estatísticas
    tabela = GladosComponents.criar_tabela(["Métrica", "Valor", "Tendência"])
    tabela.add_row("Horas de estudo", f"{stats['horas_estudo']}h", stats['tendencia_estudo'])
    tabela.add_row("Páginas lidas", str(stats['paginas_lidas']), stats['tendencia_leitura'])
    tabela.add_row("Conceitos aprendidos", str(stats['conceitos']), stats['tendencia_conceitos'])
    tabela.add_row("Taxa de conclusão", f"{stats['conclusao']}%", stats['tendencia_conclusao'])
    
    GladosComponents.imprimir_tabela(tabela)
    print(comentario_glados("estatisticas", stats['conclusao']))

# Comandos Obsidian
@glados.group(name='obsidian', help='Integração com Obsidian')
def obsidian():
    """Integração Obsidian - Para manter sua confusão sincronizada."""
    pass

@obsidian.command(name='sincronizar', help='Sincroniza com vault do Obsidian')
@click.option('--forcar', '-f', is_flag=True, help='Força sincronização completa')
def obsidian_sincronizar(forcar):
    """Sincroniza suas anotações (des)organizadas."""
    from commands.obsidian_commands import sincronizar_vault
    
    GladosComponents.imprimir_titulo("🔄 Sincronizando com Obsidian")
    
    if forcar:
        GladosComponents.imprimir_aviso("Modo forçado ativado - Isso pode demorar mais")
    
    resultado = sincronizar_vault(forcar=forcar)
    
    if resultado['sucesso']:
        GladosComponents.imprimir_sucesso("Sincronização concluída!")
        GladosComponents.imprimir_info(f"  Arquivos atualizados: {resultado['atualizados']}")
        GladosComponents.imprimir_info(f"  Novos arquivos: {resultado['novos']}")
        GladosComponents.imprimir_info(f"  Conflitos resolvidos: {resultado['conflitos']}")
    else:
        GladosComponents.imprimir_erro(f"Erro na sincronização: {resultado['erro']}")
    
    print(comentario_glados("obsidian_sincronizar", resultado.get('atualizados', 0)))

# Comando principal
if __name__ == '__main__':
    glados()
