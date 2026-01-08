#!/usr/bin/env python3
"""
Teste de integração da GLaDOS com TinyLlama
"""
import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Testa as importações básicas"""
    print("🧪 Testando importações...")
    
    try:
        from src.core.config.settings import settings
        print(f"✅ Settings importado")
        print(f"   Model path: {settings.llm.model_path}")
        return True
    except Exception as e:
        print(f"❌ Erro importando settings: {e}")
        return False

def test_vault_connector():
    """Testa o conector do vault"""
    print("\n🧪 Testando VaultConnector...")
    
    try:
        from src.core.llm.glados.brain.vault_connector import VaultStructure
        from src.core.config.settings import settings
        
        vault_path = Path(settings.paths.vault).expanduser()
        if not vault_path.exists():
            print(f"⚠️  Vault não encontrado: {vault_path}")
            return False
        
        vault = VaultStructure(str(vault_path))
        stats = vault.get_vault_stats()
        print(f"✅ Vault conectado: {stats['total_notes']} notas")
        return True
    except Exception as e:
        print(f"❌ Erro no vault connector: {e}")
        return False

def test_glados_voice():
    """Testa a voz da GLaDOS"""
    print("\n🧪 Testando GladosVoice...")
    
    try:
        from src.core.llm.glados.personality.glados_voice import GladosVoice
        
        voice = GladosVoice()
        response = voice.format_response("Teste", "Resposta de teste")
        print(f"✅ GladosVoice funcionando: {response[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Erro no GladosVoice: {e}")
        return False

def test_tinyllama_wrapper():
    """Testa o wrapper do TinyLlama"""
    print("\n🧪 Testando TinyLlama wrapper...")
    
    try:
        from src.core.llm.glados.models.tinyllama_wrapper import TinyLlamaGlados, LlamaConfig
        from src.core.llm.glados.brain.vault_connector import VaultStructure
        from src.core.llm.glados.personality.glados_voice import GladosVoice
        from src.core.config.settings import settings
        
        # Verifica se o modelo existe
        model_path = Path(settings.llm.model_path)
        if not model_path.is_absolute():
            model_path = Path(__file__).parent / model_path
        
        if not model_path.exists():
            print(f"❌ Modelo não encontrado: {model_path}")
            return False
        
        print(f"✅ Modelo encontrado: {model_path}")
        
        # Configuração
        config = LlamaConfig(
            model_path=str(model_path),
            n_ctx=settings.llm.n_ctx,
            n_threads=settings.llm.cpu.threads
        )
        
        # Vault
        vault_path = Path(settings.paths.vault).expanduser()
        vault_structure = VaultStructure(str(vault_path))
        
        # Voz
        glados_voice = GladosVoice()
        
        # Cria wrapper
        wrapper = TinyLlamaGlados(config, vault_structure, glados_voice)
        
        print(f"✅ Wrapper criado com sucesso")
        print(f"📊 Stats: {wrapper.get_stats()}")
        
        return True
    except Exception as e:
        print(f"❌ Erro no wrapper: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_local_llm():
    """Testa o módulo local_llm"""
    print("\n🧪 Testando LocalLLM...")
    
    try:
        from src.core.llm import local_llm
        
        # A instância 'llm' deve estar disponível
        if hasattr(local_llm, 'llm'):
            status = local_llm.llm.get_status()
            print(f"📊 Status do LLM: {status}")
            
            if status.get('status') == 'loaded':
                print("\n🤖 Testando geração...")
                response = local_llm.llm.generate("O que é filosofia?")
                print(f"Resposta: {response['text'][:200]}...")
                return True
            else:
                print("❌ Modelo não carregado")
                return False
        else:
            print("❌ Instância 'llm' não encontrada")
            return False
            
    except Exception as e:
        print(f"❌ Erro no local_llm: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes"""
    print("🚀 TESTE DE INTEGRAÇÃO GLaDOS")
    print("=" * 60)
    
    tests = [
        ("Importações", test_imports),
        ("Vault Connector", test_vault_connector),
        ("Glados Voice", test_glados_voice),
        ("TinyLlama Wrapper", test_tinyllama_wrapper),
        ("Local LLM", test_local_llm),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"TESTE: {test_name}")
        print(f"{'='*60}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Exceção: {e}")
            results.append((test_name, False))
    
    # Resumo
    print(f"\n{'='*60}")
    print("📊 RESUMO")
    print(f"{'='*60}")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 Resultado: {passed}/{len(results)} testes passaram")
    
    if passed == len(results):
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("   Execute: python -m src.cli.glados consultar 'O que é filosofia?'")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique acima.")

if __name__ == "__main__":
    main()
