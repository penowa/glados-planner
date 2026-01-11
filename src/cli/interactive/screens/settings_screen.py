# src/cli/interactive/screens/settings_screen.py
"""
Tela de configurações do sistema.
"""
import os
import json
from .base_screen import BaseScreen
from src.cli.theme import theme
from src.cli.icons import Icon, icon_text

class SettingsScreen(BaseScreen):
    """Tela de configurações."""
    
    def __init__(self):
        super().__init__()
        self.title = "Configurações"
        self.settings_file = "glados_settings.json"
        self.settings = self._load_settings()
    
    def show(self):
        selected_index = 0
        options = [
            ("⚙️  Configurações Gerais", self.general_settings),
            ("🎨 Aparência e Tema", self.appearance_settings),
            ("⌨️  Teclas e Atalhos", self.keyboard_settings),
            ("🔔 Notificações", self.notification_settings),
            ("📁 Caminhos e Arquivos", self.path_settings),
            ("🔄 Sincronização", self.sync_settings),
            ("🔧 Avançado", self.advanced_settings),
            ("📤 Exportar/Importar", self.import_export_settings),
            ("🔄 Restaurar Padrões", self.restore_defaults),
            ("← Voltar", lambda: "back")
        ]
        
        while True:
            self.render_menu(options, selected_index)
            
            key = self.keyboard_handler.wait_for_input()
            
            if key == Key.UP:
                selected_index = (selected_index - 1) % len(options)
            elif key == Key.DOWN:
                selected_index = (selected_index + 1) % len(options)
            elif key == Key.ENTER:
                result = options[selected_index][1]()
                if result == "back":
                    self._save_settings()
                    break
            elif key == Key.ESC:
                self._save_settings()
                break
    
    def _load_settings(self):
        """Carrega configurações do arquivo."""
        default_settings = {
            'general': {
                'auto_save': True,
                'auto_save_interval': 300,  # segundos
                'session_timeout': 1800,    # segundos
                'language': 'pt-br',
                'date_format': 'dd/mm/yyyy'
            },
            'appearance': {
                'theme': 'portal',
                'show_icons': True,
                'animations': True,
                'compact_mode': False,
                'glados_personality': 'medium'  # low, medium, high
            },
            'keyboard': {
                'navigation_delay': 100,  # ms
                'confirm_exit': True,
                'quick_shortcuts': True
            },
            'notifications': {
                'enabled': True,
                'sound': False,
                'desktop_notifications': False,
                'reminder_before_event': 15  # minutos
            },
            'paths': {
                'vault_path': '',
                'backup_path': '',
                'export_path': ''
            },
            'sync': {
                'auto_sync': False,
                'sync_interval': 3600,  # segundos
                'cloud_backup': False
            }
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Mesclar com padrões
                    for category in default_settings:
                        if category in loaded:
                            default_settings[category].update(loaded[category])
            
            return default_settings
            
        except:
            return default_settings
    
    def _save_settings(self):
        """Salva configurações no arquivo."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except:
            pass  # Silenciosamente falha se não puder salvar
    
    def general_settings(self):
        """Configurações gerais."""
        theme.clear()
        theme.rule("[Configurações Gerais]")
        
        general = self.settings['general']
        
        theme.print(f"\n{icon_text(Icon.SETTINGS, 'Configurações atuais:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        for key, value in general.items():
            theme.print(f"  {key.replace('_', ' ').title()}: {value}", style="info")
        
        theme.print(f"\n{icon_text(Icon.EDIT, 'Editar configurações:')}", style="primary")
        
        # Auto-save
        auto_save = input(f"Auto-save (atual: {general['auto_save']}) [S/n]: ").strip().lower()
        if auto_save in ['s', 'sim', '']:
            general['auto_save'] = True
        elif auto_save in ['n', 'nao', 'não']:
            general['auto_save'] = False
        
        # Intervalo de auto-save
        if general['auto_save']:
            interval = input(f"Intervalo auto-save (segundos, atual: {general['auto_save_interval']}): ").strip()
            if interval.isdigit():
                general['auto_save_interval'] = int(interval)
        
        # Idioma
        theme.print(f"\nIdioma disponíveis:", style="info")
        theme.print("  1) Português (Brasil)")
        theme.print("  2) English")
        
        lang_choice = input(f"Escolha (atual: {general['language']}): ").strip()
        if lang_choice == '1':
            general['language'] = 'pt-br'
        elif lang_choice == '2':
            general['language'] = 'en'
        
        theme.print(f"\n✅ Configurações gerais atualizadas.", style="success")
        self.wait_for_exit()
        return "continue"
    
    def appearance_settings(self):
        """Configurações de aparência."""
        theme.clear()
        theme.rule("[Aparência e Tema]")
        
        appearance = self.settings['appearance']
        
        theme.print(f"\n{icon_text(Icon.PORTAL, 'Temas disponíveis:')}", style="primary")
        theme.print("  1) 🎨 Portal (padrão GLaDOS)")
        theme.print("  2) ⚫ Dark (escuro)")
        theme.print("  3) ⚪ Light (claro)")
        theme.print("  4) 🟢 Matrix (verde)")
        theme.print("  5) 🔵 Blue (azul)")
        
        theme_choice = input(f"\nEscolha o tema (atual: {appearance['theme']}): ").strip()
        theme_map = {'1': 'portal', '2': 'dark', '3': 'light', '4': 'matrix', '5': 'blue'}
        if theme_choice in theme_map:
            appearance['theme'] = theme_map[theme_choice]
        
        # Personalidade GLaDOS
        theme.print(f"\n{icon_text(Icon.GLADOS, 'Personalidade GLaDOS:')}", style="primary")
        theme.print("  1) 🔇 Baixa (poucos comentários)")
        theme.print("  2) 🔉 Média (balanceada)")
        theme.print("  3) 🔊 Alta (muitos comentários)")
        
        personality_choice = input(f"\nNível (atual: {appearance['glados_personality']}): ").strip()
        if personality_choice == '1':
            appearance['glados_personality'] = 'low'
        elif personality_choice == '2':
            appearance['glados_personality'] = 'medium'
        elif personality_choice == '3':
            appearance['glados_personality'] = 'high'
        
        # Outras configurações
        show_icons = input(f"\nMostrar ícones (atual: {appearance['show_icons']}) [S/n]: ").strip().lower()
        if show_icons in ['s', 'sim', '']:
            appearance['show_icons'] = True
        elif show_icons in ['n', 'nao', 'não']:
            appearance['show_icons'] = False
        
        animations = input(f"Animações (atual: {appearance['animations']}) [S/n]: ").strip().lower()
        if animations in ['s', 'sim', '']:
            appearance['animations'] = True
        elif animations in ['n', 'nao', 'não']:
            appearance['animations'] = False
        
        theme.print(f"\n✅ Configurações de aparência atualizadas.", style="success")
        theme.print("Reinicie a aplicação para aplicar todas as mudanças.", style="warning")
        
        self.wait_for_exit()
        return "continue"
    
    def keyboard_settings(self):
        """Configurações de teclado."""
        theme.clear()
        theme.rule("[Teclas e Atalhos]")
        
        keyboard = self.settings['keyboard']
        
        theme.print(f"\n{icon_text(Icon.KEYBOARD, 'Configurações atuais:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        for key, value in keyboard.items():
            theme.print(f"  {key.replace('_', ' ').title()}: {value}", style="info")
        
        theme.print(f"\n{icon_text(Icon.EDIT, 'Editar configurações:')}", style="primary")
        
        # Delay de navegação
        delay = input(f"Delay de navegação (ms, atual: {keyboard['navigation_delay']}): ").strip()
        if delay.isdigit():
            keyboard['navigation_delay'] = int(delay)
        
        # Confirmar saída
        confirm = input(f"Confirmar saída (atual: {keyboard['confirm_exit']}) [S/n]: ").strip().lower()
        if confirm in ['s', 'sim', '']:
            keyboard['confirm_exit'] = True
        elif confirm in ['n', 'nao', 'não']:
            keyboard['confirm_exit'] = False
        
        # Atalhos rápidos
        shortcuts = input(f"Atalhos rápidos (atual: {keyboard['quick_shortcuts']}) [S/n]: ").strip().lower()
        if shortcuts in ['s', 'sim', '']:
            keyboard['quick_shortcuts'] = True
        elif shortcuts in ['n', 'nao', 'não']:
            keyboard['quick_shortcuts'] = False
        
        # Mostrar atalhos disponíveis
        theme.print(f"\n{icon_text(Icon.INFO, 'Atalhos disponíveis:')}", style="primary")
        theme.print("  H - Ajuda", style="dim")
        theme.print("  S - Sair", style="dim")
        theme.print("  R - Recarregar", style="dim")
        theme.print("  C - Check-in rápido", style="dim")
        theme.print("  E - Modo emergência", style="dim")
        theme.print("  M - Mostrar/ocultar menu", style="dim")
        
        theme.print(f"\n✅ Configurações de teclado atualizadas.", style="success")
        
        self.wait_for_exit()
        return "continue"
    
    def notification_settings(self):
        """Configurações de notificações."""
        theme.clear()
        theme.rule("[Notificações]")
        
        notifications = self.settings['notifications']
        
        theme.print(f"\n{icon_text(Icon.BELL, 'Configurações atuais:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        for key, value in notifications.items():
            theme.print(f"  {key.replace('_', ' ').title()}: {value}", style="info")
        
        # Habilitar/desabilitar
        enabled = input(f"\nHabilitar notificações (atual: {notifications['enabled']}) [S/n]: ").strip().lower()
        if enabled in ['s', 'sim', '']:
            notifications['enabled'] = True
        elif enabled in ['n', 'nao', 'não']:
            notifications['enabled'] = False
        
        if notifications['enabled']:
            # Som
            sound = input(f"Som (atual: {notifications['sound']}) [S/n]: ").strip().lower()
            if sound in ['s', 'sim', '']:
                notifications['sound'] = True
            elif sound in ['n', 'nao', 'não']:
                notifications['sound'] = False
            
            # Notificações de desktop
            desktop = input(f"Notificações desktop (atual: {notifications['desktop_notifications']}) [S/n]: ").strip().lower()
            if desktop in ['s', 'sim', '']:
                notifications['desktop_notifications'] = True
            elif desktop in ['n', 'nao', 'não']:
                notifications['desktop_notifications'] = False
            
            # Lembrete antes de eventos
            reminder = input(f"Lembrete antes de eventos (minutos, atual: {notifications['reminder_before_event']}): ").strip()
            if reminder.isdigit():
                notifications['reminder_before_event'] = int(reminder)
        
        theme.print(f"\n✅ Configurações de notificações atualizadas.", style="success")
        
        self.wait_for_exit()
        return "continue"
    
    def path_settings(self):
        """Configurações de caminhos."""
        theme.clear()
        theme.rule("[Caminhos e Arquivos]")
        
        paths = self.settings['paths']
        
        theme.print(f"\n{icon_text(Icon.FOLDER, 'Caminhos atuais:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        for key, value in paths.items():
            theme.print(f"  {key.replace('_', ' ').title()}: {value or '(não configurado)'}", style="info")
        
        theme.print(f"\n{icon_text(Icon.EDIT, 'Editar caminhos:')}", style="primary")
        
        # Caminho do vault
        vault_path = input(f"Caminho do vault Obsidian (atual: {paths['vault_path']}): ").strip()
        if vault_path and os.path.exists(vault_path):
            paths['vault_path'] = vault_path
            theme.print("✅ Caminho do vault validado.", style="success")
        elif vault_path:
            theme.print("❌ Caminho não existe. Mantendo anterior.", style="error")
        
        # Caminho de backup
        backup_path = input(f"Caminho de backup (atual: {paths['backup_path']}): ").strip()
        if backup_path:
            paths['backup_path'] = backup_path
        
        # Caminho de exportação
        export_path = input(f"Caminho de exportação (atual: {paths['export_path']}): ").strip()
        if export_path:
            paths['export_path'] = export_path
        
        theme.print(f"\n✅ Configurações de caminhos atualizadas.", style="success")
        
        self.wait_for_exit()
        return "continue"
    
    def sync_settings(self):
        """Configurações de sincronização."""
        theme.clear()
        theme.rule("[Sincronização]")
        
        sync = self.settings['sync']
        
        theme.print(f"\n{icon_text(Icon.SYNC, 'Configurações atuais:')}", style="primary")
        theme.print("=" * 50, style="dim")
        
        for key, value in sync.items():
            theme.print(f"  {key.replace('_', ' ').title()}: {value}", style="info")
        
        # Auto-sync
        auto_sync = input(f"\nSincronização automática (atual: {sync['auto_sync']}) [S/n]: ").strip().lower()
        if auto_sync in ['s', 'sim', '']:
            sync['auto_sync'] = True
        elif auto_sync in ['n', 'nao', 'não']:
            sync['auto_sync'] = False
        
        if sync['auto_sync']:
            # Intervalo de sync
            interval = input(f"Intervalo de sincronização (segundos, atual: {sync['sync_interval']}): ").strip()
            if interval.isdigit():
                sync['sync_interval'] = int(interval)
            
            # Backup em nuvem
            cloud = input(f"Backup em nuvem (atual: {sync['cloud_backup']}) [S/n]: ").strip().lower()
            if cloud in ['s', 'sim', '']:
                sync['cloud_backup'] = True
            elif cloud in ['n', 'nao', 'não']:
                sync['cloud_backup'] = False
        
        theme.print(f"\n✅ Configurações de sincronização atualizadas.", style="success")
        
        self.wait_for_exit()
        return "continue"
    
    def advanced_settings(self):
        """Configurações avançadas."""
        theme.clear()
        theme.rule("[Configurações Avançadas]")
        
        theme.print(f"\n{icon_text(Icon.WARNING, 'ATENÇÃO: Estas configurações são para usuários avançados.')}", style="error")
        theme.print("Alterações incorretas podem causar mau funcionamento do sistema.", style="warning")
        
        theme.print(f"\n{icon_text(Icon.INFO, 'Opções avançadas:')}", style="primary")
        theme.print("  1) 🔧 Modo desenvolvedor")
        theme.print("  2) 📝 Logging detalhado")
        theme.print("  3) 🐛 Modo debug")
        theme.print("  4) 💾 Cache avançado")
        theme.print("  5) 🚀 Otimizações de performance")
        
        choice = input("\nEscolha (1-5, ou Enter para cancelar): ").strip()
        
        if choice == '1':
            self._developer_mode()
        elif choice == '2':
            self._logging_settings()
        elif choice == '3':
            self._debug_mode()
        elif choice == '4':
            self._cache_settings()
        elif choice == '5':
            self._performance_settings()
        
        return "continue"
    
    def _developer_mode(self):
        """Ativa modo desenvolvedor."""
        theme.print(f"\n{icon_text(Icon.CODE, 'Modo desenvolvedor:')}", style="primary")
        
        enable = input("Ativar modo desenvolvedor? [S/n]: ").strip().lower()
        
        if enable in ['s', 'sim', '']:
            # Adicionar configurações de desenvolvedor
            if 'developer' not in self.settings:
                self.settings['developer'] = {}
            
            self.settings['developer']['enabled'] = True
            self.settings['developer']['show_ids'] = True
            self.settings['developer']['verbose_logging'] = True
            
            theme.print("✅ Modo desenvolvedor ativado.", style="success")
            theme.print("Recursos disponíveis:", style="info")
            theme.print("  • IDs visíveis em interfaces", style="dim")
            theme.print("  • Logging detalhado", style="dim")
            theme.print("  • Comandos de debug", style="dim")
        else:
            if 'developer' in self.settings:
                self.settings['developer']['enabled'] = False
            theme.print("Modo desenvolvedor desativado.", style="warning")
        
        self.wait_for_exit()
    
    def _logging_settings(self):
        """Configurações de logging."""
        theme.print(f"\n{icon_text(Icon.FILE, 'Configurações de logging:')}", style="primary")
        
        # TODO: Implementar configurações de logging
        
        theme.print("Em desenvolvimento...", style="warning")
        self.wait_for_exit()
    
    def _debug_mode(self):
        """Configurações de debug."""
        theme.print(f"\n{icon_text(Icon.BUG, 'Modo debug:')}", style="primary")
        
        enable = input("Ativar modo debug? [S/n]: ").strip().lower()
        
        if enable in ['s', 'sim', '']:
            if 'debug' not in self.settings:
                self.settings['debug'] = {}
            
            self.settings['debug']['enabled'] = True
            self.settings['debug']['level'] = 'verbose'
            
            theme.print("✅ Modo debug ativado.", style="success")
            theme.print("Informações de debug serão mostradas.", style="info")
        else:
            if 'debug' in self.settings:
                self.settings['debug']['enabled'] = False
            theme.print("Modo debug desativado.", style="warning")
        
        self.wait_for_exit()
    
    def _cache_settings(self):
        """Configurações de cache."""
        theme.print(f"\n{icon_text(Icon.STORAGE, 'Configurações de cache:')}", style="primary")
        
        # TODO: Implementar configurações de cache
        
        theme.print("Em desenvolvimento...", style="warning")
        self.wait_for_exit()
    
    def _performance_settings(self):
        """Configurações de performance."""
        theme.print(f"\n{icon_text(Icon.SPEED, 'Otimizações de performance:')}", style="primary")
        
        # TODO: Implementar configurações de performance
        
        theme.print("Em desenvolvimento...", style="warning")
        self.wait_for_exit()
    
    def import_export_settings(self):
        """Importar/exportar configurações."""
        theme.clear()
        theme.rule("[Importar/Exportar Configurações]")
        
        theme.print(f"\n{icon_text(Icon.EXPORT, 'Opções:')}", style="primary")
        theme.print("  1) 📤 Exportar configurações atuais")
        theme.print("  2) 📥 Importar configurações de arquivo")
        theme.print("  3) 🔗 Importar do cloud")
        theme.print("  4) 📋 Copiar configurações")
        
        choice = input("\nEscolha (1-4): ").strip()
        
        if choice == '1':
            self._export_settings()
        elif choice == '2':
            self._import_settings()
        elif choice == '3':
            self._import_from_cloud()
        elif choice == '4':
            self._copy_settings()
        
        return "continue"
    
    def _export_settings(self):
        """Exporta configurações para arquivo."""
        filename = input("Nome do arquivo (padrão: glados_backup.json): ").strip()
        if not filename:
            filename = "glados_backup.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            
            theme.print(f"\n✅ Configurações exportadas para '{filename}'.", style="success")
            
        except Exception as e:
            theme.print(f"\n❌ Erro ao exportar: {e}", style="error")
        
        self.wait_for_exit()
    
    def _import_settings(self):
        """Importa configurações de arquivo."""
        filename = input("Nome do arquivo para importar: ").strip()
        
        if not os.path.exists(filename):
            theme.print(f"\n❌ Arquivo '{filename}' não encontrado.", style="error")
            self.wait_for_exit()
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # Mesclar configurações
            for category in imported_settings:
                if category not in self.settings:
                    self.settings[category] = {}
                self.settings[category].update(imported_settings[category])
            
            theme.print(f"\n✅ Configurações importadas de '{filename}'.", style="success")
            theme.print("Algumas configurações podem exigir reinicialização.", style="warning")
            
        except Exception as e:
            theme.print(f"\n❌ Erro ao importar: {e}", style="error")
        
        self.wait_for_exit()
    
    def _import_from_cloud(self):
        """Importa configurações do cloud."""
        theme.print(f"\n{icon_text(Icon.CLOUD, 'Importar do cloud:')}", style="primary")
        theme.print("Em desenvolvimento...", style="warning")
        self.wait_for_exit()
    
    def _copy_settings(self):
        """Copia configurações para clipboard."""
        theme.print(f"\n{icon_text(Icon.COPY, 'Copiar configurações:')}", style="primary")
        
        try:
            import pyperclip
            settings_str = json.dumps(self.settings, indent=2, ensure_ascii=False)
            pyperclip.copy(settings_str)
            
            theme.print("✅ Configurações copiadas para clipboard.", style="success")
            
        except ImportError:
            theme.print("❌ pyperclip não instalado. Instale com: pip install pyperclip", style="error")
        except Exception as e:
            theme.print(f"❌ Erro ao copiar: {e}", style="error")
        
        self.wait_for_exit()
    
    def restore_defaults(self):
        """Restaura configurações padrão."""
        theme.clear()
        theme.rule("[Restaurar Padrões]")
        
        theme.print(f"\n{icon_text(Icon.WARNING, 'ATENÇÃO: Esta ação não pode ser desfeita!')}", style="error")
        theme.print("Todas as configurações personalizadas serão perdidas.", style="warning")
        
        confirm = input("\nDigite 'RESTAURAR' para confirmar: ").strip()
        
        if confirm == 'RESTAURAR':
            # Carregar configurações padrão
            default_settings = {
                'general': {
                    'auto_save': True,
                    'auto_save_interval': 300,
                    'session_timeout': 1800,
                    'language': 'pt-br',
                    'date_format': 'dd/mm/yyyy'
                },
                'appearance': {
                    'theme': 'portal',
                    'show_icons': True,
                    'animations': True,
                    'compact_mode': False,
                    'glados_personality': 'medium'
                },
                'keyboard': {
                    'navigation_delay': 100,
                    'confirm_exit': True,
                    'quick_shortcuts': True
                },
                'notifications': {
                    'enabled': True,
                    'sound': False,
                    'desktop_notifications': False,
                    'reminder_before_event': 15
                },
                'paths': {
                    'vault_path': '',
                    'backup_path': '',
                    'export_path': ''
                },
                'sync': {
                    'auto_sync': False,
                    'sync_interval': 3600,
                    'cloud_backup': False
                }
            }
            
            self.settings = default_settings
            self._save_settings()
            
            theme.print(f"\n✅ {icon_text(Icon.SUCCESS, 'Configurações restauradas para padrão.')}", style="success")
            theme.print("Reinicie a aplicação para aplicar todas as mudanças.", style="warning")
        
        else:
            theme.print(f"\n{icon_text(Icon.INFO, 'Operação cancelada.')}", style="warning")
        
        self.wait_for_exit()
        return "continue"
