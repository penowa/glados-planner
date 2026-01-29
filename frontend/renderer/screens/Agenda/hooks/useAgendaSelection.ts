import { useCallback, useState } from "react";

interface UseAgendaSelectionResult<T = string> {
  selectedId: T | null;
  select: (id: T) => void;
  clear: () => void;
  isSelected: (id: T) => boolean;
}

/**
 * useAgendaSelection
 * Gerencia seleção lógica (ex: bloco ativo, tarefa focada).
 */
export function useAgendaSelection<T = string>(): UseAgendaSelectionResult<T> {
  const [selectedId, setSelectedId] = useState<T | null>(null);

  const select = useCallback((id: T) => {
    setSelectedId(id);
  }, []);

  const clear = useCallback(() => {
    setSelectedId(null);
  }, []);

  const isSelected = useCallback(
    (id: T) => selectedId === id,
    [selectedId]
  );

  return {
    selectedId,
    select,
    clear,
    isSelected,
  };
}
