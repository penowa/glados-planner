#!/usr/bin/env python3
import sys
import os
import time
import logging
import traceback
from pathlib import Path
from typing import Dict, Any

# ============ CONFIGURAÇÃO ABSOLUTA DE IMPORTS ============

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
UI_DIR = PROJECT_ROOT / "ui"

print(f"📁 Project root: {PROJECT_ROOT}")
print(f"📁 Source dir: {SRC_DIR}")
print(f"📁 UI dir: {UI_DIR}")

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(UI_DIR))

# ============ IMPORTS DO BACKEND ============

from core.communication.event_bus import GlobalEventBus
from core.errors.error_manager import ErrorManager
from core.monitoring.performance_monitor import PerformanceMonitor
from core.recovery.state_recovery import StateRecoveryManager

from core.modules.book_processor import BookProcessor
from core.modules.reading_manager import ReadingManager
from core.modules.agenda_manager import AgendaManager
from core.llm.local_llm import llm
from core.modules.obsidian.vault_manager import ObsidianVaultManager
from utils.config_manager import ConfigManager

# ============ IMPORTS DA UI ============

from main_window import MainWindow
from utils.theme_manager import ThemeManager
from utils.animation import LoadingSplash
from utils.responsive import ResponsiveManager
from utils.shortcut_manager import ShortcutManager

# ============ IMPORTS DO PyQt6 ============

from PyQt6.QtCore import (
    QSettings, QTimer, Qt, pyqtSignal, 
    QPropertyAnimation, QEasingCurve, QPoint
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QStackedWidget, QFrame, QToolBar,
    QStatusBar, QDialog, QGridLayout, QSizePolicy
)
from PyQt6.QtGui import (
    QFont, QIcon, QPalette, QColor, QAction, 
    QPainter, QPen, QBrush, QPixmap
)

class PhilosophyPlannerApp:
    """Classe principal da aplicação com todos os sistemas integrados"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.app = None
        self.window = None
        self.splash = None
        self.config_manager = ConfigManager.instance()
        
        self.event_bus = None
        self.error_manager = None
        self.performance_monitor = None
        self.recovery_manager = None
        
        self.backend_modules = {}
        self.controllers = {}
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Carrega configuração do sistema"""
        return {
            'theme': self.config_manager.theme,
            'window_geometry': self.config_manager.get_window_geometry(),
            'window_state': self.config_manager.get_window_state(),
            'vault_path': self.config_manager.vault_path,
            'recovery_enabled': True,
            'performance_monitoring': True,
            'log_level': 'INFO'
        }
    
    def run(self) -> int:
        """Executa a aplicação com todos os sistemas integrados"""
        try:
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("GLaDOS Philosophy Planner")
            self.app.setOrganizationName("GLaDOS Project")
            self.app.setOrganizationDomain("glados.philosophy")
            
            self.app.setStyle("Fusion")
            self.show_splash_screen()
            
            self.init_core_systems()
            self.init_backend_modules()
            
            ThemeManager.instance().load_theme(self.config['theme'])
            QTimer.singleShot(100, self.create_main_window)
            
            exit_code = self.app.exec()
            self.save_state()
            self.cleanup()
            
            return exit_code
            
        except Exception as e:
            self.handle_fatal_error(e)
            return 1
    
    def show_splash_screen(self):
        """Exibe tela de carregamento"""
        self.splash = LoadingSplash()
        self.splash.show()
    
# No main.py, atualize o método init_core_systems para:

    def init_core_systems(self):
        """Inicializa todos os sistemas centrais"""
        self.splash.show_message("Configurando logging...")
    
        # Configurar logging básico
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('GLaDOS')
    
        self.splash.show_message("Inicializando sistema de eventos...")
    
        # Importar e criar instância do EventBus
        from core.communication.event_bus import GlobalEventBus
        self.event_bus = GlobalEventBus.instance()
    
        # Verificar se o super().__init__() foi chamado
        if not hasattr(self.event_bus, '_connections'):
            print("❌ EventBus não foi inicializado corretamente!")
            # Forçar inicialização
            self.event_bus = GlobalEventBus()
            GlobalEventBus._instance = self.event_bus
    
        self.logger.info("EventBus inicializado")
    
        self.splash.show_message("Configurando sistema de erros...")
        self.error_manager = ErrorManager()
    
        self.splash.show_message("Iniciando monitoramento...")
        self.performance_monitor = PerformanceMonitor()
        self.performance_monitor.metrics_updated.connect(
            self.on_performance_metrics_updated
        )  
    
        self.splash.show_message("Configurando sistema de recuperação...")
        self.recovery_manager = StateRecoveryManager()
        self.recovery_manager.recovery_completed.connect(
            self.on_recovery_completed
        )
        self.recovery_manager.recovery_failed.connect(
            self.on_recovery_failed
        )
    
        self.splash.show_message("Sistemas centrais inicializados...")
        self.logger.info("Sistemas centrais inicializados com sucesso")
        self.event_bus.app_initialized.emit()
    
    def init_backend_modules(self):
        """Inicializa módulos do backend"""
        self.splash.show_message("Carregando módulos do backend...")
        
        self.backend_modules['book_processor'] = BookProcessor()
        self.backend_modules['reading_manager'] = ReadingManager()
        self.backend_modules['agenda_manager'] = AgendaManager()
        
        self.splash.show_message("Inicializando assistente GLaDOS...")
        self.backend_modules['llm_module'] = llm
        
        self.splash.show_message("Conectando ao vault Obsidian...")
        self.backend_modules['vault_manager'] = ObsidianVaultManager.instance()
        
        self.connect_modules_to_event_bus()
        
        self.logger.info("Módulos do backend inicializados")
        self.splash.show_message("Módulos carregados com sucesso")
    
    def connect_modules_to_event_bus(self):
        """Conecta módulos ao EventBus para comunicação"""
        bus = self.event_bus
        
        for name, module in self.backend_modules.items():
            bus.module_ready.emit(name, {"status": "initialized", "version": "1.0"})
        
        bus.module_error.connect(
            lambda module, error: self.error_manager.handle_error(
                type('ModuleError', (Exception,), {
                    'code': 'MODULE_ERROR',
                    'message': f"{module}: {error}"
                })(error)
            )
        )
    
    def create_main_window(self):
        """Cria janela principal com todos os sistemas integrados"""
        self.splash.show_message("Criando interface principal...")
        
        self.window = MainWindow(
            event_bus=self.event_bus,
            error_manager=self.error_manager,
            performance_monitor=self.performance_monitor,
            recovery_manager=self.recovery_manager,
            backend_modules=self.backend_modules,
            config=self.config
        )
        
        self.window.theme_changed.connect(self.on_theme_changed)
        self.window.view_changed.connect(self.on_view_changed)
        
        ResponsiveManager.instance().register_window(self.window)
        
        # Usar fade_out_and_close em vez de finish
        if self.splash:
            self.splash.fade_out_and_close()
        
        self.window.show()
        self.restore_window_state()
        
        self.logger.info("Interface principal criada com sucesso")
        self.event_bus.notification.emit(
            "success", 
            "Bem-vindo ao GLaDOS Philosophy Planner",
            "Sistema inicializado com sucesso"
        )
    
    def restore_window_state(self):
        """Restaura estado anterior da janela"""
        geometry = self.config.get('window_geometry')
        state = self.config.get('window_state')
        
        if geometry:
            self.window.restoreGeometry(geometry)
        if state:
            self.window.restoreState(state)
    
    def save_state(self):
        """Salva estado atual da aplicação CORRETAMENTE"""
        if not self.window:
            return
        
        try:
            # 1. Salvar geometria da janela
            geometry = self.window.saveGeometry()
            if geometry:
                self.config_manager.set_window_geometry(geometry)
        
            # 2. Salvar estado da janela
            state = self.window.saveState()
            if state:
                self.config_manager.set_window_state(state)
        
            # 3. Salvar tema
            theme = self.config.get('theme', 'philosophy_dark')
            self.config_manager.theme = theme
        
            print(f"✅ Estado salvo: tema={theme}, geometria={len(geometry) if geometry else 0} bytes")
        
        except Exception as e:
            print(f"❌ Erro ao salvar estado: {e}")
    
    def cleanup(self):
        """Limpeza sistemática antes de sair"""
        self.logger.info("Iniciando limpeza do sistema...")
        
        if self.performance_monitor:
            self.performance_monitor.collection_timer.stop()
        
        self.event_bus.app_shutdown.emit()
        
        if self.window:
            self.window.cleanup()
        
        for name, module in self.backend_modules.items():
            if hasattr(module, 'cleanup'):
                module.cleanup()
        
        self.generate_shutdown_report()
        self.logger.info("Sistema encerrado com sucesso")
    
    def generate_shutdown_report(self):
        """Gera relatório de shutdown para debug"""
        report = {
            'timestamp': time.time(),
            'session_duration': time.time() - self.start_time if hasattr(self, 'start_time') else 0,
            'errors_handled': len(self.error_manager.error_history) if hasattr(self.error_manager, 'error_history') else 0,
            'performance_metrics': self.performance_monitor.get_performance_report() if self.performance_monitor else {}
        }
        
        self.logger.info(f"Shutdown report: {report}")
    
    def handle_fatal_error(self, error: Exception):
        """Lida com erros fatais durante inicialização"""
        error_msg = f"Erro fatal: {error}"
        print(error_msg, file=sys.stderr)
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Erro Fatal - GLaDOS Philosophy Planner")
        msg_box.setText("Ocorreu um erro crítico durante a inicialização.")
        msg_box.setDetailedText(str(error))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def on_theme_changed(self, theme_name: str):
        """Atualiza configuração quando tema muda"""
        self.config['theme'] = theme_name
        ThemeManager.instance().load_theme(theme_name)
    
    def on_view_changed(self, view_name: str):
        """Loga mudança de view"""
        self.logger.info(f"View changed to: {view_name}")
    
    def on_performance_metrics_updated(self, metrics: dict):
        """Processa atualizações de métricas de performance"""
        system_metrics = metrics.get('system', {})
        
        if system_metrics.get('memory_usage'):
            last_memory = system_metrics['memory_usage'][-1]
            if last_memory.get('percent', 0) > 85:
                self.event_bus.notification.emit(
                    'warning',
                    'Uso alto de memória',
                    f"Memória em {last_memory['percent']}%"
                )
    
    def on_recovery_completed(self, recovery_type: str, result: dict):
        """Lida com recuperações completadas com sucesso"""
        self.logger.info(f"Recovery completed: {recovery_type}")
        
        if result.get('notify_user', False):
            self.event_bus.notification.emit(
                'success',
                f'Recuperação: {recovery_type}',
                result.get('message', 'Operação recuperada com sucesso')
            )
    
    def on_recovery_failed(self, recovery_type: str, error: str, context: dict):
        """Lida com falhas na recuperação"""
        self.logger.error(f"Recovery failed: {recovery_type} - {error}")
        
        self.event_bus.notification.emit(
            'error',
            f'Falha na recuperação: {recovery_type}',
            f'Erro: {error}. Consulte os logs para detalhes.'
        )
    
    @classmethod
    def instance(cls):
        """Retorna instância singleton da aplicação"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def main():
    """Função principal de entrada"""
    def exception_handler(exc_type, exc_value, exc_traceback):
        """Handler global para exceções não capturadas"""
        logger = logging.getLogger('GLaDOS.Unhandled')
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        app = QApplication.instance()
        if app:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Erro não tratado")
            msg_box.setText("Ocorreu um erro não tratado no aplicativo.")
            msg_box.setDetailedText(error_msg[-1000:])
            msg_box.exec()
    
    sys.excepthook = exception_handler
    
    app = PhilosophyPlannerApp.instance()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())