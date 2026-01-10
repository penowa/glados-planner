#!/usr/bin/env python3
"""
test_integration_complete.py - Teste completo da integração LLM + Sembrain
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_vault_structure():
    """Testa a estrutura do vault"""
    print("🧠 TESTE 1: VAULT STRUCTURE")
    print("-" * 40)
    
    try:
        from src.core.llm.glados.brain.vault_connector import VaultStructure
        from src.core.config.settings import settings
        
        vault_path = Path(settings.paths.vault).expanduser()
        print(f"📂 Vault path: {vault_path}")
        
        vault = VaultStructure(str(vault_path))
        
        # Ver estatísticas
        stats = vault.get_vault_stats()
        print(f"📊 Estatísticas do vault:")
        print(f"   Total de notas: {stats['total_notes']}")
        
        for folder, count in stats['notes_by_folder'].items():
            if count > 0:
                print(f"   {folder}: {count} notas")
        
        print(f"✅ Busca semântica disponível: {stats['semantic_search']['available']}")
        
        return vault
        
    except Exception as e:
        print(f"❌ Erro no vault: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_sembrain_search(vault):
    """Testa busca semântica"""
    print("\n🔍 TESTE 2: BUSCA SEMÂNTICA")
    print("-" * 40)
    
    try:
        # Testar diferentes tipos de consulta
        test_queries = [
            ("virtude", "Conceito"),
            ("ética", "Disciplina"), 
            ("platão", "Autor"),
            ("filosofia", "Termo geral")
        ]
        
        for query, tipo in test_queries:
            print(f"\nConsulta '{tipo}': '{query}'")
            
            # Busca semântica
            results = vault.search_notes(query, semantic=True, limit=3)
            print(f"   Resultados: {len(results)}")
            
            for i, note in enumerate(results[:2], 1):
                print(f"   {i}. {note.title}")
            
            # Busca detalhada
            detailed = vault.search_detailed(query, limit=1)
            if detailed:
                print(f"   Relevância: {detailed[0]['relevance']:.3f}")
                print(f"   Tipo de busca: {detailed[0]['search_type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na busca: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_integration():
    """Testa integração com LLM"""
    print("\n🤖 TESTE 3: INTEGRAÇÃO COM LLM")
    print("-" * 40)
    
    try:
        from src.core.llm.local_llm import llm
        
        # Verificar status
        status = llm.get_status()
        print(f"📊 Status do LLM: {status['status']}")
        
        if status['status'] == 'loaded':
            print(f"✅ Modelo carregado: {status.get('model', 'Unknown')}")
            print(f"✅ Sembrain disponível: {status['sembrain']['available']}")
            print(f"📈 Notas indexadas: {status['sembrain']['notes_indexed']}")
            
            # Testar busca via LLM
            query = "O que é virtude em Aristóteles?"
            print(f"\n🔍 Consulta LLM: '{query}'")
            
            results = llm.search_notes(query, use_semantic=True, limit=2)
            print(f"   Notas encontradas: {len(results)}")
            
            for i, note in enumerate(results, 1):
                print(f"   {i}. {note['title']} (relevância: {note['relevance']:.3f})")
                print(f"      Tipo: {note['search_type']}")
            
            # Testar geração com contexto semântico
            print(f"\n🧠 Gerando resposta com contexto semântico...")
            response = llm.generate(query, use_semantic=True)
            
            if response['status'] == 'success':
                print(f"✅ Resposta gerada ({len(response['text'])} caracteres)")
                print(f"📊 Usou contexto semântico: {response['semantic_context_used']}")
                
                # Mostrar preview da resposta
                lines = response['text'].split('\n')[:10]
                for i, line in enumerate(lines, 1):
                    if line.strip():
                        print(f"   {i:2}. {line[:80]}{'...' if len(line) > 80 else ''}")
            
            elif response['status'] == 'fallback':
                print(f"⚠️  Resposta em modo fallback (apenas Sembrain)")
                print(f"📝 Preview: {response['text'][:200]}...")
            
            else:
                print(f"❌ Erro: {response.get('error', 'Unknown')}")
        
        else:
            print(f"⚠️  LLM não carregado: {status.get('message', 'Unknown')}")
            
            # Testar modo fallback
            query = "virtude"
            print(f"\n🔍 Testando modo fallback: '{query}'")
            
            results = llm.search_notes(query, use_semantic=True, limit=2)
            print(f"   Notas encontradas (fallback): {len(results)}")
            
            for i, note in enumerate(results, 1):
                print(f"   {i}. {note['title']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na integração LLM: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cli_commands():
    """Testa comandos CLI disponíveis"""
    print("\n💻 TESTE 4: COMANDOS CLI")
    print("-" * 40)
    
    commands = [
        "glados consultar 'virtude' --semantica",
        "glados buscar 'ética' --limite 3",
        "glados estatisticas",
        "glados status"
    ]
    
    print("Comandos disponíveis para testar:")
    for i, cmd in enumerate(commands, 1):
        print(f"{i}. {cmd}")
    
    return True

def main():
    print("🚀 TESTE COMPLETO DE INTEGRAÇÃO - GLaDOS Planner v0.5.0")
    print("=" * 60)
    
    # Testar vault
    vault = test_vault_structure()
    if not vault:
        return 1
    
    # Testar busca semântica
    if not test_sembrain_search(vault):
        print("⚠️  Teste de busca semântica falhou parcialmente")
    
    # Testar integração LLM
    if not test_llm_integration():
        print("⚠️  Teste de integração LLM falhou parcialmente")
    
    # Mostrar comandos CLI
    test_cli_commands()
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DO SISTEMA:")
    print("=" * 60)
    
    # Coletar estatísticas finais
    try:
        from src.core.llm.local_llm import llm
        
        # Status do LLM
        status = llm.get_status()
        print(f"1. LLM Status: {status['status']}")
        
        if status['status'] == 'loaded':
            print(f"   • Modelo: {status.get('model', 'Unknown')}")
            print(f"   • Cache: {status['cache']['hits']} hits")
        
        # Status do Sembrain
        if llm.sembrain:
            sembrain_stats = llm.sembrain.get_stats()
            print(f"2. Sembrain:")
            print(f"   • Notas indexadas: {sembrain_stats['total_notes']}")
            print(f"   • Tamanho do vocabulário: {sembrain_stats['vocabulary_size']}")
            print(f"   • Cache: {sembrain_stats['cache_size']} consultas")
        
        # Status do vault
        if vault:
            vault_stats = vault.get_vault_stats()
            print(f"3. Vault:")
            print(f"   • Total de notas: {vault_stats['total_notes']}")
            print(f"   • Pastas com notas: {sum(1 for v in vault_stats['notes_by_folder'].values() if v > 0)}")
        
        print("\n✅ SISTEMA OPERACIONAL!")
        print("\n🎯 PRÓXIMOS PASSOS:")
        print("1. Use: glados consultar 'sua pergunta' --semantica")
        print("2. Teste: glados buscar 'conceito' --limite 5")
        print("3. Veja estatísticas: glados estatisticas")
        
        return 0
        
    except Exception as e:
        print(f"❌ Erro ao gerar resumo: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
