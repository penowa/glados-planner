"""
Sistema de busca que respeita a hierarquia do vault
"""
from typing import List, Dict, Tuple
from pathlib import Path
import re

class HierarchicalSearch:
    """Busca hierárquica baseada na estrutura do vault"""
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.index = self._build_hierarchical_index()
    
    def _build_hierarchical_index(self) -> Dict:
        """Constrói índice hierárquico baseado na estrutura do vault"""
        index = {
            "nivel_0": {},  # Pastas principais (00-META, 01-LEITURAS, etc.)
            "nivel_1": {},  # Subpastas
            "nivel_2": {},  # Arquivos
            "conteudo": {}  # Conteúdo dos arquivos
        }
        
        # Indexa pastas principais
        for main_folder in self.vault_path.iterdir():
            if main_folder.is_dir():
                folder_name = main_folder.name
                index["nivel_0"][folder_name] = {
                    "path": main_folder,
                    "type": self._get_folder_type(folder_name)
                }
                
                # Indexa subpastas
                for subfolder in main_folder.iterdir():
                    if subfolder.is_dir():
                        sub_name = subfolder.name
                        index["nivel_1"][f"{folder_name}/{sub_name}"] = {
                            "path": subfolder,
                            "parent": folder_name
                        }
        
        return index
    
    def _get_folder_type(self, folder_name: str) -> str:
        """Classifica o tipo de pasta baseado na estrutura"""
        type_map = {
            "00-META": "sistema",
            "01-LEITURAS": "conhecimento",
            "02-DISCIPLINAS": "organizacional", 
            "03-PRODUÇÃO": "producao",
            "04-AGENDA": "temporal",
            "05-CONCEITOS": "conceitual",
            "06-RECURSOS": "ferramental",
            "07-PESSOAL": "pessoal",
            "08-ARCHIVE": "arquivo"
        }
        return type_map.get(folder_name, "desconhecido")
    
    def search_with_context(self, query: str, context: str = None) -> List[Dict]:
        """
        Busca considerando contexto da estrutura
        """
        results = []
        
        # Primeiro: busca em MOCs (Maps of Content)
        moc_results = self._search_mocs(query)
        results.extend(moc_results)
        
        # Segundo: busca hierárquica baseada no tipo de consulta
        if self._is_concept_query(query):
            results.extend(self._search_in_conceitos(query))
        
        if self._is_author_query(query):
            results.extend(self._search_in_autores(query))
            
        if self._is_discipline_query(query):
            results.extend(self._search_in_disciplinas(query))
        
        # Terceiro: busca no conteúdo
        content_results = self._search_content(query)
        results.extend(content_results)
        
        # Ordena por relevância hierárquica
        return self._rank_by_hierarchy(results)
    
    def _search_mocs(self, query: str) -> List[Dict]:
        """Busca em Maps of Content (estrutura de alto nível)"""
        mocs = []
        
        # MOC de disciplinas
        disciplinas_path = self.vault_path / "02-DISCIPLINAS"
        for disciplina in disciplinas_path.iterdir():
            if disciplina.is_dir():
                moc_file = disciplina / f"MOC - {disciplina.name}.md"
                if moc_file.exists():
                    content = moc_file.read_text(encoding='utf-8')
                    if self._matches_query(query, content):
                        mocs.append({
                            "type": "moc",
                            "file": moc_file,
                            "content": content[:500],  # Primeiros 500 chars
                            "relevance": 1.0,
                            "hierarchy": "alto"
                        })
        
        return mocs
    
    def _search_in_conceitos(self, query: str) -> List[Dict]:
        """Busca na estrutura de conceitos"""
        conceitos_path = self.vault_path / "05-CONCEITOS"
        results = []
        
        # Busca em "Por Área"
        por_area = conceitos_path / "Por Área"
        if por_area.exists():
            for area_dir in por_area.iterdir():
                if area_dir.is_dir():
                    for concept_file in area_dir.glob("*.md"):
                        content = concept_file.read_text(encoding='utf-8')
                        if self._matches_query(query, content):
                            results.append({
                                "type": "conceito",
                                "area": area_dir.name,
                                "file": concept_file,
                                "content": content[:300],
                                "relevance": 0.9
                            })
        
        return results
    
    def _is_concept_query(self, query: str) -> bool:
        """Detecta se a consulta é sobre conceitos"""
        concept_keywords = [
            "o que é", "definição", "conceito", "significado",
            "virtude", "felicidade", "dever", "substância",
            "essência", "existência", "causalidade"
        ]
        return any(keyword in query.lower() for keyword in concept_keywords)
