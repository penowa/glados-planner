/**
 * Utils de tempo para a Agenda
 * 
 * Funções puras, sem dependência de estado ou backend.
 */

/** Converte um horário (Date ou ISO) para minutos desde 00:00 */
export function timeToMinutes(time: Date | string): number {
  const d = typeof time === "string" ? new Date(time) : time;
  return d.getHours() * 60 + d.getMinutes();
}

/** Converte minutos desde 00:00 para percentual vertical (0–100) */
export function minutesToPercentage(minutes: number): number {
  return (minutes / (24 * 60)) * 100;
}

/** Retorna a duração em minutos entre dois horários */
export function durationInMinutes(start: Date | string, end: Date | string): number {
  return timeToMinutes(end) - timeToMinutes(start);
}

/** Normaliza um Date para o início do dia (00:00) */
export function startOfDay(date: Date): Date {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Normaliza um Date para o fim do dia (23:59:59) */
export function endOfDay(date: Date): Date {
  const d = new Date(date);
  d.setHours(23, 59, 59, 999);
  return d;
}
