import { useState, useEffect } from 'react';
import type { SkillBubble } from '../../hooks/useSkillBubbles';

// ── Componente individual da bubble ─────────────────────────────────────────

interface BubbleItemProps {
  bubble: SkillBubble;
  onRemove: (id: string) => void;
}

function BubbleItem({ bubble, onRemove }: BubbleItemProps) {
  // Phase controla qual animação CSS está ativa:
  //   hover  → pulsa no lugar (running)
  //   exit   → sobe e some (completed/failed)
  const [phase, setPhase] = useState<'hover' | 'exit'>(
    bubble.status !== 'running' ? 'exit' : 'hover'
  );

  // Quando status mudar de running → completed/failed, inicia saída
  useEffect(() => {
    if (bubble.status !== 'running') {
      setPhase('exit');
    }
  }, [bubble.status]);

  const handleAnimationEnd = () => {
    // Só remove quando a animação de SAÍDA terminar (não a hover infinita)
    if (phase === 'exit') {
      onRemove(bubble.id);
    }
  };

  return (
    <div
      className={`skill-bubble sb-phase-${phase} sb-status-${bubble.status}`}
      style={{
        left:            `calc(50% + ${bubble.offsetX}px)`,
        top:             `calc(42% + ${bubble.spawnY}px)`,
        '--sb-duration': `${bubble.duration}ms`,
        '--sb-drift':    `${bubble.driftX}px`,
      } as React.CSSProperties}
      onAnimationEnd={handleAnimationEnd}
    >
      <span className="skill-bubble-dot" />
      <span className="skill-bubble-label">{bubble.label}</span>
      {bubble.status === 'completed' && (
        <span className="skill-bubble-check">✓</span>
      )}
      {bubble.status === 'failed' && (
        <span className="skill-bubble-fail">✕</span>
      )}
    </div>
  );
}

// ── Layer ────────────────────────────────────────────────────────────────────

interface Props {
  bubbles: SkillBubble[];
  onRemove: (id: string) => void;
}

export function SkillBubbleLayer({ bubbles, onRemove }: Props) {
  return (
    <div className="skill-bubble-layer" aria-hidden="true">
      {bubbles.map(b => (
        <BubbleItem key={b.id} bubble={b} onRemove={onRemove} />
      ))}
    </div>
  );
}
