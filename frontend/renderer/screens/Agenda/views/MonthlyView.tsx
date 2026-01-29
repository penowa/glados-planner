import { AgendaState } from "../types/agenda";

interface MonthlyViewProps {
  state: AgendaState;
}

/**
 * MonthlyView
 * Modo de alocação macro.
 */
export function MonthlyView({ state }: MonthlyViewProps) {
  return (
    <div>
      <h2>Visão Mensal</h2>
      <p>Total de blocos no período: {state.timeline.length}</p>
    </div>
  );
}
