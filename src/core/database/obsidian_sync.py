# [file name]: src/core/database/obsidian_sync.py
"""
Sincronização bidirecional com vault do Obsidian
"""
from pathlib import Path
from typing import Dict, List, Optional
import sqlite3
import json
from datetime import datetime
import shutil

class VaultManager:
    """Gerenciador de sincronização com vault do Obsidian"""
    
    def __init__(self, vault_path: str, db_path: str = None):
        """
        Inicializa o gerenciador de vault
        
        Args:
            vault_path: Caminho para o vault do Obsidian
            db_path: Caminho para o banco de dados (opcional)
        """
        self.vault_path = Path(vault_path).expanduser()
        self.db_path = Path(db_path) if db_path else self.vault_path / ".obsidian" / "philosophy_sync.db"
        
        # Cria diretório do banco se necessário
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Inicializa banco de dados
        self._init_db()
    
    def _init_db(self):
        """Inicializa o banco de dados de sincronização"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de sincronização
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_path TEXT NOT NULL,
                vault_hash TEXT,
                db_hash TEXT,
                last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_direction TEXT,
                status TEXT
            )
        """)
        
        # Tabela de metadados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_metadata (
                note_path TEXT PRIMARY KEY,
                title TEXT,
                tags TEXT,
                links TEXT,
                word_count INTEGER,
                created TIMESTAMP,
                modified TIMESTAMP,
                last_accessed TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def sync_from_obsidian(self, force: bool = False) -> Dict:
        """
        Sincroniza do Obsidian para o banco de dados
        
        Args:
            force: Forçar sincronização completa
            
        Returns:
            Estatísticas da sincronização
        """
        stats = {
            "notes_scanned": 0,
            "notes_updated": 0,
            "notes_skipped": 0,
            "errors": 0
        }
        
        try:
            # Varre o vault por arquivos .md
            for md_file in self.vault_path.glob("**/*.md"):
                stats["notes_scanned"] += 1
                
                try:
                    relative_path = md_file.relative_to(self.vault_path)
                    file_hash = self._calculate_file_hash(md_file)
                    
                    # Verifica se precisa sincronizar
                    if not force and not self._needs_sync(str(relative_path), file_hash, "vault"):
                        stats["notes_skipped"] += 1
                        continue
                    
                    # Extrai metadados
                    metadata = self._extract_metadata(md_file)
                    
                    # Atualiza banco de dados
                    self._update_note_in_db(str(relative_path), metadata, file_hash)
                    
                    # Registra sincronização
                    self._log_sync(str(relative_path), file_hash, None, "from_obsidian", "success")
                    
                    stats["notes_updated"] += 1
                    
                except Exception as e:
                    print(f"Erro ao sincronizar {md_file}: {e}")
                    self._log_sync(str(relative_path), None, None, "from_obsidian", "error")
                    stats["errors"] += 1
        
        except Exception as e:
            print(f"Erro na sincronização: {e}")
            stats["errors"] += 1
        
        return stats
    
    def sync_to_obsidian(self, notes_data: List[Dict]) -> Dict:
        """
        Sincroniza do banco de dados para o Obsidian
        
        Args:
            notes_data: Lista de notas para sincronizar
            
        Returns:
            Estatísticas da sincronização
        """
        stats = {
            "notes_processed": 0,
            "notes_created": 0,
            "notes_updated": 0,
            "errors": 0
        }
        
        for note in notes_data:
            stats["notes_processed"] += 1
            
            try:
                note_path = self.vault_path / note["path"]
                content = note["content"]
                
                # Cria diretório se necessário
                note_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Verifica se arquivo existe e se precisa atualizar
                if note_path.exists():
                    existing_content = note_path.read_text(encoding='utf-8')
                    if existing_content != content:
                        note_path.write_text(content, encoding='utf-8')
                        stats["notes_updated"] += 1
                else:
                    note_path.write_text(content, encoding='utf-8')
                    stats["notes_created"] += 1
                
                # Registra sincronização
                file_hash = self._calculate_file_hash(note_path)
                self._log_sync(note["path"], None, file_hash, "to_obsidian", "success")
                
            except Exception as e:
                print(f"Erro ao sincronizar nota {note.get('path', 'desconhecido')}: {e}")
                self._log_sync(note.get("path", ""), None, None, "to_obsidian", "error")
                stats["errors"] += 1
        
        return stats
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcula hash de um arquivo"""
        import hashlib
        content = file_path.read_text(encoding='utf-8')
        return hashlib.md5(content.encode()).hexdigest()
    
    def _needs_sync(self, note_path: str, current_hash: str, source: str) -> bool:
        """Verifica se uma nota precisa ser sincronizada"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT vault_hash, db_hash, last_sync 
            FROM sync_history 
            WHERE note_path = ? 
            ORDER BY last_sync DESC 
            LIMIT 1
        """, (note_path,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return True  # Nunca sincronizado
        
        vault_hash, db_hash, last_sync = result
        
        if source == "vault":
            return vault_hash != current_hash
        else:  # source == "db"
            return db_hash != current_hash
    
    def _extract_metadata(self, file_path: Path) -> Dict:
        """Extrai metadados de um arquivo Markdown"""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        # Estatísticas básicas
        word_count = len(content.split())
        
        # Extrai título (primeiro cabeçalho ou nome do arquivo)
        title = file_path.stem
        
        import re
        # Tenta encontrar título no conteúdo
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
        
        # Extrai tags
        tags = []
        tag_matches = re.findall(r'\s#(\w+)', content)
        tags.extend(tag_matches)
        
        # Extrai links
        links = []
        link_matches = re.findall(r'\[\[([^\]]+)\]\]', content)
        links.extend(link_matches)
        
        return {
            "title": title,
            "tags": json.dumps(tags),
            "links": json.dumps(links),
            "word_count": word_count,
            "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "last_accessed": datetime.now().isoformat()
        }
    
    def _update_note_in_db(self, note_path: str, metadata: Dict, file_hash: str):
        """Atualiza uma nota no banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insere ou atualiza metadados
        cursor.execute("""
            INSERT OR REPLACE INTO note_metadata 
            (note_path, title, tags, links, word_count, created, modified, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_path,
            metadata["title"],
            metadata["tags"],
            metadata["links"],
            metadata["word_count"],
            metadata["created"],
            metadata["modified"],
            metadata["last_accessed"]
        ))
        
        conn.commit()
        conn.close()
    
    def _log_sync(self, note_path: str, vault_hash: Optional[str], db_hash: Optional[str], 
                  direction: str, status: str):
        """Registra uma operação de sincronização"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sync_history 
            (note_path, vault_hash, db_hash, sync_direction, status)
            VALUES (?, ?, ?, ?, ?)
        """, (note_path, vault_hash, db_hash, direction, status))
        
        conn.commit()
        conn.close()
    
    def get_sync_status(self) -> Dict:
        """Obtém status da sincronização"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Estatísticas gerais
        cursor.execute("SELECT COUNT(*) FROM sync_history")
        total_syncs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT note_path) FROM note_metadata")
        total_notes = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT sync_direction, status, COUNT(*) 
            FROM sync_history 
            GROUP BY sync_direction, status
        """)
        
        stats = {
            "total_syncs": total_syncs,
            "total_notes": total_notes,
            "by_direction": {},
            "by_status": {}
        }
        
        for direction, status, count in cursor.fetchall():
            stats["by_direction"][direction] = stats["by_direction"].get(direction, 0) + count
            stats["by_status"][status] = stats["by_status"].get(status, 0) + count
        
        # Últimas sincronizações
        cursor.execute("""
            SELECT note_path, sync_direction, status, last_sync 
            FROM sync_history 
            ORDER BY last_sync DESC 
            LIMIT 10
        """)
        
        recent_syncs = []
        for row in cursor.fetchall():
            recent_syncs.append({
                "note": row[0],
                "direction": row[1],
                "status": row[2],
                "time": row[3]
            })
        
        stats["recent_syncs"] = recent_syncs
        
        conn.close()
        return stats
    
    def backup_vault(self, backup_path: str) -> bool:
        """
        Cria backup do vault
        
        Args:
            backup_path: Caminho para o backup
            
        Returns:
            True se bem-sucedido
        """
        try:
            backup_dir = Path(backup_path).expanduser()
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Cria timestamp para nome do backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"vault_backup_{timestamp}"
            full_backup_path = backup_dir / backup_name
            
            # Copia o vault
            if self.vault_path.exists():
                shutil.copytree(self.vault_path, full_backup_path)
                return True
            return False
        except Exception as e:
            print(f"Erro no backup: {e}")
            return False
