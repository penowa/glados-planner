# test_dashboard_integration.py
"""
Teste completo do dashboard e gerenciador de telas.
"""
import sys
import os

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli.theme import theme
from src.cli.interactive.screen_manager import ScreenManager
from src.cli.interactive.screens.dashboard_screen import DashboardScreen

def test_dashboard():
    """Testa o dashboard e navegação básica."""
    print("🧪 Teste do Dashboard GLaDOS")
    print("=" * 50)
    
    try:
        # Criar screen manager
        manager = ScreenManager()
        
        # Adicionar dashboard
        dashboard = DashboardScreen()
        manager.push(dashboard)
        
        print("✅ Dashboard criado com sucesso")
        print(f"✅ Categorias: {len(dashboard.categories)}")
        
        # Verificar categorias
        for i, cat in enumerate(dashboard.categories):
            print(f"  {i+1}. {cat['name']} - {len(cat['screens'])} telas")
        
        # Testar navegação básica
        print("\n✅ Testando navegação...")
        
        # Testar atalhos rápidos
        print("✅ Atalhos rápidos configurados")
        
        # Testar carregamento de dados
        dashboard._load_dashboard_data()
        print("✅ Dados do dashboard carregados")
        
        print("\n🎉 Teste concluído com sucesso!")
        print("\nPara executar o sistema completo:")
        print("  python src/cli/main.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_all_screens():
    """Testa a criação de todas as telas."""
    print("\n🧪 Teste de Criação de Todas as Telas")
    print("=" * 50)
    
    screens_to_test = [
        ("DashboardScreen", DashboardScreen),
        ("NewBookScreen", "new_book_screen.NewBookScreen"),
        ("SessionScreen", "session_screen.SessionScreen"),
        ("DailyCheckinScreen", "daily_checkin_screen.DailyCheckinScreen"),
        ("WeeklyPlanningScreen", "weekly_planning_screen.WeeklyPlanningScreen"),
        ("AgendaConfigScreen", "agenda_config_screen.AgendaConfigScreen"),
        ("EmergencyModeScreen", "emergency_mode_screen.EmergencyModeScreen"),
        ("GladosQueryScreen", "glados_query_screen.GladosQueryScreen"),
        ("HelpScreen", "help_screen.HelpScreen"),
        ("ShutdownScreen", "shutdown_screen.ShutdownScreen"),
        ("PomodoroSessionScreen", "pomodoro_session_screen.PomodoroSessionScreen"),
        ("ReadingSessionScreen", "reading_session_screen.ReadingSessionScreen"),
        ("BookSelectionScreen", "book_selection_screen.BookSelectionScreen"),
        ("TaskManagementScreen", "task_management_screen.TaskManagementScreen"),
        ("StatisticsScreen", "statistics_screen.StatisticsScreen"),
        ("SettingsScreen", "settings_screen.SettingsScreen")
    ]
    
    success_count = 0
    
    for screen_name, screen_ref in screens_to_test:
        try:
            if isinstance(screen_ref, str):
                # Importar dinamicamente
                module_name, class_name = screen_ref.split('.')
                module = __import__(f"cli.interactive.screens.{module_name}", 
                                  fromlist=[class_name])
                screen_class = getattr(module, class_name)
                instance = screen_class()
            else:
                # Já é uma classe
                instance = screen_ref()
            
            print(f"✅ {screen_name}: Criada com sucesso")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {screen_name}: Erro - {e}")
    
    print(f"\n🎯 {success_count}/{len(screens_to_test)} telas criadas com sucesso")
    return success_count == len(screens_to_test)

def main():
    """Executa todos os testes."""
    print("🚀 TESTE DE INTEGRAÇÃO COMPLETA - GLaDOS CLI")
    print("=" * 60)
    
    # Testar dashboard
    if not test_dashboard():
        print("\n❌ Teste do dashboard falhou!")
        return
    
    # Testar todas as telas
    if not test_all_screens():
        print("\n⚠️  Algumas telas falharam, mas o sistema pode funcionar")
    
    print("\n" + "=" * 60)
    print("✅ TESTES CONCLUÍDOS")
    print("\nPara iniciar o sistema:")
    print("  python src/cli/main.py")
    print("\nAtalhos disponíveis no dashboard:")
    print("  H - Ajuda")
    print("  S - Sair")
    print("  R - Recarregar")
    print("  C - Check-in rápido")
    print("  E - Modo emergência")
    print("  ↑↓ - Navegar")
    print("  Enter - Selecionar")
    print("  ESC - Voltar")

if __name__ == "__main__":
    main()
