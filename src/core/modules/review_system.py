# [file name]: src/core/modules/review_system.py
"""
Sistema de revisão espaçada para aprendizado filosófico
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import random

@dataclass
class Flashcard:
    """Cartão de revisão"""
    id: str
    front: str
    back: str
    tags: List[str]
    created: str
    last_reviewed: str
    next_review: str
    ease_factor: float
    interval: int  # em dias
    review_count: int
    consecutive_correct: int

@dataclass
class QuizQuestion:
    """Questão de quiz"""
    id: str
    question: str
    options: List[str]
    correct_answer: int
    explanation: str
    difficulty: str
    tags: List[str]

class ReviewSystem:
    """Sistema de revisão espaçada para filosofia"""
    
    def __init__(self, vault_path: str):
        """
        Inicializa o sistema de revisão
        
        Args:
            vault_path: Caminho para o vault do Obsidian
        """
        self.vault_path = Path(vault_path).expanduser()
        self.flashcards_file = self.vault_path / "06-RECURSOS" / "flashcards.json"
        self.quizzes_file = self.vault_path / "06-RECURSOS" / "quizzes.json"
        self.review_stats_file = self.vault_path / "06-RECURSOS" / "review_stats.json"
        
        # Carrega dados
        self.flashcards = self._load_flashcards()
        self.quizzes = self._load_quizzes()
        self.stats = self._load_stats()
    
    def _load_flashcards(self) -> Dict[str, Flashcard]:
        """Carrega flashcards do arquivo"""
        flashcards = {}
        
        if self.flashcards_file.exists():
            try:
                with open(self.flashcards_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for card_id, card_data in data.items():
                    flashcards[card_id] = Flashcard(
                        id=card_id,
                        front=card_data.get('front', ''),
                        back=card_data.get('back', ''),
                        tags=card_data.get('tags', []),
                        created=card_data.get('created', ''),
                        last_reviewed=card_data.get('last_reviewed', ''),
                        next_review=card_data.get('next_review', ''),
                        ease_factor=card_data.get('ease_factor', 2.5),
                        interval=card_data.get('interval', 1),
                        review_count=card_data.get('review_count', 0),
                        consecutive_correct=card_data.get('consecutive_correct', 0)
                    )
            except Exception as e:
                print(f"Erro ao carregar flashcards: {e}")
        
        return flashcards
    
    def _load_quizzes(self) -> Dict[str, QuizQuestion]:
        """Carrega quizzes do arquivo"""
        quizzes = {}
        
        if self.quizzes_file.exists():
            try:
                with open(self.quizzes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for quiz_id, quiz_data in data.items():
                    quizzes[quiz_id] = QuizQuestion(
                        id=quiz_id,
                        question=quiz_data.get('question', ''),
                        options=quiz_data.get('options', []),
                        correct_answer=quiz_data.get('correct_answer', 0),
                        explanation=quiz_data.get('explanation', ''),
                        difficulty=quiz_data.get('difficulty', 'média'),
                        tags=quiz_data.get('tags', [])
                    )
            except:
                pass
        
        return quizzes
    
    def _load_stats(self) -> Dict:
        """Carrega estatísticas de revisão"""
        stats = {
            "total_reviews": 0,
            "correct_answers": 0,
            "incorrect_answers": 0,
            "accuracy": 0,
            "streak_days": 0,
            "last_review_day": None,
            "by_tag": {},
            "daily_reviews": {}
        }
        
        if self.review_stats_file.exists():
            try:
                with open(self.review_stats_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    stats.update(loaded)
            except:
                pass
        
        return stats
    
    def _save_flashcards(self):
        """Salva flashcards no arquivo"""
        try:
            data = {}
            for card_id, card in self.flashcards.items():
                data[card_id] = {
                    'front': card.front,
                    'back': card.back,
                    'tags': card.tags,
                    'created': card.created,
                    'last_reviewed': card.last_reviewed,
                    'next_review': card.next_review,
                    'ease_factor': card.ease_factor,
                    'interval': card.interval,
                    'review_count': card.review_count,
                    'consecutive_correct': card.consecutive_correct
                }
            
            self.flashcards_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.flashcards_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar flashcards: {e}")
    
    def _save_quizzes(self):
        """Salva quizzes no arquivo"""
        try:
            data = {}
            for quiz_id, quiz in self.quizzes.items():
                data[quiz_id] = {
                    'question': quiz.question,
                    'options': quiz.options,
                    'correct_answer': quiz.correct_answer,
                    'explanation': quiz.explanation,
                    'difficulty': quiz.difficulty,
                    'tags': quiz.tags
                }
            
            self.quizzes_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.quizzes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar quizzes: {e}")
    
    def _save_stats(self):
        """Salva estatísticas no arquivo"""
        try:
            self.review_stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.review_stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar estatísticas: {e}")
    
    def generate_flashcards(self, source: str = "vault", tags: List[str] = None, limit: int = 20) -> List[Flashcard]:
        """
        Gera flashcards a partir do vault
        
        Args:
            source: Fonte dos flashcards (vault, concepts, readings)
            tags: Tags para filtrar (opcional)
            limit: Número máximo de flashcards a gerar
            
        Returns:
            Lista de flashcards gerados
        """
        new_cards = []
        
        if source == "vault":
            # Gera flashcards a partir das notas do vault
            for md_file in self.vault_path.glob("**/*.md"):
                if limit <= 0:
                    break
                
                try:
                    content = md_file.read_text(encoding='utf-8', errors='ignore')
                    
                    # Extrai conceitos importantes (palavras em negrito ou itálico)
                    import re
                    
                    # Conceitos em negrito
                    bold_concepts = re.findall(r'\*\*(.*?)\*\*', content)
                    for concept in bold_concepts[:3]:  # Limita por arquivo
                        if len(concept) > 3 and len(concept) < 50:
                            card_id = f"card_{len(self.flashcards) + len(new_cards) + 1}"
                            
                            # Tenta encontrar definição próxima
                            definition = self._find_definition(content, concept)
                            
                            new_card = Flashcard(
                                id=card_id,
                                front=f"O que é {concept}?",
                                back=definition or f"Conceito filosófico: {concept}",
                                tags=self._extract_tags(md_file, content),
                                created=datetime.now().isoformat(),
                                last_reviewed="",
                                next_review=datetime.now().isoformat(),
                                ease_factor=2.5,
                                interval=1,
                                review_count=0,
                                consecutive_correct=0
                            )
                            
                            new_cards.append(new_card)
                            limit -= 1
                    
                    # Se não encontrou conceitos em negrito, tenta por títulos
                    if not bold_concepts and limit > 0:
                        # Usa título do arquivo
                        title = md_file.stem
                        if len(title) > 5 and not title.startswith('.'):
                            card_id = f"card_{len(self.flashcards) + len(new_cards) + 1}"
                            
                            new_card = Flashcard(
                                id=card_id,
                                front=f"Sobre: {title}",
                                back=f"Conteúdo relacionado a {title}. Consulte a nota para detalhes.",
                                tags=self._extract_tags(md_file, content),
                                created=datetime.now().isoformat(),
                                last_reviewed="",
                                next_review=datetime.now().isoformat(),
                                ease_factor=2.5,
                                interval=1,
                                review_count=0,
                                consecutive_correct=0
                            )
                            
                            new_cards.append(new_card)
                            limit -= 1
                
                except:
                    continue
        
        # Adiciona novos flashcards à coleção
        for card in new_cards:
            self.flashcards[card.id] = card
        
        if new_cards:
            self._save_flashcards()
        
        return new_cards
    
    def _find_definition(self, content: str, concept: str) -> Optional[str]:
        """Tenta encontrar definição de um conceito no conteúdo"""
        import re
        
        # Procura por padrões de definição próximos ao conceito
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if concept in line:
                # Procura nas linhas seguintes
                for j in range(i+1, min(i+4, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and len(next_line) < 200:
                        # Remove formatação Markdown
                        next_line = re.sub(r'[*_`#]', '', next_line)
                        return next_line
        
        return None
    
    def _extract_tags(self, file_path: Path, content: str) -> List[str]:
        """Extrai tags de um arquivo"""
        tags = []
        
        # Tags no frontmatter
        import re
        frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            tag_match = re.search(r'tags:\s*\[(.*?)\]', frontmatter)
            if tag_match:
                tag_str = tag_match.group(1)
                tags.extend([t.strip().strip('"\'') for t in tag_str.split(',')])
        
        # Tags inline
        inline_tags = re.findall(r'\s#(\w+)', content)
        tags.extend(inline_tags)
        
        # Tags baseadas no diretório
        rel_path = file_path.relative_to(self.vault_path)
        folder = str(rel_path.parent).split('/')[0] if '/' in str(rel_path) else ""
        if folder:
            tags.append(folder.replace('-', '_'))
        
        return list(set(tags))[:5]  # Limita a 5 tags únicas
    
    def create_quiz(self, topic: str = None, num_questions: int = 10, difficulty: str = None) -> Dict:
        """
        Cria um quiz personalizado
        
        Args:
            topic: Tópico do quiz (opcional)
            num_questions: Número de questões
            difficulty: Dificuldade (fácil, média, difícil)
            
        Returns:
            Quiz gerado
        """
        # Filtra questões por tópico e dificuldade
        filtered_questions = []
        
        for quiz in self.quizzes.values():
            include = True
            
            if topic and topic.lower() not in ' '.join(quiz.tags).lower():
                include = False
            
            if difficulty and quiz.difficulty != difficulty:
                include = False
            
            if include:
                filtered_questions.append(quiz)
        
        # Se não há questões suficientes, gera algumas
        if len(filtered_questions) < num_questions:
            generated = self._generate_quiz_questions(topic, num_questions - len(filtered_questions), difficulty)
            filtered_questions.extend(generated)
        
        # Seleciona questões aleatórias
        selected = random.sample(filtered_questions, min(num_questions, len(filtered_questions)))
        
        # Formata quiz
        quiz_data = {
            "id": f"quiz_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": f"Quiz de Filosofia: {topic or 'Geral'}",
            "topic": topic or "geral",
            "difficulty": difficulty or "mista",
            "created": datetime.now().isoformat(),
            "questions": []
        }
        
        for i, question in enumerate(selected):
            quiz_data["questions"].append({
                "id": question.id,
                "number": i + 1,
                "question": question.question,
                "options": question.options,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
                "difficulty": question.difficulty,
                "tags": question.tags
            })
        
        return quiz_data
    
    def _generate_quiz_questions(self, topic: str, count: int, difficulty: str = None) -> List[QuizQuestion]:
        """Gera questões de quiz automaticamente"""
        generated = []
        
        # Tenta gerar a partir do vault
        for md_file in self.vault_path.glob("**/*.md"):
            if count <= 0:
                break
            
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
                title = md_file.stem
                
                # Verifica se o arquivo é relevante para o tópico
                if topic and topic.lower() not in content.lower() and topic.lower() not in title.lower():
                    continue
                
                # Gera questão baseada no conteúdo
                question_id = f"gen_{len(self.quizzes) + len(generated) + 1}"
                
                # Extrai conceito principal
                import re
                headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
                main_concept = headings[0] if headings else title
                
                # Cria questão múltipla escolha básica
                question = QuizQuestion(
                    id=question_id,
                    question=f"Qual das alternativas melhor descreve {main_concept}?",
                    options=[
                        f"{main_concept} é um conceito central na filosofia",
                        f"{main_concept} refere-se a uma prática específica",
                        f"{main_concept} foi desenvolvido por um único filósofo",
                        f"{main_concept} não tem relevância filosófica"
                    ],
                    correct_answer=0,
                    explanation=f"Consulte a nota '{title}' para mais informações sobre {main_concept}.",
                    difficulty=difficulty or "média",
                    tags=[topic] if topic else ["geral"]
                )
                
                generated.append(question)
                count -= 1
                
            except:
                continue
        
        # Se ainda precisar de mais questões, cria genéricas
        while count > 0:
            question_id = f"gen_{len(self.quizzes) + len(generated) + 1}"
            
            generic_questions = [
                {
                    "question": "Qual filósofo é conhecido pela frase 'Penso, logo existo'?",
                    "options": ["Platão", "Aristóteles", "Descartes", "Kant"],
                    "answer": 2,
                    "explanation": "René Descartes é o autor da famosa frase 'Cogito, ergo sum'."
                },
                {
                    "question": "O que é a 'alegoria da caverna'?",
                    "options": [
                        "Uma metáfora sobre a educação em Platão",
                        "Um experimento mental de Aristóteles",
                        "Uma teoria política de Maquiavel",
                        "Um conceito ético de Kant"
                    ],
                    "answer": 0,
                    "explanation": "A alegoria da caverna é apresentada por Platão em 'A República'."
                }
            ]
            
            import random
            generic = random.choice(generic_questions)
            
            question = QuizQuestion(
                id=question_id,
                question=generic["question"],
                options=generic["options"],
                correct_answer=generic["answer"],
                explanation=generic["explanation"],
                difficulty="fácil",
                tags=["história_da_filosofia"]
            )
            
            generated.append(question)
            count -= 1
        
        # Adiciona às questões existentes
        for question in generated:
            self.quizzes[question.id] = question
        
        if generated:
            self._save_quizzes()
        
        return generated
    
    def spaced_repetition(self, tag: str = None, limit: int = 20) -> List[Flashcard]:
        """
        Seleciona flashcards para revisão espaçada
        
        Args:
            tag: Tag para filtrar (opcional)
            limit: Número máximo de flashcards
            
        Returns:
            Lista de flashcards para revisão
        """
        now = datetime.now()
        due_cards = []
        
        for card in self.flashcards.values():
            # Filtra por tag se especificado
            if tag and tag not in card.tags:
                continue
            
            # Verifica se está vencido
            try:
                next_review = datetime.fromisoformat(card.next_review)
                if next_review <= now:
                    due_cards.append(card)
            except:
                # Se data inválida, inclui para revisão
                due_cards.append(card)
            
            if len(due_cards) >= limit:
                break
        
        # Se não há cartões vencidos, pega os mais antigos
        if not due_cards:
            all_cards = list(self.flashcards.values())
            if tag:
                all_cards = [c for c in all_cards if tag in c.tags]
            
            all_cards.sort(key=lambda x: x.last_reviewed or x.created)
            due_cards = all_cards[:limit]
        
        return due_cards
    
    def review_flashcard(self, card_id: str, quality: int) -> Dict:
        """
        Registra revisão de um flashcard
        
        Args:
            card_id: ID do flashcard
            quality: Qualidade da resposta (0-5)
            
        Returns:
            Resultado da revisão
        """
        if card_id not in self.flashcards:
            return {"error": "Flashcard não encontrado"}
        
        card = self.flashcards[card_id]
        now = datetime.now()
        
        # Atualiza estatísticas
        self.stats["total_reviews"] += 1
        if quality >= 3:
            self.stats["correct_answers"] += 1
            card.consecutive_correct += 1
        else:
            self.stats["incorrect_answers"] += 1
            card.consecutive_correct = 0
        
        # Atualiza precisão
        total = self.stats["correct_answers"] + self.stats["incorrect_answers"]
        self.stats["accuracy"] = (self.stats["correct_answers"] / total * 100) if total > 0 else 0
        
        # Atualiza estatísticas por tag
        for tag in card.tags:
            if tag not in self.stats["by_tag"]:
                self.stats["by_tag"][tag] = {"total": 0, "correct": 0, "accuracy": 0}
            
            self.stats["by_tag"][tag]["total"] += 1
            if quality >= 3:
                self.stats["by_tag"][tag]["correct"] += 1
            
            tag_total = self.stats["by_tag"][tag]["total"]
            tag_correct = self.stats["by_tag"][tag]["correct"]
            self.stats["by_tag"][tag]["accuracy"] = (tag_correct / tag_total * 100) if tag_total > 0 else 0
        
        # Atualiza streak diário
        today = now.strftime("%Y-%m-%d")
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        if today not in self.stats["daily_reviews"]:
            self.stats["daily_reviews"][today] = 0
        
        self.stats["daily_reviews"][today] += 1
        
        if self.stats["last_review_day"] == yesterday:
            self.stats["streak_days"] += 1
        elif self.stats["last_review_day"] != today:
            self.stats["streak_days"] = 1
        
        self.stats["last_review_day"] = today
        
        # Algoritmo SM-2 (Spaced Repetition)
        if quality < 3:
            # Resposta incorreta - reinicia intervalo
            card.interval = 1
            card.ease_factor = max(1.3, card.ease_factor - 0.2)
        else:
            # Resposta correta
            if card.review_count == 0:
                card.interval = 1
            elif card.review_count == 1:
                card.interval = 6
            else:
                card.interval = int(card.interval * card.ease_factor)
            
            # Ajusta fator de facilidade
            card.ease_factor = card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            card.ease_factor = max(1.3, card.ease_factor)
        
        # Atualiza datas
        card.last_reviewed = now.isoformat()
        card.next_review = (now + timedelta(days=card.interval)).isoformat()
        card.review_count += 1
        
        # Salva alterações
        self._save_flashcards()
        self._save_stats()
        
        return {
            "card_id": card_id,
            "quality": quality,
            "new_interval": card.interval,
            "new_ease_factor": round(card.ease_factor, 2),
            "next_review": card.next_review,
            "consecutive_correct": card.consecutive_correct
        }
    
    def get_review_stats(self) -> Dict:
        """
        Obtém estatísticas de revisão
        
        Returns:
            Estatísticas detalhadas
        """
        # Cartões para revisão hoje
        due_today = len(self.spaced_repetition(limit=1000))
        
        # Estatísticas gerais
        stats = self.stats.copy()
        stats["due_today"] = due_today
        stats["total_flashcards"] = len(self.flashcards)
        stats["total_quizzes"] = len(self.quizzes)
        
        # Distribuição por dificuldade
        difficulty_dist = {"fácil": 0, "média": 0, "difícil": 0}
        for quiz in self.quizzes.values():
            if quiz.difficulty in difficulty_dist:
                difficulty_dist[quiz.difficulty] += 1
        stats["quiz_difficulty"] = difficulty_dist
        
        # Tempo estimado para revisão
        estimated_time = due_today * 30  # 30 segundos por cartão
        stats["estimated_review_time_minutes"] = round(estimated_time / 60, 1)
        
        return stats
    
    def export_review_data(self, format: str = "json") -> str:
        """
        Exporta dados de revisão
        
        Args:
            format: Formato de exportação (json, csv)
            
        Returns:
            Caminho do arquivo exportado
        """
        export_dir = self.vault_path / "06-RECURSOS" / "exportacoes_revisao"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            file_path = export_dir / f"review_data_{timestamp}.json"
            data = {
                "flashcards": {cid: {
                    "front": card.front,
                    "back": card.back,
                    "tags": card.tags,
                    "interval": card.interval,
                    "ease_factor": card.ease_factor,
                    "review_count": card.review_count
                } for cid, card in self.flashcards.items()},
                "statistics": self.stats
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif format == "csv":
            import csv
            
            # Exporta flashcards
            cards_file = export_dir / f"flashcards_{timestamp}.csv"
            with open(cards_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Frente", "Verso", "Tags", "Intervalo", "Fator Facilidade", "Revisões"])
                
                for card in self.flashcards.values():
                    writer.writerow([
                        card.id,
                        card.front[:100],  # Limita tamanho
                        card.back[:100],
                        ";".join(card.tags),
                        card.interval,
                        card.ease_factor,
                        card.review_count
                    ])
            
            file_path = cards_file
        
        return str(file_path)
