#!/usr/bin/env python3
"""
Identifica funções documentadas mas não configuradas
Baseado no documento Glados.md
"""
import re
from pathlib import Path
import ast

def extract_functions_from_md(md_file):
    """Extrai funções mencionadas no arquivo Markdown"""
    content = Path(md_file).read_text(encoding='utf-8')
    
    # Padrões para encontrar funções mencionadas
    patterns = [
        r'`([a-zA-Z_][a-zA-Z0-9_]*\(\))',  # `funcao()`
        r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # def funcao
        r'\.([a-zA-Z_][a-zA-Z0-9_]*\(\))',  # .funcao()
        r'"([a-zA-Z_][a-zA-Z0-9_]*)"\s*:',  # "funcao":
    ]
    
    functions = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            # Remove parênteses se houver
            func = match.replace('()', '')
            if func and len(func) > 1:  # Ignora variáveis de uma letra
                functions.add(func)
    
    return sorted(functions)

def extract_python_functions(file_path):
    """Extrai funções definidas em um arquivo Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
        
        return functions
    except Exception as e:
        print(f"⚠️  Erro ao processar {file_path}: {e}")
        return []

def find_python_files(directory):
    """Encontra todos os arquivos Python no diretório"""
    py_files = []
    for path in Path(directory).rglob("*.py"):
        py_files.append(str(path))
    return py_files

def main():
    print("🔍 Identificando funções documentadas mas não implementadas...")
    
    # Extrai funções do documento Glados.md
    documented_functions = extract_functions_from_md("Glados.md")
    print(f"\n📋 Funções documentadas no Glados.md: {len(documented_functions)}")
    
    # Encontra todas as funções implementadas no projeto
    project_root = Path(".")
    src_files = find_python_files("src")
    
    implemented_functions = set()
    for file_path in src_files:
        funcs = extract_python_functions(file_path)
        implemented_functions.update(funcs)
    
    print(f"📋 Funções implementadas no src/: {len(implemented_functions)}")
    
    # Encontra funções documentadas mas não implementadas
    missing_functions = []
    for func in documented_functions:
        if func not in implemented_functions:
            # Verifica se há função similar (case-insensitive)
            func_lower = func.lower()
            implemented_lower = [f.lower() for f in implemented_functions]
            
            if func_lower not in implemented_lower:
                missing_functions.append(func)
    
    print(f"\n⚠️  Funções documentadas mas NÃO implementadas: {len(missing_functions)}")
    
    if missing_functions:
        print("\n" + "="*80)
        print("❌ FUNÇÕES FALTANDO")
        print("="*80)
        
        # Agrupa por categoria baseada no nome
        categories = {}
        for func in sorted(missing_functions):
            # Tenta determinar categoria
            if func.startswith(('get_', 'find_', 'list_')):
                cat = "Consultas"
            elif func.startswith(('add_', 'create_', 'update_', 'delete_')):
                cat = "CRUD"
            elif func.startswith(('is_', 'has_', 'can_')):
                cat = "Verificações"
            elif func.endswith(('_manager', '_handler')):
                cat = "Gerenciadores"
            elif func.endswith(('_config', '_settings')):
                cat = "Configurações"
            else:
                cat = "Outras"
            
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(func)
        
        # Imprime por categoria
        for category, funcs in categories.items():
            print(f"\n📁 {category} ({len(funcs)}):")
            for func in funcs:
                print(f"   • {func}()")
        
        # Salva relatório
        with open("missing_functions_report.txt", "w", encoding="utf-8") as f:
            f.write("Funções documentadas mas não implementadas:\n\n")
            for category, funcs in categories.items():
                f.write(f"{category}:\n")
                for func in funcs:
                    f.write(f"  - {func}()\n")
                f.write("\n")
    else:
        print("\n✅ Todas as funções documentadas estão implementadas!")
    
    # Também mostra funções implementadas mas não documentadas
    print(f"\n🔍 Funções implementadas mas NÃO documentadas:")
    undocumented = []
    for func in implemented_functions:
        if func not in documented_functions:
            # Verifica se há similar no documento (case-insensitive)
            func_lower = func.lower()
            documented_lower = [f.lower() for f in documented_functions]
            
            if func_lower not in documented_lower:
                undocumented.append(func)
    
    if undocumented:
        print(f"\n📝 Considerar documentar ({len(undocumented)}):")
        for func in sorted(undocumented)[:20]:  # Mostra apenas as primeiras 20
            print(f"   • {func}()")
        
        if len(undocumented) > 20:
            print(f"   ... e mais {len(undocumented) - 20}")
    else:
        print("✅ Todas as funções implementadas estão documentadas!")

if __name__ == "__main__":
    main()
