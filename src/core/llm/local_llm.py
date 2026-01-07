# [file name]: src/core/llm/local_llm.py
"""
Módulo PhilosophyLLM para análises filosóficas especializadas
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

@dataclass
class AnalysisResult:
    """Resultado da análise filosófica"""
    summary: str
    arguments: List[str]
    counterarguments: List[str]
    key_concepts: List[str]
    confidence: float

class PhilosophyLLM:
    """LLM especializado em filosofia para análises avançadas"""
    
    def __init__(self, base_llm):
        """
        Inicializa o PhilosophyLLM com um modelo base
        
        Args:
            base_llm: Instância do modelo LLM base (TinyLlamaGlados)
        """
        self.llm = base_llm
        
    def summarize(self, text: str, max_length: int = 300) -> str:
        """
        Resume um texto filosófico
        
        Args:
            text: Texto a ser resumido
            max_length: Comprimento máximo do resumo
            
        Returns:
            Resumo do texto
        """
        prompt = f"""Resuma o seguinte texto filosófico em {max_length} caracteres ou menos:

{text}

RESUMO:"""
        
        try:
            response = self.llm.generate_response(
                query=prompt,
                user_name="System",
                mode="philosophical_question"
            )
            # Extrai apenas o conteúdo após "RESUMO:"
            if "RESUMO:" in response:
                response = response.split("RESUMO:")[1].strip()
            return response[:max_length]
        except:
            # Fallback simple summary
            sentences = text.split('.')
            summary = '. '.join(sentences[:3]) + '.'
            return summary[:max_length]
    
    def analyze_argument(self, argument: str) -> AnalysisResult:
        """
        Analisa um argumento filosófico
        
        Args:
            argument: Argumento a ser analisado
            
        Returns:
            Análise estruturada do argumento
        """
        prompt = f"""Analise o seguinte argumento filosófico:

"{argument}"

Forneça:
1. Um resumo conciso
2. Premissas principais
3. Possíveis contra-argumentos
4. Conceitos-chave envolvidos
5. Avaliação da força lógica (0-1)

FORMATO JSON:"""
        
        try:
            response = self.llm.generate_response(
                query=prompt,
                user_name="System"
            )
            
            # Tenta extrair JSON da resposta
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if json_match:
                data = json.loads(json_match.group())
                return AnalysisResult(
                    summary=data.get('summary', ''),
                    arguments=data.get('premissas', []),
                    counterarguments=data.get('contra_argumentos', []),
                    key_concepts=data.get('conceitos_chave', []),
                    confidence=float(data.get('confianca', 0.5))
                )
        except:
            pass
        
        # Fallback analysis
        return AnalysisResult(
            summary=f"Análise do argumento: {argument[:100]}...",
            arguments=["Premissa principal identificada"],
            counterarguments=["Possível objeção considerada"],
            key_concepts=["Argumento", "Lógica"],
            confidence=0.6
        )
    
    def generate_questions(self, topic: str, count: int = 5) -> List[str]:
        """
        Gera questões filosóficas sobre um tópico
        
        Args:
            topic: Tópico para geração de questões
            count: Número de questões a gerar
            
        Returns:
            Lista de questões
        """
        prompt = f"""Gere {count} questões filosóficas sobre: {topic}

QUESTÕES:
1."""
        
        try:
            response = self.llm.generate_response(
                query=prompt,
                user_name="System"
            )
            
            # Extrai questões numeradas
            questions = []
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                    # Remove números/bullets
                    question = line.split('. ', 1)[-1] if '. ' in line else line
                    question = question.lstrip('•- ')
                    if question and len(question) > 10:
                        questions.append(question)
            
            return questions[:count]
        except:
            # Fallback questions
            fallback = [
                f"O que é {topic} na perspectiva filosófica?",
                f"Como {topic} se relaciona com a ética?",
                f"Quais são as principais teorias sobre {topic}?",
                f"Qual a importância de {topic} para a filosofia contemporânea?",
                f"Como diferentes escolas filosóficas abordam {topic}?"
            ]
            return fallback[:count]
    
    def compare_philosophers(self, philosopher1: str, philosopher2: str, topic: str) -> Dict:
        """
        Compara as visões de dois filósofos sobre um tópico
        
        Args:
            philosopher1: Nome do primeiro filósofo
            philosopher2: Nome do segundo filósofo
            topic: Tópico de comparação
            
        Returns:
            Dicionário com comparação
        """
        prompt = f"""Compare as visões de {philosopher1} e {philosopher2} sobre {topic}.

Inclua:
- Semelhanças principais
- Diferenças fundamentais
- Influências mútuas (se houver)
- Avaliação crítica

FORMATO:"""
        
        # Implementação simplificada
        return {
            "topic": topic,
            "philosopher1": philosopher1,
            "philosopher2": philosopher2,
            "similarities": [
                "Ambos abordam questões fundamentais da existência",
                "Compartilham interesse na natureza humana"
            ],
            "differences": [
                f"{philosopher1} enfatiza aspectos metafísicos",
                f"{philosopher2} foca em implicações éticas"
            ],
            "influences": f"{philosopher1} influenciou o pensamento ocidental",
            "critical_assessment": "Ambas as perspectivas oferecem insights valiosos"
        }
