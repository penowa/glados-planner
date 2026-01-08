#!/usr/bin/env python3
"""
Teste rápido do TinyLlama com a estrutura atual do projeto
"""
import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_settings():
    """Testa as configurações do sistema"""
    print("🧪 Testando configurações...")
    from src.core.config.settings import settings
    
    print(f"📁 BASE_DIR: {settings.BASE_DIR}")
    print(f"📁 DATA_DIR: {settings.DATA_DIR}")
    print(f"📁 MODELS_DIR: {settings.MODELS_DIR}")
    print(f"🤖 MODEL_PATH: {settings.MODEL_PATH}")
    
    # Verifica se o modelo existe
    if settings.MODEL_PATH and settings.MODEL_PATH.exists():
        print(f"✅ Modelo encontrado: {settings.MODEL_PATH.name}")
        return True
    else:
        print(f"❌ Modelo não encontrado em: {settings.MODEL_PATH}")
        return False

def test_wrapper():
    """Testa o wrapper do TinyLlama"""
    print("\n🧪 Testando wrapper do TinyLlama...")
    
    try:
        from src.core.llm.grados.models.tinyllama_wrapper import TinyLlamaGlados, LlamaConfig
        
        # Configuração básica
        config = LlamaConfig(
            model_path=str(Path("data/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")),
            n_ctx=2048,
            n_threads=4
        )
        
        # Tenta criar a instância (sem dependências complexas)
        class MockVault:
            def search_notes(self, query, limit=3):
                return []
            
            def format_as_brain_context(self, notes):
                return "Contexto simulado"
            
            def get_vault_stats(self):
                return {"total_notes": 0}
        
        class MockGladosVoice:
            def format_response(self, query, response):
                return f"Resposta formatada: {response}"
        
        wrapper = TinyLlamaGlados(
            config=config,
            vault_structure=MockVault(),
            glados_voice=MockGladosVoice()
        )
        
        print(f"✅ Wrapper criado com sucesso")
        print(f"📊 Estatísticas: {wrapper.get_stats()}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar wrapper: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_integration():
    """Testa a integração completa do LLM"""
    print("\n🧪 Testando integração LLM...")
    
    try:
        # Primeiro verifica se temos o local_llm.py
        local_llm_path = Path("src/core/llm/local_llm.py")
        if not local_llm_path.exists():
            print("❌ Arquivo local_llm.py não encontrado")
            return False
        
        print("✅ Arquivo local_llm.py encontrado")
        
        # Tenta importar
        from src.core.llm import local_llm
        
        print("✅ Módulo local_llm importado com sucesso")
        
        # Verifica se tem uma instância LLM
        if hasattr(local_llm, 'llm'):
            print("✅ Instância 'llm' encontrada no módulo")
            
            # Tenta obter status
            status = local_llm.llm.get_status() if hasattr(local_llm.llm, 'get_status') else {}
            print(f"📊 Status do LLM: {status}")
            
            return True
        else:
            print("⚠️  Instância 'llm' não encontrada no módulo")
            return False
            
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes"""
    print("🚀 TESTE DE INTEGRAÇÃO TINYLLAMA")
    print("=" * 60)
    
    tests = [
        ("Configurações", test_settings),
        ("Wrapper TinyLlama", test_wrapper),
        ("Integração LLM", test_llm_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            print(f"TESTE: {test_name}")
            print(f"{'='*60}")
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Exceção em {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo
    print(f"\n{'='*60}")
    print("📊 RESUMO DOS TESTES")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 Todos os testes passaram! O LLM está pronto para uso.")
    else:
        print("\n⚠️  Alguns testes falharam. Veja acima para detalhes.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
