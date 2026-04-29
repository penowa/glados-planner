#!/usr/bin/env python3
import sys
import os
import time
import logging
import traceback
import subprocess
import shutil
from urllib import request as urllib_request
from urllib.parse import urlsplit, urlunsplit
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

try:
    import PyQt6  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name == "PyQt6":
        print("\n❌ PyQt6 não está instalado no interpretador Python atual.")
        print(f"🐍 Python em uso: {sys.executable}")
        print("\nUse o ambiente virtual do projeto antes de iniciar a UI:")
        print("   source venv/bin/activate")
        print("   python -m ui.main")
        print("\nOu execute diretamente com o Python do venv:")
        print("   venv/bin/python -m ui.main")
        print("\nSe o venv ainda não tiver as dependências:")
        print("   venv/bin/python -m pip install -r requirements.txt")
        raise SystemExit(1) from exc
    raise

# ============ IMPORTS DO BACKEND ============

from core.communication.event_bus import GlobalEventBus
from core.errors.error_manager import ErrorManager
from core.monitoring.performance_monitor import PerformanceMonitor
from core.recovery.state_recovery import StateRecoveryManager
from core.modules.obsidian.lazy_vault_manager import LazyObsidianVaultManager
from core.modules.book_processor import BookProcessor
from core.modules.reading_manager import ReadingManager
from core.modules.agenda_manager import AgendaManager
from core.config.settings import settings as core_settings
from core.llm.backend_router import llm
from core.vault.bootstrap import bootstrap_vault
from ui.utils.config_manager import ConfigManager

# ============ IMPORTS DA UI ============

from ui.main_window import MainWindow
from ui.utils.theme_manager import ThemeManager
from ui.utils.animation import LoadingSplash
from ui.utils.responsive import ResponsiveManager
from ui.utils.shortcut_manager import ShortcutManager

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
        self.ollama_process = None
        self._ollama_started_by_app = False
        self._ollama_log_handle = None
        
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

    def _configure_qt_backend(self) -> None:
        """
        Ajusta backend gráfico do Qt para evitar falhas conhecidas em Wayland.
        Pode ser sobrescrito definindo QT_QPA_PLATFORM manualmente no ambiente.
        """
        if os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("QT_QPA_PLATFORM"):
            # Fallback estável para ambientes Wayland com problemas de SHM/pintura.
            os.environ["QT_QPA_PLATFORM"] = "xcb"
            os.environ.setdefault("QT_OPENGL", "software")
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
    
    def run(self) -> int:
        """Executa a aplicação com todos os sistemas integrados"""
        try:
            self._configure_qt_backend()
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("GLaDOS's Planner")
            self.app.setOrganizationName("Penowa")
            self.app.setOrganizationDomain("glados.philosophy")
            
            self.app.setStyle("Fusion")
            self.show_splash_screen()
            
            self.init_core_systems()
            self.ensure_ollama_service_for_cloud_backend()
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

    @staticmethod
    def _normalize_ollama_api_base(api_base: str) -> str:
        value = str(api_base or "").strip().rstrip("/")
        if not value:
            return "http://127.0.0.1:11434"
        try:
            parsed = urlsplit(value)
        except Exception:
            return value
        if not parsed.scheme:
            return value
        host = (parsed.hostname or "").strip().lower()
        if host != "localhost":
            return value
        netloc = "127.0.0.1"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)).rstrip("/")

    @staticmethod
    def _is_ollama_cloud_backend_active() -> bool:
        backend = str(getattr(core_settings.llm, "backend", "local") or "local").strip().lower()
        if backend != "cloud":
            return False
        model = str(getattr(core_settings.llm.cloud, "model", "") or "").strip().lower()
        return model.startswith("ollama/")

    @staticmethod
    def _is_ollama_reachable(api_base: str, timeout_seconds: float = 1.5) -> bool:
        target = str(api_base or "").strip().rstrip("/")
        if not target:
            return False
        url = f"{target}/api/tags"
        req = urllib_request.Request(url, method="GET")
        opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=max(0.5, float(timeout_seconds))) as resp:
                return int(getattr(resp, "status", 0) or 0) == 200
        except Exception:
            return False

    @staticmethod
    def _find_ollama_binary() -> str | None:
        candidates = []
        env_bin = str(os.environ.get("OLLAMA_BIN", "") or "").strip()
        if env_bin:
            candidates.append(Path(env_bin).expanduser())
        which_bin = shutil.which("ollama")
        if which_bin:
            candidates.append(Path(which_bin))
        candidates.append(Path.home() / ".local" / "bin" / "ollama")
        candidates.append(Path("/usr/bin/ollama"))

        for candidate in candidates:
            try:
                path = candidate.expanduser().resolve()
            except Exception:
                path = candidate
            if path.exists() and os.access(path, os.X_OK):
                return str(path)
        return None

    def ensure_ollama_service_for_cloud_backend(self):
        """Inicia `ollama serve` automaticamente quando backend cloud/ollama estiver ativo."""
        if not self._is_ollama_cloud_backend_active():
            return

        api_base = self._normalize_ollama_api_base(
            str(getattr(core_settings.llm.cloud, "api_base", "") or "")
        )

        if self._is_ollama_reachable(api_base):
            self.logger.info("Ollama já está ativo em %s", api_base)
            return

        ollama_bin = self._find_ollama_binary()
        if not ollama_bin:
            self.logger.warning("Backend cloud=ollama ativo, mas binário 'ollama' não foi encontrado no PATH.")
            return

        try:
            if self.splash:
                self.splash.show_message("Inicializando serviço Ollama...")

            logs_dir = Path(core_settings.paths.data_dir) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_path = logs_dir / "ollama-serve.log"
            self._ollama_log_handle = open(log_path, "a", encoding="utf-8")

            env = os.environ.copy()
            env["OLLAMA_HOST"] = api_base
            self.ollama_process = subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=self._ollama_log_handle,
                stderr=self._ollama_log_handle,
                env=env,
            )
            self._ollama_started_by_app = True
            self.logger.info("Subprocesso do Ollama iniciado (pid=%s, host=%s)", self.ollama_process.pid, api_base)
        except Exception as exc:
            self.logger.error("Falha ao iniciar ollama serve automaticamente: %s", exc)
            self._ollama_started_by_app = False
            self.ollama_process = None
            if self._ollama_log_handle:
                self._ollama_log_handle.close()
                self._ollama_log_handle = None
            return

        deadline = time.time() + 18.0
        while time.time() < deadline:
            if self._is_ollama_reachable(api_base):
                self.logger.info("Ollama pronto em %s", api_base)
                return
            if self.ollama_process and self.ollama_process.poll() is not None:
                break
            time.sleep(0.4)

        self.logger.warning("Ollama foi iniciado, mas não ficou pronto dentro do timeout inicial (%s).", api_base)

    def stop_managed_ollama_service(self):
        """Encerra o ollama iniciado pela aplicação."""
        if not self._ollama_started_by_app or self.ollama_process is None:
            if self._ollama_log_handle:
                self._ollama_log_handle.close()
                self._ollama_log_handle = None
            return

        try:
            if self.ollama_process.poll() is None:
                self.ollama_process.terminate()
                try:
                    self.ollama_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.ollama_process.kill()
                    self.ollama_process.wait(timeout=3)
        except Exception as exc:
            self.logger.warning("Falha ao encerrar processo do Ollama gerenciado pela app: %s", exc)
        finally:
            self.ollama_process = None
            self._ollama_started_by_app = False
            if self._ollama_log_handle:
                self._ollama_log_handle.close()
                self._ollama_log_handle = None
    
    def show_splash_screen(self):
        """Exibe tela de carregamento"""
        _, assistant_name = self._resolve_custom_identity()
        self.splash = LoadingSplash()
        self.splash.set_identity("", assistant_name)
        self.splash.show_message(f"{assistant_name} esta configurando seu planner")
        self.splash.show()

    def _resolve_custom_identity(self) -> tuple[str, str]:
        """Obtém nomes customizados (usuário/assistente) do YAML de configuração."""
        user_name = "Pindarolas"
        assistant_name = "GLaDOS"
        try:
            from core.config.settings import Settings

            current_settings = Settings.from_yaml()
            yaml_user = str(current_settings.llm.glados.user_name or "").strip()
            yaml_assistant = str(current_settings.llm.glados.glados_name or "").strip()

            if yaml_user:
                user_name = yaml_user
            if yaml_assistant:
                assistant_name = yaml_assistant
        except Exception:
            pass
        return user_name, assistant_name
    
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
        self.splash.show_message("Validando configurações do vault...")
        configured_vault_path = str(Path(core_settings.paths.vault).expanduser())
        bootstrapped_vault = bootstrap_vault(
            vault_path=configured_vault_path,
            vault_structure=getattr(core_settings.obsidian, "vault_structure", []),
        )
        vault_path = str(bootstrapped_vault)
        self.logger.info("Vault pronto: %s", vault_path)

        # Vault fica lazy: apenas valida path no boot; scan completo só sob demanda.
        self.backend_modules['vault_manager'] = LazyObsidianVaultManager(vault_path)

        self.splash.show_message("Inicializando módulos de leitura e agenda...")
        self.backend_modules['book_processor'] = BookProcessor(
            vault_manager=self.backend_modules['vault_manager']
        )
        self.backend_modules['reading_manager'] = ReadingManager(vault_path=vault_path)
        self.backend_modules['agenda_manager'] = AgendaManager(vault_path=vault_path)
        
        self.splash.show_message("Inicializando núcleo cognitivo da GLaDOS...")
        self.backend_modules['llm_module'] = llm

        self.splash.show_message("Sincronização do vault será sob demanda...")
        
        self.connect_modules_to_event_bus()
        
        self.logger.info("Módulos do backend inicializados")
        self.splash.show_message("Módulos carregados com sucesso")
    
    def connect_modules_to_event_bus(self):
        """Conecta módulos ao EventBus para comunicação"""
        bus = self.event_bus
        
        for name, module in self.backend_modules.items():
            bus.module_ready.emit(name, {"status": "initialized", "version": "1.0.0"})
        
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
            QApplication.processEvents()
            time.sleep(2)
            self.splash.fade_out_and_close()
        
        self.window.show()
        self.restore_window_state()
        
        self.logger.info("Interface principal criada com sucesso")
        if self.window and self.window.statusBar():
            self.window.statusBar().showMessage(
                "Bem-vindo ao seu Planner. Sistema inicializado com sucesso.",
                6000
            )
        if self.window:
            QTimer.singleShot(350, self.window.show_onboarding_dialog)
    
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

        self.stop_managed_ollama_service()
        
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
        msg_box.setWindowTitle("Erro Fatal - Planner")
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
