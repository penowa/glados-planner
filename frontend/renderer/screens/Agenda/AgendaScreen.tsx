import { useMemo, useCallback } from "react";

import { AgendaIntent, AgendaIntentPayload } from "@/contracts/agenda";

import { useAgendaNavigation } from "./hooks/useAgendaNavigation";
import { useAgendaSelection } from "./hooks/useAgendaSelection";
import { useAgendaState } from "./hooks/useAgendaState";

import { DailyView } from "./views/DailyView";
import { WeeklyView } from "./views/WeeklyView";
import { MonthlyView } from "./views/MonthlyView";
import { SemesterView } from "./views/SemesterView";

import { LoadIndicator } from "./components/LoadIndicator";

/**
 * AgendaScreen
 * Orquestrador da Agenda.
 */
export function AgendaScreen() {
  const navigation = useAgendaNavigation();
  const selection = useAgendaSelection<string>();

  const agenda = useAgendaState({
    date: navigation.date,
    viewMode: navigation.viewMode,
  });

  /**
   * Callback padrão de seleção de bloco
   * Mantém a responsabilidade fora das Views
   */
  const handleBlockSelect = useCallback(
    (blockId: string) => {
      selection.select(blockId);
    },
    [selection]
  );

  // Enquanto não há estado, exibimos loading forte
  if (agenda.loading && !agenda.state) {
    return <LoadIndicator level="balanced" />;
  }

  // Segurança: views nunca recebem state nulo
  if (!agenda.state) {
    return <LoadIndicator level="low" />;
  }

  const commonViewProps = useMemo(
    () => ({
      date: navigation.date,
      state: agenda.state!,
      selection,
      onBlockSelect: handleBlockSelect,
      onIntent: (intent: AgendaIntent, payload: AgendaIntentPayload) =>
        agenda.sendIntent(intent, payload),
    }),
    [navigation.date, agenda.state, selection, handleBlockSelect, agenda]
  );

  switch (navigation.viewMode) {
    case "daily":
      return <DailyView {...commonViewProps} />;
    case "weekly":
      return <WeeklyView {...commonViewProps} />;
    case "monthly":
      return <MonthlyView {...commonViewProps} />;
    case "semester":
      return <SemesterView {...commonViewProps} />;
    default:
      return null;
  }
}
