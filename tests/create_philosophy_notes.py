#!/usr/bin/env python3
"""
create_philosophy_notes.py - Cria notas filosóficas de exemplo no vault
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

def create_sample_notes():
    """Cria notas filosóficas de exemplo"""
    
    # Caminho do vault
    from src.core.config.settings import settings
    vault_path = Path(settings.paths.vault).expanduser()
    
    # Notas de exemplo ricas em conteúdo filosófico
    sample_notes = {
        # Conceitos
        "02 - Conceitos/virtude.md": {
            "title": "Virtude (Areté)",
            "tags": ["ética", "aristóteles", "filosofia grega", "conceito"],
            "content": """# Virtude (Areté)

## Definição
A virtude (areté em grego) é a excelência do caráter que permite ao ser humano realizar sua função própria (ergon) e alcançar a eudaimonia (felicidade/florescimento).

## Em Aristóteles
Para Aristóteles na **Ética a Nicômaco**, a virtude é:
- **Meio-termo**: Entre dois extremos viciosos (excesso e deficiência)
- **Habituação**: Adquirida pela prática repetida (éthos)
- **Racional**: Guiada pela razão prática (phronesis)

## Exemplos de Virtudes
1. **Coragem**: Meio-termo entre covardia e temeridade
2. **Generosidade**: Meio-termo entre avareza e prodigalidade
3. **Modéstia**: Meio-termo entre arrogância e auto-depreciação

## Importância Filosófica
A virtude é central na **ética das virtudes**, uma das principais abordagens da filosofia moral, contrapondo-se ao utilitarismo (consequencialismo) e à deontologia kantiana.

## Conexões
- [[Ética a Nicômaco]]
- [[Eudaimonia]]
- [[Aristóteles]]
- [[Ética das Virtudes]]

---
*Criado em: {date}*
*Atualizado em: {date}*""".format(date=datetime.now().strftime("%Y-%m-%d"))
        },
        
        "02 - Conceitos/eudaimonia.md": {
            "title": "Eudaimonia",
            "tags": ["ética", "aristóteles", "felicidade", "filosofia grega"],
            "content": """# Eudaimonia

## Definição
Termo grego que significa literalmente "ter um bom daimon (espírito guia)". Frequentemente traduzido como **felicidade** ou **florescimento humano**, mas difere do conceito moderno de felicidade como estado emocional.

## Características em Aristóteles
1. **Atividade da alma**: Não é um estado passivo, mas atividade em acordo com a virtude
2. **Bem supremo**: Fim último (telos) da vida humana
3. **Autossuficiência**: Desejável por si mesma, não como meio para outro fim
4. **Racional**: Envolve o exercício da faculdade racional

## Componentes da Eudaimonia
- **Virtudes éticas**: Excelências do caráter
- **Virtudes dianoéticas**: Excelências intelectuais (sabedoria, prudência)
- **Bens externos**: Saúde, amigos, recursos (em medida adequada)

## Diferença do Hedonismo
Ao contrário do hedonismo (busca do prazer), a eudaimonia aristotélica envolve:
- Realização da natureza racional humana
- Vida contemplativa (bios theoretikos)
- Participação na vida da polis

## Conexões
- [[Virtude (Areté)]]
- [[Ética a Nicômaco]]
- [[Aristóteles]]
- [[Teleologia]]

---
*Criado em: {date}*""".format(date=datetime.now().strftime("%Y-%m-%d"))
        },
        
        # Leituras
        "01 - Leituras/aristoteles_etica_nicomaco.md": {
            "title": "Ética a Nicômaco - Aristóteles",
            "tags": ["aristóteles", "ética", "leitura", "filosofia grega"],
            "content": """# Ética a Nicômaco - Aristóteles

## Metadados
- **Autor**: Aristóteles (384-322 a.C.)
- **Período**: Filosofia Grega Clássica
- **Tema Principal**: Ética das virtudes
- **Data de Leitura**: Janeiro 2026
- **Status**: Lido e anotado

## Resumo Estruturado

### Livro I: O Bem Humano
- Investigação sobre o bem supremo (summum bonum)
- Definição de eudaimonia como atividade da alma em conformidade com a virtude
- Função própria (ergon) do ser humano: vida racional

### Livro II: Natureza da Virtude Ética
- Virtude como meio-termo (mesotes)
- Distinção entre virtude ética e intelectual
- Papel do hábito na formação do caráter

### Livro III-V: Virtudes Específicas
- Análise de virtudes como coragem, temperança, generosidade, magnanimidade
- Discussão sobre justiça como virtude completa

### Livro VI: Virtudes Intelectuais
- Phronesis (prudência/sabedoria prática) vs Sophia (sabedoria teórica)
- Papel da razão prática na vida ética

### Livro VII-X: Continuação e Conclusão
- Discussão sobre fraqueza da vontade (akrasia)
- Amizade (philia) como componente essencial da vida boa
- Vida contemplativa como forma mais elevada de eudaimonia

## Conceitos-Chave
1. **Meio-termo**: Nem excesso, nem deficiência
2. **Phronesis**: Sabedoria prática necessária para discernir o meio-termo
3. **Habituação**: "Somos o que repetidamente fazemos"
4. **Teleologia**: Tudo tem um fim/telos

## Citações Importantes
> "A excelência é uma arte conquistada pelo treino e pelo hábito. Não agimos corretamente porque temos virtude ou excelência, mas nós as temos porque agimos corretamente. Somos o que repetidamente fazemos. A excelência, então, não é um ato, mas um hábito."

> "O homem feliz vive bem e age bem."

## Análise Crítica
**Pontos fortes**:
- Abordagem holística da vida ética
- Reconhecimento da importância do caráter
- Integração entre razão e emoção

**Limitações**:
- Visão aristocrática da vida boa
- Dependência excessiva da razão prática
- Contexto cultural específico da Grécia antiga

## Conexões
- [[Virtude (Areté)]]
- [[Eudaimonia]]
- [[Platão]] (comparação)
- [[Ética Kantiana]] (contraste)

---
*Anotações feitas durante estudo para curso de Ética*""".format(date=datetime.now().strftime("%Y-%m-%d"))
        },
        
        "01 - Leituras/platao_republica.md": {
            "title": "A República - Platão",
            "tags": ["platão", "política", "filosofia grega", "epistemologia"],
            "content": """# A República - Platão

## Metadados
- **Autor**: Platão (428/427-348/347 a.C.)
- **Diálogo**: Sócrates como personagem principal
- **Tema Principal**: Justiça e a cidade ideal
- **Data de Leitura**: Dezembro 2025

## Alegorias Fundamentais

### 1. Alegoria da Caverna
**Descrição**: Prisioneiros acorrentados numa caverna veem apenas sombras projetadas na parede, tomando-as pela realidade.

**Significado**:
- Metáfora da educação filosófica
- Distinção entre mundo sensível e mundo inteligível
- Processo de libertação mediante o conhecimento

### 2. Analogia do Sol
- Sol = Ideia do Bem
- Luz = Conhecimento
- Visão = Capacidade de conhecer

### 3. Linha Dividida
- Níveis de conhecimento: conjectura, crença, pensamento, intuição
- Correspondência com níveis da realidade

## Estrutura da Cidade Ideal

### Classes Sociais
1. **Governantes-Filósofos**: Razão (alma racional) → Sabedoria
2. **Guardiões**: Vontade (alma irascível) → Coragem
3. **Produtores**: Desejo (alma apetitiva) → Moderação

### Justiça como Harmonia
- Justiça individual: cada parte da alma cumpre sua função
- Justiça social: cada classe cumpre sua função
- Analogia entre alma e polis

## Teoria das Formas/Ideias
- Realidade última são as Formas (Eidos) eternas e imutáveis
- Mundo sensível é cópia imperfeita
- Conhecimento verdadeiro é das Formas

## Crítica às Formas de Governo
1. **Timocracia**: Governo dos honoráveis → degenera em
2. **Oligarquia**: Governo dos ricos → degenera em
3. **Democracia**: Governo do povo → degenera em
4. **Tirania**: Governo do tirano

## Conexões
- [[Teoria das Formas]]
- [[Epistemologia Platônica]]
- [[Filosofia Política]]
- [[Aristóteles]] (críticas)

## Significado Contemporâneo
- Fundamentos da epistemologia ocidental
- Influência no pensamento político
- Questões sobre educação e papel do intelectual

---
*Estudo para disciplina de Filosofia Política*""".format(date=datetime.now().strftime("%Y-%m-%d"))
        },
        
        # Disciplinas
        "03 - Disciplinas/ética_filosofica.md": {
            "title": "Ética Filosófica",
            "tags": ["ética", "filosofia moral", "disciplina", "curso"],
            "content": """# Ética Filosófica

## Visão Geral
Disciplina filosófica que investiga os fundamentos da moralidade, valores e conduta humana.

## Principais Teorias Éticas

### 1. Ética das Virtudes (Aristóteles)
- **Foco**: Caráter do agente
- **Conceito central**: Virtude como meio-termo
- **Objetivo**: Eudaimonia (florescimento)
- **Representantes**: Aristóteles, Alasdair MacIntyre

### 2. Deontologia (Kant)
- **Foco**: Dever e obrigação moral
- **Conceito central**: Imperativo categórico
- **Princípio**: "Aja apenas segundo máxima que possas querer que se torne lei universal"
- **Representantes**: Immanuel Kant

### 3. Consequencialismo (Utilitarismo)
- **Foco**: Consequências das ações
- **Conceito central**: Maior felicidade para o maior número
- **Princípio**: Maximização do bem-estar
- **Representantes**: Jeremy Bentham, John Stuart Mill, Peter Singer

### 4. Ética do Cuidado (Care Ethics)
- **Foco**: Relações e responsabilidades
- **Conceito central**: Cuidado, empatia, vulnerabilidade
- **Contexto**: Crítica feminista às teorias tradicionais
- **Representantes**: Carol Gilligan, Nel Noddings

## Problemas Éticos Fundamentais

### Metaética
- Natureza dos juízos morais
- Objetivismo vs Subjetivismo
- Realismo vs Anti-realismo moral

### Ética Normativa
- Como devemos agir?
- Critérios para ações morais
- Conflito de valores

### Ética Aplicada
- Bioética (eutanásia, aborto)
- Ética animal
- Ética ambiental
- Ética tecnológica

## Métodos de Investigação
1. **Análise conceitual**
2. **Argumentação dialética**
3. **Casos e dilemas**
4. **Reflexão sobre experiências morais**

## Conexões Interdisciplinares
- **Psicologia**: Desenvolvimento moral
- **Sociologia**: Normas sociais
- **Direito**: Fundamentos da justiça
- **Neurociência**: Bases cerebrais da moralidade

## Leituras Essenciais
1. Aristóteles - *Ética a Nicômaco*
2. Kant - *Fundamentação da Metafísica dos Costumes*
3. Mill - *Utilitarismo*
4. MacIntyre - *Depois da Virtude*

---
*Conteúdo do curso de Ética I - Universidade*""".format(date=datetime.now().strftime("%Y-%m-%d"))
        },
        
        # Conceitos avançados
        "02 - Conceitos/teleologia.md": {
            "title": "Teleologia",
            "tags": ["metafísica", "aristóteles", "filosofia da natureza"],
            "content": """# Teleologia

## Definição
Do grego *telos* (fim, propósito) + *logos* (estudo). Doutrina filosófica que explica fenômenos em termos de seus fins ou propósitos, em contraste com explicações mecanicistas ou causais.

## Em Aristóteles
Aristóteles propõe quatro causas para explicar a realidade:

### As Quatro Causas
1. **Causa material**: De que é feito (mármore)
2. **Causa formal**: Forma ou essência (estátua de Atena)
3. **Causa eficiente**: Agente que produz (escultor)
4. **Causa final**: Propósito ou fim (culto à deusa)

### Teleologia Natural
- Seres naturais têm fins intrínsecos
- Semente → Planta (realização da forma)
- Acorn → Carvalho (atualização da potência)

## Teleologia na Ética
- Eudaimonia como telos da vida humana
- Virtudes como meios para alcançar o fim
- Vida boa como realização do propósito humano

## Críticas e Alternativas

### Críticas Modernas
1. **Francis Bacon**: Ciência deve investigar causas eficientes, não finais
2. **Descartes**: Mecanicismo vs finalismo
3. **Espinoza**: Rejeição da teleologia na natureza

### Darwin e Teleologia
- Evolução por seleção natural parece teleológica
- Adaptação como "propósito" sem agente consciente
- Teleonomia vs teleologia

## Teleologia Contemporânea
1. **Filosofia da Biologia**: Funções biológicas
2. **Filosofia da Mente**: Intencionalidade
3. **Ética**: Propósito da vida humana

## Conexões
- [[Aristóteles]]
- [[Metafísica]]
- [[Filosofia da Ciência]]
- [[Eudaimonia]]

---
*Conceito fundamental na metafísica aristotélica*""".format(date=datetime.now().strftime("%Y-%m-%d"))
        }
    }
    
    created = 0
    for rel_path, note_data in sample_notes.items():
        note_path = vault_path / rel_path
        note_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Formatar nota com frontmatter
        content = f"""---
title: "{note_data['title']}"
tags: {note_data['tags']}
created: {datetime.now().strftime('%Y-%m-%d')}
---

{note_data['content']}
"""
        
        if not note_path.exists():
            note_path.write_text(content, encoding='utf-8')
            print(f"✅ Criada nota: {rel_path}")
            created += 1
        else:
            print(f"⚠️  Nota já existe: {rel_path}")
            # Atualizar conteúdo se existir
            note_path.write_text(content, encoding='utf-8')
            print(f"📝 Atualizada nota: {rel_path}")
    
    print(f"\n📚 {created} notas filosóficas criadas/atualizadas!")
    print(f"\n🎯 Agora teste o sistema com:")
    print("   python test_integration_complete.py")
    print("   glados consultar 'o que é virtude' --semantica")
    print("   glados buscar 'aristóteles' --limite 5")
    
    return created

if __name__ == "__main__":
    create_sample_notes()
