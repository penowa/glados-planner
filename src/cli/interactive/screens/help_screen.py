# src/cli/interactive/screens/help_screen.py
"""
Tela de ajuda hierárquica com busca.
"""
from .base_screen import BaseScreen
from cli.theme import theme
from cli.icons import Icon, icon_text

class HelpScreen(BaseScreen):
    """Tela de ajuda do sistema."""
    
    def __init__(self):
        super().__init__()
        self.title = "Ajuda"
        self.help_sections = self._load_help_sections()
    
    def show(self):
        selected_index = 0
        sections = list(self.help_sections.keys()) + ["← Voltar"]
        
        while True:
            self.render_menu([(section, None) for section in sections], selected_index)
            
            key = self.keyboard_handler.wait_for_input()
            
            if key == Key.UP:
                selected_index = (selected_index - 1) % len(sections)
            elif key == Key.DOWN:
                selected_index = (selected_index + 1) % len(sections)
            elif key == Key.ENTER:
                if selected_index == len(sections) - 1:  # Voltar
                    break
                else:
                    section_name = sections[selected_index]
                    self.show_section(section_name)
                    # Voltar ao menu principal após ver seção
                    selected_index = 0
            elif key == Key.ESC:
                break
    
    def show_section(self, section_name):
        """Mostra uma seção específica de ajuda."""
        if section_name in self.help_sections:
            section = self.help_sections[section_name]
            
            while True:
                theme.clear()
                theme.rule(f"[Ajuda: {section_name}]")
                
                theme.print(f"\n{section['description']}", style="info")
                theme.print("=" * 70, style="dim")
                
                # Mostrar tópicos
                for i, topic in enumerate(section['topics'], 1):
                    theme.print(f"\n{i}. {topic['title']}", style="primary")
                    theme.print(f"   {topic['content']}", style="dim")
                
                # Comandos rápidos se disponíveis
                if 'shortcuts' in section:
                    theme.print(f"\n{icon_text(Icon.TIMER, 'Atalhos rápidos:')}", style="info")
                    for shortcut, action in section['shortcuts'].items():
                        theme.print(f"  {shortcut}: {action}", style="dim")
                
                theme.print(f"\n{icon_text(Icon.INFO, 'Pressione ESC para voltar')}", style="dim")
                
                key = self.keyboard_handler.wait_for_input()
                if key == Key.ESC:
                    break
    
    def _load_help_sections(self):
        """Carrega as seções de ajuda."""
        return {
            "Navegação Básica": {
                "description": "Como navegar no sistema GLaDOS CLI",
                "topics": [
                    {
                        "title": "Movimentação",
                        "content": "Use as teclas ↑ ↓ para mover entre itens. Enter para selecionar. ESC para voltar."
                    },
                    {
                        "title": "Atalhos Globais",
                        "content": "H - Ajuda, S - Sair, R - Recarregar, C - Check-in rápido, E - Modo emergência"
                    },
                    {
                        "title": "Menu Principal",
                        "content": "Acesse todas as funcionalidades através do Dashboard principal."
                    }
                ],
                "shortcuts": {
                    "↑↓": "Navegar",
                    "Enter": "Selecionar",
                    "ESC": "Voltar/Sair",
                    "H": "Ajuda",
                    "S": "Sair"
                }
            },
            "Comandos Principais": {
                "description": "Funcionalidades principais do sistema",
                "topics": [
                    {
                        "title": "Gerenciamento de Leitura",
                        "content": "Adicione livros, acompanhe progresso, agende sessões de leitura."
                    },
                    {
                        "title": "Agenda",
                        "content": "Gerencie compromissos, aulas, eventos. Sistema de notificações."
                    },
                    {
                        "title": "Check-in Diário",
                        "content": "Registro de humor, metas, sonhos. Acompanhamento de produtividade."
                    },
                    {
                        "title": "Sessões de Estudo",
                        "content": "Pomodoro, leitura focada, revisão. Temporizadores integrados."
                    }
                ]
            },
            "Sistema GLaDOS": {
                "description": "Sobre a personalidade e funcionalidades da GLaDOS",
                "topics": [
                    {
                        "title": "Consultas",
                        "content": "Faça perguntas à GLaDOS sobre seus dados, planejamento, etc."
                    },
                    {
                        "title": "Personalidade",
                        "content": "A GLaDOS tem um tom passivo-agressivo característico. Isso é normal."
                    },
                    {
                        "title": "Sugestões",
                        "content": "O sistema oferece sugestões baseadas em seus hábitos e dados."
                    }
                ]
            },
            "Solução de Problemas": {
                "description": "Problemas comuns e suas soluções",
                "topics": [
                    {
                        "title": "Cores não aparecem",
                        "content": "Verifique se seu terminal suporta cores 256. Use TERM=xterm-256color"
                    },
                    {
                        "title": "Backend não carrega",
                        "content": "Verifique as dependências. Use python test_integration.py para diagnóstico."
                    },
                    {
                        "title": "Teclas não respondem",
                        "content": "Alguns terminais podem ter mapeamento diferente. Use modo alternativo."
                    },
                    {
                        "title": "Dados não salvam",
                        "content": "Verifique permissões de escrita no diretório do vault."
                    }
                ]
            },
            "Sobre o Sistema": {
                "description": "Informações técnicas sobre o GLaDOS Planner",
                "topics": [
                    {
                        "title": "Versão",
                        "content": "GLaDOS Planner CLI v0.1.0 - Fase 0: Fundamentos"
                    },
                    {
                        "title": "Arquitetura",
                        "content": "CLI Python com backend modular. Integração com Obsidian."
                    },
                    {
                        "title": "Desenvolvimento",
                        "content": "Sistema em desenvolvimento ativo. Relate bugs no repositório."
                    },
                    {
                        "title": "Licença",
                        "content": "Software educacional para uso pessoal."
                    }
                ]
            }
        }
