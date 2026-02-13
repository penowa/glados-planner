#!/usr/bin/env python3
"""
processar_livro.py - Processador simples de livros PDF para Obsidian
Localização: raiz do projeto GLaDOS/

Uso:
    python processar_livro.py livro.pdf [--capitulos 3] [--autor "Autor"] [--titulo "Título"]
"""

import sys
import os
import logging
from pathlib import Path
import argparse

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adiciona src ao path
ROOT_DIR = Path(__file__).parent.absolute()
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

class LivroProcessor:
    """Processador simplificado de livros para Obsidian"""
    
    def __init__(self):
        try:
            from core.modules.obsidian.vault_manager import ObsidianVaultManager
            
            # Configura caminho do vault
            vault_path = Path.home() / "Documentos" / "Obsidian" / "Philosophy_Vault"
            if not vault_path.exists():
                print(f"⚠️  Vault não encontrado. Criando em: {vault_path}")
                vault_path.mkdir(parents=True, exist_ok=True)
                (vault_path / "01-LEITURAS").mkdir(exist_ok=True)
                (vault_path / "06-RECURSOS").mkdir(exist_ok=True)
            
            self.vault = ObsidianVaultManager(str(vault_path))
            
            if not self.vault.is_connected():
                print("❌ Não foi possível conectar ao vault")
                sys.exit(1)
                
            print(f"✅ Vault conectado: {vault_path}")
            
        except Exception as e:
            print(f"❌ Erro ao inicializar: {e}")
            sys.exit(1)
    
    def processar_pdf_simples(self, pdf_path, num_capitulos=None, autor=None, titulo=None):
        """Processa um PDF de forma simples"""
        try:
            import fitz  # PyMuPDF
            import re
            from datetime import datetime
            
            pdf_path = Path(pdf_path).expanduser()
            if not pdf_path.exists():
                print(f"❌ Arquivo não encontrado: {pdf_path}")
                return False
            
            print(f"📖 Processando: {pdf_path.name}")
            
            # Abre o PDF
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            
            # Obtém metadados
            pdf_metadata = doc.metadata
            book_title = titulo or pdf_metadata.get('title', pdf_path.stem)
            book_author = autor or pdf_metadata.get('author', 'Autor Desconhecido')
            
            print(f"📚 Título: {book_title}")
            print(f"✍️  Autor: {book_author}")
            print(f"📄 Páginas: {total_pages}")
            
            # Configurações
            pages_per_chapter = 10
            if num_capitulos:
                pages_per_chapter = max(1, total_pages // num_capitulos)
            
            total_chapters = max(1, total_pages // pages_per_chapter)
            
            # Cria diretório no vault
            safe_author = self._sanitizar_nome(book_author)
            safe_title = self._sanitizar_nome(book_title)
            book_dir = self.vault.vault_path / "01-LEITURAS" / safe_author / safe_title
            book_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"📁 Diretório criado: {book_dir}")
            
            # Processa capítulos
            chapters_created = 0
            
            for chapter_num in range(1, total_chapters + 1):
                start_page = (chapter_num - 1) * pages_per_chapter
                end_page = min(start_page + pages_per_chapter - 1, total_pages - 1)
                
                if start_page >= total_pages:
                    break
                
                print(f"\n📑 Processando capítulo {chapter_num} (páginas {start_page+1}-{end_page+1})")
                
                # Extrai texto das páginas
                chapter_text = ""
                chapter_content = ""
                
                for page_num in range(start_page, end_page + 1):
                    if page_num >= total_pages:
                        break
                    
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    
                    if text.strip():
                        chapter_text += text
                        chapter_content += f"\n\n--- Página {page_num + 1} ---\n\n{text}\n"
                
                if not chapter_text.strip():
                    print(f"  ⚠️  Nenhum texto encontrado no capítulo {chapter_num}")
                    continue
                
                # Determina título do capítulo
                chapter_title = self._extrair_titulo_capitulo(chapter_text, chapter_num)
                
                # Cria arquivo Markdown
                filename = f"{chapter_num:03d} - {self._sanitizar_nome(chapter_title)}.md"
                filepath = book_dir / filename
                
                # Frontmatter
                frontmatter = f"""---
title: "{chapter_title}"
book: "{book_title}"
author: "{book_author}"
chapter: {chapter_num}
pages: "{start_page + 1}-{end_page + 1}"
total_pages: {total_pages}
processed_date: "{datetime.now().isoformat()}"
---

"""
                
                # Conteúdo completo
                content = f"""# {chapter_title}

## 📚 Livro
[[{book_title}]]

## 📖 Informações
- **Livro**: {book_title}
- **Autor**: {book_author}
- **Capítulo**: {chapter_num}
- **Páginas**: {start_page + 1}-{end_page + 1}

## 📝 Conteúdo
{chapter_content}

## 💭 Anotações
<!-- Adicione suas anotações aqui -->

## 🔗 Links Relacionados
[[{book_title}]] | [[Índice - {book_title}]]
"""
                
                full_content = frontmatter + content
                filepath.write_text(full_content, encoding='utf-8')
                
                print(f"  ✅ Capítulo salvo: {filename}")
                chapters_created += 1
            
            doc.close()
            
            # Cria índice do livro
            self._criar_indice_livro(book_dir, book_title, book_author, total_pages, chapters_created)
            
            # Registra livro
            self._registrar_livro(book_title, book_author, book_dir, total_pages, chapters_created)
            
            print(f"\n🎉 Processamento concluído!")
            print(f"   📚 Livro: {book_title}")
            print(f"   ✍️  Autor: {book_author}")
            print(f"   📑 Capítulos criados: {chapters_created}")
            print(f"   📁 Local: {book_dir}")
            
            return True
            
        except ImportError:
            print("❌ PyMuPDF não instalado. Instale com: pip install pymupdf")
            return False
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _extrair_titulo_capitulo(self, texto, numero_capitulo):
        """Extrai título do capítulo do texto"""
        import re
        
        # Procura por padrões comuns de títulos
        patterns = [
            r'Cap[íi]tulo\s+\d+\s*[:\.]\s*(.+)',
            r'CHAPTER\s+\d+\s*[:\.]\s*(.+)',
            r'^([A-Z][A-Z\s]{10,100})$',
            r'^\s*(\d+\.\s*.+)$'
        ]
        
        lines = texto.strip().split('\n')
        for line in lines[:10]:  # Examina as primeiras 10 linhas
            line = line.strip()
            if 20 < len(line) < 200:
                # Remove números de página
                line = re.sub(r'\s+\d+\s*$', '', line)
                
                # Testa padrões
                for pattern in patterns:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        title = match.group(1) if len(match.groups()) > 0 else line
                        return title[:100]
                
                # Se linha parece um título (começa com letra maiúscula, não tem pontuação no final)
                if (line[0].isupper() and 
                    not line.endswith('.') and 
                    not line.endswith(',') and
                    not line.endswith(';')):
                    return line[:100]
        
        # Fallback
        return f"Capítulo {numero_capitulo}"
    
    def _criar_indice_livro(self, book_dir, titulo, autor, total_paginas, total_capitulos):
        """Cria índice do livro"""
        try:
            from datetime import datetime
            
            indice_path = book_dir / f"📖 {titulo}.md"
            
            # Coleta capítulos
            chapters = []
            for md_file in book_dir.glob("*.md"):
                if md_file.name.startswith("📖 "):
                    continue
                
                try:
                    content = md_file.read_text(encoding='utf-8', errors='ignore')
                    # Extrai título e capítulo
                    import re
                    title_match = re.search(r'title:\s*"([^"]+)"', content)
                    chapter_match = re.search(r'chapter:\s*(\d+)', content)
                    
                    if title_match and chapter_match:
                        chapters.append({
                            'file': md_file.name.replace('.md', ''),
                            'title': title_match.group(1),
                            'chapter': int(chapter_match.group(1))
                        })
                except:
                    continue
            
            chapters.sort(key=lambda x: x['chapter'])
            
            # Cria conteúdo do índice
            frontmatter = f"""---
title: "{titulo}"
author: "{autor}"
type: "livro"
total_pages: {total_paginas}
total_chapters: {len(chapters)}
created: "{datetime.now().isoformat()}"
---

"""
            
            content = f"""# {titulo}

## 👤 Autor
{autor}

## 📊 Informações
- **Total de páginas**: {total_paginas}
- **Total de capítulos**: {len(chapters)}
- **Processado em**: {datetime.now().strftime('%d/%m/%Y %H:%M')}

## 📑 Capítulos
"""
            
            for chap in chapters:
                content += f"{chap['chapter']}. [[{chap['file']}|{chap['title']}]]\n"
            
            content += f"""

## 📝 Notas Gerais
<!-- Adicione suas notas sobre o livro aqui -->

## 🎯 Objetivos de Leitura
1. [ ] Compreender os conceitos principais
2. [ ] Extrair citações importantes
3. [ ] Relacionar com outros livros lidos
4. [ ] Aplicar conceitos na prática

## 📅 Progresso
| Capítulo | Data de Leitura | Status | Notas |
|----------|-----------------|--------|-------|
"""
            
            for chap in chapters:
                content += f"| {chap['chapter']} |  | 📖 Pendente | |\n"
            
            indice_path.write_text(frontmatter + content, encoding='utf-8')
            print(f"📖 Índice criado: {indice_path.name}")
            
        except Exception as e:
            print(f"⚠️  Erro ao criar índice: {e}")
    
    def _registrar_livro(self, titulo, autor, diretorio, total_paginas, total_capitulos):
        """Registra livro no sistema"""
        try:
            import json
            from datetime import datetime
            
            registry_path = self.vault.vault_path / "06-RECURSOS" / "livros_processados.json"
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Carrega registro existente
            registry = {}
            if registry_path.exists():
                try:
                    with open(registry_path, 'r', encoding='utf-8') as f:
                        registry = json.load(f)
                except:
                    registry = {}
            
            # ID do livro
            import hashlib
            book_id = hashlib.md5(f"{titulo}_{autor}".encode()).hexdigest()[:12]
            
            # Adiciona livro
            registry[book_id] = {
                'titulo': titulo,
                'autor': autor,
                'diretorio': str(diretorio.relative_to(self.vault.vault_path)),
                'total_paginas': total_paginas,
                'total_capitulos': total_capitulos,
                'processado_em': datetime.now().isoformat(),
                'book_id': book_id
            }
            
            # Salva registro
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
            
            print(f"📝 Livro registrado com ID: {book_id}")
            
        except Exception as e:
            print(f"⚠️  Erro ao registrar livro: {e}")
    
    def _sanitizar_nome(self, nome):
        """Sanitiza nome para sistema de arquivos"""
        import re
        # Remove caracteres inválidos
        nome = re.sub(r'[<>:"/\\|?*]', '_', nome)
        # Remove múltiplos espaços
        nome = re.sub(r'\s+', ' ', nome).strip()
        # Limita tamanho
        return nome[:80]
    
    def listar_livros(self):
        """Lista livros processados"""
        try:
            import json
            registry_path = self.vault.vault_path / "06-RECURSOS" / "livros_processados.json"
            
            if not registry_path.exists():
                print("📚 Nenhum livro processado ainda")
                return
            
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            print("📚 LIVROS PROCESSADOS")
            print("="*60)
            
            for i, (book_id, info) in enumerate(registry.items(), 1):
                print(f"\n{i}. 📖 {info['titulo']}")
                print(f"   ✍️  Autor: {info['autor']}")
                print(f"   📊 Páginas: {info['total_paginas']}")
                print(f"   📑 Capítulos: {info['total_capitulos']}")
                print(f"   🆔 ID: {book_id}")
                print(f"   📁 Diretório: {info['diretorio']}")
                print(f"   📅 Processado: {info['processado_em'][:10]}")
                print("   " + "-"*40)
                
        except Exception as e:
            print(f"❌ Erro ao listar livros: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Processa livros PDF para o Obsidian',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos:
  %(prog)s livro.pdf
  %(prog)s livro.pdf --capitulos 5
  %(prog)s livro.pdf --autor "Fiódor Dostoiévski" --titulo "Crime e Castigo"
  %(prog)s --listar
        '''
    )
    
    parser.add_argument('pdf_path', nargs='?', help='Caminho do arquivo PDF')
    parser.add_argument('--capitulos', type=int, help='Número de capítulos a criar')
    parser.add_argument('--autor', help='Nome do autor (sobrescreve metadados)')
    parser.add_argument('--titulo', help='Título do livro (sobrescreve metadados)')
    parser.add_argument('--listar', action='store_true', help='Lista livros já processados')
    
    args = parser.parse_args()
    
    print("🤖 GLaDOS - Processador de Livros PDF")
    print("="*60)
    
    processor = LivroProcessor()
    
    if args.listar:
        processor.listar_livros()
    elif args.pdf_path:
        processor.processar_pdf_simples(
            pdf_path=args.pdf_path,
            num_capitulos=args.capitulos,
            autor=args.autor,
            titulo=args.titulo
        )
    else:
        parser.print_help()
    
    print("\n" + "="*60)
    print("👋 Processamento concluído")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)