
---

# PLANNER (GLaDOS Edition) - Documentação Mestra

Versão: 0.4.0 (Estabilização Avançada)

Data da Atualização: 6 de Janeiro de 2026

Arquitetura: Local-first / MVC / LLM On-Premise

---

## 1. VISÃO GERAL

O **Planner** (codinome: _GLaDOS Planner_) é um sistema de gestão acadêmica integrado desenvolvido especificamente para estudantes. Diferente de planejadores genéricos, ele combina:

1. **Gestão Bibliográfica Profunda:** Focada em leitura ativa e revisão espaçada.
    
2. **Sincronização Bidirecional:** Integração nativa com **Obsidian**.
    
3. **Assistente IA Local:** Um "Cérebro de Silício" rodando **TinyLlama 1.1B** localmente, imbuído da personalidade sarcástica e condescendente da GLaDOS (Portal), garantindo privacidade total dos dados.
    
4. **Interface CLI Rica:** Uma experiência de terminal moderna e visualmente agradável.
    

---

## 2. ESTRUTURA GERAL DO PROJETO

Abaixo está a estrutura real de arquivos do projeto (excluindo dependências externas em `venv`).

Plaintext

```
.
├── check_system.sh                 # Script de diagnóstico do sistema
├── setup.sh                        # Script de configuração inicial
├── estrutura.txt                   # Snapshot da estrutura
├── requirements.txt                # Dependências de produção
├── requirements-dev.txt            # Dependências de desenvolvimento
├── requirements-llm.txt            # Dependências específicas para IA Local
├── config/
│   └── templates/                  # Templates Jinja2/Obsidian
├── data/
│   ├── cache/                      # Cache temporário
│   ├── database/
│   │   └── philosophy.db           # Banco de Dados SQLite principal
│   ├── exports/                    # Saída de relatórios
│   └── models/                     # Arquivos GGUF do TinyLlama
├── docs/
│   ├── api/
│   ├── examples/
│   └── guides/
├── migrations/                     # Controle de versão do Banco de Dados (Alembic)
│   ├── env.py
│   └── versions/
│       └── b8fefbf785d3_corrigir_conflito_de_nomes_notes_tags.py
├── scripts/                        # Utilitários de manutenção
│   ├── check_imports.py
│   ├── init_database.py
│   ├── test_obsidian_integration.py
│   └── deployment/
│   └── maintenance/
├── src/                            # CÓDIGO FONTE PRINCIPAL
│   ├── api/                        # (Futuro) Endpoints API
│   ├── cli/                        # Interface de Linha de Comando (Typer/Rich)
│   │   ├── glados.py               # Entrypoint da CLI
│   │   ├── main.py                 # Orquestrador principal
│   │   └── commands/
│   │       ├── data_commands.py    # Comandos de gestão de dados
│   │       └── obsidian_commands.py # Comandos de sincronização
│   ├── core/
│   │   ├── config/                 # Configurações do sistema
│   │   │   └── settings.py         # Pydantic settings management
│   │   ├── database/               # Camada de Dados (SQLAlchemy 2.0)
│   │   │   ├── base.py
│   │   │   ├── repository.py       # Padrão Repository Genérico
│   │   │   └── obsidian_sync.py    # Lógica de Sync
│   │   ├── llm/                    # Módulo de Inteligência Artificial
│   │   │   ├── local_llm.py        # Wrapper para Llama.cpp
│   │   │   ├── glados/             # Personalidade e Cérebro
│   │   │   │   ├── brain/          # Busca semântica e contexto
│   │   │   │   │   ├── semantic_search.py
│   │   │   │   │   └── vault_connector.py
│   │   │   │   └── commands/       # Comandos de NLP
│   │   │   │       └── brain_query.py
│   │   │   ├── personality/        # Motor de Personalidade
│   │   │   │   ├── config.py
│   │   │   │   ├── glados_voice.py # Formatação de resposta sarcástica
│   │   │   │   └── user_context.py
│   │   │   └── models/
│   │   │       ├── response_formatter.py
│   │   │       └── tinyllama_wrapper.py
│   │   ├── models/                 # Modelos ORM (Banco de Dados)
│   │   │   ├── base.py
│   │   │   ├── book.py
│   │   │   ├── note.py
│   │   │   ├── reading_session.py
│   │   │   └── task.py
│   │   ├── modules/                # Lógica de Negócios (Services)
│   │   │   ├── agenda_manager.py
│   │   │   ├── pomodoro_timer.py
│   │   │   ├── reading_manager.py
│   │   │   ├── review_system.py
│   │   │   ├── translation_module.py
│   │   │   ├── writing_assistant.py
│   │   │   └── obsidian/
│   │   │       ├── vault_manager.py
│   │   │       └── templates/
│   │   │           └── book_template.py
│   │   ├── repositories/           # Implementações Concretas de Repositórios
│   │   │   ├── book_repository.py
│   │   │   ├── note_repository.py
│   │   │   ├── reading_session_repository.py
│   │   │   └── task_repository.py
│   │   └── vault/                  # Gestão de Arquivos Físicos
│   │       └── manager.py
├── tests/                          # Suíte de Testes (Pytest)
│   ├── integration/
│   ├── unit/
│   ├── test_functionality.py
│   ├── test_glados.py
│   └── test_config.py
└── venv/                           # Ambiente Virtual (Dependências)
```

---

## 3. STATUS DOS MÓDULOS (v0.4.0)

O sistema encontra-se com 95% do MVP funcional.

|**Módulo**|**Status**|**Descrição Atualizada**|
|---|---|---|
|**ReadingManager**|✅ Pronto|Gestão completa de livros, progresso e metadados. Erros de indentação e tipagem corrigidos.|
|**AgendaManager**|✅ Pronto|Calendário acadêmico e gestão de prazos operacionais.|
|**ObsidianVaultManager**|✅ Pronto|Sincronização bidirecional, detecção de arquivos e templates funcionais.|
|**Database Core**|✅ Pronto|SQLAlchemy 2.0, Migrações Alembic e Repositories implementados.|
|**CLI (Interface)**|✅ Pronto|Interface baseada em Typer/Rich com esquema de cores unificado.|
|**TranslationAssistant**|✅ Pronto|Módulo de tradução de termos técnicos implementado.|
|**Pomodoro & Writing**|✅ Pronto|Temporizadores e assistente de escrita integrados.|
|**Cérebro GLaDOS**|⚠️ Parcial|Arquitetura (`brain_query.py`, `semantic_search.py`) existe, mas integração final com modelo GGUF e otimização de CPU estão pendentes.|

---

## 4. DETALHAMENTO TÉCNICO

### **Stack Tecnológico Atualizado**

- **Linguagem:** Python 3.13 (Ambiente Arch Linux).
    
- **Interface:** `Typer` (Comandos) + `Rich` (UI/UX) + `Questionary` (Input).
    
- **Dados:** `SQLAlchemy 2.0` (ORM) + `Alembic` (Migrações) + `SQLite`.
    
- **LLM:** `llama-cpp-python` rodando **TinyLlama-1.1B-Chat** (GGUF quantizado).
    
- **Arquivos:** `Watchdog` para monitoramento do Obsidian Vault.
    

### **Módulos Principais**

#### **1. Core & Database (`src/core/database` & `repositories`)**

Implementa o padrão Repository para abstrair consultas SQL.

- **Modelos:** `Book`, `Task`, `Note`, `ReadingSession`.
    
- **Destaque:** Uso de `BaseRepository` genérico para operações CRUD, estendido por repositórios específicos (ex: `BookRepository.get_reading_progress`).
    

#### **2. Módulo GLaDOS / LLM (`src/core/llm`)**

O diferencial do projeto. Não é apenas um chatbot, é uma "persona" integrada.

- **Estrutura:**
    
    - `personality/glados_voice.py`: Injeta sarcasmo e condescendência nas respostas.
        
    - `glados/brain/semantic_search.py`: Realiza RAG (Retrieval-Augmented Generation) nas notas do Obsidian.
        
    - `models/tinyllama_wrapper.py`: Interface com o modelo local.
        
- **Status:** Arquivos estruturados, aguardando download do modelo e _wiring_ final do `brain_query.py`.
    

#### **3. Gestores de Negócio (`src/core/modules`)**

- **ReadingManager:** Controla o fluxo de leitura, páginas lidas por dia e estatísticas.
    
- **AgendaManager:** Gerencia o calendário acadêmico.
    
- **Obsidian/VaultManager:** Responsável por garantir que o banco de dados SQL e os arquivos Markdown do Obsidian estejam em sincronia.
    

---

## 5. FLUXOS DE INTERAÇÃO (Workflow)

### **Fluxo 1: CLI & Inicialização**

Usuário executa `python -m src.cli.main status`.

1. O sistema carrega configurações de `src/core/config/settings.py`.
    
2. Verifica conexão com DB e Vault.
    
3. Verifica presença do modelo LLM (`data/models/`).
    
4. GLaDOS responde com status (e um comentário sarcástico sobre a ausência do cérebro, se for o caso).
    

### **Fluxo 2: Gestão de Leituras (ReadingManager)**

1. Comando: `glados data add-book`.
    
2. Sistema solicita ISBN ou dados manuais.
    
3. Registra no SQLite (`Book` model).
    
4. Gera automaticamente uma nota no Obsidian em `01-LEITURAS/` usando `book_template.py`.
    

### **Fluxo 3: Consulta Filosófica (Cérebro GLaDOS)**

1. Comando: `glados glados consultar "O que é a Caverna de Platão?"`.
    
2. `brain_query.py` é acionado.
    
3. `semantic_search.py` busca notas relevantes no Vault.
    
4. Prompt é montado: _Contexto do Vault + Pergunta + Personalidade GLaDOS_.
    
5. `tinyllama_wrapper.py` gera a resposta.
    
6. Saída exibida no terminal com formatação Rich.
    

---

## 6. ESTRUTURA DO VAULT OBSIDIAN (Validada)

A estrutura de diretórios do Obsidian que o sistema gerencia:

Plaintext

```
Philosophy_Vault/
├── 00-META/             # Metadados do sistema
├── 01-LEITURAS/         # Gerado pelo ReadingManager
├── 02-DISCIPLINAS/      # Organização acadêmica
├── 03-PRODUÇÃO/         # Outputs de escrita
├── 04-AGENDA/           # Sincronizado com AgendaManager
├── 05-CONCEITOS/        # Base de conhecimento para RAG
├── 06-RECURSOS/
├── 07-PESSOAL/
└── 08-ARCHIVE/
```

---

## 7. ROADMAP ATUALIZADO

### **Concluído (Fases 0-5)**

- ✅ Arquitetura MVC e Repositories.
    
- ✅ Banco de Dados e Migrações.
    
- ✅ CLI com UX avançada (Cores, Tabelas, Painéis).
    
- ✅ Integração básica Obsidian (Templates e Criação de Arquivos).
    
- ✅ Gerenciadores de Leitura e Agenda.
    

### **Em Andamento (Fase 6 - Reta Final)**

- 🔄 **Integração do Modelo:** Baixar `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` e conectar ao `local_llm.py`.
    
- 🔄 **Otimização:** Ajustar parâmetros de threads da CPU para evitar latência alta na inferência.
    
- 🔄 **Brain Query:** Finalizar a lógica de `brain_query.py` para unir a busca semântica com a geração de texto.
    

### **Próximos Passos (Futuro Próximo)**

- **Fine-tuning:** Ajustar o modelo para vocabulário filosófico específico.
    
- **Plugin Nativo:** Criar um plugin dentro do Obsidian (JS) que comunique com este backend Python.
    
- **Gamificação:** Implementar o sistema de XP e Badges definido no design original.
    

---

> _"O sistema está 95% pronto. A estrutura está lá, o código é sólido. Só falta acender a luz no cérebro de silício."_ — Diário de Desenvolvimento, Dia 11.