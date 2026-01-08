from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config.settings import settings

print("=== Configurações Carregadas ===")
print(f"App: {settings.app.name} v{settings.app.version}")
print(f"Usuário: {settings.llm.glados.user_name}")
print(f"Modelo: {settings.llm.model_name}")
print(f"Vault: {settings.paths.vault}")
print(f"Personalidade GLaDOS: {settings.features.enable_glados_personality}")
