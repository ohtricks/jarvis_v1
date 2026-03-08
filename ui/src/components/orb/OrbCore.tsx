import { VoiceStatus } from '../../hooks/useVoice';
import { OrbRings } from './OrbRings';
import { OrbParticles } from './OrbParticles';
import { OrbPulse } from './OrbPulse';

export interface OrbCoreProps {
  state:       VoiceStatus;
  intensity?:  number;   // 0-1, default 0.5
  audioLevel?: number;   // 0-1, future mic integration
}

interface OrbConfig {
  ringSpeed:   number;
  pulseActive: boolean;
  pulseColor:  string;
  glowColor:   string;
}

const STATE_CONFIG: Record<VoiceStatus, OrbConfig> = {
  disconnected: {
    ringSpeed: 0.22, pulseActive: false, pulseColor: '',
    glowColor: 'rgba(35,55,80,0.18)',
  },
  connecting: {
    ringSpeed: 0.65, pulseActive: false, pulseColor: '',
    glowColor: 'rgba(0,160,210,0.22)',
  },
  idle: {
    ringSpeed: 1.00, pulseActive: false, pulseColor: '',
    glowColor: 'rgba(0,205,248,0.24)',
  },
  listening: {
    ringSpeed: 1.80, pulseActive: false, pulseColor: '',
    glowColor: 'rgba(0,225,255,0.40)',
  },
  processing: {
    ringSpeed: 2.80, pulseActive: false, pulseColor: '',
    glowColor: 'rgba(242,158,22,0.32)',
  },
  speaking: {
    ringSpeed: 2.20, pulseActive: true,
    pulseColor: 'rgba(145,122,255,0.48)',
    glowColor: 'rgba(145,122,255,0.40)',
  },
};

const STATUS_CAPTION: Record<VoiceStatus, string> = {
  disconnected: 'offline',
  connecting:   'conectando',
  idle:         'aguardando',
  listening:    'ouvindo',
  processing:   'processando',
  speaking:     'falando',
};

export function OrbCore({ state, intensity = 0.5, audioLevel = 0 }: OrbCoreProps) {
  const cfg       = STATE_CONFIG[state];
  const speedMult = 1 + (intensity - 0.5) * 0.4;

  return (
    <div
      className="orb-scene2"
      data-state={state}
      style={{
        '--orb-intensity':   intensity,
        '--orb-audio-level': audioLevel,
      } as React.CSSProperties}
    >
      {/* Layer 1 — Halo externo difuso */}
      <div
        className="orb2-halo"
        style={{ background: `radial-gradient(circle at center, ${cfg.glowColor} 0%, transparent 68%)` }}
      />

      {/* Layer 2 — Ondas radiais de emissão (só speaking) */}
      <div className="orb2-pulse-anchor">
        <OrbPulse active={cfg.pulseActive} color={cfg.pulseColor} />
      </div>

      {/* Layer 3 — Nuvem de partículas (a orbe em si) */}
      <OrbParticles state={state} audioLevel={audioLevel} />

      {/* Layer 4 — Anéis orbitais SVG */}
      <div className="orb2-rings-wrap">
        <OrbRings state={state} ringSpeed={cfg.ringSpeed * speedMult} />
      </div>

      {/* Layer 6 — Caption */}
      <span className="orb2-caption">{STATUS_CAPTION[state]}</span>
    </div>
  );
}
