# src/cli/interactive/menu.py
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import sys
import os

# Adiciona o diretório src ao path para importações
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cli.theme import theme
from cli.icons import Icon, icon_text

class MenuItem:
    """Representa um item de menu com ação associada"""
    
    def __init__(self, 
                 label: str, 
                 icon: Optional[str] = None,
                 action: Optional[Callable] = None,
                 data: Optional[Dict] = None,
                 enabled: bool = True):
        self.label = label
        self.icon = icon
        self.action = action
        self.data = data or {}
        self.enabled = enabled
        self._id = id(self)
    
    def __str__(self):
        if self.icon:
            return icon_text(self.icon, self.label)
        return self.label

class MenuStyle(Enum):
    """Estilos de menu disponíveis"""
    VERTICAL = "vertical"      # Lista vertical (padrão)
    HORIZONTAL = "horizontal"  # Barra horizontal
    GRID = "grid"              # Grade 2D
    TREE = "tree"              # Hierárquico

class Menu:
    """Sistema de menu interativo com navegação por teclado"""
    
    def __init__(self, 
                 title: str = "Menu",
                 items: List[MenuItem] = None,
                 style: MenuStyle = MenuStyle.VERTICAL,
                 show_help: bool = True):
        self.title = title
        self.items = items or []
        self.style = style
        self.show_help = show_help
        self.selected_index = 0
        self.running = False
        self.callback = None
        
        # Configurações de estilo
        self.indicator = "▶"  # Indicador de item selecionado
        self.disabled_style = "dim"
        self.border_enabled = True
        
        # Histórico de navegação
        self._history = []
    
    def add_item(self, label: str, **kwargs) -> 'MenuItem':
        """Adiciona item ao menu"""
        item = MenuItem(label, **kwargs)
        self.items.append(item)
        return item
    
    def insert_item(self, index: int, label: str, **kwargs) -> 'MenuItem':
        """Insere item em posição específica"""
        item = MenuItem(label, **kwargs)
        self.items.insert(index, item)
        # Ajusta seleção se necessário
        if index <= self.selected_index:
            self.selected_index += 1
        return item
    
    def remove_item(self, index: int) -> bool:
        """Remove item por índice"""
        if 0 <= index < len(self.items):
            # Ajusta seleção se necessário
            if index < self.selected_index:
                self.selected_index -= 1
            elif index == self.selected_index:
                self.selected_index = min(self.selected_index, len(self.items) - 2)
            
            self.items.pop(index)
            return True
        return False
    
    def get_selected_item(self) -> Optional[MenuItem]:
        """Retorna item atualmente selecionado"""
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None
    
    def move_up(self) -> None:
        """Move seleção para cima"""
        if len(self.items) == 0:
            return
        
        # Encontra próximo item habilitado acima
        for i in range(1, len(self.items)):
            new_index = (self.selected_index - i) % len(self.items)
            if self.items[new_index].enabled:
                self.selected_index = new_index
                break
    
    def move_down(self) -> None:
        """Move seleção para baixo"""
        if len(self.items) == 0:
            return
        
        # Encontra próximo item habilitado abaixo
        for i in range(1, len(self.items)):
            new_index = (self.selected_index + i) % len(self.items)
            if self.items[new_index].enabled:
                self.selected_index = new_index
                break
    
    def move_to(self, index: int) -> bool:
        """Move seleção para índice específico"""
        if 0 <= index < len(self.items) and self.items[index].enabled:
            self.selected_index = index
            return True
        return False
    
    def select(self) -> Any:
        """Seleciona item atual e executa ação"""
        item = self.get_selected_item()
        if item and item.enabled and item.action:
            # Salva no histórico
            self._history.append(self.selected_index)
            
            # Executa ação
            try:
                if item.data:
                    return item.action(**item.data)
                else:
                    return item.action()
            except Exception as e:
                theme.print(f"Erro ao executar ação: {e}", style="error")
                return None
        return None
    
    def render(self) -> str:
        """Renderiza o menu para exibição"""
        lines = []
        
        # Título
        if self.title:
            if self.border_enabled:
                theme.rule(f" {self.title} ", style="primary")
            else:
                theme.print(f"\n{self.title}", style="accent")
                theme.print("─" * len(self.title), style="secondary")
        
        # Itens do menu
        if not self.items:
            theme.print("(Nenhum item disponível)", style="dim")
            return ""
        
        for i, item in enumerate(self.items):
            prefix = "  "
            if i == self.selected_index:
                prefix = f"{self.indicator} "
            
            # Estilo baseado no estado
            style = "primary"
            if not item.enabled:
                style = self.disabled_style
            elif i == self.selected_index:
                style = "accent"
            
            # Renderiza item
            item_text = str(item)
            theme.print(f"{prefix}{item_text}", style=style)
        
        # Ajuda
        if self.show_help:
            self._render_help()
        
        return "\n".join(lines)
    
    def _render_help(self) -> None:
        """Renderiza instruções de ajuda"""
        theme.print("\n" + "─" * 40, style="dim")
        theme.print("↑↓: Navegar | Enter: Selecionar | ESC: Voltar", style="info")
    
    def clear_screen(self) -> None:
        """Limpa a tela (compatível com múltiplos sistemas)"""
        theme.clear()
    
    def run(self, clear_each_cycle: bool = False) -> Any:
        """Executa loop principal do menu"""
        from src.cli.interactive.terminal import Key
        
        self.running = True
        result = None
        
        try:
            while self.running:
                if clear_each_cycle:
                    self.clear_screen()
                
                # Renderiza menu
                print()
                self.render()
                
                # Aguarda input
                key = keyboard_handler.wait_for_input()
                
                # Processa tecla
                if key == Key.UP:
                    self.move_up()
                elif key == Key.DOWN:
                    self.move_down()
                elif key == Key.ENTER:
                    result = self.select()
                    if result is not None:
                        break
                elif key == Key.ESC:
                    self.running = False
                    result = None
                    break
                elif isinstance(key, str) and key.isdigit():
                    # Seleção direta por número
                    idx = int(key) - 1
                    if 0 <= idx < len(self.items):
                        self.move_to(idx)
                elif isinstance(key, Key):
                    # Outras teclas do enum
                    pass

        except KeyboardInterrupt:
            from cli.theme import theme
            theme.print("\nInterrompido pelo usuário", style="warning")
        finally:
            self.running = False
        
        return result

class MultiLevelMenu:
    """Menu hierárquico com múltiplos níveis"""
    
    def __init__(self, title: str = "Sistema GLaDOS"):
        self.title = title
        self.menu_stack = []  # Pilha de menus
        self.history = []     # Histórico completo
    
    def create_submenu(self, title: str, items: List[MenuItem] = None) -> Menu:
        """Cria submenu e adiciona à pilha"""
        menu = Menu(title, items)
        self.menu_stack.append(menu)
        return menu
    
    def go_back(self) -> bool:
        """Volta para menu anterior"""
        if len(self.menu_stack) > 1:
            self.menu_stack.pop()
            return True
        return False
    
    def get_current_menu(self) -> Optional[Menu]:
        """Retorna menu atual"""
        if self.menu_stack:
            return self.menu_stack[-1]
        return None
    
    def run(self) -> Any:
        """Executa sistema de menus hierárquico"""
        theme.clear()
        theme.rule(f" {self.title} ", style="accent")
        
        while self.menu_stack:
            current_menu = self.get_current_menu()
            if not current_menu:
                break
            
            # Executa menu atual
            result = current_menu.run(clear_each_cycle=False)
            
            # Se menu retornou None (ESC), volta um nível
            if result is None:
                if not self.go_back():
                    break
            else:
                # Salva resultado no histórico
                self.history.append({
                    'menu': current_menu.title,
                    'result': result
                })
        
        return self.history[-1]['result'] if self.history else None
