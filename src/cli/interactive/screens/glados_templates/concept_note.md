---
title: "{{title}}"
type: concept
tags: [{{tags}}]
source: "Consulta GLaDOS"
date: {{date}}
---

# {{title}}

**Consulta original:**
> {{question}}

**Resposta do GLaDOS:**
{{response}}

**Fontes utilizadas:**
{% for source in sources %}
- [[{{source.path}}]] ({{source.score}}%)
{% endfor %}

**Conceitos relacionados:**
{% for concept in concepts %}
- [[{{concept}}]]
{% endfor %}

---
*Consulta realizada via GLaDOS CLI em {{timestamp}}*
