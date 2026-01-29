import { useCallback, useEffect, useState } from "react";
import {
  AgendaIntent,
  AgendaIntentPayload,
  AgendaState,
  AgendaViewMode,
} from "@/contracts/agenda";
import { getAgendaState, sendAgendaIntent } from "@/api/agendaApi";

interface UseAgendaStateParams {
  date: Date;
  viewMode: AgendaViewMode;
}

interface UseAgendaStateResult {
  state: AgendaState | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  sendIntent: (
    intent: AgendaIntent,
    payload: AgendaIntentPayload
  ) => Promise<void>;
}

/**
 * useAgendaState
 * Fonte única de verdade da Agenda no frontend.
 * Conecta navegação + intents ao backend via api do renderer.
 */
export function useAgendaState({
  date,
  viewMode,
}: UseAgendaStateParams): UseAgendaStateResult {
  const [state, setState] = useState<AgendaState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchState = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getAgendaState({
        date: date.toISOString(),
        view: viewMode,
      });

      if (response.status !== "ok" || !response.data) {
        throw new Error(response.error?.message ?? "Erro ao carregar agenda");
      }

      setState(response.data);
    } catch (err: any) {
      setError(err?.message ?? "Erro inesperado");
    } finally {
      setLoading(false);
    }
  }, [date, viewMode]);

  const sendIntentHandler = useCallback(
    async (intent: AgendaIntent, payload: AgendaIntentPayload) => {
      try {
        const response = await sendAgendaIntent({ intent, payload });

        if (response.status !== "ok") {
          throw new Error(response.error?.message ?? "Erro ao executar ação");
        }

        await fetchState();
      } catch (err: any) {
        setError(err?.message ?? "Erro ao enviar intenção");
      }
    },
    [fetchState]
  );

  useEffect(() => {
    fetchState();
  }, [fetchState]);

  return {
    state,
    loading,
    error,
    refresh: fetchState,
    sendIntent: sendIntentHandler,
  };
}
