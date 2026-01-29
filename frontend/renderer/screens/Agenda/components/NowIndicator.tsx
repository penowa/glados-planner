/**
 * NowIndicator
 * Marca visualmente o horário atual na timeline.
 */
export function NowIndicator() {
  const now = new Date();
  const top = (now.getHours() * 60 + now.getMinutes()) / (24 * 60) * 100;

  return (
    <div
      className="now-indicator"
      style={{ top: `${top}%` }}
    />
  );
}
