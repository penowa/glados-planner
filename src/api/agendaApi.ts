/**
 * Agenda API Adapter
 * 
 * Camada fina entre o frontend (Electron) e o ui_bridge (backend).
 * 
 * A UI NUNCA chama fetch diretamente fora daqui.
 */

import { AgendaState, AgendaIntent, AgendaIntentPayload, AgendaViewMode } from "../contracts/agenda";

const BASE_URL = "http://localhost:8000/ui"; // ui_bridge

interface ApiResponse<T> {
  status: "ok" | "error";
  data?: T;
  error?: {
    message: string;
    details?: any;
  };
}

export async function getAgendaState(params: {
  date: string;
  view: AgendaViewMode;
}): Promise<ApiResponse<AgendaState>> {
  const url = new URL(`${BASE_URL}/agenda/day`);
  url.searchParams.set("date", params.date);

  const res = await fetch(url.toString());
  return res.json();
}

export async function sendAgendaIntent(params: {
  intent: AgendaIntent;
  payload: AgendaIntentPayload;
}): Promise<ApiResponse<any>> {
  const res = await fetch(`${BASE_URL}/agenda/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  return res.json();
}
