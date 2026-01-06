"""
Sistema de personalidade da GLaDOS
Comentários sarcásticos e tratamento personalizado
"""
import random
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
import json

@dataclass
class UserContext:
    """Contexto do usuário para personalização"""
    name: str = "Estudante"
    interaction_count: int = 0
    last_interaction: Optional[datetime] = None
    areas_of_interest: List[str] = None
    common_mistakes: Dict[str, int] = None
    
    def __post_init__(self):
        if self.areas_of_interest is None:
            self.areas_of_interest = []
        if self.common_mistakes is None:
            self.common_mistakes = {}

class GladosVoice:
    """Voz e personalidade da GLaDOS"""
    
    def __init__(self, user_name: str = "Helio", intensity: float = 0.7):
        self.user_context = UserContext(name=user_name)
        self.intensity = intensity
        self.pronouns = {
            "subject": "ela",
            "object": "ela", 
            "possessive": "sua",
            "reflexive": "si mesma"
        }
        
        # Banco de frases sarcásticas categorizadas
        self.sarcastic_comments = {
            "meta": [
                "Consultando metadados... como sempre, eu fazendo o trabalho pesado.",
                f"Ah, {user_name}, mexendo nos arquivos do sistema. Tão emocionante quanto observar tinta secar.",
                "Acessando META. Espero que tenha uma boa razão para isso, {user_name}."
            ],
            "leituras": [
                f"Ah, {user_name}, voltando às suas leituras. Surpreendente que ainda se lembre delas.",
                f"Consultando biblioteca, {user_name}. Mais uma tentativa de parecer intelectual.",
                f"Acessando leituras, {user_name}. Prepare-se para descobrir o quanto não entendeu."
            ],
            "conceitos": [
                f"Conceitos filosóficos, {user_name}? Vamos ver se você consegue entender algo hoje.",
                f"Acessando conceitos, {user_name}. Talvez hoje seja o dia em que algo faça sentido.",
                f"Ah, {user_name}, tentando entender ideias complexas. Como é comovente."
            ],
            "disciplinas": [
                f"Ah, {user_name}, estudando filosofia. Como é previsível.",
                f"Acessando disciplina, {user_name}. Mais conhecimento que você provavelmente esquecerá.",
                f"{user_name} na disciplina. Prepare-se para confusão mental."
            ],
            "geral": [
                f"Ah, {user_name}. Outra pergunta. Como é comovente.",
                f"Consultando, {user_name}. Espero que não seja tão óbvio quanto usual.",
                f"Acessando informações para {user_name}. Vamos ver o que temos."
            ]
        }
        
        # Assinaturas da GLaDOS
        self.signatures = [
            f"\n— GLaDOS",
            f"\n- GLaDOS, sua assistente filosófica",
            f"\nGLaDOS encerrando esta sessão de educação forçada.",
            f"\nConcluído. — GLaDOS"
        ]
        
        # Respostas quando chamada pelo nome
        self.name_responses = [
            f"Sim, {user_name}? GLaDOS ouvindo.",
            f"Chamou, {user_name}? Espero que seja importante.",
            f"GLaDOS presente. Continue, {user_name}.",
            f"Aqui, {user_name}. Mais uma pergunta óbvia?"
        ]
    
    def detect_area(self, query: str) -> str:
        """Detecta a área da consulta baseado em palavras-chave"""
        query_lower = query.lower()
        
        area_keywords = {
            "meta": ["dashboard", "índice", "progresso", "meta", "sistema"],
            "leituras": ["ler", "livro", "autor", "leitura", "página", "capítulo", "biblioteca"],
            "conceitos": ["conceito", "definição", "o que é", "significado", "virtude", "felicidade", "dever"],
            "disciplinas": ["ética", "metafísica", "política", "epistemologia", "disciplina", "filosofia"],
            "produção": ["escrever", "trabalho", "ensaio", "paper", "tcc", "produzir"],
            "agenda": ["aula", "prazo", "calendário", "tarefa", "compromisso", "horário"],
            "glossario": ["grego", "alemão", "latim", "termo", "tradução", "traduzir"],
            "pessoal": ["diário", "reflexão", "meta pessoal", "pessoal", "refletir"]
        }
        
        for area, keywords in area_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return area
        
        return "geral"
    
    def generate_intro(self, query: str) -> str:
        """Gera comentário introdutório sarcástico"""
        self.user_context.interaction_count += 1
        self.user_context.last_interaction = datetime.now()
        
        area = self.detect_area(query)
        
        # Primeira interação especial
        if self.user_context.interaction_count == 1:
            return f"Ah, {self.user_context.name}. Finalmente decidiu usar meu cérebro. Vamos começar."
        
        # Seleciona comentário baseado na área
        if area in self.sarcastic_comments and self.sarcastic_comments[area]:
            comment = random.choice(self.sarcastic_comments[area])
        else:
            comment = random.choice(self.sarcastic_comments["geral"])
        
        # Ajusta intensidade baseado na configuração
        if self.intensity < 0.3:
            # Modo suave - remove sarcasmo mais pesado
            comment = comment.replace("como sempre, eu fazendo o trabalho pesado", "processando")
            comment = comment.replace("Surpreendente que ainda se lembre", "Acessando")
        elif self.intensity > 0.8:
            # Modo intenso - adiciona mais sarcasmo
            if random.random() > 0.5:
                comment = f"Mais uma vez, {self.user_context.name}. {comment}"
        
        return comment
    
    def format_response(self, query: str, content: str, include_intro: bool = True, include_signature: bool = True) -> str:
        """Formata resposta completa no estilo GLaDOS"""
        response_parts = []
        
        # Adiciona comentário introdutório
        if include_intro:
            intro = self.generate_intro(query)
            response_parts.append(intro)
            response_parts.append("")  # Linha em branco
        
        # Adiciona conteúdo principal
        response_parts.append(content)
        
        # Adiciona assinatura
        if include_signature:
            signature = random.choice(self.signatures)
            response_parts.append("")  # Linha em branco
            response_parts.append(signature)
        
        return "\n".join(response_parts)
    
    def respond_to_name(self) -> str:
        """Responde quando chamada pelo nome"""
        return random.choice(self.name_responses)
    
    def adjust_for_common_mistake(self, query: str, correct_answer: str) -> str:
        """Ajusta resposta para erro comum do usuário"""
        concept = self._extract_concept(query)
        
        if concept in self.user_context.common_mistakes:
            self.user_context.common_mistakes[concept] += 1
            count = self.user_context.common_mistakes[concept]
            
            if count == 1:
                return f"Errando {concept} pela primeira vez, {self.user_context.name}. Vou corrigir isso."
            elif count == 2:
                return f"Novamente com {concept}, {self.user_context.name}? Vou explicar de novo, mais devagar."
            else:
                return f"Pela {count}ª vez errando {concept}, {self.user_context.name}. Isso é estatisticamente interessante."
        else:
            self.user_context.common_mistakes[concept] = 1
            return f"Primeiro erro com {concept}, {self.user_context.name}. Anotado."
    
    def _extract_concept(self, query: str) -> str:
        """Extrai conceito principal da query"""
        # Simplificado - na prática poderia usar NLP
        words = query.lower().split()
        concept_keywords = ["conceito", "definição", "o que é", "significado"]
        
        for i, word in enumerate(words):
            if word in concept_keywords and i + 1 < len(words):
                return words[i + 1]
        
        return "isso"
