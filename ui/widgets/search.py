"""
Widget de busca global
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger('GLaDOS.UI.Search')


class GlobalSearchDialog(QDialog):
    """Diálogo de busca global"""
    
    item_selected = pyqtSignal(dict)
    
    def __init__(self, controllers=None):
        super().__init__()
        self.controllers = controllers or {}
        self.setWindowTitle("Busca Global")
        self.setFixedSize(600, 500)
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Campo de busca
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar livros, notas, conceitos, tarefas...")
        self.search_input.setObjectName("global_search_input")
        
        # Contador de resultados
        self.results_label = QLabel("Digite para buscar")
        self.results_label.setObjectName("search_results_label")
        
        # Lista de resultados
        self.results_list = QListWidget()
        self.results_list.setObjectName("search_results_list")
        
        layout.addWidget(self.search_input)
        layout.addWidget(self.results_label)
        layout.addWidget(self.results_list)
        
        self.setLayout(layout)
    
    def setup_connections(self):
        self.search_input.textChanged.connect(self.perform_search)
        self.results_list.itemDoubleClicked.connect(self.on_item_selected)
    
    def perform_search(self, search_text):
        """Executa busca com o texto fornecido"""
        if len(search_text) < 2:
            self.results_list.clear()
            self.results_label.setText("Digite pelo menos 2 caracteres")
            return
        
        # Buscar em todos os controllers disponíveis
        results = []
        
        # Buscar livros
        if 'book' in self.controllers:
            # Simular busca - implementar chamada real ao controller
            results.append({
                'type': 'book',
                'title': f"Livro relacionado a '{search_text}'",
                'description': 'Resultado de busca em biblioteca',
                'action': lambda: print(f"Abrir livro sobre {search_text}")
            })
        
        # Buscar notas
        results.append({
            'type': 'note',
            'title': f"Nota: {search_text}",
            'description': 'Nota encontrada no vault',
            'action': lambda: print(f"Abrir nota sobre {search_text}")
        })
        
        self.display_results(results)
    
    def display_results(self, results):
        """Exibe resultados na lista"""
        self.results_list.clear()
        
        for result in results[:20]:  # Limitar a 20 resultados
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, result)
            
            # Widget customizado para o item
            widget = QWidget()
            layout = QVBoxLayout()
            
            title = QLabel(result['title'])
            title.setObjectName("search_result_title")
            font = QFont("Arial", 11, QFont.Weight.Bold)
            title.setFont(font)
            
            description = QLabel(result['description'])
            description.setObjectName("search_result_description")
            
            type_label = QLabel(f"Tipo: {result['type']}")
            type_label.setObjectName("search_result_type")
            
            layout.addWidget(title)
            layout.addWidget(description)
            layout.addWidget(type_label)
            widget.setLayout(layout)
            
            item.setSizeHint(widget.sizeHint())
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
        
        self.results_label.setText(f"{len(results)} resultados encontrados")
    
    def on_item_selected(self, item):
        """Quando um item é selecionado"""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result and 'action' in result:
            result['action']()
            self.accept()