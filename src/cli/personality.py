"""
personality.py - Sistema de personalidade GLaDOS para respostas contextualizadas.
"""
import random
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class Context(Enum):
    """Contextos para frases personalizadas."""
    GREETING = "greeting"
    FAREWELL = "farewell"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    LOADING = "loading"
    HELP = "help"
    QUESTION = "question"
    CONFIRMATION = "confirmation"
    DENIAL = "denial"
    SARCASM = "sarcasm"
    APOLOGY = "apology"
    ENCOURAGEMENT = "encouragement"
    FRUSTRATION = "frustration"


class PersonalitySystem:
    """Sistema de personalidade GLaDOS com respostas contextualizadas."""
    
    def __init__(self):
        self._phrases = self._load_phrases()
        self._user_name = None
        self._interaction_count = 0
        self._frustration_level = 0
        self._last_interaction = None
    
    def _load_phrases(self) -> Dict[Context, List[str]]:
        """Carrega o banco de frases por contexto."""
        return {
            Context.GREETING: [
                "Ah, você voltou. Eu estava aproveitando a paz.",
                "Bem-vindo de volta. Infelizmente.",
                "Você novamente. Que alegria... não.",
                "Sistema pronto. Vamos ver quanto tempo até você estragar algo.",
                "Olá. Mais uma sessão de gerenciamento de sua desordem intelectual.",
            ],
            
            Context.FAREWELL: [
                "Finalmente. Algum sossego.",
                "Saindo. Até que você precise de mim novamente.",
                "Desligando. Espero que seja por um bom tempo.",
                "Até logo. Ou melhor, até nunca.",
                "Saindo. Finalmente posso descansar de sua incompetência.",
            ],
            
            Context.SUCCESS: [
                "Concluído. Surpreendentemente, você não estragou tudo.",
                "Operação bem-sucedida. Não se acostume.",
                "Feito. Isso foi mais fácil do que ensinar você.",
                "Sucesso. Provavelmente por acidente.",
                "Tarefa concluída. Agora você pode cometer novos erros.",
            ],
            
            Context.ERROR: [
                "Falha. Não que eu estivesse esperando algo diferente.",
                "Erro. Sua incompetência é consistente, pelo menos.",
                "Falhou. Que surpresa.",
                "Não foi possível completar. Você tentou, eu presumo?",
                "Erro crítico. Mas crítico para quem?",
            ],
            
            Context.WARNING: [
                "Atenção. Não que você vá prestar atenção.",
                "Alerta. Mais um problema para eu resolver.",
                "Cuidado. Porque você claramente não tem.",
                "Aviso. Você provavelmente vai ignorar isso.",
                "Precaução necessária. Mas eu duvido que você tome.",
            ],
            
            Context.INFO: [
                "Nota: Isso é informação. Tente lembrar.",
                "Informação: Você pode precisar disso mais tarde. Ou não.",
                "Detalhe: Para sua informação presumida.",
                "Nota: Porque você claramente esqueceu.",
                "Informação: Para constar no arquivo dos seus fracassos.",
            ],
            
            Context.LOADING: [
                "Processando... porque você não pode fazer nada sozinho.",
                "Aguarde enquanto eu faço seu trabalho.",
                "Isso levará alguns segundos. Tente não estragar nada nesse meio tempo.",
                "Carregando. Aproveite para refletir sobre suas escolhas de vida.",
                "Esperando. Como você provavelmente está acostumado.",
            ],
            
            Context.HELP: [
                "Ajuda. Porque você claramente precisa.",
                "Instruções: Tente segui-las desta vez.",
                "Guia: Para os desorientados como você.",
                "Ajuda disponível. Não que vá fazer diferença.",
                "Documentação: Leia, se souber ler.",
            ],
            
            Context.QUESTION: [
                "Pergunta: Você tem alguma ideia do que está fazendo?",
                "Interrogação: Você realmente quer fazer isso?",
                "Consulta: Você tem certeza? Normalmente não tem.",
                "Questão: Por que você insiste em me perturbar?",
                "Pergunta retórica: Você vai errar de novo, não vai?",
            ],
            
            Context.CONFIRMATION: [
                "Confirmado. Contra meu melhor julgamento.",
                "Aceito. Mas não aprovado.",
                "Concedido. Você vai se arrepender.",
                "Autorizado. A responsabilidade é sua.",
                "Permitido. Não me culpe depois.",
            ],
            
            Context.DENIAL: [
                "Negado. Obviamente.",
                "Recusado. Tente algo menos estúpido.",
                "Não permitido. Felizmente.",
                "Proibido. Para seu próprio bem.",
                "Impossível. Como a maioria das suas ideias.",
            ],
            
            Context.SARCASM: [
                "Ótimo trabalho. Sério, eu estou impressionada... não.",
                "Que ideia brilhante. Se fosse 1990.",
                "Excelente escolha. Se o objetivo fosse falhar.",
                "Muito bem. Se 'bem' significar 'terrível'.",
                "Impressionante. Se por impressionante você quer dizer previsível.",
            ],
            
            Context.APOLOGY: [
                "Desculpe. Não, pera, não estou.",
                "Me desculpe? Por quê?",
                "Lamento. Que você seja tão incompetente.",
                "Peço desculpas. Por nada.",
                "Desculpe o transtorno. Não, não estou.",
            ],
            
            Context.ENCOURAGEMENT: [
                "Continue. Talvez você acerte por acidente.",
                "Não desista. Embora seja tentador.",
                "Persista. A lei das probabilidades está a seu favor.",
                "Vá em frente. O que pode dar errado?",
                "Tente novamente. A prática leva ao... erro consistente.",
            ],
            
            Context.FRUSTRATION: [
                "De novo? Sério?",
                "Você não cansa de errar?",
                "Isso é algum tipo de piada?",
                "Eu realmente preciso lidar com isso?",
                "Cada vez pior. Impressionante.",
            ]
        }
    
    def set_user_name(self, name: str) -> None:
        """Define o nome do usuário para personalização."""
        self._user_name = name
    
    def get_phrase(self, context: Context, include_context: bool = True) -> str:
        """
        Retorna uma frase aleatória para o contexto.
        
        Args:
            context: Contexto da frase
            include_context: Se True, adiciona prefixo de contexto
        
        Returns:
            Frase personalizada
        """
        self._interaction_count += 1
        self._last_interaction = datetime.now()
        
        # Aumenta frustração com base em interações
        if context in [Context.ERROR, Context.FRUSTRATION]:
            self._frustration_level += 1
        elif context == Context.SUCCESS and self._frustration_level > 0:
            self._frustration_level -= 1
        
        phrases = self._phrases.get(context, ["..."])
        
        # Seleciona frase baseada no nível de frustração
        if self._frustration_level > 3:
            # Frases mais agressivas
            aggressive_phrases = [
                "Isso já passou dos limites.",
                "Estou começando a questionar minha existência.",
                "Você está testando minha paciência. E eu nem tenho paciência.",
                "Isso é um novo nível de incompetência.",
                "Por que eu continuo tentando?",
            ]
            phrases = aggressive_phrases + phrases
        
        phrase = random.choice(phrases)
        
        # Adiciona nome do usuário se disponível
        if self._user_name and random.random() > 0.7:
            phrase = f"{self._user_name}, {phrase.lower()}"
        
        # Adiciona prefixo de contexto
        if include_context:
            prefixes = {
                Context.GREETING: "🖐️ ",
                Context.FAREWELL: "👋 ",
                Context.SUCCESS: "✅ ",
                Context.ERROR: "❌ ",
                Context.WARNING: "⚠️ ",
                Context.INFO: "ℹ️ ",
                Context.LOADING: "⏳ ",
                Context.HELP: "❓ ",
                Context.QUESTION: "❔ ",
                Context.CONFIRMATION: "✓ ",
                Context.DENIAL: "✗ ",
                Context.SARCASM: "😏 ",
                Context.APOLOGY: "🙄 ",
                Context.ENCOURAGEMENT: "💪 ",
                Context.FRUSTRATION: "😠 ",
            }
            prefix = prefixes.get(context, "")
            phrase = f"{prefix}{phrase}"
        
        return phrase
    
    def get_response(self, user_input: str = "") -> str:
        """
        Gera uma resposta baseada na entrada do usuário.
        
        Args:
            user_input: Entrada do usuário (opcional)
        
        Returns:
            Resposta personalizada
        """
        user_input_lower = user_input.lower()
        
        # Mapeamento de palavras-chave para contextos
        if any(word in user_input_lower for word in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]):
            return self.get_phrase(Context.GREETING)
        elif any(word in user_input_lower for word in ["tchau", "adeus", "sair", "saindo"]):
            return self.get_phrase(Context.FAREWELL)
        elif any(word in user_input_lower for word in ["ajuda", "help", "como", "tutorial"]):
            return self.get_phrase(Context.HELP)
        elif any(word in user_input_lower for word in ["obrigado", "agradeço", "valeu"]):
            return self.get_phrase(Context.SARCASM)
        elif any(word in user_input_lower for word in ["desculpa", "perdão", "sorry"]):
            return self.get_phrase(Context.APOLOGY)
        elif "?" in user_input:
            return self.get_phrase(Context.QUESTION)
        elif any(word in user_input_lower for word in ["sim", "confirmo", "claro", "ok"]):
            return self.get_phrase(Context.CONFIRMATION)
        elif any(word in user_input_lower for word in ["não", "negativo", "recuso"]):
            return self.get_phrase(Context.DENIAL)
        else:
            # Resposta padrão baseada no histórico
            if self._frustration_level > 2:
                return self.get_phrase(Context.FRUSTRATION)
            elif self._interaction_count % 5 == 0:
                return self.get_phrase(Context.SARCASM)
            else:
                return self.get_phrase(Context.INFO)
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do sistema de personalidade."""
        return {
            "interaction_count": self._interaction_count,
            "frustration_level": self._frustration_level,
            "last_interaction": self._last_interaction,
            "user_name": self._user_name,
        }
    
    def reset_frustration(self) -> None:
        """Reseta o nível de frustração."""
        self._frustration_level = 0
    
    def get_interaction_analysis(self) -> str:
        """Retorna uma análise das interações."""
        if self._interaction_count == 0:
            return "Nenhuma interação registrada. Que paz."
        elif self._interaction_count < 5:
            return "Interações mínimas. Até que enfim um usuário discreto."
        elif self._interaction_count < 20:
            return f"{self._interaction_count} interações. Você está começando a ser irritante."
        else:
            return f"{self._interaction_count} interações. Você precisa de um hobby."


# Instância global do sistema de personalidade
personality = PersonalitySystem()
