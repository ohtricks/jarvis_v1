import { useEffect, useRef } from 'react';
import { VoiceStatus } from '../../hooks/useVoice';

// ── Canvas dimensions ─────────────────────────────────────────────────────────
const SIZE  = 320; // canvas px — fills the orb-scene2
const CX    = SIZE / 2;
const CY    = SIZE / 2;
const R_ORB = 96;  // cloud radius

// ── Box-Muller Gaussian (mean=0, σ=1) ────────────────────────────────────────
function gauss(): number {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

// ── Particle definition ───────────────────────────────────────────────────────
interface Particle {
  // Current position
  x: number;
  y: number;
  // Orbit anchor (slowly drifts too)
  anchorX: number;
  anchorY: number;
  // Orbit params
  orbitR: number;
  orbitAngle: number;
  orbitSpeed: number;
  // Anchor drift
  driftAngle: number;
  driftSpeed: number;
  driftR: number;
  // Visual
  glowR: number;
  baseAlpha: number;
  phase: number;
  phaseSpeed: number;
  // Layer: 0=core  1=mid  2=haze
  layer: 0 | 1 | 2;
}

// ── State configs ─────────────────────────────────────────────────────────────
const STATE_COLOR: Record<VoiceStatus, [number, number, number]> = {
  disconnected: [50,  70,  95],
  connecting:   [0,  160, 205],
  idle:         [0,  205, 248],
  listening:    [0,  225, 255],
  processing:   [242, 158,  22],
  speaking:     [145, 122, 255],
};

// Secondary color blended into core (inner warmth)
const CORE_COLOR: Record<VoiceStatus, [number, number, number]> = {
  disconnected: [60,  80, 110],
  connecting:   [20, 180, 220],
  idle:         [120, 235, 255],
  listening:    [150, 245, 255],
  processing:   [255, 200,  80],
  speaking:     [190, 170, 255],
};

// [core count, mid count, haze count]
const STATE_COUNTS: Record<VoiceStatus, [number, number, number]> = {
  disconnected: [ 6,  18,  6],
  connecting:   [10,  30,  8],
  idle:         [18,  55, 14],
  listening:    [24,  70, 16],
  processing:   [30,  88, 20],
  speaking:     [36, 100, 22],
};

const STATE_SPEED: Record<VoiceStatus, number> = {
  disconnected: 0.12,
  connecting:   0.30,
  idle:         0.48,
  listening:    0.80,
  processing:   1.35,
  speaking:     1.75,
};

// ── Factory ───────────────────────────────────────────────────────────────────
function makeParticle(layer: 0 | 1 | 2): Particle {
  const spreadFrac = [0.28, 0.68, 0.95][layer];
  const maxR       = R_ORB * spreadFrac;

  // Gaussian distribution — naturally dense in centre, sparse at edges
  const angle  = Math.random() * Math.PI * 2;
  const rawR   = Math.abs(gauss()) * maxR * 0.7;
  const r      = Math.min(rawR, maxR);
  const anchorX = CX + Math.cos(angle) * r;
  const anchorY = CY + Math.sin(angle) * r;

  const orbitR = ([
    2  + Math.random() * 10,
    6  + Math.random() * 22,
    12 + Math.random() * 32,
  ])[layer];

  const glowR = ([
    5  + Math.random() * 9,
    16 + Math.random() * 22,
    32 + Math.random() * 36,
  ])[layer];

  const baseAlpha = ([
    0.55 + Math.random() * 0.45,
    0.14 + Math.random() * 0.22,
    0.04 + Math.random() * 0.07,
  ])[layer];

  const orbitSpeed = ([
    0.015 + Math.random() * 0.025,
    0.004 + Math.random() * 0.012,
    0.001 + Math.random() * 0.004,
  ])[layer] * (Math.random() > 0.5 ? 1 : -1);

  return {
    x: anchorX,
    y: anchorY,
    anchorX,
    anchorY,
    orbitR,
    orbitAngle: Math.random() * Math.PI * 2,
    orbitSpeed,
    driftAngle: Math.random() * Math.PI * 2,
    driftSpeed: (0.0008 + Math.random() * 0.0015) * (Math.random() > 0.5 ? 1 : -1),
    driftR: r * 0.22,
    glowR,
    baseAlpha,
    phase:      Math.random() * Math.PI * 2,
    phaseSpeed: 0.006 + Math.random() * 0.018,
    layer,
  };
}

// ── Component ─────────────────────────────────────────────────────────────────
interface Props {
  state:      VoiceStatus;
  audioLevel?: number;
}

export function OrbParticles({ state, audioLevel = 0 }: Props) {
  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const rafRef     = useRef<number>(0);
  const stateRef   = useRef({ state, audioLevel });
  const particles  = useRef<Particle[]>([]);
  const timeRef    = useRef(0);

  useEffect(() => { stateRef.current = { state, audioLevel }; }, [state, audioLevel]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.width  = SIZE;
    canvas.height = SIZE;

    // Pre-create maximum pool
    const maxCounts = STATE_COUNTS.speaking;
    particles.current = [
      ...Array.from({ length: maxCounts[0] }, () => makeParticle(0)),
      ...Array.from({ length: maxCounts[1] }, () => makeParticle(1)),
      ...Array.from({ length: maxCounts[2] }, () => makeParticle(2)),
    ];

    const ctx = canvas.getContext('2d')!;

    function loop() {
      const { state: st, audioLevel: al } = stateRef.current;
      const [rc, mc, hc] = STATE_COUNTS[st];
      const target       = rc + mc + hc;
      const speed        = STATE_SPEED[st] * (1 + al * 1.3);
      const [r, g, b]    = STATE_COLOR[st];
      const [cr, cg, cb] = CORE_COLOR[st];

      timeRef.current += 0.016;
      const t = timeRef.current;

      // Speaking breath — cloud inhales and exhales
      const breathPhase = st === 'speaking'
        ? 1 + 0.10 * Math.sin(t * 3.5) + 0.06 * Math.sin(t * 7.2) + al * 0.14
        : 1 + 0.018 * Math.sin(t * 0.9); // very subtle idle breath

      ctx.clearRect(0, 0, SIZE, SIZE);

      // Additive blending → overlapping glows accumulate into bright zones
      ctx.globalCompositeOperation = 'lighter';

      const ps    = particles.current;
      const total = Math.min(target, ps.length);

      for (let i = 0; i < total; i++) {
        const p = ps[i];

        // Advance orbit
        p.orbitAngle += p.orbitSpeed * speed;

        // Anchor drifts slowly
        p.driftAngle += p.driftSpeed * speed;
        const baseAX = CX + Math.cos(p.driftAngle) * p.driftR; // where anchor wants to be (relative offset)
        // We keep drift relative to initial anchor to avoid runaway
        const targetAX = p.anchorX + (baseAX - CX) * 0.3;
        const targetAY = p.anchorY + (Math.sin(p.driftAngle) * p.driftR) * 0.3;
        p.x += ((targetAX + Math.cos(p.orbitAngle) * p.orbitR) - p.x) * 0.05;
        p.y += ((targetAY + Math.sin(p.orbitAngle) * p.orbitR) - p.y) * 0.05;

        // Clamp to orb boundary (softly)
        const dx = p.x - CX, dy = p.y - CY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const maxDist = R_ORB * ([0.32, 0.76, 1.02][p.layer]);
        if (dist > maxDist) {
          p.x = CX + (dx / dist) * maxDist * 0.96;
          p.y = CY + (dy / dist) * maxDist * 0.96;
        }

        // Apply breath scale from centre
        const px = CX + (p.x - CX) * breathPhase;
        const py = CY + (p.y - CY) * breathPhase;

        // Alpha pulse
        p.phase += p.phaseSpeed * speed;
        const pulse = 0.55 + 0.45 * Math.sin(p.phase);
        const alpha = p.baseAlpha * pulse;

        // Glow radius also breathes slightly in speaking
        const gr = p.glowR * (p.layer === 0 ? 1 : breathPhase * 0.92 + 0.08);

        // Choose color: core particles blend towards secondary color
        const blend = p.layer === 0 ? 0.55 : 0;
        const fr = r + (cr - r) * blend;
        const fg = g + (cg - g) * blend;
        const fb = b + (cb - b) * blend;

        // Radial gradient glow
        const grad = ctx.createRadialGradient(px, py, 0, px, py, gr);
        grad.addColorStop(0.00, `rgba(${fr|0},${fg|0},${fb|0},${alpha})`);
        grad.addColorStop(0.28, `rgba(${fr|0},${fg|0},${fb|0},${alpha * 0.5})`);
        grad.addColorStop(0.60, `rgba(${r},${g},${b},${alpha * 0.18})`);
        grad.addColorStop(1.00, `rgba(${r},${g},${b},0)`);

        ctx.beginPath();
        ctx.arc(px, py, gr, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();
      }

      ctx.globalCompositeOperation = 'source-over';
      rafRef.current = requestAnimationFrame(loop);
    }

    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, []); // only on mount — state is read via ref

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top:    '50%',
        left:   '50%',
        transform: 'translate(-50%, -50%)',
        width:  SIZE,
        height: SIZE,
        pointerEvents: 'none',
        zIndex: 2,
      }}
    />
  );
}
