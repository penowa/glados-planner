/**
 * Contrato oficial da Agenda no frontend.
 * 
 * Este arquivo é o ESPELHO direto dos contratos expostos pelo ui_bridge.
 * Nenhum tipo aqui deve existir apenas por conveniência visual.
 */

/* =========================
 * Modos de visualização
 * ========================= */

export type AgendaViewMode = "daily" | "weekly" | "monthly" | "semester";

/* =========================
 * Estado global da Agenda
 * ========================= */

export interface AgendaState {
  date: string; // ISO-8601 (dia de referência)
  view: AgendaViewMode;

  summary: AgendaSummary;
  timeline: AgendaBlock[];
}

/* =========================
 * Resumo cognitivo do dia/semana
 * ========================= */

export interface AgendaSummary {
  focusScore: number; // 0–100
  loadLevel: "low" | "balanced" | "overload";
  energyForecast?: EnergyForecast;
}

export interface EnergyForecast {
  morning: number;   // 0–1
  afternoon: number; // 0–1
  evening: number;   // 0–1
}

/* =========================
 * Blocos da linha do tempo
 * ========================= */

export interface AgendaBlock {
  id: string;

  type: AgendaBlockType;
  status: AgendaBlockStatus;

  title: string;
  description?: string;

  start: string; // ISO-8601 datetime
  end: string;   // ISO-8601 datetime

  energyCost: number; // 0–1
  priority?: number; // 1–5

  metadata?: Record<string, any>;
}

export type AgendaBlockType =
  | "fixed"      // compromissos rígidos
  | "flexible"   // tarefas ajustáveis
  | "suggested"; // sugestões do sistema

export type AgendaBlockStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "skipped";

/* =========================
 * Intenções da UI
 * ========================= */

export type AgendaIntent =
  | "MOVE_BLOCK"
  | "RESIZE_BLOCK"
  | "COMPLETE_BLOCK"
  | "SKIP_BLOCK"
  | "ACCEPT_SUGGESTION"
  | "REQUEST_REALLOCATION";

export type AgendaIntentPayload =
  | MoveBlockPayload
  | ResizeBlockPayload
  | CompleteBlockPayload
  | SkipBlockPayload
  | AcceptSuggestionPayload
  | RequestReallocationPayload;

/* =========================
 * Payloads das intenções
 * ========================= */

export interface MoveBlockPayload {
  blockId: string;
  newStart: string; // ISO-8601 datetime
}

export interface ResizeBlockPayload {
  blockId: string;
  newEnd: string; // ISO-8601 datetime
}

export interface CompleteBlockPayload {
  blockId: string;
}

export interface SkipBlockPayload {
  blockId: string;
}

export interface AcceptSuggestionPayload {
  blockId: string;
}

export interface RequestReallocationPayload {
  scope: "day" | "week";
}
