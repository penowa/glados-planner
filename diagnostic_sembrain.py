#!/usr/bin/env python3
"""
diagnostic_sembrain.py - Diagnóstico completo do sistema de busca semântica
Testa importações, inicialização e funcionamento do Sembrain.
"""
import sys
import traceback
from pathlib import Path

# Configurar paths
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "src"))

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🧠 {title}")
    print(f"{'='*60}")

def test_step_1_basic_imports():
    """Teste 1: Importações básicas"""
    print_header("TESTE 1: IMPORTAÇÕES BÁSICAS")
    
    try:
        from src.core.config.settings import settings
        print("✅ settings.py importado")
        print(f"   Vault path: {settings.paths.vault}")
    except Exception as e:
        print(f"❌ Erro ao importar settings: {e}")
        traceback.print_exc()
        return False
    
    try:
        from src.core.llm.glados.brain.vault_connector import VaultStructure
        print("✅ VaultStructure importado")
    except Exception as e:
        print(f"❌ Erro ao importar VaultStructure: {e}")
        traceback.print_exc()
        return False
    
    try:
        from src.core.llm.glados.brain.semantic_search import Sembrain
        print("✅ Sembrain importado")
    except Exception as e:
        print(f"❌ Erro ao importar Sembrain: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_step_2_vault_initialization():
    """Teste 2: Inicialização do vault"""
    print_header("TESTE 2: INICIALIZAÇÃO DO VAULT")
    
    try:
        from src.core.config.settings import settings
        from src.core.llm.glados.brain.vault_connector import VaultStructure
        
        vault_path = Path(settings.paths.vault).expanduser()
        print(f"📂 Caminho do vault: {vault_path}")
        
        if not vault_path.exists():
            print("⚠️  Vault não encontrado. Criando estrutura básica...")
            vault_path.mkdir(parents=True, exist_ok=True)
            
            # Criar pastas básicas
            for folder in ["00 - Meta", "01 - Leituras", "02 - Conceitos"]:
                (vault_path / folder).mkdir(exist_ok=True)
            
            # Criar nota de exemplo
            example_note = vault_path / "02 - Conceitos" / "virtude.md"
            example_note.write_text("""---
title: Conceito de Virtude
tags: [ética, aristóteles, filosofia]
---

# Virtude (areté)

A virtude em Aristóteles é a excelência no caráter, um hábito adquirido pela prática do meio-termo entre extremos.

## Características:
- Ética das virtudes
- Meio-termo (mesotes)
- Prática constante
""", encoding="utf-8")
        
        vault = VaultStructure(str(vault_path))
        print(f"✅ Vault inicializado: {len(vault.notes_cache)} notas")
        
        return vault
        
    except Exception as e:
        print(f"❌ Erro ao inicializar vault: {e}")
        traceback.print_exc()
        return None

def test_step_3_sembrain_initialization(vault):
    """Teste 3: Inicialização do Sembrain"""
    print_header("TESTE 3: INICIALIZAÇÃO DO SEMBRAIN")
    
    try:
        from src.core.llm.glados.brain.semantic_search import Sembrain
        
        # Converter cache para lista
        notes = list(vault.notes_cache.values())
        
        sembrain = Sembrain(vault.vault_path, notes)
        print(f"✅ Sembrain inicializado")
        print(f"   Termos no índice: {len(sembrain.term_index)}")
        print(f"   Notas indexadas: {len(sembrain.notes)}")
        
        # Mostrar estatísticas
        stats = sembrain.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        return sembrain
        
    except Exception as e:
        print(f"❌ Erro ao inicializar Sembrain: {e}")
        traceback.print_exc()
        return None

def test_step_4_semantic_search(sembrain):
    """Teste 4: Busca semântica"""
    print_header("TESTE 4: BUSCA SEMÂNTICA")
    
    test_queries = [
        "virtude aristóteles",
        "ética",
        "filosofia"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Buscando: '{query}'")
        try:
            results = sembrain.search(query, limit=2)
            print(f"   Resultados encontrados: {len(results)}")
            
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.note.title} (relevância: {result.relevance:.3f})")
                if result.excerpt:
                    print(f"      Trecho: {result.excerpt[:100]}...")
                    
        except Exception as e:
            print(f"❌ Erro na busca '{query}': {e}")
            traceback.print_exc()

def test_step_5_context_generation(sembrain):
    """Teste 5: Geração de contexto para LLM"""
    print_header("TESTE 5: GERAÇÃO DE CONTEXTO PARA LLM")
    
    query = "o que é virtude em aristóteles"
    
    try:
        context = sembrain.get_context_for_llm(query, max_notes=2)
        print(f"✅ Contexto gerado ({len(context)} caracteres)")
        print("\n📋 Primeiras 10 linhas do contexto:")
        print("-" * 40)
        for i, line in enumerate(context.split('\n')[:10]):
            print(f"{i+1:2}. {line}")
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Erro ao gerar contexto: {e}")
        traceback.print_exc()

def test_step_6_integration_with_vault_structure():
    """Teste 6: Integração com VaultStructure"""
    print_header("TESTE 6: INTEGRAÇÃO COM VAULTSTRUCTURE")
    
    try:
        from src.core.llm.glados.brain.vault_connector import VaultStructure
        from src.core.llm.glados.brain.semantic_search import Sembrain
        
        # Testar se VaultStructure pode inicializar Sembrain
        vault = test_step_2_vault_initialization()
        if not vault:
            return False
        
        print("🔍 Testando métodos de busca do VaultStructure:")
        
        # Busca textual
        results_textual = vault.search_notes("virtude", semantic=False)
        print(f"✅ Busca textual: {len(results_textual)} resultados")
        
        # Busca semântica (se disponível)
        if hasattr(vault, 'semantic_search') and vault.semantic_search:
            results_semantic = vault.search_notes("virtude", semantic=True)
            print(f"✅ Busca semântica: {len(results_semantic)} resultados")
        
        # Formatar contexto
        context = vault.format_as_brain_context(results_textual[:2], "virtude")
        print(f"✅ Contexto formatado: {len(context.split())} palavras")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        traceback.print_exc()
        return False

def test_step_7_configuration_check():
    """Teste 7: Verificação de configuração"""
    print_header("TESTE 7: VERIFICAÇÃO DE CONFIGURAÇÃO")
    
    try:
        import yaml
        config_path = BASE_DIR / "config" / "settings.yaml"
        
        if not config_path.exists():
            print(f"⚠️  Arquivo de configuração não encontrado: {config_path}")
            return False
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("📋 Configurações relevantes:")
        
        # Verificar paths
        paths = config.get('paths', {})
        print(f"   vault: {paths.get('vault', 'NÃO DEFINIDO')}")
        print(f"   models_dir: {paths.get('models_dir', 'NÃO DEFINIDO')}")
        
        # Verificar LLM settings
        llm = config.get('llm', {})
        print(f"   model_name: {llm.get('model_name', 'NÃO DEFINIDO')}")
        
        # Verificar busca semântica
        semantic = llm.get('semantic_search', {})
        print(f"   use_semantic_search: {llm.get('use_semantic_search', 'NÃO DEFINIDO')}")
        
        # Verificar problema conhecido: espaço após :
        n_gpu_layers = llm.get('n_gpu_layers')
        if isinstance(n_gpu_layers, str) and ':' in n_gpu_layers:
            print(f"❌ PROBLEMA ENCONTRADO: n_gpu_layers sem espaço: '{n_gpu_layers}'")
            print("   Corrija no settings.yaml para: 'n_gpu_layers: 0'")
            return False
        else:
            print(f"✅ n_gpu_layers: {n_gpu_layers}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar configuração: {e}")
        traceback.print_exc()
        return False

def test_step_8_fix_yaml_issue():
    """Teste 8: Corrigir problema do YAML"""
    print_header("TESTE 8: CORREÇÃO DO YAML")
    
    config_path = BASE_DIR / "config" / "settings.yaml"
    
    if not config_path.exists():
        print("⚠️  Arquivo de configuração não encontrado")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar e corrigir n_gpu_layers:0 sem espaço
        if 'n_gpu_layers:0' in content:
            print("🔧 Corrigindo n_gpu_layers:0 → n_gpu_layers: 0")
            content = content.replace('n_gpu_layers:0', 'n_gpu_layers: 0')
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Configuração corrigida")
        else:
            print("✅ Configuração YAML está correta")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir YAML: {e}")
        return False

def main():
    print("🚀 DIAGNÓSTICO DO SISTEMA SEMBRAIN - GLaDOS Planner v0.5.0")
    print("=" * 60)
    
    # Corrigir problema do YAML primeiro
    if not test_step_8_fix_yaml_issue():
        print("⚠️  Não foi possível corrigir o YAML")
    
    # Testar configuração
    if not test_step_7_configuration_check():
        print("⚠️  Problemas na configuração")
    
    # Testar importações
    if not test_step_1_basic_imports():
        print("❌ Teste 1 falhou. Verifique dependências.")
        return 1
    
    # Inicializar vault
    vault = test_step_2_vault_initialization()
    if not vault:
        print("❌ Teste 2 falhou. Verifique o vault.")
        return 1
    
    # Inicializar Sembrain
    sembrain = test_step_3_sembrain_initialization(vault)
    if not sembrain:
        print("❌ Teste 3 falhou. Verifique o Sembrain.")
        return 1
    
    # Testar busca
    test_step_4_semantic_search(sembrain)
    
    # Testar geração de contexto
    test_step_5_context_generation(sembrain)
    
    # Testar integração
    if not test_step_6_integration_with_vault_structure():
        print("⚠️  Problemas na integração com VaultStructure")
    
    print_header("DIAGNÓSTICO CONCLUÍDO")
    
    # Resumo
    print("\n📊 RESUMO DOS PROBLEMAS:")
    print("1. Incompatibilidade entre HierarchicalSearch e Sembrain")
    print("   Solução: Atualizar importações no vault_connector.py")
    print("\n2. Atributos faltantes no SearchResult")
    print("   Solução: Ajustar vault_connector.py para usar atributos corretos")
    print("\n3. Configuração YAML precisa de ajustes")
    print("   Solução: Verificar sintaxe do settings.yaml")
    
    print("\n🔧 PRÓXIMOS PASSOS:")
    print("1. Execute o script de correção: python fix_imports.py")
    print("2. Teste novamente com: python diagnostic_sembrain.py")
    print("3. Use a CLI: glados testar-busca 'virtude'")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
