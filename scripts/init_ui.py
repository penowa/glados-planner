# scripts/init_ui.py
"""
Script para criar estrutura inicial da UI
"""
import os
import shutil

def create_project_structure():
    """Cria estrutura de diretórios do projeto"""
    directories = [
        'ui/widgets',
        'ui/views',
        'ui/controllers',
        'ui/themes',
        'ui/resources/icons',
        'ui/resources/fonts',
        'ui/resources/styles',
        'ui/utils',
        'tests/unit',
        'tests/integration',
        'tests/ui',
        'docs/ui_specs',
        'docs/components',
        'docs/api',
        'scripts'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, '__init__.py'), 'w') as f:
            f.write('')
    
    print("✅ Estrutura de diretórios criada!")

def create_main_files():
    """Cria arquivos principais"""
    files = {
        'ui/main.py': '''
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
''',
        
        'ui/main_window.py': '''
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from ui.views.dashboard import DashboardView
from ui.widgets.navigation import NavigationBar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GLaDOS Philosophy Planner")
        self.setGeometry(100, 100, 1200, 800)
        self.setup_ui()
        
    def setup_ui(self):
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Barra de navegação
        self.nav_bar = NavigationBar()
        layout.addWidget(self.nav_bar)
        
        # Área de conteúdo
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack)
        
        # Views
        self.dashboard_view = DashboardView()
        self.content_stack.addWidget(self.dashboard_view)
        
        # Conectar navegação
        self.nav_bar.view_changed.connect(self.change_view)
        
    def change_view(self, view_name):
        """Troca a view atual"""
        # Implementar troca de views
        pass
'''
    }
    
    for path, content in files.items():
        with open(path, 'w') as f:
            f.write(content)
    
    print("✅ Arquivos principais criados!")

if __name__ == "__main__":
    create_project_structure()
    create_main_files()
    print("\n🎉 Projeto inicializado com sucesso!")
    print("Instale as dependências:")
    print("  pip install PyQt6 pyinstaller qdarkstyle")