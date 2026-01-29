import { AgendaState } from "../types/agenda";

interface SemesterViewProps {
  state: AgendaState;
}

/**
 * SemesterView
 * Modo estratégico.
 * Foco em tendências e intenção de longo prazo.
 */
export function SemesterView({ state }: SemesterViewProps) {
  return (
    <div>
      <h2>Visão Semestral</h2>
      <p>Eventos mapeados: {state.timeline.length}</p>
    </div>
  );
}
