# [file name]: src/core/modules/translation_module.py
"""
Módulo de tradução para termos filosóficos
"""
from typing import Dict, List, Optional
import json
from pathlib import Path

class TranslationAssistant:
    """Assistente de tradução para termos filosóficos"""
    
    def __init__(self, vault_path: str):
        """
        Inicializa o assistente de tradução
        
        Args:
            vault_path: Caminho para o vault do Obsidian
        """
        self.vault_path = Path(vault_path).expanduser()
        self.glossary_file = self.vault_path / "06-RECURSOS" / "glossario_filosofico.json"
        
        # Carrega glossário
        self.glossary = self._load_glossary()
        
        # Idiomas suportados
        self.supported_languages = {
            "grego": "Grego Antigo",
            "latim": "Latim",
            "alemão": "Alemão",
            "francês": "Francês",
            "inglês": "Inglês",
            "português": "Português"
        }
    
    def _load_glossary(self) -> Dict:
        """Carrega glossário filosófico"""
        glossary = {}
        
        if self.glossary_file.exists():
            try:
                with open(self.glossary_file, 'r', encoding='utf-8') as f:
                    glossary = json.load(f)
            except:
                # Cria glossário básico se não existir
                glossary = self._create_basic_glossary()
        else:
            glossary = self._create_basic_glossary()
            self._save_glossary(glossary)
        
        return glossary
    
    def _create_basic_glossary(self) -> Dict:
        """Cria glossário filosófico básico"""
        return {
            "logos": {
                "grego": "λόγος",
                "tradução": "razão, palavra, discurso",
                "definição": "Princípio racional que governa o universo; na filosofia grega, a razão ou a palavra divina.",
                "exemplos": ["Heráclito: 'Tudo acontece segundo o logos'", "Estoicos: 'Viver de acordo com o logos'"]
            },
            "eudaimonia": {
                "grego": "εὐδαιμονία",
                "tradução": "felicidade, florescimento humano",
                "definição": "Estado de bem-aventurança ou realização humana plena na filosofia aristotélica.",
                "exemplos": ["Aristóteles: 'A eudaimonia é o fim último da vida humana'"]
            },
            "arete": {
                "grego": "ἀρετή",
                "tradução": "virtude, excelência",
                "definição": "Excelência de caráter ou habilidade em alcançar o propósito de algo.",
                "exemplos": ["Platão: 'A arete é conhecimento'", "Aristóteles: 'A arete é uma disposição de caráter'"]
            },
            "dasein": {
                "alemão": "Dasein",
                "tradução": "ser-aí, existência",
                "definição": "Termo heideggeriano para o modo específico de ser do ser humano, caracterizado pela compreensão do ser.",
                "exemplos": ["Heidegger: 'O Dasein é o ente para o qual seu próprio ser está em jogo'"]
            },
            "a priori": {
                "latim": "a priori",
                "tradução": "a partir do anterior",
                "definição": "Conhecimento independente da experiência, anterior a ela.",
                "exemplos": ["Kant: 'Juízos sintéticos a priori são possíveis'"]
            }
        }
    
    def _save_glossary(self, glossary: Dict):
        """Salva glossário no arquivo"""
        try:
            self.glossary_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.glossary_file, 'w', encoding='utf-8') as f:
                json.dump(glossary, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar glossário: {e}")
    
    def translate_term(self, term: str, source_lang: str = None, target_lang: str = "português") -> Dict:
        """
        Traduz um termo filosófico
        
        Args:
            term: Termo a ser traduzido
            source_lang: Idioma de origem (detecta automaticamente se None)
            target_lang: Idioma de destino
            
        Returns:
            Informações de tradução
        """
        # Primeiro, procura no glossário
        term_lower = term.lower()
        
        for glossary_term, data in self.glossary.items():
            # Verifica se o termo está em algum idioma no glossário
            for lang, value in data.items():
                if isinstance(value, str) and term_lower in value.lower():
                    result = {
                        "termo": glossary_term,
                        "original": value,
                        "idioma_original": lang,
                        "tradução": data.get("tradução", "Não disponível"),
                        "definição": data.get("definição", "Não disponível"),
                        "exemplos": data.get("exemplos", []),
                        "encontrado_no_glossario": True
                    }
                    
                    # Se target_lang for específico, tenta obter tradução direta
                    if target_lang in data:
                        result[f"tradução_para_{target_lang}"] = data[target_lang]
                    
                    return result
        
        # Se não encontrou no glossário, procura no vault
        return self._search_term_in_vault(term, target_lang)
    
    def _search_term_in_vault(self, term: str, target_lang: str) -> Dict:
        """Procura termo no vault do Obsidian"""
        result = {
            "termo": term,
            "encontrado_no_glossario": False,
            "tradução": "Tradução não encontrada",
            "notas_encontradas": []
        }
        
        try:
            # Procura por menções ao termo
            for md_file in self.vault_path.glob("**/*.md"):
                try:
                    content = md_file.read_text(encoding='utf-8', errors='ignore')
                    
                    if term.lower() in content.lower():
                        # Extrai contexto
                        import re
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if term.lower() in line.lower():
                                context_start = max(0, i - 2)
                                context_end = min(len(lines), i + 3)
                                context = '\n'.join(lines[context_start:context_end])
                                
                                result["notas_encontradas"].append({
                                    "arquivo": md_file.relative_to(self.vault_path).as_posix(),
                                    "contexto": context,
                                    "linha": i + 1
                                })
                except:
                    continue
            
            # Se encontrou notas, tenta inferir tradução
            if result["notas_encontradas"]:
                # Procura por padrões de tradução
                for note in result["notas_encontradas"]:
                    context = note["contexto"]
                    
                    # Procura por padrões como "termo (tradução)"
                    import re
                    pattern = rf'{re.escape(term)}\s*\(([^)]+)\)'
                    match = re.search(pattern, context, re.IGNORECASE)
                    
                    if match:
                        result["tradução"] = match.group(1)
                        break
                    
                    # Procura por "tradução: ..."
                    pattern2 = rf'(?:tradução|significado)[:\s]+([^\n,.]+)'
                    match2 = re.search(pattern2, context, re.IGNORECASE)
                    
                    if match2:
                        result["tradução"] = match2.group(1).strip()
                        break
        
        except Exception as e:
            result["erro"] = str(e)
        
        return result
    
    def get_pronunciation(self, term: str, language: str = "grego") -> Dict:
        """
        Obtém pronúncia de um termo
        
        Args:
            term: Termo a ser pronunciado
            language: Idioma do termo
            
        Returns:
            Informações de pronúncia
        """
        # Tabela de pronúncia básica
        pronunciation_guides = {
            "grego": {
                "φ": "f",
                "θ": "th",
                "χ": "ch (como em 'bach')",
                "ψ": "ps",
                "αι": "e",
                "ει": "i",
                "οι": "i",
                "ου": "u",
                "αυ": "av/af",
                "ευ": "ev/ef",
                "γγ": "ng",
                "γκ": "g",
                "μπ": "b",
                "ντ": "d"
            },
            "alemão": {
                "ä": "e",
                "ö": "e (com lábios arredondados)",
                "ü": "i (com lábios arredondados)",
                "ß": "ss",
                "ch": "ch (como em 'bach')",
                "sch": "sh",
                "ei": "ai",
                "ie": "i"
            },
            "latim": {
                "c": "k (sempre)",
                "v": "u",
                "j": "i",
                "ae": "e",
                "oe": "e",
                "ch": "k",
                "ph": "f",
                "th": "t"
            }
        }
        
        result = {
            "termo": term,
            "idioma": language,
            "pronúncia": "Não disponível",
            "guia": pronunciation_guides.get(language, {}),
            "dica": ""
        }
        
        # Procura pronúncia no glossário
        term_lower = term.lower()
        for glossary_term, data in self.glossary.items():
            if term_lower == glossary_term.lower():
                if "pronúncia" in data:
                    result["pronúncia"] = data["pronúncia"]
                break
        
        # Dicas baseadas no idioma
        if language == "grego":
            result["dica"] = "O grego antigo tinha tom (acento musical), não acento de intensidade como no português."
        elif language == "latim":
            result["dica"] = "O latim pronuncia-se exatamente como se escreve, com vogais sempre claras."
        elif language == "alemão":
            result["dica"] = "O alemão tem vogais longas e curtas; consoantes no final são sempre surdas."
        
        return result
    
    def add_to_glossary(self, term: str, translations: Dict) -> bool:
        """
        Adiciona um termo ao glossário
        
        Args:
            term: Termo a ser adicionado
            translations: Dicionário com traduções
            
        Returns:
            True se bem-sucedido
        """
        if term not in self.glossary:
            self.glossary[term] = translations
        else:
            # Atualiza traduções existentes
            self.glossary[term].update(translations)
        
        # Salva glossário atualizado
        self._save_glossary(self.glossary)
        return True
    
    def search_by_language(self, language: str) -> List[Dict]:
        """
        Procura termos por idioma
        
        Args:
            language: Idioma para busca
            
        Returns:
            Lista de termos no idioma
        """
        results = []
        
        for term, data in self.glossary.items():
            if language in data:
                results.append({
                    "termo": term,
                    language: data[language],
                    "tradução": data.get("tradução", ""),
                    "definição": data.get("definição", "")
                })
        
        return results
    
    def export_glossary(self, format: str = "json") -> str:
        """
        Exporta glossário em diferentes formatos
        
        Args:
            format: Formato de exportação (json, csv, markdown)
            
        Returns:
            Caminho do arquivo exportado
        """
        export_dir = self.vault_path / "06-RECURSOS" / "exportacoes"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            file_path = export_dir / f"glossario_exportado_{timestamp}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.glossary, f, indent=2, ensure_ascii=False)
        
        elif format == "csv":
            import csv
            file_path = export_dir / f"glossario_exportado_{timestamp}.csv"
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Termo", "Idioma", "Original", "Tradução", "Definição"])
                
                for term, data in self.glossary.items():
                    for lang, value in data.items():
                        if isinstance(value, str) and lang not in ["tradução", "definição", "exemplos", "pronúncia"]:
                            writer.writerow([
                                term,
                                lang,
                                value,
                                data.get("tradução", ""),
                                data.get("definição", "")[:100]  # Limita tamanho
                            ])
        
        elif format == "markdown":
            file_path = export_dir / f"glossario_exportado_{timestamp}.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Glossário Filosófico\n\n")
                f.write(f"*Exportado em {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n\n")
                
                for term, data in self.glossary.items():
                    f.write(f"## {term}\n\n")
                    
                    # Idiomas
                    for lang, value in self.supported_languages.items():
                        if lang in data:
                            f.write(f"- **{value}:** {data[lang]}\n")
                    
                    # Informações adicionais
                    if "tradução" in data:
                        f.write(f"- **Tradução:** {data['tradução']}\n")
                    
                    if "definição" in data:
                        f.write(f"- **Definição:** {data['definição']}\n")
                    
                    if "exemplos" in data and data["exemplos"]:
                        f.write(f"\n**Exemplos:**\n")
                        for exemplo in data["exemplos"]:
                            f.write(f"  - {exemplo}\n")
                    
                    f.write("\n---\n\n")
        
        return str(file_path)
