# ============ SCRIPT DE BUSCA (execute separadamente) ============
"""
Execute este script no diretório raiz do projeto para encontrar todas as
referências a settings.vault_path
"""

import os
import re
from pathlib import Path

def find_settings_references(root_dir):
    """Busca todas as referências a settings em arquivos Python"""
    
    patterns = [
        r'settings\.vault_path',
        r'settings\.get\s*\(\s*[\'"]vault_path[\'"]',
        r'settings\.value\s*\(\s*[\'"]vault_path[\'"]',
        r'from.*settings.*import',
        r'import.*settings',
    ]
    
    matches = []
    
    for root, dirs, files in os.walk(root_dir):
        # Ignorar diretórios de ambiente virtual e cache
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        for pattern in patterns:
                            if re.search(pattern, content):
                                matches.append((file_path, pattern))
                                
                                # Mostrar contexto
                                print(f"\n🔍 Encontrado em: {file_path}")
                                print(f"📌 Padrão: {pattern}")
                                
                                # Mostrar linhas
                                lines = content.split('\n')
                                for i, line in enumerate(lines, 1):
                                    if re.search(pattern, line):
                                        print(f"   Linha {i}: {line.strip()}")
                                        
                except Exception as e:
                    print(f"⚠️  Erro ao ler {file_path}: {e}")
    
    return matches

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent  # Ajuste conforme necessário
    print(f"🔎 Buscando em: {project_root}")
    
    matches = find_settings_references(project_root)
    
    if matches:
        print(f"\n✅ Encontradas {len(matches)} referências a settings")
        print("\n💡 SOLUÇÃO: Substitua todas as ocorrências por:")
        print("   config_manager.vault_path  # ou ConfigManager.instance().vault_path")
    else:
        print("\n✅ Nenhuma referência a settings.vault_path encontrada")
        print("O erro deve estar em tempo de execução (import dinâmico)")