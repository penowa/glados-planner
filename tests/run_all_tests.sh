#!/bin/bash
# Script completo para executar todos os testes

echo "🚀 INICIANDO TESTES COMPLETOS DO GLADOS PLANNER"
echo "=================================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para mostrar resultado
show_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

echo -e "\n${YELLOW}📦 TESTE 1: Importações básicas${NC}"
echo "--------------------------------------------------"
python tests/test_imports.py
IMPORT_RESULT=$?
show_result $IMPORT_RESULT "Teste de importações"

echo -e "\n${YELLOW}🔧 TESTE 2: Funcionalidade${NC}"
echo "--------------------------------------------------"
python tests/test_functionality.py
FUNC_RESULT=$?
show_result $FUNC_RESULT "Teste de funcionalidade"

echo -e "\n${YELLOW}🔍 TESTE 3: Identificação de funções faltantes${NC}"
echo "--------------------------------------------------"
python tests/identify_missing_functions.py
IDENTIFY_RESULT=$?
show_result $IDENTIFY_RESULT "Identificação de funções"

echo -e "\n${YELLOW}📊 RESUMO DOS RELATÓRIOS${NC}"
echo "--------------------------------------------------"

if [ -f "test_imports_report.txt" ]; then
    echo -e "${GREEN}✅ Relatório de importações: test_imports_report.txt${NC}"
    grep -E "(PASS:|FAIL:)" test_imports_report.txt
fi

if [ -f "functionality_test_report.txt" ]; then
    echo -e "${GREEN}✅ Relatório de funcionalidade: functionality_test_report.txt${NC}"
    grep -E "(PASS:|FAIL:)" functionality_test_report.txt
fi

if [ -f "missing_functions_report.txt" ]; then
    echo -e "${YELLOW}⚠️  Relatório de funções faltantes: missing_functions_report.txt${NC}"
    echo "(Consulte o arquivo para detalhes)"
fi

if [ -f "missing_modules.txt" ]; then
    echo -e "${YELLOW}⚠️  Módulos faltantes: missing_modules.txt${NC}"
    head -10 missing_modules.txt
fi

echo -e "\n${YELLOW}🎯 PRÓXIMOS PASSOS RECOMENDADOS${NC}"
echo "--------------------------------------------------"

# Verifica resultados e faz recomendações
if [ $IMPORT_RESULT -ne 0 ] || [ $FUNC_RESULT -ne 0 ]; then
    echo "1. 🔧 Corrija os erros de importação identificados"
    echo "2. 🛠️ Implemente os módulos faltantes listados"
    echo "3. 📝 Documente funções implementadas mas não documentadas"
    echo "4. 🧪 Execute os testes novamente"
else
    echo "1. 🎉 Todos os testes básicos passaram!"
    echo "2. 📈 Considere implementar módulos avançados"
    echo "3. 🚀 Prepare para deploy no GitHub"
    echo "4. 📢 Anuncie para a comunidade"
fi

echo -e "\n📁 Arquivos gerados:"
ls -la *.txt 2>/dev/null || echo "Nenhum relatório encontrado"

echo -e "\n🚀 Testes completados!"
EOF
