import type { SkillBubble } from '../../hooks/useSkillBubbles';

interface Props {
  bubbles: SkillBubble[];
  onRemove: (id: string) => void;
}

export function SkillBubbleLayer({ bubbles, onRemove }: Props) {
  return (
    <div className="skill-bubble-layer" aria-hidden="true">
      {bubbles.map(b => (
        <div
          key={b.id}
          className="skill-bubble"
          style={{
            left:             `calc(50% + ${b.offsetX}px)`,
            top:              `calc(42% + ${b.spawnY}px)`,
            '--sb-duration':  `${b.duration}ms`,
            '--sb-drift':     `${b.driftX}px`,
          } as React.CSSProperties}
          onAnimationEnd={() => onRemove(b.id)}
        >
          <span className="skill-bubble-dot" />
          <span className="skill-bubble-label">{b.label}</span>
        </div>
      ))}
    </div>
  );
}
