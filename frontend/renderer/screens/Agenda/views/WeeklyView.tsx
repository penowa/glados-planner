import { AgendaState } from "../types/agenda";

interface WeeklyViewProps {
  state: AgendaState;
}

/**
 * WeeklyView
 * Modo de planejamento.
 * Visão agregada da semana.
 */
export function WeeklyView({ state }: WeeklyViewProps) {
  return (
    <div>
      <h2>Visão Semanal</h2>
      <p>Blocos na semana: {state.timeline.length}</p>
    </div>
  );
}
