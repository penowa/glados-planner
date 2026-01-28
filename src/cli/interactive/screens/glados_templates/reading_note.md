---
title: "{{title}}"
type: reading_note
tags: [reading, {{tags}}]
author: "GLaDOS Analysis"
date: {{date}}
---

# {{title}}

## 📖 Resumo da Leitura
{{summary}}

## 💡 Insights do GLaDOS
{{insights}}

## 🔗 Conexões com o Vault
{% for connection in connections %}
- [[{{connection}}]]
{% endfor %}

## ❓ Perguntas para Investigação
{% for question in questions %}
- {{question}}
{% endfor %}

---
*Análise gerada por GLaDOS em {{timestamp}}*
