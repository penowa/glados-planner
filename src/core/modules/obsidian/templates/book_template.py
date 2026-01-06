# src/core/modules/obsidian/templates/book_template.py
"""
Templates para notas de livros no Obsidian.
"""

BOOK_METADATA_TEMPLATE = """---
title: "{title}"
author: "{author}"
status: "{status}"
progress: "{progress}%"
current_page: {current_page}
total_pages: {total_pages}
discipline: "{discipline}"
tags: ["book", "{discipline_lower}"]
date: "{date}"
---

# {title}

## 📋 Informações Básicas
- **Autor**: {author}
- **Editora**: {publisher}
- **Ano**: {year}
- **ISBN**: {isbn}
- **Status**: {status}
- **Progresso**: {current_page}/{total_pages} páginas ({progress}%)

## 📅 Datas
- **Início**: {start_date}
- **Prazo**: {deadline}
- **Conclusão**: {finish_date}

## 🎯 Metas de Leitura
- **Páginas por dia**: {pages_per_day}
- **Dias restantes**: {days_remaining}

## 📝 Anotações Relacionadas
<!--
[[Resumo - {title}]]
[[Conceitos - {title}]]
[[Citações - {title}]]
-->

## 📚 Progresso Detalhado
```dataview
TABLE WITHOUT ID
    file.link as "Sessão",
    pages_read as "Páginas",
    duration_minutes as "Duração (min)",
    focus_score as "Foco (1-10)",
    comprehension_score as "Compreensão (1-10)"
FROM "Sessões de Leitura"
WHERE book = "{title}"
SORT start_time DESC
💭 Reflexões
<!-- Adicione suas reflexões sobre o livro aqui -->"""
BOOK_SUMMARY_TEMPLATE = """---
title: "Resumo - {book_title}"
type: book-summary
book: "{book_title}"
author: "{author}"
tags: ["summary", "book"]
date: "{date}"

Resumo: {book_title}
🎯 Tese Central
<!-- Qual é a tese principal do livro? -->
📖 Argumentos Principais
🔑 Conceitos-Chave
❓ Questões Importantes
🤔 Críticas e Limitações
🔗 Conexões com Outras Obras
📝 Notas Adicionais
<!-- Espaço para notas livres -->"""
CONCEPT_TEMPLATE = """---
title: "{concept_name}"
type: concept
tags: ["concept", "{discipline}"]
related_books: ["{related_books}"]
date: "{date}"

{concept_name}
📚 Definição
<!-- Definição clara do conceito -->
📖 Origem e Desenvolvimento
<!-- Como este conceito surgiu e evoluiu? -->
👥 Autores Relacionados
<!-- Quais autores trabalharam com este conceito? -->
🔄 Variações e Interpretações
<!-- Diferentes interpretações do conceito -->
💡 Exemplos e Aplicações
<!-- Exemplos concretos do conceito em uso -->
🔗 Conceitos Relacionados
<!-- [[Conceito Relacionado 1]] [[Conceito Relacionado 2]] -->
📚 Referências Bibliográficas
<!-- 1. 2. 3. -->"""
CLASS_NOTE_TEMPLATE = """---
title: "{class_title}"
type: class-note
course: "{course}"
professor: "{professor}"
date: "{date}"
tags: ["class", "{course}"]

{class_title}
📅 Informações da Aula
Disciplina: {course}

Professor: {professor}

Data: {date}

Tópico: {topic}

🎯 Objetivos de Aprendizado
📝 Resumo da Aula
<!-- Resumo dos principais pontos abordados -->
💡 Pontos Principais
❓ Dúvidas e Questões
📚 Leituras Recomendadas
🔗 Conexões com Outros Conceitos
📖 Referências
<!-- 1. 2. 3. -->"""
