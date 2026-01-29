/**
 * Utils de energia para a Agenda
 * 
 * Regras puramente visuais e auxiliares.
 * NÃO representam lógica cognitiva do backend.
 */

/** Normaliza um valor de energia para o intervalo 0–1 */
export function normalizeEnergy(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

/** Converte energia (0–1) em opacidade visual */
export function energyToOpacity(energy: number): number {
  const e = normalizeEnergy(energy);
  return 0.2 + e * 0.8; // mínimo visível
}

/** Mapeia energia (0–1) para classe semântica */
export function energyToLevel(energy: number): "low" | "medium" | "high" {
  if (energy < 0.33) return "low";
  if (energy < 0.66) return "medium";
  return "high";
}
