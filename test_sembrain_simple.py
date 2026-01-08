#!/usr/bin/env python3
"""
test_sembrain_simple.py - Teste simplificado do Sembrain
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Mock de uma nota para teste
class MockNote:
    def __init__(self, path, title, content, tags=None):
        self.path = Path(path)
        self.title = title
        self.content = content
        self.tags = tags or []
    
    def to_dict(self):
        return {
            'path': str(self.path),
            'title': self.title,
            'content': self.content[:100],
            'tags': self.tags
        }

def main():
    print("🧪 Teste Simplificado do Sembrain")
    
    # Criar notas de exemplo
    notes = [
        MockNote("filosofia/etica.md", "Ética Aristotélica", 
                "A ética em Aristóteles é teleológica, focada na eudaimonia.", 
                ["ética", "aristóteles"]),
        MockNote("filosofia/virtude.md", "Conceito de Virtude",
                "Virtude é excelência no caráter, o meio-termo entre extremos.",
                ["virtude", "ética", "aristóteles"]),
    ]
    
    # Importar Sembrain
    try:
        from src.core.llm.glados.brain.semantic_search import Sembrain
        
        sembrain = Sembrain(Path("."), notes)
        print(f"✅ Sembrain inicializado com {len(notes)} notas")
        
        # Testar busca
        query = "virtude aristóteles"
        print(f"\n🔍 Buscando: '{query}'")
        
        results = sembrain.search(query, limit=3)
        print(f"📊 Resultados: {len(results)}")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.note.title} (relevância: {result.relevance:.3f})")
            if result.excerpt:
                print(f"   Trecho: {result.excerpt[:80]}...")
        
        return 0
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
