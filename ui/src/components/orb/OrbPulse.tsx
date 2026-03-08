interface OrbPulseProps {
  active: boolean;
  color: string; // CSS color string
}

export function OrbPulse({ active, color }: OrbPulseProps) {
  if (!active) return null;

  return (
    <div className="orb-pulse-layer" aria-hidden>
      {[0, 1, 2].map(i => (
        <div
          key={i}
          className="orb-pulse-ring"
          style={{
            '--pulse-color': color,
            '--pulse-delay': `${i * 0.52}s`,
          } as React.CSSProperties}
        />
      ))}
    </div>
  );
}
