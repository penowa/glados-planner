import { AgendaBlock } from "../types/agenda";

interface TimeBlockProps {
  block: AgendaBlock;
  onSelect?: (blockId: string) => void;
}

/**
 * TimeBlock
 * Representa visualmente um bloco da agenda.
 */
export function TimeBlock({ block, onSelect }: TimeBlockProps) {
  return (
    <div
      className={`time-block type-${block.type} status-${block.status}`}
      onClick={() => onSelect?.(block.id)}
    >
      <strong>{block.title}</strong>
      <span>
        {new Date(block.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        {" - "}
        {new Date(block.end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </span>
    </div>
  );
}
