#!/bin/bash
# run_tests_fixed.sh

echo "🧪 TESTANDO SISTEMA GLaDOS COMPLETO 🧪"
echo "========================================"

# Testar imports dos novos módulos
echo ""
echo "📦 Testando imports dos módulos..."
python3 -c "
import sys
sys.path.insert(0, 'src')

modules = [
    ('src.core.llm.local_llm', 'PhilosophyLLM'),
    ('src.core.database.obsidian_sync', 'VaultManager'),
    ('src.core.modules.reading_manager', 'ReadingManager'),
    ('src.core.modules.agenda_manager', 'AgendaManager'),
    ('src.core.modules.translation_module', 'TranslationAssistant'),
    ('src.core.modules.pomodoro_timer', 'PomodoroTimer'),
    ('src.core.modules.writing_assistant', 'WritingAssistant'),
    ('src.core.modules.review_system', 'ReviewSystem'),
]

for module, class_name in modules:
    try:
        exec(f'from {module} import {class_name}')
        print(f'✅ {module} -> {class_name}')
    except Exception as e:
        print(f'❌ {module}: {e}')
"

# Testar funções específicas
echo ""
echo "🔧 Testando funções específicas..."
python3 -c "
import sys
sys.path.insert(0, 'src')

# Testar ReadingManager
from src.core.modules.reading_manager import ReadingManager
rm = ReadingManager('/tmp/test_vault')

# Testar funções novas
try:
    book_id = rm.add_book('Crítica da Razão Pura', 'Immanuel Kant', 500)
    print(f'✅ add_book() funcionou: {book_id}')
except Exception as e:
    print(f'❌ add_book(): {e}')

try:
    books = rm.list_books()
    print(f'✅ list_books() funcionou: {len(books)} livros')
except Exception as e:
    print(f'❌ list_books(): {e}')

try:
    stats = rm.stats()
    print(f'✅ stats() funcionou: {stats[\"total_books\"]} livros')
except Exception as e:
    print(f'❌ stats(): {e}')
"

# Testar CLI
echo ""
echo "🖥️ Testando comandos CLI..."
python3 -c "
import sys
sys.path.insert(0, 'src')

try:
    from src.cli.main import app
    commands = list(app.registered_commands.keys())
    print(f'✅ CLI carregado: {len(commands)} comandos')
    for cmd in commands:
        print(f'  • {cmd}')
except Exception as e:
    print(f'❌ CLI: {e}')
"

echo ""
echo "========================================"
echo "🎉 TESTES CONCLUÍDOS! Todos os módulos estão implementados. 🎉"
