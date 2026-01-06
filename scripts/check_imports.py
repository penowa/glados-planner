# scripts/check_imports.py
#!/usr/bin/env python3
"""
Verifica todos os imports no projeto.
"""

import ast
import os
from pathlib import Path

def check_imports_in_file(filepath: Path):
    """Verifica imports em um arquivo Python."""
    print(f"\n🔍 Verificando: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    print(f"  import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                print(f"  from {module} import {[n.name for n in node.names]}")
                
    except Exception as e:
        print(f"  ❌ Erro: {e}")

def main():
    project_root = Path(__file__).parent.parent
    
    for py_file in project_root.rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        
        check_imports_in_file(py_file)

if __name__ == "__main__":
    main()
