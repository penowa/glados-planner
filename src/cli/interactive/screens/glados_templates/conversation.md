---
title: "Conversa GLaDOS - {{date}}"
type: conversation
tags: [glados, consulta, ai]
participants: [usuário, GLaDOS]
date: {{date}}
---

# Conversa com GLaDOS

**Contexto:** {{context}}
**Data e hora:** {{timestamp}}
**Duração:** {{duration}}
**Total de mensagens:** {{message_count}}

## Diálogo Completo

{% for turn in conversation %}
### {{turn.role | capitalize }}
**Hora:** {{turn.timestamp}}
{% if turn.sources %}
**Fontes utilizadas:**
{% for source in turn.sources %}
- [[{{source.path}}]] ({{source.score}}%)
{% endfor %}
{% endif %}

{{turn.content}}

---
{% endfor %}

## 📊 Estatísticas
- Total de tokens: {{token_count}}
- Média de tokens por mensagem: {{avg_tokens}}
- Fontes consultadas: {{source_count}}

## 🏷️ Tags Geradas
{% for tag in generated_tags %}
- #{{tag}}
{% endfor %}

---
*Conversa exportada do GLaDOS CLI*
