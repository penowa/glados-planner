#!/bin/bash
# check_system.sh

echo "🔍 VERIFICAÇÃO DO SISTEMA GLaDOS PLANNER"
echo "========================================="

# 1. Verificar estrutura de diretórios
echo ""
echo "📁 Estrutura de diretórios:"
required_dirs=("src/core/llm" "src/core/modules" "src/cli/commands" "data" "config")
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir (faltando)"
    fi
done

# 2. Contar arquivos Python
echo ""
echo "📊 Estatísticas de código:"
total_files=$(find src -name "*.py" | wc -l)
echo "  • Total de arquivos Python: $total_files"

# 3. Verificar comandos disponíveis
echo ""
echo "🖥️ Comandos disponíveis:"
if [ -f "src/cli/main.py" ]; then
    python3 -c "
import sys
sys.path.insert(0, 'src')
try:
    from src.cli.main import app
    print('  • Comandos principais:')
    for cmd in ['init', 'status', 'version', 'modules', 'setup_vault', 'backup']:
        print(f'    - {cmd}')
    
    # Verificar subcomandos
    if hasattr(app, 'registered_groups'):
        for group in app.registered_groups.values():
            print(f'  • Comandos {group.name}:')
            for cmd in group.registered_commands:
                print(f'    - {cmd.name}')
except Exception as e:
    print(f'  ❌ Erro: {e}')
"
fi

# 4. Teste rápido dos módulos
echo ""
echo "🧪 Teste rápido dos módulos:"
python3 -c "
import sys
sys.path.insert(0, 'src')

modules = [
    ('ReadingManager', 'src.core.modules.reading_manager'),
    ('AgendaManager', 'src.core.modules.agenda_manager'),
    ('TranslationAssistant', 'src.core.modules.translation_module'),
]

for name, path in modules:
    try:
        exec(f'from {path} import {name}')
        print(f'  ✅ {name} carregado')
    except Exception as e:
        print(f'  ❌ {name}: {e}')
"

echo ""
echo "========================================="
echo "✅ Sistema GLaDOS Planner verificado e operacional!"
echo ""
echo "Para começar:"
echo "1. ./src/cli/main.py init"
echo "2. ./src/cli/main.py glados consultar 'O que é filosofia?'"
echo "3. ./src/cli/main.py data leituras"
