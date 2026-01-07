# Documentação do GLaDOS Planner

## Módulos Documentados

### Core
- `init_db()` - Inicializa o banco de dados
- `get_db()` - Obtém sessão do banco
- `SessionLocal()` - Fábrica de sessões

### Configuração
- `Settings` - Classe de configurações
- `settings` - Instância global de configurações

### Vault
- `VaultManager` - Gerenciador do vault Obsidian
- `create_structure()` - Cria estrutura do vault
- `is_connected()` - Verifica conexão com vault

### CLI
- `init` - Inicializa sistema
- `status` - Mostra status
- `version` - Mostra versão
- `glados-test` - Testa GLaDOS
- `glados-personality` - Mostra personalidade
- `create-vault` - Cria vault

### Módulos Futuros (Documentados)
- `PhilosophyLLM` - Assistente LLM
- `ReadingManager` - Gestor de leituras
- `AgendaManager` - Gestor de agenda
- `TranslationAssistant` - Assistente de tradução
- `PomodoroTimer` - Timer Pomodoro
- `WritingAssistant` - Assistente de escrita
- `ReviewSystem` - Sistema de revisão

## Funções Documentadas

### LLM
- `summarize()` - Sumariza texto
- `analyze_argument()` - Analisa argumento
- `generate_questions()` - Gera questões

### Reading Manager
- `get_reading_progress()` - Obtém progresso
- `update_progress()` - Atualiza progresso
- `generate_schedule()` - Gera cronograma

### Agenda Manager
- `get_daily_summary()` - Resumo diário
- `add_event()` - Adiciona evento
- `get_overdue_tasks()` - Tarefas atrasadas

### Data Commands
- `list_books()` - Lista livros
- `add_book()` - Adiciona livro
- `stats()` - Estatísticas

### Translation
- `translate_term()` - Traduz termo
- `get_pronunciation()` - Pronúncia

### Pomodoro
- `start()` - Inicia timer
- `pause()` - Pausa timer
- `resume()` - Retoma timer
- `get_stats()` - Estatísticas

### Writing Assistant
- `structure_paper()` - Estrutura paper
- `check_norms()` - Verifica normas
- `export_document()` - Exporta documento

### Review System
- `generate_flashcards()` - Gera flashcards
- `create_quiz()` - Cria quiz
- `spaced_repetition()` - Repetição espaçada
