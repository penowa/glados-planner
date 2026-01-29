/**
 * TimeGrid
 * Renderiza a grade horária de fundo.
 * Componente puramente visual.
 */
export function TimeGrid() {
  const hours = Array.from({ length: 24 }, (_, i) => i);

  return (
    <div className="time-grid">
      {hours.map(hour => (
        <div key={hour} className="time-grid-hour">
          {hour}:00
        </div>
      ))}
    </div>
  );
}
