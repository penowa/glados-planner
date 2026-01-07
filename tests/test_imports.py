#!/usr/bin/env python3
"""
Teste de importações básicas - Verifica se todas as funções documentadas existem
"""
import sys
import os
from pathlib import Path
import importlib
from typing import List, Tuple, Dict, Any

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

class ImportTester:
    """Testa importações de módulos e funções documentadas"""
    
    def __init__(self):
        self.results = []
        self.errors = []
        
    def test_import(self, module_path: str, class_name: str = None, 
                   function_names: List[str] = None) -> Dict[str, Any]:
        """Testa uma importação específica"""
        result = {
            "module": module_path,
            "class": class_name,
            "functions": function_names or [],
            "status": "PENDING",
            "errors": []
        }
        
        try:
            # Tenta importar o módulo
            module = importlib.import_module(module_path)
            result["status"] = "MODULE_OK"
            
            # Se há classe para testar
            if class_name:
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    result["status"] = "CLASS_OK"
                    
                    # Testa funções da classe
                    if function_names:
                        for func_name in function_names:
                            if hasattr(cls, func_name):
                                result["functions_status"] = "ALL_FUNCTIONS_OK"
                            else:
                                result["errors"].append(f"Função '{func_name}' não encontrada na classe {class_name}")
                else:
                    result["errors"].append(f"Classe '{class_name}' não encontrada no módulo")
            
            # Se não há classe, testa funções diretamente no módulo
            elif function_names:
                for func_name in function_names:
                    if hasattr(module, func_name):
                        result["functions_status"] = "ALL_FUNCTIONS_OK"
                    else:
                        result["errors"].append(f"Função '{func_name}' não encontrada no módulo")
                        
        except ImportError as e:
            result["status"] = "IMPORT_ERROR"
            result["errors"].append(f"Erro ao importar módulo: {e}")
        except Exception as e:
            result["status"] = "OTHER_ERROR"
            result["errors"].append(f"Erro inesperado: {e}")
            
        # Determina status final
        if result["errors"]:
            result["final_status"] = "FAIL"
        else:
            result["final_status"] = "PASS"
            
        self.results.append(result)
        return result
    
    def print_results(self):
        """Imprime resultados formatados"""
        print("\n" + "="*80)
        print("📊 RESULTADOS DOS TESTES DE IMPORTAÇÃO")
        print("="*80)
        
        passes = 0
        fails = 0
        
        for result in self.results:
            status_symbol = "✅" if result["final_status"] == "PASS" else "❌"
            print(f"\n{status_symbol} Módulo: {result['module']}")
            
            if result.get('class'):
                print(f"   ├── Classe: {result['class']}")
            
            if result.get('functions'):
                print(f"   ├── Funções: {', '.join(result['functions'])}")
            
            print(f"   ├── Status: {result['status']}")
            
            if result['errors']:
                print(f"   └── Erros:")
                for error in result['errors']:
                    print(f"        • {error}")
                fails += 1
            else:
                passes += 1
                
        print(f"\n{'='*80}")
        print(f"📈 RESUMO: {passes} ✅ | {fails} ❌")
        print("="*80)
        
        # Salva relatório em arquivo
        with open("test_imports_report.txt", "w", encoding="utf-8") as f:
            f.write(f"PASS: {passes}\n")
            f.write(f"FAIL: {fails}\n\n")
            
            for result in self.results:
                if result['errors']:
                    f.write(f"❌ {result['module']}\n")
                    for error in result['errors']:
                        f.write(f"   - {error}\n")
                    f.write("\n")

def test_documented_functions():
    """Testa todas as funções documentadas baseadas no README e arquivos"""
    
    tester = ImportTester()
    
    # ============ CORE DATABASE ============
    print("🧪 Testando módulos de banco de dados...")
    tester.test_import("src.core.database.base", None, 
                      ["init_db", "get_db", "SessionLocal", "Base", "engine"])
    
    # ============ CORE CONFIG ============
    print("🧪 Testando módulos de configuração...")
    tester.test_import("src.core.config.settings", "Settings", [])
    
    # ============ CORE VAULT ============
    print("🧪 Testando módulos de vault...")
    tester.test_import("src.core.vault.manager", "VaultManager",
                      ["is_connected", "create_structure"])
    
    # ============ CLI ============
    print("🧪 Testando módulos CLI...")
    tester.test_import("src.cli.main", None, 
                      ["app", "console", "init", "status", "version"])
    
    tester.test_import("src.cli.glados", None,
                      ["add_glados_to_cli", "console"])
    
    # ============ TESTE DE COMANDOS DOCUMENTADOS ============
    print("🧪 Testando funções documentadas no README...")
    
    # Comandos básicos do sistema
    tester.test_import("src.cli.main", None, ["init", "status", "version"])
    
    # Comandos GLaDOS
    tester.test_import("src.cli.glados", None, 
                      ["add_glados_to_cli"])
    
    # ============ VERIFICAÇÃO DE MÓDULOS FALTANTES ============
    print("\n🔍 Verificando módulos documentados mas não implementados...")
    
    documented_modules = [
        # Módulos mencionados no Glados.md
        ("src.core.llm.local_llm", "PhilosophyLLM", 
         ["summarize", "analyze_argument", "generate_questions"]),
        
        ("src.core.database.obsidian_sync", "VaultManager", 
         ["sync_from_obsidian", "sync_to_obsidian"]),
        
        ("src.core.modules.reading_manager", "ReadingManager",
         ["get_reading_progress", "update_progress", "generate_schedule"]),
        
        ("src.core.modules.agenda_manager", "AgendaManager",
         ["get_daily_summary", "add_event", "get_overdue_tasks"]),
        
        ("src.cli.commands.data_commands", None,
         ["list_books", "add_book", "stats"]),
        
        # Módulos do fluxo de trabalho
        ("src.core.modules.translation_module", "TranslationAssistant",
         ["translate_term", "get_pronunciation"]),
        
        ("src.core.modules.pomodoro_timer", "PomodoroTimer",
         ["start", "pause", "resume", "get_stats"]),
        
        ("src.core.modules.writing_assistant", "WritingAssistant",
         ["structure_paper", "check_norms", "export_document"]),
        
        ("src.core.modules.review_system", "ReviewSystem",
         ["generate_flashcards", "create_quiz", "spaced_repetition"]),
    ]
    
    for module_path, class_name, functions in documented_modules:
        print(f"\n🔎 Verificando: {module_path}")
        try:
            importlib.import_module(module_path)
            print(f"   ✅ Módulo existe")
            
            if class_name:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    print(f"   ✅ Classe '{class_name}' existe")
                    cls = getattr(module, class_name)
                    
                    for func in functions:
                        if hasattr(cls, func):
                            print(f"   ✅ Função '{func}' existe")
                        else:
                            print(f"   ⚠️  Função '{func}' FALTANDO")
                else:
                    print(f"   ❌ Classe '{class_name}' NÃO ENCONTRADA")
        except ImportError:
            print(f"   ❌ Módulo NÃO IMPLEMENTADO")
        except Exception as e:
            print(f"   ⚠️  Erro ao verificar: {e}")
    
    print("\n" + "="*80)
    print("📋 RESUMO DOS MÓDULOS FALTANTES")
    print("="*80)
    
    missing_modules = []
    for module_path, class_name, functions in documented_modules:
        try:
            importlib.import_module(module_path)
        except ImportError:
            missing_modules.append(module_path)
            print(f"❌ {module_path}")
            
            if class_name:
                print(f"   └── Classe: {class_name}")
                if functions:
                    print(f"        └── Funções: {', '.join(functions)}")
    
    # Salva relatório de módulos faltantes
    if missing_modules:
        with open("missing_modules.txt", "w", encoding="utf-8") as f:
            f.write("Módulos documentados mas não implementados:\n\n")
            for module in missing_modules:
                f.write(f"- {module}\n")
    
    # ============ IMPRIME RESULTADOS ============
    tester.print_results()
    
    return tester

if __name__ == "__main__":
    print("🧪 Iniciando testes de importação...")
    tester = test_documented_functions()
    
    # Se houver erros, mostra recomendações
    if any(r["final_status"] == "FAIL" for r in tester.results):
        print("\n" + "="*80)
        print("💡 RECOMENDAÇÕES")
        print("="*80)
        
        print("\nMódulos prioritários para implementar:")
        print("1. src.core.llm.local_llm - Assistente LLM local")
        print("2. src.cli.commands.data_commands - Comandos de gestão de dados")
        print("3. src.core.modules.reading_manager - Gestor de leituras")
        print("4. src.core.modules.agenda_manager - Gestor de agenda")
        
        print("\nPróximos passos:")
        print("1. Execute: python tests/test_imports.py")
        print("2. Veja o relatório em: test_imports_report.txt")
        print("3. Veja módulos faltantes em: missing_modules.txt")
