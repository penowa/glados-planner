#!/usr/bin/env python3
"""
Teste de funcionalidade - Testa se as funções estão configuradas corretamente
"""
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_database():
    """Testa funcionalidades do banco de dados"""
    print("🧪 Testando banco de dados...")
    
    try:
        from src.core.database.base import init_db, SessionLocal, Base
        
        # Cria um diretório temporário para teste
        temp_dir = tempfile.mkdtemp()
        os.environ['DATA_DIR'] = temp_dir
        
        # Tenta inicializar o banco
        init_db()
        print("✅ init_db() funciona")
        
        # Tenta criar uma sessão
        db = SessionLocal()
        db.close()
        print("✅ SessionLocal() funciona")
        
        # Limpa
        shutil.rmtree(temp_dir)
        return True
        
    except Exception as e:
        print(f"❌ Erro no banco de dados: {e}")
        return False

def test_settings():
    """Testa configurações"""
    print("\n🧪 Testando configurações...")
    
    try:
        from src.core.config.settings import settings
        
        print(f"✅ Settings carregadas")
        print(f"   ├── App: {settings.app.name}")
        print(f"   ├── Versão: {settings.app.version}")
        print(f"   └── Vault: {settings.paths.vault}")
        return True
        
    except Exception as e:
        print(f"❌ Erro nas configurações: {e}")
        return False

def test_vault_manager():
    """Testa o gerenciador de vault"""
    print("\n🧪 Testando VaultManager...")
    
    try:
        from src.core.vault.manager import VaultManager
        
        # Cria diretório temporário
        temp_vault = tempfile.mkdtemp()
        
        # Testa criação
        manager = VaultManager(temp_vault)
        print("✅ VaultManager instanciado")
        
        # Testa criação de estrutura
        result = manager.create_structure()
        if result:
            print("✅ create_structure() funciona")
        else:
            print("⚠️  create_structure() retornou False")
        
        # Testa verificação de conexão
        if manager.is_connected():
            print("✅ is_connected() funciona")
        
        # Limpa
        shutil.rmtree(temp_vault)
        return True
        
    except Exception as e:
        print(f"❌ Erro no VaultManager: {e}")
        return False

def test_cli_commands():
    """Testa comandos CLI"""
    print("\n🧪 Testando comandos CLI...")
    
    try:
        from src.cli.main import app
        from src.cli.glados import add_glados_to_cli
        
        print("✅ CLI app importado")
        print("✅ Função add_glados_to_cli importada")
        
        # Verifica comandos disponíveis
        commands = [cmd.name for cmd in app.registered_commands]
        print(f"✅ Comandos disponíveis: {len(commands)}")
        
        for cmd in sorted(commands):
            print(f"   ├── {cmd}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no CLI: {e}")
        return False

def test_glados_functionality():
    """Testa funcionalidades específicas do GLaDOS"""
    print("\n🧪 Testando funcionalidades GLaDOS...")
    
    try:
        from src.cli.glados import add_glados_to_cli
        
        print("✅ Módulo GLaDOS importado")
        
        # Testa importação de configurações GLaDOS
        from src.core.config.settings import settings
        glados_config = settings.llm.glados
        
        print(f"✅ Configurações GLaDOS carregadas")
        print(f"   ├── Usuário: {glados_config.user_name}")
        print(f"   ├── Nome GLaDOS: {glados_config.gladios_name}")
        print(f"   └── Intensidade: {glados_config.personality_intensity}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nas funcionalidades GLaDOS: {e}")
        return False

def test_all():
    """Executa todos os testes"""
    print("🚀 Iniciando testes de funcionalidade...")
    print("="*80)
    
    results = {
        "database": test_database(),
        "settings": test_settings(),
        "vault_manager": test_vault_manager(),
        "cli_commands": test_cli_commands(),
        "glados": test_glados_functionality(),
    }
    
    print("\n" + "="*80)
    print("📊 RESUMO DOS TESTES DE FUNCIONALIDADE")
    print("="*80)
    
    passes = sum(results.values())
    total = len(results)
    
    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print(f"\n🎯 Resultado: {passes}/{total} testes passaram")
    
    # Salva relatório
    with open("functionality_test_report.txt", "w", encoding="utf-8") as f:
        f.write(f"PASS: {passes}\n")
        f.write(f"FAIL: {total - passes}\n\n")
        
        for test_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            f.write(f"{status}: {test_name}\n")
    
    return all(results.values())

if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
