# [file name]: src/core/modules/writing_assistant.py
"""
Assistente de escrita acadêmica
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
import json
from pathlib import Path
from datetime import datetime

@dataclass
class WritingStructure:
    """Estrutura de um trabalho acadêmico"""
    title: str
    sections: List[Dict]
    word_count_target: int
    references: List[str]
    style_guide: str  # ABNT, APA, Chicago, etc.

class WritingAssistant:
    """Assistente para escrita de trabalhos acadêmicos"""
    
    def __init__(self, vault_path: str):
        """
        Inicializa o assistente de escrita
        
        Args:
            vault_path: Caminho para o vault do Obsidian
        """
        self.vault_path = Path(vault_path).expanduser()
        self.templates_dir = self.vault_path / "06-RECURSOS" / "templates_escrita"
        self.projects_dir = self.vault_path / "03-PRODUÇÃO"
        
        # Cria diretórios se não existirem
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        
        # Carrega templates
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        """Carrega templates de escrita"""
        templates = {}
        
        # Templates padrão
        default_templates = {
            "ensaio_filosofico": {
                "name": "Ensaio Filosófico",
                "sections": [
                    {"title": "Introdução", "description": "Apresentação do problema filosófico", "word_target": 300},
                    {"title": "Exposição do Problema", "description": "Contextualização e formulação precisa", "word_target": 500},
                    {"title": "Análise de Conceitos", "description": "Definição e análise dos conceitos centrais", "word_target": 600},
                    {"title": "Argumentação", "description": "Desenvolvimento dos argumentos principais", "word_target": 800},
                    {"title": "Objeções e Respostas", "description": "Antecipação e resposta a possíveis críticas", "word_target": 400},
                    {"title": "Conclusão", "description": "Síntese e implicações da argumentação", "word_target": 300}
                ],
                "style_guide": "ABNT",
                "references_section": True
            },
            "paper_academico": {
                "name": "Paper Acadêmico",
                "sections": [
                    {"title": "Resumo", "description": "Abstract", "word_target": 250},
                    {"title": "Introdução", "description": "Contexto e justificativa", "word_target": 500},
                    {"title": "Revisão de Literatura", "description": "Estado da arte", "word_target": 1000},
                    {"title": "Metodologia", "description": "Abordagem e métodos", "word_target": 400},
                    {"title": "Análise e Discussão", "description": "Resultados e interpretação", "word_target": 1200},
                    {"title": "Conclusão", "description": "Síntese e contribuições", "word_target": 400},
                    {"title": "Referências", "description": "Bibliografia", "word_target": 0}
                ],
                "style_guide": "APA",
                "references_section": True
            },
            "resenha_critica": {
                "name": "Resenha Crítica",
                "sections": [
                    {"title": "Identificação da Obra", "description": "Dados bibliográficos", "word_target": 100},
                    {"title": "Resumo da Obra", "description": "Síntese do conteúdo", "word_target": 400},
                    {"title": "Análise Crítica", "description": "Avaliação e crítica", "word_target": 600},
                    {"title": "Conclusão", "description": "Avaliação final", "word_target": 200}
                ],
                "style_guide": "ABNT",
                "references_section": False
            }
        }
        
        # Carrega templates do diretório
        template_files = list(self.templates_dir.glob("*.json"))
        for file_path in template_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    template_name = file_path.stem
                    templates[template_name] = template_data
            except:
                continue
        
        # Adiciona templates padrão se não existirem
        for name, template in default_templates.items():
            if name not in templates:
                templates[name] = template
                
                # Salva template padrão
                template_file = self.templates_dir / f"{name}.json"
                with open(template_file, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2, ensure_ascii=False)
        
        return templates
    
    def structure_paper(self, title: str, template_type: str = "ensaio_filosofico", 
                       discipline: str = None) -> WritingStructure:
        """
        Estrutura um novo trabalho acadêmico
        
        Args:
            title: Título do trabalho
            template_type: Tipo de template a usar
            discipline: Disciplina relacionada
            
        Returns:
            Estrutura do trabalho
        """
        template = self.templates.get(template_type, self.templates["ensaio_filosofico"])
        
        # Cria estrutura baseada no template
        structure = WritingStructure(
            title=title,
            sections=template["sections"].copy(),
            word_count_target=sum(section["word_target"] for section in template["sections"]),
            references=[],
            style_guide=template["style_guide"]
        )
        
        # Cria arquivo no vault
        self._create_paper_file(title, structure, discipline)
        
        return structure
    
    def _create_paper_file(self, title: str, structure: WritingStructure, discipline: str = None):
        """Cria arquivo de trabalho no vault"""
        # Define diretório baseado na disciplina
        if discipline:
            paper_dir = self.projects_dir / discipline
        else:
            paper_dir = self.projects_dir / "geral"
        
        paper_dir.mkdir(parents=True, exist_ok=True)
        
        # Cria nome do arquivo
        timestamp = datetime.now().strftime("%Y%m%d")
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_").rstrip()
        filename = f"{timestamp} - {safe_title}.md"
        file_path = paper_dir / filename
        
        # Conteúdo do arquivo
        content = f"""---
title: "{title}"
type: "trabalho_academico"
template: "{structure.style_guide}"
discipline: "{discipline or 'geral'}"
status: "rascunho"
created: "{datetime.now().isoformat()}"
word_target: {structure.word_count_target}
---

# {title}

*Trabalho em andamento - Estrutura gerada por GLaDOS Writing Assistant*

## Estrutura Proposta

"""
        
        # Adiciona seções
        for i, section in enumerate(structure.sections, 1):
            content += f"\n### {i}. {section['title']}\n\n"
            content += f"*{section['description']}*\n"
            content += f"*Meta: {section['word_target']} palavras*\n\n"
            content += "[Escreva aqui...]\n\n"
        
        # Adiciona seção de referências se necessário
        if hasattr(structure, 'references_section') and structure.references_section:
            content += "\n## Referências\n\n"
            content += "[Adicione as referências bibliográficas aqui]\n"
        
        # Escreve arquivo
        file_path.write_text(content, encoding='utf-8')
        
        # Cria arquivo de metadados
        metadata = {
            "title": title,
            "file_path": str(file_path.relative_to(self.vault_path)),
            "structure": [{"title": s["title"], "target": s["word_target"]} for s in structure.sections],
            "total_target": structure.word_count_target,
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "status": "rascunho"
        }
        
        metadata_file = paper_dir / f"{file_path.stem}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def check_norms(self, file_path: str, style_guide: str = "ABNT") -> Dict:
        """
        Verifica conformidade com normas acadêmicas
        
        Args:
            file_path: Caminho do arquivo a verificar
            style_guide: Norma a verificar (ABNT, APA, Chicago)
            
        Returns:
            Relatório de conformidade
        """
        report = {
            "file": file_path,
            "style_guide": style_guide,
            "checks_performed": [],
            "issues_found": [],
            "suggestions": [],
            "score": 100
        }
        
        try:
            full_path = self.vault_path / file_path
            if not full_path.exists():
                report["issues_found"].append("Arquivo não encontrado")
                report["score"] = 0
                return report
            
            content = full_path.read_text(encoding='utf-8')
            
            # Verificações básicas
            checks = []
            
            # 1. Verifica título
            if "# " not in content[:100]:
                checks.append({"check": "título", "status": "fail", "message": "Título não encontrado com formatação H1"})
                report["score"] -= 10
            else:
                checks.append({"check": "título", "status": "pass", "message": "Título formatado corretamente"})
            
            # 2. Verifica estrutura de seções
            import re
            headings = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
            
            if len(headings) < 3:
                checks.append({"check": "estrutura", "status": "warning", "message": "Poucas seções identificadas"})
                report["score"] -= 5
            
            # 3. Verifica citações
            citation_patterns = {
                "ABNT": [r'\([A-Z][a-z]+, \d{4}\)', r'\([A-Z][a-z]+ et al., \d{4}\)'],
                "APA": [r'\([A-Za-z]+, \d{4}\)', r'\([A-Za-z]+ & [A-Za-z]+, \d{4}\)'],
                "Chicago": [r'\([A-Za-z]+, \d{4}, p\. \d+\)']
            }
            
            citations_found = False
            for pattern in citation_patterns.get(style_guide, []):
                if re.search(pattern, content):
                    citations_found = True
                    break
            
            if citations_found:
                checks.append({"check": "citações", "status": "pass", "message": f"Citações no formato {style_guide} encontradas"})
            else:
                checks.append({"check": "citações", "status": "warning", "message": f"Nenhuma citação no formato {style_guide} encontrada"})
                report["score"] -= 15
            
            # 4. Verifica referências/bibliografia
            ref_keywords = ["## Referências", "## Bibliografia", "## References"]
            has_references = any(keyword in content for keyword in ref_keywords)
            
            if has_references:
                checks.append({"check": "referências", "status": "pass", "message": "Seção de referências encontrada"})
            else:
                checks.append({"check": "referências", "status": "fail", "message": "Seção de referências não encontrada"})
                report["score"] -= 20
            
            # 5. Verifica resumo/abstract
            if style_guide in ["ABNT", "APA"]:
                has_abstract = "## Resumo" in content or "## Abstract" in content
                if has_abstract:
                    checks.append({"check": "resumo", "status": "pass", "message": "Resumo/Abstract encontrado"})
                else:
                    checks.append({"check": "resumo", "status": "warning", "message": "Resumo/Abstract não encontrado"})
                    report["score"] -= 10
            
            report["checks_performed"] = checks
            
            # Gera sugestões baseadas nos problemas
            for check in checks:
                if check["status"] in ["fail", "warning"]:
                    report["issues_found"].append(check["message"])
                    
                    # Sugestões específicas
                    if "citação" in check["message"].lower():
                        if style_guide == "ABNT":
                            report["suggestions"].append("Use: (AUTOR, ANO) para citações diretas")
                        elif style_guide == "APA":
                            report["suggestions"].append("Use: (Author, Year) para citações no texto")
                    
                    if "referências" in check["message"].lower():
                        report["suggestions"].append("Adicione uma seção '## Referências' no final do documento")
            
            # Limita score entre 0 e 100
            report["score"] = max(0, min(100, report["score"]))
            
        except Exception as e:
            report["issues_found"].append(f"Erro na verificação: {str(e)}")
            report["score"] = 0
        
        return report
    
    def export_document(self, file_path: str, format: str = "pdf") -> str:
        """
        Exporta documento para diferentes formatos
        
        Args:
            file_path: Caminho do arquivo no vault
            format: Formato de exportação (pdf, docx, html)
            
        Returns:
            Caminho do arquivo exportado
        """
        try:
            full_path = self.vault_path / file_path
            if not full_path.exists():
                return f"Arquivo não encontrado: {file_path}"
            
            # Diretório de exportação
            export_dir = self.projects_dir / "exportacoes"
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # Nome do arquivo exportado
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = full_path.stem
            export_name = f"{base_name}_{timestamp}"
            
            if format == "pdf":
                export_path = export_dir / f"{export_name}.pdf"
                # Implementação simplificada - converter markdown para PDF
                self._export_to_pdf(full_path, export_path)
                
            elif format == "docx":
                export_path = export_dir / f"{export_name}.docx"
                self._export_to_docx(full_path, export_path)
                
            elif format == "html":
                export_path = export_dir / f"{export_name}.html"
                self._export_to_html(full_path, export_path)
            else:
                return f"Formato não suportado: {format}"
            
            return str(export_path)
            
        except Exception as e:
            return f"Erro na exportação: {str(e)}"
    
    def _export_to_pdf(self, source_path: Path, target_path: Path):
        """Exporta Markdown para PDF (implementação simplificada)"""
        content = source_path.read_text(encoding='utf-8')
        
        # Remove frontmatter
        import re
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
        
        # HTML básico
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{source_path.stem}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #666; }}
        h2 {{ color: #555; margin-top: 30px; }}
        h3 {{ color: #777; }}
        .metadata {{ color: #888; font-size: 0.9em; margin-bottom: 30px; }}
    </style>
</head>
<body>
{self._markdown_to_html(content)}
</body>
</html>"""
        
        target_path.write_text(html_content, encoding='utf-8')
        
        # Nota: Para PDF real, precisaria de wkhtmltopdf ou similar
        print(f"HTML gerado em: {target_path}")
        print("Nota: Para PDF real, instale wkhtmltopdf e use: wkhtmltopdf input.html output.pdf")
    
    def _export_to_docx(self, source_path: Path, target_path: Path):
        """Exporta Markdown para DOCX (implementação simplificada)"""
        content = source_path.read_text(encoding='utf-8')
        
        # Cria documento de texto simples como placeholder
        target_path.write_text(f"Exportado de: {source_path.name}\n\n{content}", encoding='utf-8')
        print(f"Documento de texto gerado em: {target_path}")
        print("Nota: Para DOCX real, use python-docx ou pandoc")
    
    def _export_to_html(self, source_path: Path, target_path: Path):
        """Exporta Markdown para HTML"""
        content = source_path.read_text(encoding='utf-8')
        
        # Remove frontmatter
        import re
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
        
        html = self._markdown_to_html(content)
        target_path.write_text(html, encoding='utf-8')
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Converte Markdown básico para HTML"""
        import re
        
        # Cabeçalhos
        markdown = re.sub(r'^# (.*)$', r'<h1>\1</h1>', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'^## (.*)$', r'<h2>\1</h2>', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'^### (.*)$', r'<h3>\1</h3>', markdown, flags=re.MULTILINE)
        
        # Negrito
        markdown = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', markdown)
        
        # Itálico
        markdown = re.sub(r'\*(.*?)\*', r'<em>\1</em>', markdown)
        
        # Listas
        markdown = re.sub(r'^- (.*)$', r'<li>\1</li>', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', markdown)
        
        # Parágrafos
        lines = markdown.split('\n')
        html_lines = []
        in_paragraph = False
        
        for line in lines:
            if line.strip() and not line.startswith('<'):
                if not in_paragraph:
                    html_lines.append('<p>')
                    in_paragraph = True
                html_lines.append(line)
            else:
                if in_paragraph:
                    html_lines.append('</p>')
                    in_paragraph = False
                html_lines.append(line)
        
        if in_paragraph:
            html_lines.append('</p>')
        
        return '\n'.join(html_lines)
    
    def analyze_writing_style(self, file_path: str) -> Dict:
        """
        Analisa estilo de escrita
        
        Args:
            file_path: Caminho do arquivo a analisar
            
        Returns:
            Análise do estilo de escrita
        """
        analysis = {
            "file": file_path,
            "basic_stats": {},
            "readability": {},
            "vocabulary": {},
            "suggestions": []
        }
        
        try:
            full_path = self.vault_path / file_path
            content = full_path.read_text(encoding='utf-8')
            
            # Remove frontmatter
            import re
            content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
            
            # Estatísticas básicas
            words = content.split()
            sentences = re.split(r'[.!?]+', content)
            
            analysis["basic_stats"] = {
                "word_count": len(words),
                "sentence_count": len([s for s in sentences if s.strip()]),
                "character_count": len(content),
                "average_word_length": sum(len(w) for w in words) / len(words) if words else 0,
                "average_sentence_length": len(words) / len(sentences) if sentences else 0
            }
            
            # Legibilidade (Flesch Reading Ease simplificado)
            word_count = analysis["basic_stats"]["word_count"]
            sentence_count = analysis["basic_stats"]["sentence_count"]
            
            if word_count > 0 and sentence_count > 0:
                asl = word_count / sentence_count  # Average Sentence Length
                flesch = 206.835 - (1.015 * asl)
                analysis["readability"]["flesch_score"] = flesch
                
                if flesch > 60:
                    analysis["readability"]["level"] = "fácil"
                elif flesch > 30:
                    analysis["readability"]["level"] = "médio"
                else:
                    analysis["readability"]["level"] = "difícil"
            
            # Vocabulário
            unique_words = set(w.lower() for w in words)
            analysis["vocabulary"] = {
                "unique_words": len(unique_words),
                "lexical_diversity": len(unique_words) / len(words) if words else 0
            }
            
            # Sugestões
            avg_sent_len = analysis["basic_stats"]["average_sentence_length"]
            if avg_sent_len > 25:
                analysis["suggestions"].append("Considere dividir frases muito longas para melhor clareza")
            
            if analysis["readability"].get("level") == "difícil":
                analysis["suggestions"].append("Tente simplificar a linguagem para maior acessibilidade")
            
            if analysis["vocabulary"]["lexical_diversity"] < 0.3:
                analysis["suggestions"].append("Considere usar sinônimos para enriquecer o vocabulário")
        
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
