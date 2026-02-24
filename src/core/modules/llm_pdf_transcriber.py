# src/core/modules/llm_pdf_processor.py
"""
Processamento de PDFs usando a LLM local do GLaDOS
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import fitz  # PyMuPDF
import re
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

from .book_processor import BookMetadata, ProcessingResult, ProcessingStatus
from .obsidian.vault_manager import ObsidianVaultManager

logger = logging.getLogger(__name__)

@dataclass
class PDFPage:
    """Representa uma página de PDF processada."""
    page_num: int
    text: str
    confidence: float = 1.0
    requires_llm: bool = False
    llm_processed: bool = False
    hash: str = ""

class LLMPDFProcessor:
    """Processador de PDFs usando LLM local do GLaDOS."""
    
    def __init__(self, llm_instance=None, vault_manager: Optional[ObsidianVaultManager] = None):
        """
        Inicializa com a LLM local do GLaDOS.
        
        Args:
            llm_instance: Instância da LLM (se None, tenta importar)
            vault_manager: Gerenciador do vault
        """
        self.llm = llm_instance
        self.vault_manager = vault_manager or ObsidianVaultManager()
        self.page_cache = {}
        
        # Tenta importar a LLM se não foi fornecida
        if self.llm is None:
            try:
                # Importação ABSOLUTA da LLM do GLaDOS
                from core.llm.backend_router import llm as glados_llm
                self.llm = glados_llm
                logger.info("✅ LLM do GLaDOS carregada com sucesso")
            except ImportError as e:
                logger.warning(f"⚠️  Não foi possível importar a LLM do GLaDOS: {e}")
                logger.info("📚 Usando apenas extração básica de texto")
        
        logger.info(f"LLMPDFProcessor inicializado (LLM: {self.llm is not None})")
    
    def extract_page_text(self, pdf_path: str, page_num: int) -> str:
        """
        Extrai texto de uma página do PDF.
        
        Args:
            pdf_path: Caminho do PDF
            page_num: Número da página (0-index)
            
        Returns:
            Texto extraído
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num)
            text = page.get_text()
            doc.close()
            
            return text
        except Exception as e:
            logger.error(f"Erro extraindo página {page_num}: {e}")
            return ""
    
    def process_page_with_llm(self, pdf_path: str, page_num: int, 
                            metadata: BookMetadata) -> str:
        """
        Processa uma página do PDF usando LLM do GLaDOS.
        
        Args:
            pdf_path: Caminho do PDF
            page_num: Número da página
            metadata: Metadados do livro
            
        Returns:
            Texto processado pela LLM
        """
        try:
            # Primeiro, tenta extrair texto normalmente
            text = self.extract_page_text(pdf_path, page_num)
            
            # Se extraiu texto suficiente, retorna
            if len(text.strip()) > 100:
                logger.debug(f"Página {page_num+1}: Texto extraído normalmente ({len(text)} chars)")
                return text
            
            # Se pouco texto, usa LLM para melhorar
            if self.llm and hasattr(self.llm, 'generate'):
                logger.info(f"Página {page_num+1} usando LLM para melhorar extração")
                
                # Cria prompt para a LLM
                prompt = self._create_llm_prompt(text, metadata, page_num)
                
                # Usa a LLM do GLaDOS
                response = self.llm.generate(prompt, use_semantic=False)
                
                if response and "text" in response:
                    llm_text = response["text"]
                    logger.debug(f"LLM retornou {len(llm_text)} caracteres")
                    
                    # Combina o texto original com a melhoria da LLM
                    if len(text.strip()) > 0:
                        # Se tinha algum texto, mantém e adiciona a melhoria
                        combined = f"{text}\n\n--- Melhoria da LLM ---\n\n{llm_text}"
                    else:
                        combined = llm_text
                    
                    return combined
                else:
                    logger.warning("LLM não retornou texto válido")
                    return f"[Página {page_num+1}: Falha na melhoria com LLM]\n{text}"
            else:
                logger.debug(f"LLM não disponível para página {page_num+1}")
                return text if text else f"[Página {page_num+1}: Sem texto extraído]"
                
        except Exception as e:
            logger.error(f"Erro processando página {page_num} com LLM: {e}")
            return f"[ERRO LLM: {str(e)[:100]}]\n{text if 'text' in locals() else ''}"
    
    # Adicione este método à classe LLMPDFProcessor

    def process_chapter_range(self, pdf_path: str, start_page: int, end_page: int,
                             metadata: BookMetadata, chapter_num: int = None) -> Dict:
        """
        Processa um intervalo específico de páginas como um capítulo
    
        Args:
            pdf_path: Caminho do PDF
            start_page: Página inicial (0-index)
            end_page: Página final (0-index)
            metadata: Metadados do livro
            chapter_num: Número do capítulo
        
        Returns:
            Resultado do processamento
        """
        try:
            import fitz
        
            doc = fitz.open(pdf_path)
            chapter_text = ""
        
            # Garante que as páginas estão dentro dos limites
            start_page = max(0, start_page)
            end_page = min(len(doc) - 1, end_page)
        
            print(f"📄 Processando páginas {start_page+1} a {end_page+1}")
        
            for page_num in range(start_page, end_page + 1):
                if page_num >= len(doc):
                    break
                
                print(f"  Página {page_num+1}/{len(doc)}")
            
                # Extrai texto
                text = self.extract_page_text(pdf_path, page_num)
            
                # Usa LLM se texto insuficiente
                if len(text.strip()) < 100 and self.llm:
                    text = self.process_page_with_llm(pdf_path, page_num, metadata)
            
                chapter_text += f"\n\n--- Página {page_num + 1} ---\n\n{text}"
        
            doc.close()
        
            # Detecta título do capítulo
            lines = chapter_text.strip().split('\n')
            chapter_title = f"Capítulo {chapter_num}" if chapter_num else "Capítulo"
        
            for line in lines[:10]:
                line = line.strip()
                if (len(line) > 30 and len(line) < 200 and 
                    not line.startswith('---') and
                    not re.match(r'^\d+$', line)):
                
                    # Remove caracteres especiais do início
                    clean_line = re.sub(r'^[^a-zA-Z0-9]*', '', line)
                    if clean_line and len(clean_line) > 10:
                        chapter_title = clean_line[:100]
                        break
        
            return {
                'success': True,
                'chapter_num': chapter_num,
                'chapter_title': chapter_title,
                'start_page': start_page + 1,
                'end_page': end_page + 1,
                'num_pages': (end_page - start_page + 1),
                'content': chapter_text,
                'content_length': len(chapter_text)
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'chapter_num': chapter_num
            }

    def _create_llm_prompt(self, extracted_text: str, metadata: BookMetadata, 
                          page_num: int) -> str:
        """Cria prompt para a LLM melhorar texto extraído."""
        # Se tem pouco texto, pede para a LLM tentar reconstruir
        if len(extracted_text.strip()) < 50:
            return f"""Você é um assistente filosófico especializado em Dostoiévski.

Livro: {metadata.title}
Autor: {metadata.author}
Página: {page_num + 1}

TEXTO EXTRAÍDO (muito curto ou incompleto):
"{extracted_text}"

Com base no contexto do livro e no estilo de Dostoiévski, escreva o que provavelmente estaria nesta página.

Considere:
1. O estilo denso e psicológico de Dostoiévski
2. Temas de culpa, redenção e moralidade
3. Contexto de "Crime e Castigo"

Forneça uma reconstrução plausível desta página."""
        else:
            return f"""Você é um assistente especializado em processamento de textos filosóficos.

LIVRO: {metadata.title}
AUTOR: {metadata.author}
PÁGINA: {page_num + 1}

TEXTO EXTRAÍDO (pode ter problemas de formatação ou OCR):

INSTRUÇÕES:
1. Corrija erros óbvios de formatação
2. Organize em parágrafos lógicos
3. Melhore a pontuação se necessário
4. Mantenha o significado filosófico original
5. Se algo estiver ilegível, marque como "[...]"
6. Preserve qualquer termo filosófico específico

Responda APENAS com o texto corrigido, sem comentários adicionais."""
    
    def process_book(self, pdf_path: str, metadata: BookMetadata,
                    output_dir: Path, max_pages: int = None) -> Dict[str, Any]:
        """
        Processa um livro completo usando LLM.
        
        Args:
            pdf_path: Caminho do PDF
            metadata: Metadados do livro
            output_dir: Diretório de saída
            max_pages: Número máximo de páginas a processar
            
        Returns:
            Resultados do processamento
        """
        logger.info(f"Processando livro '{metadata.title}' com LLM")
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if max_pages:
                pages_to_process = min(max_pages, total_pages)
                logger.info(f"Limitado a {pages_to_process}/{total_pages} páginas")
            else:
                pages_to_process = total_pages
            
            processed_pages = []
            
            for page_num in range(pages_to_process):
                logger.info(f"Processando página {page_num+1}/{pages_to_process}")
                
                # Tenta extrair texto normalmente primeiro
                text = self.extract_page_text(pdf_path, page_num)
                
                # Decide se precisa de LLM
                needs_llm = len(text.strip()) < 100  # Pouco texto
                
                if needs_llm and self.llm:
                    logger.debug(f"Página {page_num+1} usando LLM")
                    text = self.process_page_with_llm(pdf_path, page_num, metadata)
                elif needs_llm:
                    logger.debug(f"Página {page_num+1} precisa de LLM mas não disponível")
                
                # Calcula hash do conteúdo
                content_hash = hashlib.md5(text.encode()).hexdigest()
                
                processed_pages.append(PDFPage(
                    page_num=page_num + 1,
                    text=text,
                    confidence=0.9 if not needs_llm else 0.7,
                    requires_llm=needs_llm,
                    llm_processed=needs_llm and self.llm is not None,
                    hash=content_hash
                ))
                
                # Pequena pausa para não sobrecarregar
                import time
                if needs_llm and self.llm:
                    time.sleep(0.5)  # 500ms entre páginas com LLM
            
            doc.close()
            
            # Organiza em capítulos
            chapters = self._organize_into_chapters(processed_pages, metadata, output_dir)
            
            # Estatísticas
            llm_pages = sum(1 for p in processed_pages if p.llm_processed)
            total_chars = sum(len(p.text) for p in processed_pages)
            
            stats = {
                'total_pages': total_pages,
                'pages_processed': len(processed_pages),
                'llm_pages': llm_pages,
                'total_characters': total_chars,
                'avg_confidence': sum(p.confidence for p in processed_pages) / len(processed_pages) if processed_pages else 0,
                'output_dir': str(output_dir),
                'chapters_created': len(chapters)
            }
            
            logger.info(f"✅ Processamento concluído: {stats}")
            
            return {
                'success': True,
                'processed_pages': processed_pages,
                'chapters': chapters,
                'stats': stats,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Erro processando livro: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_pages': [],
                'chapters': [],
                'stats': {}
            }
    
    def _organize_into_chapters(self, pages: List[PDFPage], 
                               metadata: BookMetadata, 
                               output_dir: Path) -> List[Dict[str, Any]]:
        """Organiza páginas em capítulos."""
        chapters = []
        pages_per_chapter = 10  # 10 páginas por capítulo
        
        for i in range(0, len(pages), pages_per_chapter):
            chapter_num = (i // pages_per_chapter) + 1
            chapter_pages = pages[i:i + pages_per_chapter]
            
            # Conteúdo do capítulo
            chapter_text = ""
            for page in chapter_pages:
                chapter_text += f"\n\n--- Página {page.page_num} ---\n\n{page.text}\n"
            
            # Nome do arquivo
            filename = f"capitulo-{chapter_num:03d}.md"
            filepath = output_dir / filename
            
            # Frontmatter
            frontmatter = f"""---
title: "Capítulo {chapter_num}: Páginas {chapter_pages[0].page_num}-{chapter_pages[-1].page_num}"
book: "{metadata.title}"
author: "{metadata.author}"
chapter: {chapter_num}
pages: "{chapter_pages[0].page_num}-{chapter_pages[-1].page_num}"
llm_pages: {sum(1 for p in chapter_pages if p.llm_processed)}
confidence: {sum(p.confidence for p in chapter_pages) / len(chapter_pages):.2f}
processed_date: "{datetime.now().isoformat()}"
---

"""
            
            # Título e conteúdo
            content = f"# Capítulo {chapter_num}\n\n"
            content += chapter_text
            
            # Se temos LLM, adiciona seção de análise
            if self.llm and chapter_num <= 3:  # Apenas para os primeiros 3 capítulos (para não sobrecarregar)
                try:
                    analysis = self._analyze_chapter(chapter_text, metadata, chapter_num)
                    content += f"\n\n## 🧠 Análise Automática\n\n{analysis}\n"
                except Exception as e:
                    logger.warning(f"Erro analisando capítulo {chapter_num}: {e}")
                    content += f"\n\n## 🧠 Análise Automática\n\n*Análise não disponível devido a erro: {str(e)[:100]}*\n"
            
            # Seção para notas do usuário
            content += f"\n\n## 📝 Notas\n\n<!-- Adicione suas anotações aqui -->\n"
            
            # Salva arquivo completo
            full_content = frontmatter + content
            filepath.write_text(full_content, encoding='utf-8')
            
            chapters.append({
                'number': chapter_num,
                'filename': filename,
                'filepath': str(filepath),
                'pages': f"{chapter_pages[0].page_num}-{chapter_pages[-1].page_num}",
                'llm_pages': sum(1 for p in chapter_pages if p.llm_processed),
                'content_preview': chapter_text[:500] + "..." if len(chapter_text) > 500 else chapter_text
            })
            
            logger.debug(f"✅ Capítulo {chapter_num} salvo: {filename}")
        
        return chapters
    
    def _analyze_chapter(self, content: str, metadata: BookMetadata, 
                        chapter_num: int) -> str:
        """Usa LLM para analisar o conteúdo do capítulo."""
        if not self.llm:
            return "*LLM não disponível para análise*"
        
        try:
            # Cria prompt para análise
            prompt = f"""Analise este capítulo do livro "{metadata.title}" de {metadata.author}:

CAPÍTULO: {chapter_num}

CONTEÚDO (resumido):
{content[:1500]}...

Forneça uma análise filosófica concisa:
1. Tema principal (1-2 frases)
2. 2-3 conceitos filosóficos presentes
3. Como se relaciona com a obra como um todo
4. 1 questão para reflexão

Seja direto e filosófico, evite formalidades excessivas."""
            
            response = self.llm.generate(prompt, use_semantic=True)
            
            if response and "text" in response:
                return response["text"]
            else:
                return "*Análise não disponível*"
                
        except Exception as e:
            logger.warning(f"Erro analisando capítulo {chapter_num}: {e}")
            return f"*Erro na análise: {str(e)[:50]}*"
