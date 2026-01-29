import { useCallback, useState } from "react";
import { AgendaViewMode } from "@/contracts/agenda";

interface UseAgendaNavigationResult {
  date: Date;
  viewMode: AgendaViewMode;
  setDate: (date: Date) => void;
  next: () => void;
  previous: () => void;
  setViewMode: (mode: AgendaViewMode) => void;
}

/**
 * useAgendaNavigation
 * Responsável exclusivamente por navegação temporal e modo de visualização.
 */
export function useAgendaNavigation(
  initialDate: Date = new Date(),
  initialView: AgendaViewMode = "daily"
): UseAgendaNavigationResult {
  const [date, setDate] = useState<Date>(initialDate);
  const [viewMode, setViewMode] = useState<AgendaViewMode>(initialView);

  const next = useCallback(() => {
    const d = new Date(date);

    switch (viewMode) {
      case "daily":
        d.setDate(d.getDate() + 1);
        break;
      case "weekly":
        d.setDate(d.getDate() + 7);
        break;
      case "monthly":
        d.setMonth(d.getMonth() + 1);
        break;
      case "semester":
        d.setMonth(d.getMonth() + 6);
        break;
    }

    setDate(d);
  }, [date, viewMode]);

  const previous = useCallback(() => {
    const d = new Date(date);

    switch (viewMode) {
      case "daily":
        d.setDate(d.getDate() - 1);
        break;
      case "weekly":
        d.setDate(d.getDate() - 7);
        break;
      case "monthly":
        d.setMonth(d.getMonth() - 1);
        break;
      case "semester":
        d.setMonth(d.getMonth() - 6);
        break;
    }

    setDate(d);
  }, [date, viewMode]);

  return {
    date,
    viewMode,
    setDate,
    next,
    previous,
    setViewMode,
  };
}
