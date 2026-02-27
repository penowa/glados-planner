"""
Notas de referencia para o diretorio 00-META do vault.

Estas notas sao semeadas automaticamente quando o vault e criado
e o diretorio 00-META ainda nao possui documentacao funcional.
"""
from __future__ import annotations

from textwrap import dedent


def get_meta_help_notes() -> dict[str, str]:
    """Retorna o conjunto padrao de notas de ajuda da UI."""
    notes: dict[str, str] = {
        "00-LLM-HELP-POLICY.md": """
            # 00-META: Politica de help assistido

            Objetivo:
            - Este diretorio e a base de verdade para explicar o funcionamento da UI do planner.
            - Sempre priorize estas notas para responder duvidas sobre fluxos, telas e dialogs.

            Regras de resposta:
            - Se houver conflito entre memoria e esta documentacao, use esta documentacao.
            - Se a pergunta nao estiver coberta, responda que o ponto nao esta documentado aqui.
            - Cite o nome da view/dialog e o arquivo fonte quando possivel.

            Escopo:
            - Views em `ui/views/*.py`.
            - Dialogs em `ui/widgets/dialogs/*.py`.
            - Dialogs auxiliares declarados dentro das proprias views.
        """,
        "01-UI-MAPA-GERAL.md": """
            # Mapa geral da UI

            Views principais registradas na janela:
            - `dashboard` (`ui/views/dashboard.py`)
            - `library` (`ui/views/library.py`)
            - `agenda` (`ui/views/agenda.py`)
            - `session` (`ui/views/session.py`)
            - `weekly_review` (`ui/views/weekly_review.py`)
            - `review_workspace` (`ui/views/review_workspace.py`)
            - `vault_glados` (`ui/views/vault_glados.py`)
            - `discipline_chat` (`ui/views/discipline_chat.py`)

            Fluxo funcional mais comum:
            1. Dashboard abre cards de agenda e compromissos.
            2. Biblioteca importa livro e abre leitura.
            3. Sessao de leitura gera notas/resumos e atualiza progresso.
            4. Review Workspace consolida mapa mental de revisao.
            5. Weekly Review mostra metricas e sugestoes da semana.

            Integracoes:
            - Agenda e leituras usam controllers (`agenda`, `reading`, `book`).
            - LLM usa `glados_controller` nas views de chat/sessao.
            - Vault e sincronizado por controller proprio e por managers do backend.
        """,
        "02-VIEW-DASHBOARD.md": """
            # DashboardView

            Arquivo: `ui/views/dashboard.py`

            Objetivo:
            - Tela inicial com cards de agenda e proximos compromissos.
            - Disparar fluxos de criacao de evento, sessao de leitura e revisao.

            Dependencias:
            - Controllers `book`, `agenda`, `reading`, `daily_checkin`.
            - `AgendaCard`, `UpcomingCommitmentsCard`, `EventCreationDialog`.

            Fluxos principais:
            1. `load_initial_data()` recarrega cards e dados de leitura.
            2. `open_event_creation_dialog()` cria evento manual.
            3. `open_week_event_editor_dialog()` abre edicao da semana.
            4. `handle_start_session()` inicia leitura e navega para `session`.
            5. Botao unico de check-in escolhe matinal/noturno por estado diario.

            Sinais relevantes:
            - `navigate_to(str)`
            - `review_requested(dict)`
            - `review_workspace_requested(dict)`
        """,
        "03-VIEW-AGENDA.md": """
            # AgendaView

            Arquivo: `ui/views/agenda.py`

            Objetivo:
            - Agenda mensal com painel diario e drag-and-drop de compromissos.

            Componentes:
            - `MonthDayEventList`: lista por dia no calendario.
            - `HourlyAgendaTable`: grade por hora no painel lateral.
            - `AgendaView`: coordena mes, detalhe diario e persistencia.

            Fluxos principais:
            1. `load_month_data()` monta eventos por dia e renderiza mes.
            2. `on_day_selected()` abre painel com detalhe do dia.
            3. `on_event_dropped_to_day()` move evento entre dias.
            4. `on_event_retimed()` move evento para outro horario.
            5. `add_event()`, `delete_selected_event()`, `toggle_selected_event()`.

            Dialogs internos:
            - `RoutineSettingsDialog`: rotina (sono, refeicoes, revisao dominical).
            - `AddEventDialog`: cadastro manual de compromisso com disciplina.
            - `FindSlotDialog` e `EmergencyModeDialog`: compatibilidade.

            Observacao:
            - Eventos fixos virtuais (sono/refeicao) sao gerados localmente e nao podem ser editados/excluidos.
        """,
        "04-VIEW-LIBRARY.md": """
            # LibraryView

            Arquivo: `ui/views/library.py`

            Objetivo:
            - Exibir livros do vault em formato de prateleira visual.
            - Abrir leitura, editar metadados, agendar sessoes e iniciar revisao.

            Fluxos principais:
            1. `refresh_books()` varre `01-LEITURAS` (multiplos roots candidatos).
            2. `LibraryBookTile` mostra capa, progresso e menu de acoes.
            3. `show_import_dialog()` abre `BookImportDialog`.
            4. `start_book_processing()` delega processamento ao `book_controller`.
            5. `open_book_requested(Path)` navega para sessao de leitura.

            Operacoes de metadados:
            - Leitura de frontmatter da nota indice.
            - Sincronizacao com `reading_manager`.
            - Atualizacao de frontmatter em notas do livro.

            Dialogs internos:
            - `MetadataEditDialog`
            - `ScheduleDialog`
        """,
        "05-VIEW-SESSION.md": """
            # SessionView

            Arquivo: `ui/views/session.py`

            Objetivo:
            - Sessao de leitura em pagina dupla com Pomodoro, busca global e assistente LLM.

            Recursos centrais:
            - Navegacao de paginas, progresso em tempo real e encerramento de sessao.
            - Fullscreen com overlays (pomodoro e painel assistente).
            - Busca textual no livro com highlights.
            - Geracao de resumo/notas via LLM.
            - Gravacao de notas em `02-ANOTACOES` e materiais de revisao em `03-REVISAO`.

            Fluxo de revisao automatica:
            1. `start_review_generation()` monta contexto do capitulo.
            2. Gera fila de tarefas (resumo; formato validado).
            3. Salva material no vault e liga no capitulo atual.
            4. Atualiza mapa mental incrementalmente.

            Dialogs internos:
            - `PomodoroConfigDialog`
            - `ReviewGenerationDialog`
            - `ManualQuestionsDialog`
        """,
        "06-VIEW-REVIEW-WORKSPACE.md": """
            # ReviewWorkspaceView

            Arquivo: `ui/views/review_workspace.py`

            Objetivo:
            - Workspace de revisao com mapa mental editavel (nos, arestas, cores, resize e conexoes).

            Modos:
            - Revisao por obra (`open_review`).
            - Revisao por disciplina (`open_discipline_review`).

            Fluxos principais:
            1. Cria/carrega canvas de `04-MAPAS MENTAIS`.
            2. Renderiza nos/arestas e persiste alteracoes em JSON canvas.
            3. Permite criar card de texto/imagem e editar conteudo no painel lateral.
            4. Salva anotacoes de revisao em `02-ANOTACOES` e cria backlinks.
            5. Integra livro existente em mapa de disciplina.
            6. Ingestao de imagem para disciplina (`ingest_discipline_image`).

            Assistencia de estudo:
            - Pomodoro com configuracao.
            - Prompt periodico de pergunta de revisao (ReviewSystem).

            Dialogs internos:
            - `PomodoroConfigDialog`
            - `ReviewQuestionDialog`
        """,
        "07-VIEW-VAULT-GLADOS.md": """
            # VaultGladosView

            Arquivo: `ui/views/vault_glados.py`

            Objetivo:
            - Chat guiado para pesquisa no vault, selecao de contexto e resumo assistido.

            Maquina de estados:
            - `waiting_topic`: usuario informa tema.
            - `waiting_summary_decision`: decide se quer resumo longo.
            - `context_chat`: conversa livre com contexto fixo selecionado.

            Fluxo:
            1. Busca notas com `vault_controller.search_notes`.
            2. Abre `ContextSelectionDialog` para marcar notas.
            3. Monta prompt contextual e chama `glados_controller`.
            4. Valida resposta de resumo (tamanho/qualidade/fallback).
            5. Opcionalmente salva resumo em `03-REVISAO` e atualiza mapas mentais.

            Dialog interno:
            - `ContextSelectionDialog` agrupa notas por autor/obra e permite checagem hierarquica.
        """,
        "08-VIEW-DISCIPLINE-CHAT.md": """
            # DisciplineChatView

            Arquivo: `ui/views/discipline_chat.py`

            Objetivo:
            - Chat por disciplina, com conversas separadas e contexto vindo do vault.

            Conversas fixas:
            - Assistente geral (`__assistant__`) usa contexto de `00-META`.
            - Agenda (`agenda`) usa eventos e preferencias atuais.
            - Demais conversas usam disciplina + mapa mental da disciplina.

            Fluxos principais:
            1. `_build_meta_context()` carrega notas de help de `00-META`.
            2. `_build_agenda_context()` serializa agenda e preferencias.
            3. `_build_discipline_context()` agrega notas/canvas da disciplina.
            4. Envia prompt para LLM com historico recente.

            Atalhos de criacao:
            - Adicionar livro novo (`BookImportDialog`).
            - Vincular livro existente ao mapa da disciplina.
            - Adicionar imagem ao mapa da disciplina.
            - Abrir `AddEventDialog` predefinido para a disciplina.

            Dialogs internos:
            - `_NewChatDialog`
            - `_ExistingVaultBookDialog`
        """,
        "09-VIEW-WEEKLY-REVIEW.md": """
            # WeeklyReviewView

            Arquivo: `ui/views/weekly_review.py`

            Objetivo:
            - Painel semanal com metricas de desempenho, humor e sugestoes.

            Blocos exibidos:
            - Resumo rapido (dias produtivos, melhor periodo, taxa de conclusao).
            - Grafico de humor na semana.
            - Barras de status (concluidas, atrasadas, puladas).
            - Matriz por periodo (manha/tarde/noite) e tipo de atividade.
            - Lista de sessoes abertas com barra de progresso temporal.
            - Sugestoes vindas de agenda e checkins.

            Fonte de dados:
            - `agenda_manager.events`
            - `daily_checkin.checkin_system`

            Entrada de tela:
            - `refresh()` recalcula tudo no range segunda-domingo atual.
        """,
        "10-VIEW-REVIEW-PLANNER.md": """
            # ReviewPlanView e ReviewPlanDialog

            Arquivo: `ui/views/review_planner.py`

            Objetivo:
            - Coletar parametros para plano de revisao de obra concluida.

            Campos:
            - Livro (fixo ou selecionavel).
            - Horizonte de dias (3, 7, 14).
            - Horas por sessao.
            - Sessoes por dia.

            Comportamento:
            - `ReviewPlanView` recalcula preview a cada alteracao.
            - `ReviewPlanDialog` habilita botao de confirmar apenas com livro valido.
            - `values()` retorna payload pronto para agendamento automatico.
        """,
        "11-DIALOG-ONBOARDING.md": """
            # OnboardingDialog

            Arquivo: `ui/widgets/dialogs/onboarding_dialog.py`

            Objetivo:
            - Configuracao inicial rapida da aplicacao (opcional).

            Abas principais:
            - Inicio (identidade + presets rapidos).
            - LLM (local/cloud, GPU, downloads, setup Ollama).
            - Arquivos (vault e diretorios auto-gerenciados).
            - Agenda (rotina base).
            - Pomodoro e Review.
            - Features.
            - Resumo final.

            Fluxo de salvar:
            1. Valida caminho do vault.
            2. Atualiza `settings.yaml` e preferencias de UI.
            3. Chama `bootstrap_vault(...)`.
            4. Salva preferencias de rotina no AgendaManager.
            5. Emite `onboarding_preferences_saved`.

            Fluxos auxiliares:
            - Download de modelos GGUF.
            - Automacao de login e setup Ollama cloud.
        """,
        "12-DIALOG-SETTINGS.md": """
            # SettingsDialog

            Arquivo: `ui/widgets/dialogs/settings_dialog.py`

            Objetivo:
            - Edicao completa de configuracoes de runtime.

            Abas:
            - App, Paths, LLM, Obsidian, Review View, Aparencia, Features.

            Fluxos:
            1. `_load_current_values()` carrega YAML e config local.
            2. `_save_settings()` persiste `settings.yaml`, preferencias UI e emite `settings_saved`.
            3. `open_onboarding_now` reabre onboarding manualmente.
            4. `factory_reset` limpa cache/export/historico/DB e restaura defaults.

            Destaques:
            - Descoberta de modelos GGUF e GPUs NVIDIA.
            - Troca entre backend local/cloud com campos dinamicos.
            - Cor secundaria global de botoes.
        """,
        "13-DIALOG-BOOK-IMPORT.md": """
            # BookImportDialog

            Arquivo: `ui/widgets/dialogs/book_import_dialog.py`

            Objetivo:
            - Confirmar e ajustar configuracao antes de processar livro (PDF/EPUB).

            Abas:
            - Metadados (com camada de confianca por campo).
            - Processamento (qualidade, OCR, IA, layout).
            - Notas (template, destino no vault, disciplina).
            - Agendamento (meta diaria, inicio, estrategia).

            Validacoes:
            - Titulo obrigatorio.
            - Para PDF, disciplina obrigatoria.
            - Disciplina pode ser criada na hora.

            Saida:
            - Emite `import_confirmed(dict)` com payload unico de processamento.
            - Emite `import_cancelled()` ao fechar sem confirmar.
        """,
        "14-DIALOG-WEEKLY-EVENT-EDITOR.md": """
            # WeeklyEventEditorDialog

            Arquivo: `ui/widgets/dialogs/weekly_event_editor_dialog.py`

            Objetivo:
            - Editar e excluir eventos da semana em fluxo rapido.

            Estrutura:
            - Lista lateral com eventos da semana.
            - Formulario de edicao usando `EventCreationCard`.
            - Acoes: salvar alteracoes, excluir, recarregar.

            Fluxo:
            1. `_load_week_events()` filtra eventos por intervalo semanal.
            2. Selecao carrega evento no formulario.
            3. `_on_save_clicked()` aplica alteracoes no objeto do evento e persiste via `agenda_manager._save_events()`.
            4. `_on_delete_clicked()` confirma exclusao e remove evento.

            Sinal:
            - `event_changed` para forcar refresh em telas chamadoras.
        """,
        "15-DIALOG-MORNING-CHECKIN.md": """
            # MorningCheckinDialog

            Arquivo: `ui/widgets/dialogs/morning_checkin_dialog.py`

            Objetivo:
            - Registrar estado de inicio do dia.

            Campos:
            - Energia (1-5)
            - Foco (1-5)
            - Metas do dia (opcional)

            Comportamento:
            - Carrega dica dinamica por energia/foco via `DailyCheckinSystem`.
            - Ao confirmar, chama `checkin_system.morning_routine(...)`.
            - `get_data()` retorna snapshot do formulario para consumo externo.
        """,
        "16-DIALOG-EVENING-CHECKIN.md": """
            # EveningCheckinDialog

            Arquivo: `ui/widgets/dialogs/evening_checkin_dialog.py`

            Objetivo:
            - Registrar fechamento do dia e gerar resumo rapido.

            Campos:
            - Humor (1-5)
            - Conquistas
            - Desafios
            - Insights

            Comportamento:
            - Ao confirmar, chama `checkin_system.evening_checkin(...)`.
            - Mostra resumo textual retornado pelo sistema.
            - Desabilita formulario e fecha com atraso curto para leitura do resumo.
            - `get_data()` retorna snapshot do formulario.
        """,
    }

    normalized: dict[str, str] = {}
    for relative_path, content in notes.items():
        normalized[relative_path] = dedent(content).strip() + "\n"
    return normalized

