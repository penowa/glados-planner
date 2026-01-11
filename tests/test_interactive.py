#!/usr/bin/env python3
"""
Script de teste para a implementação do Dia 1.
"""
import os
import sys

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cli.interactive.screens.test_screen import TestScreen
from cli.interactive.screens.base_screen import ScreenManager


def main():
    """Função principal de teste."""
    print("🤖 TESTE DO SISTEMA INTERATIVO GLaDOS PLANNER")
    print("=" * 50)
    
    # Teste simples do KeyboardHandler
    print("\n1. Testando KeyboardHandler...")
    from cli.interactive.input.keyboard_handler import KeyboardHandler, Key
    handler = KeyboardHandler()
    
    def test_callback():
        print("✓ Callback de Enter acionado!")
    
    handler.register_callback(Key.ENTER, test_callback)
    print("   Pressione Enter para testar o callback (ou ESC para pular)...")
    handler.wait_for_key([Key.ENTER, Key.ESC], timeout=5)
    
    # Teste do NavigationState
    print("\n2. Testando NavigationState...")
    from cli.interactive.input.navigation_state import NavigationState
    nav = NavigationState(["Item 1", "Item 2", "Item 3"])
    nav.move_down()
    print(f"   Item selecionado: {nav.selected_item} (índice: {nav.selected_index})")
    
    # Teste da tela interativa
    print("\n3. Iniciando tela interativa de teste...")
    print("   Use as setas para navegar, Enter para selecionar, Q para sair.")
    input("   Pressione Enter para continuar...")
    
    # Iniciar o ScreenManager com a tela de teste
    manager = ScreenManager()
    manager.push_screen(TestScreen())
    
    try:
        manager.run()
        print("\n✅ Teste concluído com sucesso!")
    except KeyboardInterrupt:
        print("\n⏹️ Teste interrompido pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
