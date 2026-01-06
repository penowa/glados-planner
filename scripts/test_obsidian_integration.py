# scripts/test_obsidian_integration.py
#!/usr/bin/env python3
"""
Testa a integração com o Obsidian.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_obsidian_integration():
    """Testa a integração básica com Obsidian."""
    print("🧪 Testando integração com Obsidian...\n")
    
    try:
        # 1. Testar importação do módulo
        from src.core.modules.obsidian import ObsidianVaultManager
        print("✅ Módulo ObsidianVaultManager importado")
        
        # 2. Testar criação do manager (sem vault real)
        try:
            # Tentar criar com caminho que não existe (deve falhar)
            manager = ObsidianVaultManager("/caminho/inexistente")
            print("❌ Deveria ter falhado com caminho inexistente")
            return False
        except ValueError as e:
            print(f"✅ Validação de caminho funcionando: {e}")
        
        # 3. Testar templates
        from src.core.modules.obsidian.templates import book_template
        print("✅ Templates importados")
        
        # 4. Testar se podemos instanciar com mock (opcional)
        print("\n✅ Integração básica testada com sucesso!")
        print("\n📝 Para testar com um vault real, execute:")
        print("   python -m src.cli.main obsidian --vault-path ~/seu-vault vault-status")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_obsidian_integration()
    sys.exit(0 if success else 1)
