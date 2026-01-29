interface LoadIndicatorProps {
  level: "low" | "balanced" | "overload";
}

/**
 * LoadIndicator
 * Indica visualmente o nível de carga do dia.
 */
export function LoadIndicator({ level }: LoadIndicatorProps) {
  return (
    <div className={`load-indicator level-${level}`}>
      {level}
    </div>
  );
}
