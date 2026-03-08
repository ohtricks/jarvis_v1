import { useMemo } from 'react';
import { VoiceStatus } from '../../hooks/useVoice';

interface OrbRingsProps {
  state: VoiceStatus;
  ringSpeed: number;
}

interface RingDef {
  rx: number;
  ry: number;
  baseDur: number;
  reverse: boolean;
  dashArray: string;
  dashOffset: number;
  opacity: number;
  rotate: number; // initial static rotation (deg) for variety
}

const RINGS: RingDef[] = [
  { rx: 47, ry: 47, baseDur: 24, reverse: false, dashArray: '60 240', dashOffset: 0,   opacity: 0.22, rotate: 0   },
  { rx: 47, ry: 15, baseDur: 16, reverse: true,  dashArray: '40 260', dashOffset: 90,  opacity: 0.30, rotate: 15  },
  { rx: 47, ry: 33, baseDur: 30, reverse: false, dashArray: '80 220', dashOffset: 180, opacity: 0.18, rotate: -20 },
  { rx: 45, ry: 7,  baseDur: 12, reverse: true,  dashArray: '30 270', dashOffset: 45,  opacity: 0.25, rotate: 8   },
  { rx: 47, ry: 42, baseDur: 38, reverse: false, dashArray: '100 200', dashOffset: 130, opacity: 0.14, rotate: 35 },
];

const STATE_OPACITY: Record<VoiceStatus, number> = {
  disconnected: 0.25,
  connecting:   0.45,
  idle:         0.65,
  listening:    0.85,
  processing:   1.0,
  speaking:     0.95,
};

const STATE_COLOR: Record<VoiceStatus, [string, string]> = {
  disconnected: ['rgba(60,80,100,',    'rgba(40,60,80,'],
  connecting:   ['rgba(0,212,255,',    'rgba(0,150,200,'],
  idle:         ['rgba(0,212,255,',    'rgba(0,180,220,'],
  listening:    ['rgba(0,230,255,',    'rgba(0,200,240,'],
  processing:   ['rgba(240,160,32,',   'rgba(200,120,20,'],
  speaking:     ['rgba(149,128,255,',  'rgba(110,90,220,'],
};

export function OrbRings({ state, ringSpeed }: OrbRingsProps) {
  const stateOpacity = STATE_OPACITY[state];
  const [colorA, colorB] = STATE_COLOR[state];

  const rings = useMemo(() => RINGS.map((r, i) => {
    const dur = r.baseDur / ringSpeed;
    const animName = r.reverse ? 'orb-ring-spin-rev' : 'orb-ring-spin';
    // Alternate colors between rings
    const strokeColor = i % 2 === 0 ? colorA : colorB;
    const opacity = r.opacity * stateOpacity;
    return { ...r, dur, animName, strokeColor, opacity };
  }), [ringSpeed, colorA, colorB, stateOpacity]);

  return (
    <svg
      className="orb-rings-svg"
      viewBox="0 0 200 200"
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible', pointerEvents: 'none' }}
    >
      {rings.map((r, i) => {
        const circumference = Math.PI * (r.rx + r.ry); // approx ellipse perimeter
        return (
          <ellipse
            key={i}
            cx="100"
            cy="100"
            rx={r.rx}
            ry={r.ry}
            fill="none"
            stroke={`${r.strokeColor}${r.opacity})`}
            strokeWidth="0.8"
            strokeDasharray={r.dashArray}
            strokeDashoffset={r.dashOffset}
            strokeLinecap="round"
            transform={`rotate(${r.rotate} 100 100)`}
            style={{
              transformOrigin: '100px 100px',
              animation: `${r.animName} ${r.dur.toFixed(2)}s linear infinite`,
              transition: 'stroke 0.8s ease, opacity 0.6s ease',
            }}
          />
        );
      })}
    </svg>
  );
}
