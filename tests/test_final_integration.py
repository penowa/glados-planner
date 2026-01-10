#!/usr/bin/env python3
"""
test_final_integration.py - Teste final corrigido
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_complete():
    print("🚀 TESTE FINAL DO SISTEMA GLaDOS - VERSÃO CORRIGIDA")
    print("=" * 60)
    
    try:
        from src.core.llm.local_llm import llm
        
        # 1. Verificar status
        print("\n📊 STATUS DO SISTEMA")
        print("-" * 40)
        
        status = llm.get_status()
        print(f"LLM: {status['status']}")
        print(f"Modelo: {status.get('model', 'N/A')}")
        print(f"Sembrain disponível: {status['sembrain']['available']}")
        print(f"Notas indexadas: {status['sembrain']['notes_indexed']}")
        
        # 2. Testar busca semântica
        print("\n🔍 TESTE DE BUSCA SEMÂNTICA")
        print("-" * 40)
        
        test_queries = [
            "virtude aristóteles",
            "ética filosófica",
            "platão república",
            "teleologia"
        ]
        
        for query in test_queries:
            print(f"\nConsulta: '{query}'")
            results = llm.search_notes(query, use_semantic=True, limit=2)
            print(f"  Resultados: {len(results)}")
            
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['title']} (relevância: {result['relevance']:.3f}, tipo: {result['search_type']})")
        
        # 3. Testar geração com contexto semântico
        print("\n🤖 TESTE DE GERAÇÃO COM CONTEXTO SEMÂNTICO")
        print("-" * 40)
        
        query = "Explique o conceito de virtude em Aristóteles"
        print(f"Consulta: '{query}'")
        
        response = llm.generate(query, use_semantic=True)
        
        print(f"Status: {response['status']}")
        print(f"Usou contexto semântico: {response.get('semantic_context_used', False)}")
        print(f"Tamanho da resposta: {len(response['text'])} caracteres")
        
        # Mostrar parte da resposta
        print("\n📝 Parte da resposta:")
        lines = response['text'].split('\n')
        for line in lines[:5]:
            if line.strip():
                print(f"  {line[:100]}" + ("..." if len(line) > 100 else ""))
        
        # 4. Testar busca detalhada
        print("\n📋 TESTE DE BUSCA DETALHADA")
        print("-" * 40)
        
        if llm.vault_structure:
            detailed = llm.vault_structure.search_detailed("ética", limit=2)
            print(f"Resultados detalhados: {len(detailed)}")
            for i, result in enumerate(detailed, 1):
                print(f"\n  {i}. {result['note'].get('title', 'Sem título')}")
                print(f"     Relevância: {result.get('relevance', 0):.3f}")
                print(f"     Tipo: {result.get('search_type', 'N/A')}")
                if result.get('excerpt'):
                    print(f"     Trecho: {result['excerpt'][:100]}...")
        
        # 5. Estatísticas do sistema
        print("\n📈 ESTATÍSTICAS FINAIS")
        print("-" * 40)
        
        if llm.vault_structure:
            vault_stats = llm.vault_structure.get_vault_stats()
            print(f"Total de notas no vault: {vault_stats['total_notes']}")
            print(f"Busca semântica disponível: {vault_stats['semantic_search']['available']}")
        
        print(f"Respostas em cache: {len(llm.response_cache)}")
        print(f"Histórico de consultas: {len(llm.query_history)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ SISTEMA FUNCIONANDO CORRETAMENTE!")
        print("\n🎯 COMANDOS PARA TESTAR:")
        print("  glados consultar 'o que é eudaimonia' --semantica")
        print("  glados buscar 'aristóteles' --limite 3")
        print("  glados status")
    else:
        print("⚠️  ALGUNS PROBLEMAS FORAM ENCONTRADOS")
    
    sys.exit(0 if success else 1)
