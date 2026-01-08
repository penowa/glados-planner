"""
sembrain.py - Sistema de busca semântica ultra-leve (0 dependências externas)
Transforma o vault do Obsidian em banco de dados contextual para a LLM
"""
from typing import List, Dict, Optional, Any
from pathlib import Path
import re
import hashlib
import json
import pickle
from datetime import datetime
from dataclasses import dataclass
from collections import Counter, defaultdict
import math

@dataclass
class SearchResult:
    """Resultado de busca"""
    note: Any
    relevance: float
    search_type: str
    matched_fields: List[str]
    excerpt: Optional[str] = None

class Sembrain:
    """
    Sistema de Busca Semântica Cerebral
    Transforma notas Markdown em 'memórias' para a LLM
    
    Técnicas usadas:
    1. TF-IDF básico (sem scikit-learn)
    2. Similaridade de cosseno manual
    3. Indexação leve em memória
    4. Cache inteligente
    """
    
    def __init__(self, vault_path: Path, notes: List[Any]):
        self.vault_path = vault_path
        self.notes = notes
        
        # Índices leves
        self.term_index = {}           # termo -> {note_id: tf}
        self.note_lengths = {}         # note_id -> total_terms
        self.idf_cache = {}            # termo -> idf
        
        # Cache de consultas
        self.query_cache = {}
        
        # Configurações
        self.max_terms = 1000          # Limite do vocabulário
        self.min_term_length = 3
        self.similarity_threshold = 0.1
        
        # Construir índices
        self._build_indices()
    
    def _build_indices(self):
        """Constrói índices leves das notas"""
        print(f"🧠 Indexando {len(self.notes)} notas...")
        
        # Passo 1: Contar termos em cada nota
        for note in self.notes:
            note_id = self._get_note_id(note)
            text = self._extract_note_text(note)
            terms = self._tokenize(text)
            
            self.note_lengths[note_id] = len(terms)
            
            # Contar frequência de termos
            term_counts = Counter(terms)
            for term, count in term_counts.items():
                if term not in self.term_index:
                    self.term_index[term] = {}
                self.term_index[term][note_id] = count
        
        # Passo 2: Calcular IDF (Inverse Document Frequency)
        total_notes = len(self.notes)
        for term, note_counts in self.term_index.items():
            docs_with_term = len(note_counts)
            self.idf_cache[term] = math.log(total_notes / (1 + docs_with_term))
        
        print(f"✅ Vocabulário: {len(self.term_index)} termos")
    
    def _extract_note_text(self, note) -> str:
        """Extrai e limpa texto da nota"""
        title = getattr(note, 'title', '')
        content = getattr(note, 'content', '')[:2000]  # Limita
        tags = ' '.join(getattr(note, 'tags', []))
        
        # Remove markdown básico
        text = f"{title} {tags} {content}"
        text = re.sub(r'[#*_`\[\]]', '', text)  # Remove formatação
        text = re.sub(r'\n+', ' ', text)        # Remove quebras
        return text.lower()
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenização básica em português"""
        # Remove pontuação e extrai palavras
        words = re.findall(r'[a-zà-ú]{3,}', text.lower())
        
        # Lista de stopwords básica
        stopwords = {
            'que', 'com', 'para', 'por', 'uma', 'um', 'as', 'os', 'do', 'da',
            'de', 'em', 'no', 'na', 'nos', 'nas', 'o', 'a', 'e', 'é', 'se',
            'mas', 'como', 'mais', 'isso', 'isto', 'aquilo', 'ser', 'estar',
            'ter', 'há', 'muito', 'pouco', 'não', 'sim', 'ainda', 'já'
        }
        
        return [w for w in words if w not in stopwords]
    
    def _get_note_id(self, note) -> str:
        """ID único baseado no caminho"""
        return str(note.path)
    
    def _tf_idf_vector(self, text: str, note_id: str = None) -> Dict[str, float]:
        """Calcula vetor TF-IDF manualmente"""
        terms = self._tokenize(text)
        vector = {}
        
        # Contar termos
        term_counts = Counter(terms)
        total_terms = len(terms)
        
        if total_terms == 0:
            return vector
        
        # Calcular TF-IDF para cada termo
        for term, count in term_counts.items():
            if term in self.idf_cache:
                # TF (Term Frequency)
                if note_id and term in self.term_index and note_id in self.term_index[term]:
                    tf = self.term_index[term][note_id] / self.note_lengths[note_id]
                else:
                    tf = count / total_terms
                
                # IDF (Inverse Document Frequency)
                idf = self.idf_cache[term]
                
                # TF-IDF
                vector[term] = tf * idf
        
        return vector
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Similaridade de cosseno manual"""
        if not vec1 or not vec2:
            return 0.0
        
        # Produto escalar
        dot_product = 0
        for term, weight in vec1.items():
            if term in vec2:
                dot_product += weight * vec2[term]
        
        # Normas
        norm1 = math.sqrt(sum(w * w for w in vec1.values()))
        norm2 = math.sqrt(sum(w * w for w in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _find_excerpt(self, note, query: str, context_chars: int = 100) -> str:
        """Encontra trecho relevante na nota"""
        content = getattr(note, 'content', '').lower()
        query = query.lower()
        
        # Tenta encontrar a query inteira
        if query in content:
            idx = content.find(query)
            start = max(0, idx - context_chars)
            end = min(len(content), idx + len(query) + context_chars)
            return content[start:end]
        
        # Tenta encontrar palavras individuais
        query_words = set(self._tokenize(query))
        content_words = self._tokenize(content)
        
        for i, word in enumerate(content_words):
            if word in query_words:
                # Pega contexto ao redor
                start_word = max(0, i - 5)
                end_word = min(len(content_words), i + 10)
                excerpt_words = content_words[start_word:end_word]
                return ' '.join(excerpt_words)
        
        # Fallback: primeiras palavras
        return content[:200] if len(content) > 200 else content
    
    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """
        Busca semântica usando TF-IDF básico
        
        Args:
            query: Texto da consulta
            limit: Máximo de resultados
        
        Returns:
            Lista de resultados ordenada por relevância
        """
        if not query.strip():
            return []
        
        # Cache simples
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if query_hash in self.query_cache:
            cached_time, results = self.query_cache[query_hash]
            if (datetime.now().timestamp() - cached_time) < 3600:  # 1 hora
                return results[:limit]
        
        print(f"🔍 Buscando: '{query[:50]}...'")
        
        # Vetor da consulta
        query_vector = self._tf_idf_vector(query)
        
        results = []
        for note in self.notes:
            note_id = self._get_note_id(note)
            
            # Vetor da nota
            note_text = self._extract_note_text(note)
            note_vector = self._tf_idf_vector(note_text, note_id)
            
            # Similaridade
            similarity = self._cosine_similarity(query_vector, note_vector)
            
            if similarity > self.similarity_threshold:
                excerpt = self._find_excerpt(note, query)
                
                # Boost baseado em fatores simples
                relevance = similarity
                
                # Boost se a query está no título
                title = getattr(note, 'title', '').lower()
                if query.lower() in title:
                    relevance *= 1.3
                
                # Boost se a query está nas tags
                tags = [tag.lower() for tag in getattr(note, 'tags', [])]
                for tag in tags:
                    if query.lower() in tag or any(word in tag for word in query.lower().split()):
                        relevance *= 1.2
                        break
                
                results.append(SearchResult(
                    note=note,
                    relevance=relevance,
                    search_type="semantic",
                    matched_fields=["content"],
                    excerpt=excerpt[:300] if excerpt else None
                ))
        
        # Ordenar por relevância
        results.sort(key=lambda x: x.relevance, reverse=True)
        
        # Cache
        self.query_cache[query_hash] = (datetime.now().timestamp(), results)
        
        # Limitar cache
        if len(self.query_cache) > 100:
            # Remove o mais antigo
            oldest = min(self.query_cache.keys(), 
                        key=lambda k: self.query_cache[k][0])
            del self.query_cache[oldest]
        
        return results[:limit]
    
    def get_context_for_llm(self, query: str, max_notes: int = 3) -> str:
        """
        Formata contexto para a LLM baseado na busca
        
        Args:
            query: Consulta do usuário
            max_notes: Máximo de notas para incluir
        
        Returns:
            String formatada para o prompt da LLM
        """
        results = self.search(query, limit=max_notes)
        
        if not results:
            return "# Contexto do Vault\nNenhuma nota relevante encontrada.\n"
        
        context_lines = ["# Contexto do Vault (Notas Relevantes)", ""]
        
        for i, result in enumerate(results, 1):
            note = result.note
            title = getattr(note, 'title', 'Sem título')
            path = str(note.path.relative_to(self.vault_path)) if hasattr(note, 'path') else "?"
            
            context_lines.append(f"## Nota {i}: {title}")
            context_lines.append(f"**Arquivo:** `{path}`")
            context_lines.append(f"**Relevância:** {result.relevance:.2f}")
            
            if result.excerpt:
                context_lines.append(f"**Trecho relevante:**")
                context_lines.append(f"> {result.excerpt}")
            
            context_lines.append("")  # Linha em branco
        
        context_lines.append("---")
        context_lines.append("Use o contexto acima para responder à consulta do usuário.")
        context_lines.append("Se uma informação não estiver no contexto, indique que não tem dados suficientes.")
        
        return "\n".join(context_lines)
    
    def add_note(self, note):
        """Adiciona uma nota ao índice (incremental)"""
        self.notes.append(note)
        # Reindexa apenas a nova nota
        self._reindex_note(note)
    
    def _reindex_note(self, note):
        """Reindexa uma única nota"""
        note_id = self._get_note_id(note)
        text = self._extract_note_text(note)
        terms = self._tokenize(text)
        
        # Atualiza contagens
        self.note_lengths[note_id] = len(terms)
        
        # Remove termos antigos desta nota
        for term, note_counts in list(self.term_index.items()):
            if note_id in note_counts:
                del note_counts[note_id]
                if not note_counts:  # Termo não aparece em mais nenhuma nota
                    del self.term_index[term]
                    if term in self.idf_cache:
                        del self.idf_cache[term]
        
        # Adiciona novos termos
        term_counts = Counter(terms)
        for term, count in term_counts.items():
            if term not in self.term_index:
                self.term_index[term] = {}
            self.term_index[term][note_id] = count
        
        # Recalcula IDF para termos modificados
        total_notes = len(self.notes)
        terms_to_update = set(term_counts.keys())
        
        for term in terms_to_update:
            if term in self.term_index:
                docs_with_term = len(self.term_index[term])
                self.idf_cache[term] = math.log(total_notes / (1 + docs_with_term))
    
    def get_stats(self) -> Dict:
        """Estatísticas do sistema"""
        return {
            "total_notes": len(self.notes),
            "vocabulary_size": len(self.term_index),
            "cache_size": len(self.query_cache),
            "avg_terms_per_note": sum(self.note_lengths.values()) / len(self.note_lengths) if self.note_lengths else 0
        }

# ============================================================================
# INTEGRAÇÃO COM O SISTEMA EXISTENTE
# ============================================================================

def integrate_with_vault_structure(vault_structure):
    """
    Função para integrar com o VaultStructure existente
    """
    from pathlib import Path
    
    class EnhancedVaultStructure:
        """VaultStructure com busca semântica integrada"""
        
        def __init__(self, vault_path: Path):
            self.vault_path = vault_path
            self.original_structure = vault_structure(vault_path)
            self.sembrain = None
            self._init_sembrain()
        
        def _init_sembrain(self):
            """Inicializa o sistema de busca semântica"""
            # Obtém todas as notas do vault
            notes = self.original_structure.get_all_notes()
            self.sembrain = Sembrain(self.vault_path, notes)
        
        def search_with_context(self, query: str, limit: int = 5) -> str:
            """
            Busca e retorna contexto formatado para LLM
            
            Args:
                query: Consulta do usuário
                limit: Máximo de notas para incluir
            
            Returns:
                Contexto formatado para o prompt
            """
            return self.sembrain.get_context_for_llm(query, limit)
        
        def semantic_search(self, query: str, limit: int = 5):
            """
            Busca semântica nas notas
            
            Args:
                query: Texto da busca
                limit: Máximo de resultados
            
            Returns:
                Lista de SearchResult
            """
            return self.sembrain.search(query, limit)
        
        # Delegate outros métodos para a estrutura original
        def __getattr__(self, name):
            return getattr(self.original_structure, name)
    
    return EnhancedVaultStructure

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

def example_usage():
    """Exemplo de como usar o sistema"""
    
    # Mock de uma nota
    class MockNote:
        def __init__(self, path, title, content, tags=None):
            self.path = Path(path)
            self.title = title
            self.content = content
            self.tags = tags or []
    
    # Cria algumas notas de exemplo
    notes = [
        MockNote(
            "filosofia/etica.md",
            "Ética Aristotélica",
            "A ética em Aristóteles é teleológica, focada na eudaimonia (felicidade/florescimento). A virtude é o meio-termo entre extremos.",
            ["ética", "aristóteles", "virtude", "felicidade"]
        ),
        MockNote(
            "filosofia/republica.md",
            "A República de Platão",
            "Platão descreve a alegoria da caverna como metáfora da educação filosófica. O filósofo-rei governa com sabedoria.",
            ["platão", "política", "conhecimento", "alegoria"]
        ),
        MockNote(
            "conceitos/virtude.md",
            "O Conceito de Virtude",
            "Virtude (areté) é excelência no caráter. Para Aristóteles, é um hábito adquirido pela prática do meio-termo.",
            ["virtude", "aristóteles", "ética", "caráter"]
        )
    ]
    
    # Cria sistema de busca
    vault_path = Path("filosofia_vault")
    sembrain = Sembrain(vault_path, notes)
    
    # Testa buscas
    queries = [
        "o que é virtude em aristóteles",
        "platão conhecimento",
        "ética felicidade"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {query}")
        print(f"{'='*60}")
        
        results = sembrain.search(query, limit=2)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.note.title}")
            print(f"   Relevância: {result.relevance:.3f}")
            if result.excerpt:
                print(f"   Trecho: {result.excerpt[:150]}...")
    
    # Contexto para LLM
    print(f"\n{'='*60}")
    print("CONTEXTO PARA LLM:")
    print(f"{'='*60}")
    context = sembrain.get_context_for_llm("virtude aristotélica", max_notes=2)
    print(context)
    
    # Estatísticas
    print(f"\n{'='*60}")
    print("ESTATÍSTICAS:")
    print(f"{'='*60}")
    stats = sembrain.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    example_usage()
