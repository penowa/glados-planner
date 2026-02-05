"""
Gerenciador de atalhos de teclado globais
"""
from PyQt6.QtCore import Qt, QObject
from PyQt6.QtGui import QKeySequence, QShortcut
from typing import Dict, Callable, Optional
import logging

logger = logging.getLogger('GLaDOS.UI.Shortcuts')


class ShortcutManager(QObject):
    """Gerencia atalhos de teclado globais"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.shortcuts = {}
        self.enabled = True
        
        logger.info("ShortcutManager inicializado")
    
    def register(self, key_sequence: str, callback: Callable, description: str = ""):
        """
        Registra um atalho de teclado
        
        Args:
            key_sequence: Sequência de teclas (ex: "Ctrl+S", "F5")
            callback: Função a ser chamada
            description: Descrição do atalho (opcional)
        """
        if key_sequence in self.shortcuts:
            logger.warning(f"Atalho {key_sequence} já registrado, substituindo")
        
        # Criar shortcut do Qt
        shortcut = QShortcut(QKeySequence(key_sequence), self.parent)
        shortcut.activated.connect(callback)
        
        # Armazenar informações
        self.shortcuts[key_sequence] = {
            'shortcut': shortcut,
            'callback': callback,
            'description': description,
            'enabled': True
        }
        
        logger.debug(f"Atalho registrado: {key_sequence} - {description}")
    
    def unregister(self, key_sequence: str):
        """Remove um atalho registrado"""
        if key_sequence in self.shortcuts:
            shortcut_info = self.shortcuts.pop(key_sequence)
            shortcut_info['shortcut'].deleteLater()
            logger.debug(f"Atalho removido: {key_sequence}")
    
    def enable_shortcut(self, key_sequence: str, enabled: bool = True):
        """Habilita ou desabilita um atalho específico"""
        if key_sequence in self.shortcuts:
            shortcut_info = self.shortcuts[key_sequence]
            shortcut_info['shortcut'].setEnabled(enabled)
            shortcut_info['enabled'] = enabled
            
            status = "habilitado" if enabled else "desabilitado"
            logger.debug(f"Atalho {key_sequence} {status}")
    
    def enable_all(self, enabled: bool = True):
        """Habilita ou desabilita todos os atalhos"""
        self.enabled = enabled
        for key_sequence, shortcut_info in self.shortcuts.items():
            shortcut_info['shortcut'].setEnabled(enabled)
        
        status = "habilitados" if enabled else "desabilitados"
        logger.info(f"Todos os atalhos {status}")
    
    def get_shortcut_info(self, key_sequence: str) -> Optional[Dict]:
        """Retorna informações sobre um atalho"""
        return self.shortcuts.get(key_sequence)
    
    def get_all_shortcuts(self) -> Dict[str, Dict]:
        """Retorna todos os atalhos registrados"""
        return self.shortcuts.copy()
    
    def get_shortcuts_by_category(self, category_filter: Callable = None) -> Dict[str, Dict]:
        """
        Retorna atalhos filtrados por categoria
        
        Args:
            category_filter: Função que recebe descrição e retorna True/False
        """
        if not category_filter:
            return self.get_all_shortcuts()
        
        filtered = {}
        for key_seq, info in self.shortcuts.items():
            if category_filter(info.get('description', '')):
                filtered[key_seq] = info
        
        return filtered
    
    def create_shortcuts_table(self) -> str:
        """Cria tabela HTML com todos os atalhos"""
        html = """
        <html>
        <head>
            <style>
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #3A2C1F; padding: 8px; text-align: left; }
                th { background-color: #2D2D2D; color: #F5F5DC; }
                tr:nth-child(even) { background-color: #3A3A3A; }
                .disabled { color: #666; text-decoration: line-through; }
            </style>
        </head>
        <body>
            <h2>Atalhos de Teclado - GLaDOS Philosophy Planner</h2>
            <table>
                <tr>
                    <th>Atalho</th>
                    <th>Descrição</th>
                    <th>Status</th>
                </tr>
        """
        
        for key_seq, info in sorted(self.shortcuts.items()):
            status = "✅ Ativo" if info['enabled'] else "❌ Inativo"
            row_class = "" if info['enabled'] else " class='disabled'"
            
            html += f"""
                <tr{row_class}>
                    <td><code>{key_seq}</code></td>
                    <td>{info['description']}</td>
                    <td>{status}</td>
                </tr>
            """
        
        html += """
            </table>
            <p><em>Total: {count} atalhos registrados</em></p>
        </body>
        </html>
        """.format(count=len(self.shortcuts))
        
        return html
    
    def export_to_json(self) -> str:
        """Exporta configurações de atalhos para JSON"""
        import json
        
        export_data = []
        for key_seq, info in self.shortcuts.items():
            export_data.append({
                'shortcut': key_seq,
                'description': info['description'],
                'enabled': info['enabled']
            })
        
        return json.dumps(export_data, indent=2)
    
    def import_from_json(self, json_data: str):
        """Importa configurações de atalhos de JSON"""
        import json
        
        try:
            shortcuts_data = json.loads(json_data)
            
            for shortcut_data in shortcuts_data:
                key_seq = shortcut_data['shortcut']
                
                # Atualizar status se já existir
                if key_seq in self.shortcuts:
                    self.enable_shortcut(key_seq, shortcut_data.get('enabled', True))
            
            logger.info(f"Configurações de atalhos importadas: {len(shortcuts_data)} entradas")
            
        except Exception as e:
            logger.error(f"Erro ao importar atalhos: {e}")
    
    def clear_all(self):
        """Remove todos os atalhos"""
        for key_seq in list(self.shortcuts.keys()):
            self.unregister(key_seq)
        
        logger.info("Todos os atalhos removidos")