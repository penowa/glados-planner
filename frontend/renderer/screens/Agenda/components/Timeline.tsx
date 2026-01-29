import { AgendaBlock } from "../types/agenda";
import { TimeGrid } from "./TimeGrid";
import { TimeBlock } from "./TimeBlock";
import { NowIndicator } from "./NowIndicator";
import { EnergyOverlay } from "./EnergyOverlay";

interface TimelineProps {
  blocks: AgendaBlock[];
  onBlockSelect?: (blockId: string) => void;
}

/**
 * Timeline
 * Container principal da linha do tempo diária.
 * Não possui lógica de negócio.
 */
export function Timeline({ blocks, onBlockSelect }: TimelineProps) {
  return (
    <div className="timeline">
      <EnergyOverlay />
      <TimeGrid />
      <NowIndicator />

      {blocks.map(block => (
        <TimeBlock
          key={block.id}
          block={block}
          onSelect={onBlockSelect}
        />
      ))}
    </div>
  );
}
