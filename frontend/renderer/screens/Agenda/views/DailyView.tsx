import { AgendaBlock, AgendaState } from "../types/agenda";
import { Timeline } from "../components/Timeline";

interface DailyViewProps {
  state: AgendaState;
  onBlockSelect: (blockId: string) => void;
}

/**
 * DailyView
 * Modo de execução.
 * Mostra a linha do tempo detalhada do dia.
 */
export function DailyView({ state, onBlockSelect }: DailyViewProps) {
  return (
    <Timeline
      blocks={state.timeline}
      onBlockSelect={onBlockSelect}
    />
  );
}
