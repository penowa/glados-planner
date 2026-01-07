# Crie diretório de templates
mkdir -p /home/penowa/Glados/config/templates

# Crie template para anotações de leitura
cat > /home/penowa/Glados/config/templates/leitura.md << 'EOF'
# {{title}}

## 📋 Metadados
- **Autor:** {{autor}}
- **Obra:** {{obra}}
- **Data de Leitura:** {{date:YYYY-MM-DD}}
- **Status:** #leitura/em_andamento
- **Tags:** #filosofia #leitura

## 🎯 Objetivo da Leitura
O que você espera aprender/compreender com este texto?

## 📖 Resumo
<!-- Faça um resumo com suas próprias palavras -->

## 🔑 Conceitos Chave
- 
- 
- 

## ❓ Questões e Dúvidas
1. 
2. 
3. 

## 💡 Insights e Conexões
- 
- 
- 

## 📚 Citações Importantes
> 

## 🔗 Ligações
- [[Conceitos Relacionados]]
- [[Textos Complementares]]

## 📝 Notas Adicionais

---

*Anotação gerada com GLaDOS - {{date:HH:mm}}*
EOF

# Crie template para conceitos
cat > /home/penowa/Glados/config/templates/conceito.md << 'EOF'
# {{conceito}}

## 📋 Definição
<!-- Defina o conceito de forma clara -->

## 🧠 Compreensão
<!-- Explique com suas próprias palavras -->

## 📚 Origem
- **Filósofo:** 
- **Obra:** 
- **Contexto:** 

## 🔄 Evolução
Como este conceito evoluiu ao longo da história?

## 🔗 Relações
### Conceitos Relacionados
- [[ ]] - 
- [[ ]] - 
- [[ ]] - 

### Opostos/Contrastes
- [[ ]] - 
- [[ ]] - 

## 💡 Aplicações
Como este conceito se aplica a situações contemporâneas?

## ❓ Questões em Aberto
1. 
2. 

## 📖 Referências
1. 
2. 

## 🏷️ Tags
#conceito #filosofia #{{categoria}}

---

*Conceito mapeado por GLaDOS - {{date:YYYY-MM-DD}}*
EOF
