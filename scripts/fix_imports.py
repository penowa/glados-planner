#!/usr/bin/env python3
"""
fix_imports.py - Corrige incompatibilidades entre Sembrain e VaultStructure
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
VAULT_CONNECTOR_PATH = BASE_DIR / "src" / "core" / "llm" / "glados" / "brain" / "vault_connector.py"

def fix_vault_connector():
    """Corrige o vault_connector.py para usar Sembrain corretamente"""
    if not VAULT_CONNECTOR_PATH.exists():
        print(f"❌ Arquivo não encontrado: {VAULT_CONNECTOR_PATH}")
        return False
    
    with open(VAULT_CONNECTOR_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Corrigir importação
    old_import = "from .semantic_search import HierarchicalSearch, SearchResult"
    new_import = "from .semantic_search import Sembrain, SearchResult"
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        print("✅ Importação corrigida: HierarchicalSearch → Sembrain")
    
    # 2. Corrigir inicialização do semantic_search
    old_init = "self.semantic_search = HierarchicalSearch(self.vault_path, notes_list)"
    new_init = "self.semantic_search = Sembrain(self.vault_path, notes_list)"
    
    if old_init in content:
        content = content.replace(old_init, new_init)
        print("✅ Inicialização corrigida")
    
    # 3. Corrigir search_detailed para usar atributos corretos
    # Localizar a função search_detailed
    if 'def search_detailed(self, query: str, limit: int = 5) -> List[Dict]:' in content:
        # Encontrar e substituir o corpo da função
        import re
        pattern = r'def search_detailed\(self, query: str, limit: int = 5\) -> List\[Dict\]:.*?return detailed_results'
        replacement = '''def search_detailed(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Busca detalhada com metadados de relevância
        """
        if not self.semantic_search:
            return []
        
        results = self.semantic_search.search(query, limit=limit)
        
        detailed_results = []
        for result in results:
            detailed_results.append({
                'note': result.note.to_dict(),
                'relevance': result.relevance,
                'search_type': result.search_type,
                'matched_fields': result.matched_fields,
                'excerpt': result.excerpt
            })
        
        return detailed_results'''
        
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        print("✅ Função search_detailed corrigida")
    
    # 4. Corrigir chamada de update_index
    old_update = "self.semantic_search.update_index([note])"
    new_update = "self.semantic_search.add_note(note)"
    
    if old_update in content:
        content = content.replace(old_update, new_update)
        print("✅ Método update_index corrigido")
    
    # Salvar alterações
    with open(VAULT_CONNECTOR_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ vault_connector.py corrigido com sucesso!")
    return True

def create_test_script():
    """Cria um script de teste simplificado"""
    test_script = BASE_DIR / "test_sembrain_simple.py"
    
    test_code = '''#!/usr/bin/env python3
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
        print(f"\\n🔍 Buscando: '{query}'")
        
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
'''
    
    with open(test_script, 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    print(f"✅ Script de teste criado: {test_script}")
    return True

def main():
    print("🔧 CORRIGINDO IMPORTAÇÕES DO SEMBRAIN")
    print("=" * 50)
    
    if not fix_vault_connector():
        return 1
    
    create_test_script()
    
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Execute o teste simplificado:")
    print("   python test_sembrain_simple.py")
    print("\n2. Teste a correção completa:")
    print("   python diagnostic_sembrain.py")
    print("\n3. Use a CLI corrigida:")
    print("   glados consultar 'virtude' --semantica")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
