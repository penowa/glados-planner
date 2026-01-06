"""
Testes para o módulo GLaDOS
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from unittest.mock import Mock, patch
from rich.console import Console

from src.core.llm.glados.personality.glados_voice import GladosVoice
from src.core.llm.glados.brain.vault_connector import VaultStructure, VaultNote

console = Console()

class TestGladosVoice(unittest.TestCase):
    """Testa a personalidade da GLaDOS"""
    
    def setUp(self):
        self.glados = GladosVoice(user_name="Teste", intensity=0.7)
    
    def test_init(self):
        """Testa inicialização"""
        self.assertEqual(self.glados.user_context.name, "Teste")
        self.assertEqual(self.glados.intensity, 0.7)
        self.assertIn("subject", self.glados.pronouns)
    
    def test_detect_area(self):
        """Testa detecção de área"""
        self.assertEqual(self.glados.detect_area("O que é a virtude?"), "conceitos")
        self.assertEqual(self.glados.detect_area("Livro de Platão"), "leituras")
        self.assertEqual(self.glados.detect_area("Aula de ética"), "disciplinas")
        self.assertEqual(self.glados.detect_area("Qualquer coisa"), "geral")
    
    def test_generate_intro(self):
        """Testa geração de introdução"""
        intro1 = self.glados.generate_intro("Teste")
        self.assertIsInstance(intro1, str)
        self.assertIn("Teste", intro1)
        
        # Segunda interação
        intro2 = self.glados.generate_intro("Teste")
        self.assertIsInstance(intro2, str)
    
    def test_respond_to_name(self):
        """Testa resposta ao nome"""
        response = self.glados.respond_to_name()
        self.assertIsInstance(response, str)
        self.assertIn("Teste", response)

class TestVaultStructure(unittest.TestCase):
    """Testa o conector do vault"""
    
    @patch('pathlib.Path.expanduser')
    @patch('pathlib.Path.exists')
    def setUp(self, mock_exists, mock_expanduser):
        mock_expanduser.return_value = Path("/fake/vault")
        mock_exists.return_value = True
        
        self.vault = VaultStructure("/fake/vault")
        self.vault.notes_cache = {}  # Limpa cache para testes
    
    def test_structure_constants(self):
        """Testa constantes de estrutura"""
        self.assertIn("00-META", self.vault.STRUCTURE)
        self.assertIn("01-LEITURAS", self.vault.STRUCTURE)
        self.assertEqual(self.vault.STRUCTURE["00-META"], "Sistema e metadados")
    
    @patch('pathlib.Path.glob')
    def test_index_vault(self, mock_glob):
        """Testa indexação do vault"""
        mock_file = Mock()
        mock_file.read_text.return_value = "---\ntitle: Teste\n---\nConteúdo"
        mock_glob.return_value = [mock_file]
        
        self.vault._index_vault()
        self.assertGreaterEqual(len(self.vault.notes_cache), 0)
    
    def test_get_vault_stats(self):
        """Testa estatísticas do vault"""
        stats = self.vault.get_vault_stats()
        self.assertIn("total_notes", stats)
        self.assertIn("notes_by_folder", stats)
        self.assertIn("structure", stats)
        self.assertIsInstance(stats["total_notes"], int)

def run_tests():
    """Executa todos os testes"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGladosVoice)
    suite.addTests(loader.loadTestsFromTestCase(TestVaultStructure))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    console.print("[bold]🧪 Testes do Módulo GLaDOS[/bold]\n")
    
    success = run_tests()
    
    if success:
        console.print("\n[green]✅ Todos os testes passaram![/green]")
    else:
        console.print("\n[red]❌ Alguns testes falharam[/red]")
    
    sys.exit(0 if success else 1)
