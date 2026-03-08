import { VoiceStatus, AgentState } from '../../hooks/useVoice';
import { OrbRings } from './OrbRings';
import { OrbParticles } from './OrbParticles';
import { OrbPulse } from './OrbPulse';

export interface OrbCoreProps {
  state:       VoiceStatus;
  agentState?: AgentState;
  intensity?:  number;   // 0-1, default 0.5
  audioLevel?: number;   // 0-1, future mic integration
}

interface OrbConfig {
  ringSpeed:   number;
  pulseActive: boolean;
  pulseColor:  string;
  glowColor:   string;
}

// Config base por VoiceStatus
const VOICE_CONFIG: Record<VoiceStatus, OrbConfig> = {
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

// Overrides de config por AgentState — aplicados quando status = processing
const AGENT_CONFIG_OVERRIDE: Partial<Record<AgentState, Partial<OrbConfig>>> = {
  thinking: {
    ringSpeed: 2.20,
    glowColor: 'rgba(242,158,22,0.28)',
  },
  planning: {
    ringSpeed: 3.20,
    glowColor: 'rgba(242,200,22,0.35)',
  },
  compiling: {
    ringSpeed: 2.80,
    glowColor: 'rgba(200,140,40,0.32)',
  },
  executing: {
    ringSpeed: 3.80,
    pulseActive: true,
    pulseColor: 'rgba(0,212,255,0.30)',
    glowColor: 'rgba(0,180,255,0.38)',
  },
  responding: {
    ringSpeed: 2.40,
    pulseActive: true,
    pulseColor: 'rgba(145,122,255,0.35)',
    glowColor: 'rgba(145,122,255,0.35)',
  },
  blocked: {
    ringSpeed: 1.20,
    pulseActive: true,
    pulseColor: 'rgba(255,95,126,0.30)',
    glowColor: 'rgba(255,95,126,0.28)',
  },
};

// Caption: agentState tem precedência quando voice está processing
const AGENT_CAPTION: Partial<Record<AgentState, string>> = {
  thinking:   'analisando',
  planning:   'planejando',
  compiling:  'compilando',
  executing:  'executando',
  responding: 'respondendo',
  blocked:    'aguardando',
};

const VOICE_CAPTION: Record<VoiceStatus, string> = {
  disconnected: 'offline',
  connecting:   'conectando',
  idle:         'aguardando',
  listening:    'ouvindo',
  processing:   'processando',
  speaking:     'falando',
};

export function OrbCore({ state, agentState = 'idle', intensity = 0.5, audioLevel = 0 }: OrbCoreProps) {
  // Computa config efetiva: base de voice + override de agentState (quando ativo)
  const baseConfig = VOICE_CONFIG[state];
  const agentOverride = (agentState !== 'idle' && state === 'processing')
    ? (AGENT_CONFIG_OVERRIDE[agentState] ?? {})
    : {};

  const cfg: OrbConfig = { ...baseConfig, ...agentOverride };
  const speedMult = 1 + (intensity - 0.5) * 0.4;

  // Caption: mostra estado do agente quando relevante
  const caption = (agentState !== 'idle' && state === 'processing')
    ? (AGENT_CAPTION[agentState] ?? VOICE_CAPTION[state])
    : VOICE_CAPTION[state];

  // data-state reflete o estado mais específico para CSS
  const dataState = (agentState !== 'idle' && state === 'processing')
    ? agentState
    : state;

  return (
    <div
      className="orb-scene2"
      data-state={dataState}
      style={{
        '--orb-intensity':   intensity,
        '--orb-audio-level': audioLevel,
      } as React.CSSProperties}
    >
      {/* Layer 1 — Nuvem de partículas */}
      <OrbParticles state={state} audioLevel={audioLevel} />

      {/* Layer 2 — Ondas radiais de emissão */}
      <div className="orb2-pulse-anchor">
        <OrbPulse active={cfg.pulseActive} color={cfg.pulseColor} />
      </div>

      {/* Layer 3 — Anéis orbitais SVG */}
      <div className="orb2-rings-wrap">
        <OrbRings state={state} ringSpeed={cfg.ringSpeed * speedMult} />
      </div>

      {/* Layer 4 — Caption */}
      <span className="orb2-caption">{caption}</span>
    </div>
  );
}
