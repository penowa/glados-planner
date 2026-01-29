"""
ui_bridge.py

Camada oficial de integração entre o backend do GLaDOS e qualquer interface gráfica.
Esta é a ÚNICA fronteira que a UI pode conhecer.

Nenhuma lógica de negócio deve existir aqui.
Nenhum módulo interno deve ser exposto diretamente.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, Optional
from datetime import datetime

# =========================
# Core imports (internos)
# =========================

from core.modules.agenda_manager import AgendaManager
from core.modules.reading_manager import ReadingManager
from core.modules.preference_manager import PreferenceManager
from core.modules.smart_allocator import SmartAllocator

from core.vault.vault_manager import VaultManager
from core.llm.local_llm import LocalLLM

# =========================
# App initialization
# =========================

app = FastAPI(
    title="GLaDOS UI Bridge",
    description="Interface oficial entre o backend do GLaDOS e a UI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # UI local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Singletons (backend)
# =========================

agenda_manager = AgendaManager()
reading_manager = ReadingManager()
preference_manager = PreferenceManager()
vault_manager = VaultManager()
llm = LocalLLM()

# =========================
# Helpers
# =========================

def ok(data: Any) -> Dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
    }

def error(message: str, details: Optional[Any] = None) -> Dict[str, Any]:
    return {
        "status": "error",
        "timestamp": datetime.utcnow().isoformat(),
        "error": {
            "message": message,
            "details": details,
        },
    }

# =========================
# System / Health
# =========================

@app.get("/ui/system/health")
def system_health():
    """
    Usado pela UI para saber se o backend está vivo.
    """
    return ok({
        "alive": True,
        "modules": {
            "agenda": True,
            "vault": True,
            "llm": llm.is_available(),
        }
    })

# =========================
# Dashboard
# =========================

@app.get("/ui/dashboard/state")
def dashboard_state():
    """
    Estado resumido do sistema para a dashboard.
    Nenhuma lógica pesada deve ser feita aqui.
    """
    try:
        agenda_overview = agenda_manager.get_today_overview()
        reading_overview = reading_manager.get_status()

        return ok({
            "agenda": agenda_overview,
            "reading": reading_overview,
        })

    except Exception as e:
        return error("Failed to load dashboard state", str(e))

# =========================
# Agenda
# =========================

@app.get("/ui/agenda/day")
def agenda_day(date: Optional[str] = None):
    """
    Retorna a visão diária da agenda.
    A UI NÃO deve inferir nada além do que vem aqui.
    """
    try:
        events = agenda_manager.get_day_events(date)
        checkin = agenda_manager.get_daily_checkin(date)

        return ok({
            "date": date,
            "checkin": checkin,
            "events": events,
        })

    except Exception as e:
        return error("Failed to load daily agenda", str(e))


@app.post("/ui/agenda/action")
def agenda_action(payload: Dict[str, Any]):
    """
    Recebe intenções da UI (ex: mover evento, otimizar agenda).
    NÃO aplica mudanças automaticamente.
    """
    try:
        result = agenda_manager.handle_ui_action(payload)
        return ok(result)

    except Exception as e:
        return error("Agenda action failed", str(e))

# =========================
# Reading / Books
# =========================

@app.get("/ui/reading/status")
def reading_status():
    """
    Estado atual da leitura (progresso, metas, blocos sugeridos).
    """
    try:
        status = reading_manager.get_status()
        return ok(status)

    except Exception as e:
        return error("Failed to load reading status", str(e))

# =========================
# Vault / Knowledge
# =========================

@app.get("/ui/vault/search")
def vault_search(query: str):
    """
    Busca semântica no vault.
    """
    try:
        results = vault_manager.semantic_search(query)
        return ok(results)

    except Exception as e:
        return error("Vault search failed", str(e))


@app.get("/ui/vault/note")
def vault_note(note_id: str):
    """
    Retorna uma nota específica para visualização.
    """
    try:
        note = vault_manager.get_note(note_id)
        return ok(note)

    except Exception as e:
        return error("Failed to load note", str(e))

# =========================
# LLM / GLaDOS
# =========================

@app.post("/ui/llm/query")
def llm_query(payload: Dict[str, Any]):
    """
    Consulta direta ao GLaDOS (LLM).
    """
    try:
        prompt = payload.get("prompt")
        context = payload.get("context")

        response = llm.query(prompt, context=context)
        return ok(response)

    except Exception as e:
        return error("LLM query failed", str(e))

# =========================
# Preferences
# =========================

@app.get("/ui/preferences")
def get_preferences():
    try:
        prefs = preference_manager.get_all()
        return ok(prefs)

    except Exception as e:
        return error("Failed to load preferences", str(e))


@app.post("/ui/preferences")
def set_preferences(payload: Dict[str, Any]):
    try:
        preference_manager.update(payload)
        return ok({"updated": True})

    except Exception as e:
        return error("Failed to update preferences", str(e))
