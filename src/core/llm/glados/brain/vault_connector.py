"""
Conector do vault do Obsidian como cérebro da GLaDOS
Atualizado com busca semântica integrada
"""
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import re
import yaml
import frontmatter
from dataclasses import dataclass
from datetime import datetime
import json

from .semantic_search import Sembrain, SearchResult
try:
    from core.vault.bootstrap import bootstrap_vault
except Exception:
    bootstrap_vault = None

@dataclass
class VaultNote:
    """Representa uma nota do vault"""
    path: Path
    title: str
    content: str
    frontmatter: Dict[str, Any]
    tags: List[str]
    links: List[str]
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'path': str(self.path),
            'title': self.title,
            'content_preview': self.content[:200] + '...' if len(self.content) > 200 else self.content,
            'tags': self.tags,
            'links': self.links,
            'created': self.created.isoformat() if self.created else None,
            'modified': self.modified.isoformat() if self.modified else None
        }

class VaultStructure:
    """Mapeia a estrutura REAL do vault com busca semântica integrada"""
    
    # Estrutura REAL baseada na sua pasta
    STRUCTURE = {
        "00-META": "Sistema e metadados",
        "01-LEITURAS": "Gestão de leituras por autor/obra",
        "02-ANOTAÇÕES": "Anotações do usuário",
        "03-REVISÃO": "Materiais de revisão gerados",
        "04-MAPAS MENTAIS": "Mapas mentais (ex: Canva)",
        "05-DISCIPLINAS": "Conteúdos organizados por disciplina",
        "06-RECURSOS": "Recursos, registros e dados auxiliares"
    }
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).expanduser()
        self.notes_cache = {}
        self.semantic_search = None
        self._validate_structure()
        self._index_vault()
        self._init_semantic_search()
    
    def _init_semantic_search(self):
        """Inicializa o sistema de busca semântica"""
        try:
            # Converte cache para lista de notas
            notes_list = list(self.notes_cache.values())
            self.semantic_search = Sembrain(self.vault_path, notes_list)
            print(f"[GLaDOS] ✅ Busca semântica inicializada: {len(notes_list)} notas indexadas")
            
            # Mostra estatísticas CORRIGIDO: Sembrain não tem 'model_loaded'
            if self.semantic_search:
                stats = self.semantic_search.get_stats()
                print(f"[GLaDOS] 📊 Estatísticas busca: notas={stats['total_notes']}, vocabulário={stats['vocabulary_size']}")
        except Exception as e:
            print(f"[GLaDOS] ⚠️  Erro ao inicializar busca semântica: {e}")
            self.semantic_search = None
    
    def _validate_structure(self) -> bool:
        """Valida se o vault existe (modo flexível)"""
        vault_exists = self.vault_path.exists()
        if not vault_exists:
            print(f"[GLaDOS] ❌ Vault não encontrado: {self.vault_path}")
            print(f"[GLaDOS] Criando estrutura básica...")
        else:
            print(f"[GLaDOS] ✅ Vault encontrado: {self.vault_path}")

        if bootstrap_vault is not None:
            try:
                self.vault_path = bootstrap_vault(
                    vault_path=str(self.vault_path),
                    vault_structure=self.STRUCTURE.keys(),
                )
            except Exception as exc:
                print(f"[GLaDOS] ⚠️  Falha no bootstrap do vault: {exc}")
                if not self.vault_path.exists():
                    self._create_basic_structure()
        elif not self.vault_path.exists():
            self._create_basic_structure()
        
        # Lista diretórios existentes
        existing_dirs = [d.name for d in self.vault_path.iterdir() if d.is_dir()]
        print(f"[GLaDOS] Diretórios encontrados: {existing_dirs}")
        
        return True
    
    def _create_basic_structure(self):
        """Cria estrutura básica do vault se não existir"""
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        for folder_name, description in self.STRUCTURE.items():
            folder_path = self.vault_path / folder_name
            folder_path.mkdir(exist_ok=True)
            
            # Cria README em cada pasta
            readme_path = folder_path / "README.md"
            if not readme_path.exists():
                readme_content = f"""# {folder_name}

{description}

*Esta pasta é gerenciada automaticamente pelo sistema GLaDOS.*

## Conteúdo Esperado:
- {description.lower()}
- Notas relacionadas
- Metadados do sistema

---
*Criado por GLaDOS v0.4.0*
"""
                readme_path.write_text(readme_content, encoding="utf-8")
        
        print(f"[GLaDOS] ✅ Estrutura criada em: {self.vault_path}")
    
    def _index_vault(self):
        """Indexa todas as notas do vault"""
        print(f"[GLaDOS] 🔍 Indexando vault...")
        
        # Lista de extensões de arquivos de nota
        note_extensions = ['.md', '.txt', '.markdown']
        
        note_count = 0
        for ext in note_extensions:
            for md_file in self.vault_path.glob(f"**/*{ext}"):
                try:
                    note = self._parse_note(md_file)
                    if note:
                        relative_path = md_file.relative_to(self.vault_path)
                        self.notes_cache[str(relative_path)] = note
                        note_count += 1
                except Exception as e:
                    print(f"[GLaDOS] ⚠️  Erro ao parsear {md_file}: {e}")
        
        print(f"[GLaDOS] ✅ {note_count} notas indexadas")
    
    def _parse_note(self, file_path: Path) -> Optional[VaultNote]:
        """Parseia uma nota Markdown com frontmatter"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Tenta extrair frontmatter
            frontmatter_data = {}
            if content.startswith('---'):
                try:
                    # Usa frontmatter se disponível
                    parsed = frontmatter.loads(content)
                    content = parsed.content
                    frontmatter_data = parsed.metadata
                except:
                    # Fallback para parsing simples
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter_str = parts[1]
                        content = parts[2].lstrip('\n')
                        try:
                            frontmatter_data = yaml.safe_load(frontmatter_str) or {}
                        except:
                            frontmatter_data = {}
            
            # Extrai título do frontmatter ou do nome do arquivo
            title = frontmatter_data.get('title', file_path.stem)
            
            # Extrai tags
            tags = frontmatter_data.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]
            
            # Extrai links [[link]]
            import re
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            
            return VaultNote(
                path=file_path,
                title=title,
                content=content.strip(),
                frontmatter=frontmatter_data,
                tags=tags,
                links=links,
                created=datetime.fromtimestamp(file_path.stat().st_ctime),
                modified=datetime.fromtimestamp(file_path.stat().st_mtime)
            )
        except Exception as e:
            print(f"[GLaDOS] ⚠️  Erro ao parsear {file_path}: {e}")
            return None
    
    def get_notes_by_folder(self, folder_name: str) -> List[VaultNote]:
        """Retorna todas as notas de uma pasta específica"""
        folder_path = self.vault_path / folder_name
        notes = []
        
        for note_path, note in self.notes_cache.items():
            if note_path.startswith(folder_name):
                notes.append(note)
        
        return notes
    
    def get_concept_notes(self) -> List[VaultNote]:
        """Retorna notas de estudo/conceitos."""
        notes = self.get_notes_by_folder("02-ANOTAÇÕES")
        if notes:
            return notes
        return self.get_notes_by_folder("02 - Conceitos")
    
    def get_reading_notes(self) -> List[VaultNote]:
        """Retorna notas de leituras."""
        notes = self.get_notes_by_folder("01-LEITURAS")
        if notes:
            return notes
        return self.get_notes_by_folder("01 - Leituras")
    
    def get_discipline_notes(self) -> List[VaultNote]:
        """Retorna materiais de revisão estruturados."""
        notes = self.get_notes_by_folder("03-REVISÃO")
        if notes:
            return notes
        return self.get_notes_by_folder("03 - Disciplinas")

    def get_discipline_anchor_notes(self) -> List[VaultNote]:
        """Retorna as notas-âncora de disciplinas."""
        notes = self.get_notes_by_folder("05-DISCIPLINAS")
        if notes:
            return notes
        return self.get_discipline_notes()

    @staticmethod
    def _normalize_terms(text: str) -> List[str]:
        import re

        cleaned = re.sub(r"[^\w\sà-úÀ-Ú-]", " ", str(text or ""), flags=re.UNICODE)
        return [part for part in re.split(r"\s+", cleaned.lower()) if len(part) >= 3]

    def _note_search_text(self, note: VaultNote) -> str:
        parts = [
            str(getattr(note, "title", "") or ""),
            str(getattr(note, "content", "") or "")[:1800],
            " ".join(str(tag) for tag in getattr(note, "tags", []) or []),
            " ".join(str(link) for link in getattr(note, "links", []) or []),
            str(getattr(note, "path", "") or ""),
        ]
        return " ".join(parts).lower()

    def _score_anchor_match(self, note: VaultNote, query: str) -> float:
        query_terms = set(self._normalize_terms(query))
        note_terms = set(self._normalize_terms(self._note_search_text(note)))
        if not query_terms or not note_terms:
            return 0.0

        overlap = len(query_terms.intersection(note_terms))
        score = overlap / max(1, len(query_terms))

        title = str(getattr(note, "title", "") or "").lower()
        if any(term in title for term in query_terms):
            score += 0.4

        path = str(getattr(note, "path", "") or "").lower()
        if "05-disciplinas" in path:
            score += 0.2

        return score

    def _build_discipline_anchor(self, query: str) -> Optional[VaultNote]:
        anchor_notes = self.get_discipline_anchor_notes()
        if not anchor_notes:
            return None

        ranked: List[tuple[float, VaultNote]] = []
        for note in anchor_notes:
            ranked.append((self._score_anchor_match(note, query), note))

        ranked.sort(key=lambda item: item[0], reverse=True)
        if not ranked:
            return None

        top_score, top_note = ranked[0]
        if top_score <= 0:
            return None
        return top_note

    def _collect_related_notes(self, anchor: Optional[VaultNote], query: str, max_notes: int) -> List[VaultNote]:
        all_notes = list(self.notes_cache.values())
        if anchor is None:
            if self.semantic_search:
                try:
                    results = self.semantic_search.search(query, limit=max_notes * 3, notes=all_notes)
                    return [result.note for result in results[:max_notes]]
                except Exception:
                    pass
            return all_notes[:max_notes]

        anchor_terms = self._normalize_terms(f"{anchor.title} {query} {' '.join(anchor.tags)}")
        anchor_links = {link.lower() for link in getattr(anchor, "links", []) or []}
        try:
            anchor_root = anchor.path.relative_to(self.vault_path).parts[0]
        except Exception:
            anchor_root = ""

        candidate_notes: List[VaultNote] = []
        for note in all_notes:
            if note.path == anchor.path:
                candidate_notes.append(note)
                continue

            note_text = self._note_search_text(note)
            path_text = str(note.path).lower()
            linked_text = " ".join(getattr(note, "links", []) or []).lower()

            if any(term in note_text for term in anchor_terms):
                candidate_notes.append(note)
                continue
            if any(link in linked_text for link in anchor_links):
                candidate_notes.append(note)
                continue
            if anchor_root:
                try:
                    note_root = note.path.relative_to(self.vault_path).parts[0]
                    if note_root == anchor_root:
                        candidate_notes.append(note)
                        continue
                except Exception:
                    pass

        if anchor not in candidate_notes:
            candidate_notes.insert(0, anchor)

        if self.semantic_search:
            try:
                semantic_results = self.semantic_search.search(
                    query,
                    limit=max_notes * 4,
                    notes=candidate_notes,
                )
                ordered_notes = [result.note for result in semantic_results]
                if len(ordered_notes) >= max_notes:
                    return ordered_notes[:max_notes]

                seen_paths = {str(note.path) for note in ordered_notes}
                for note in candidate_notes:
                    if str(note.path) not in seen_paths:
                        ordered_notes.append(note)
                        seen_paths.add(str(note.path))
                    if len(ordered_notes) >= max_notes:
                        break
                return ordered_notes[:max_notes]
            except Exception:
                pass

        return candidate_notes[:max_notes]

    def build_navigation_packet(self, query: str, max_notes: int = 8, excerpt_chars: int = 280) -> Dict[str, Any]:
        """
        Constrói um pacote de navegação centrado em disciplinas.

        Retorna:
            {
                "discipline": str,
                "anchor": Optional[Dict],
                "notes": List[Dict],
                "context": str,
            }
        """
        anchor = self._build_discipline_anchor(query)
        related_notes = self._collect_related_notes(anchor, query, max_notes=max_notes)
        safe_excerpt_chars = max(120, min(int(excerpt_chars or 280), 480))

        notes_payload: List[Dict[str, Any]] = []
        for index, note in enumerate(related_notes, start=1):
            note_dict = note.to_dict()
            try:
                note_dict["folder"] = note.path.relative_to(self.vault_path).parts[0]
            except Exception:
                note_dict["folder"] = "raiz"
            note_dict["role"] = "anchor" if anchor and note.path == anchor.path else "related"
            note_dict["index"] = index
            notes_payload.append(note_dict)

        discipline_name = str(anchor.title if anchor else "Geral").strip() or "Geral"
        discipline_name = re.sub(r"(?i)^disciplina\s*-\s*", "", discipline_name).strip() or discipline_name
        context_lines = [
            "### INICIO_CONTEXTO_NAVEGACAO ###",
            f"Disciplina identificada: {discipline_name}",
            "Use a disciplina identificada como âncora para navegar até leituras, anotações e revisões relacionadas.",
            "",
            f"Pergunta do usuário: {query.strip()}",
            "",
        ]

        if anchor is not None:
            context_lines.extend(
                [
                    "Âncora principal:",
                    f"- Título: {anchor.title}",
                    f"- Caminho: {anchor.path}",
                    f"- Tags: {', '.join(anchor.tags) if anchor.tags else 'sem tags'}",
                    "",
                ]
            )

        context_lines.append("Notas relacionadas para resposta:")
        for note in related_notes:
            try:
                folder = note.path.relative_to(self.vault_path).parts[0]
            except Exception:
                folder = "raiz"
            context_lines.append(f"--- {folder} :: {note.title} ---")
            context_lines.append(f"Caminho: {note.path}")
            if note.tags:
                context_lines.append(f"Tags: {', '.join(note.tags[:6])}")
            if note.links:
                context_lines.append(f"Links: {', '.join(note.links[:6])}")
            excerpt = note.content[:safe_excerpt_chars].strip()
            if excerpt:
                context_lines.append("Trecho:")
                context_lines.append(f"> {excerpt}")
            context_lines.append("")

        context_lines.extend(
            [
                "Regras:",
                "- Priorize a disciplina âncora e suas relações diretas.",
                "- Expanda para livros, anotações e revisões associadas antes de responder.",
                "- Se a informação estiver ausente, diga que não encontrou nas notas relacionadas.",
                "### FIM_CONTEXTO_NAVEGACAO ###",
            ]
        )

        return {
            "discipline": discipline_name,
            "anchor": anchor.to_dict() if anchor is not None else None,
            "notes": notes_payload,
            "context": "\n".join(context_lines),
        }
    
    # ADICIONADO: Método para compatibilidade com local_llm.py
    def get_all_notes(self) -> List[VaultNote]:
        """Retorna todas as notas do vault (para compatibilidade)"""
        return list(self.notes_cache.values())
    
    def search_notes(self, query: str, limit: int = 5, semantic: bool = True) -> List[Union[VaultNote, Dict]]:
        """
        Busca por texto nas notas usando busca semântica ou textual
        
        Args:
            query: Texto da consulta
            limit: Número máximo de resultados
            semantic: Se True, usa busca semântica; senão, só busca textual
        
        Returns:
            Lista de notas ou resultados detalhados
        """
        if not query.strip():
            return []
        
        # Usa busca semântica se disponível
        if semantic and self.semantic_search:
            try:
                results = self.semantic_search.search(query, limit=limit)
                
                # Retorna apenas as notas (backward compatibility)
                notes = [result.note for result in results]
                return notes[:limit]
            except Exception as e:
                print(f"[GLaDOS] ⚠️  Erro na busca semântica: {e}. Usando busca textual.")
                return self._textual_search(query, limit)
        else:
            # Fallback para busca textual
            return self._textual_search(query, limit)
    
    def search_detailed(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Busca detalhada com metadados de relevância
        """
        if not self.semantic_search:
            return []
        
        results = self.semantic_search.search(query, limit=limit)
        
        detailed_results = []
        for result in results:
            detailed_results.append({
                'note': result.note.to_dict(),
                'relevance': result.relevance,
                'search_type': result.search_type,
                'matched_fields': result.matched_fields,
                'excerpt': result.excerpt
            })
        
        return detailed_results
    
    def _textual_search(self, query: str, limit: int) -> List[VaultNote]:
        """Busca textual (fallback quando semântica não disponível)"""
        query_lower = query.lower()
        scored_notes = []
        
        for note in self.notes_cache.values():
            score = 0.0
            
            # Busca no título (maior peso)
            if query_lower in note.title.lower():
                score += 0.6
            
            # Busca em tags
            for tag in note.tags:
                if query_lower in tag.lower():
                    score += 0.3
                    break
            
            # Busca no conteúdo
            if query_lower in note.content.lower():
                score += 0.1
            
            if score > 0:
                scored_notes.append((note, score))
        
        # Ordena por pontuação
        scored_notes.sort(key=lambda x: x[1], reverse=True)
        return [note for note, _ in scored_notes[:limit]]
    
    def get_note_by_path(self, path: str) -> Optional[VaultNote]:
        """Obtém uma nota específica pelo caminho relativo"""
        return self.notes_cache.get(path)
    
    def get_vault_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do vault"""
        total_notes = len(self.notes_cache)
        notes_by_folder = {}
        
        for folder in self.STRUCTURE.keys():
            notes = self.get_notes_by_folder(folder)
            notes_by_folder[folder] = len(notes)
        
        # Estatísticas de busca semântica CORRIGIDAS
        semantic_stats = {}
        if self.semantic_search:
            try:
                semantic_stats = self.semantic_search.get_stats()
            except:
                semantic_stats = {}
        
        return {
            "total_notes": total_notes,
            "notes_by_folder": notes_by_folder,
            "structure": self.STRUCTURE,
            "vault_path": str(self.vault_path),
            "semantic_search": {
                "available": self.semantic_search is not None,
                "total_notes": semantic_stats.get('total_notes', 0),
                "vocabulary_size": semantic_stats.get('vocabulary_size', 0),
                "cache_size": semantic_stats.get('cache_size', 0)
            }
        }
    
    def format_as_brain_context(self, notes: List[VaultNote], query: str = "") -> str:
        """
        Formata notas como contexto cerebral para a LLM
        Melhorado para incluir informações de relevância
        """
        if not notes:
            return "[MEMÓRIA VAZIA] Nenhuma informação relevante encontrada no meu cérebro."
        
        context = f"[CONSULTA AO CÉREBRO DE GLaDOS - '{query}']\n"
        context += f"Consulta retornou {len(notes)} nota(s) relevantes do meu conhecimento:\n\n"
        
        # Se temos busca semântica, tenta obter detalhes de relevância
        detailed_results = []
        if self.semantic_search and query:
            try:
                detailed_results = self.search_detailed(query, limit=len(notes))
            except:
                detailed_results = []
        
        for i, note in enumerate(notes):
            relative_path = note.path.relative_to(self.vault_path)
            folder = str(relative_path).split('/')[0] if '/' in str(relative_path) else "raiz"
            
            # Tenta obter relevância da busca detalhada
            relevance_info = ""
            if i < len(detailed_results):
                detail = detailed_results[i]
                relevance_info = f" (Relevância: {detail['relevance']:.2f}, Método: {detail['search_type']})"
            
            context += f"--- NOTA {i+1}: {folder}/{relative_path.name}{relevance_info} ---\n"
            context += f"Título: {note.title}\n"
            
            if note.tags:
                context += f"Tags: {', '.join(note.tags)}\n"
            
            # Resumo inteligente do conteúdo
            if len(note.content) > 500:
                # Tenta encontrar sentenças mais relevantes
                sentences = note.content.split('. ')
                if len(sentences) > 3:
                    # Pega primeira, última e algumas do meio
                    summary = '. '.join([sentences[0]] + sentences[1:3] + ["..."]) + "."
                else:
                    summary = note.content[:500] + "..."
            else:
                summary = note.content
            
            context += f"Conteúdo: {summary}\n"
            
            if note.links:
                context += f"Links relacionados: {', '.join(note.links[:3])}"
                if len(note.links) > 3:
                    context += f" ... (+{len(note.links)-3} mais)"
                context += "\n"
            
            context += "\n"
        
        context += "[FIM DA CONSULTA AO CÉREBRO]\n"
        context += "Instrução: Use essas informações como base principal para sua resposta. "
        context += "Se necessário, complemente com seu conhecimento geral, mas priorize o conteúdo acima."
        
        return context
    
    def add_note_to_index(self, note_path: Path):
        """Adiciona uma nova nota ao índice"""
        try:
            note = self._parse_note(note_path)
            if note:
                relative_path = note_path.relative_to(self.vault_path)
                self.notes_cache[str(relative_path)] = note
                
                # Atualiza índice semântico se disponível
                if self.semantic_search:
                    self.semantic_search.add_note(note)
                
                return note
        except Exception as e:
            print(f"[GLaDOS] ⚠️  Erro ao adicionar nota ao índice: {e}")
        return None
