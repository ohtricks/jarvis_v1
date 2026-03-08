import { useEffect, useRef } from 'react';
import { VoiceStatus } from '../../hooks/useVoice';

// ── Canvas ─────────────────────────────────────────────────────────────────────
const SIZE = 380;
const CX   = SIZE / 2;
const CY   = SIZE / 2;

// ── Box-Muller Gaussian ────────────────────────────────────────────────────────
function gauss(): number {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

// ── Particle ───────────────────────────────────────────────────────────────────
interface Particle {
  // Position
  x: number; y: number;
  // Base anchor (gaussian distributed from centre)
  ax: number; ay: number;
  // Slow anchor drift
  driftAngle: number; driftSpeed: number; driftR: number;
  // Fast local orbit (tiny ellipse per particle)
  orbitAngle: number; orbitSpeed: number;
  orbitRx: number;    orbitRy: number;  // slightly elliptical for organic feel
  // Visual
  radius: number;      // hard dot radius (1–3.5px)
  glowR: number;       // soft glow radius (separate pass)
  baseAlpha: number;
  phase: number; phaseSpeed: number;
  // Which ring: 0=inner  1=mid  2=outer  3=sparks (escapees)
  ring: 0 | 1 | 2 | 3;
  // Velocity for physics-based movement (thinking/speaking)
  vx: number; vy: number;
}

// ── State palette ──────────────────────────────────────────────────────────────
// [primary R,G,B], [hot-core R,G,B], [edge R,G,B]
type RGB = [number, number, number];
const PALETTE: Record<VoiceStatus, { main: RGB; hot: RGB; edge: RGB }> = {
  disconnected: { main: [40,  55,  80], hot: [55,  75, 100], edge: [30, 45, 70] },
  connecting:   { main: [0,  160, 210], hot: [40, 200, 240], edge: [0, 120, 180] },
  idle:         { main: [0,  210, 252], hot: [160, 245, 255], edge: [0, 160, 220] },
  listening:    { main: [0,  230, 255], hot: [180, 250, 255], edge: [0, 180, 240] },
  processing:   { main: [242, 160,  20], hot: [255, 215, 100], edge: [200, 100, 10] },
  speaking:     { main: [145, 122, 255], hot: [210, 195, 255], edge: [100,  80, 230] },
};

// ── Population per ring (max pool = speaking) ─────────────────────────────────
// [inner, mid, outer, sparks]
const STATE_POP: Record<VoiceStatus, [number, number, number, number]> = {
  disconnected: [ 8,  16,   0,  0],
  connecting:   [12,  32,   8,  2],
  idle:         [22,  60,  18,  4],
  listening:    [30,  80,  28,  8],
  processing:   [40, 100,  40, 14],
  speaking:     [50, 120,  55, 20],
};

const MAX_POP: [number, number, number, number] = [50, 120, 55, 20];

// ── Base cloud radius per ring ─────────────────────────────────────────────────
const RING_R = [26, 62, 100, 130] as const; // px from centre

// ── Speed multiplier ───────────────────────────────────────────────────────────
const STATE_SPEED: Record<VoiceStatus, number> = {
  disconnected: 0.10,
  connecting:   0.35,
  idle:         0.50,
  listening:    0.85,
  processing:   1.40,
  speaking:     1.80,
};

// ── Factory ───────────────────────────────────────────────────────────────────
function makeParticle(ring: 0 | 1 | 2 | 3): Particle {
  const cloudR = RING_R[ring];

  // Gaussian spread — inner rings much tighter
  const sigma  = cloudR * ([0.38, 0.46, 0.52, 0.70][ring]);
  const angle  = Math.random() * Math.PI * 2;
  const rawR   = Math.abs(gauss()) * sigma;
  const r      = Math.min(rawR, cloudR);
  const ax     = CX + Math.cos(angle) * r;
  const ay     = CY + Math.sin(angle) * r;

  // Dot radius: inner = bright small dots; outer = larger softer sparks
  const radius = ring === 0
    ? 0.8 + Math.random() * 1.6
    : ring === 1
      ? 0.6 + Math.random() * 1.2
      : ring === 2
        ? 0.4 + Math.random() * 1.0
        : 0.5 + Math.random() * 2.0; // sparks can be bigger briefly

  // Soft glow: small — this is what changes everything vs the old code
  // We want INDIVIDUAL visible glows, not one merged blob.
  // Keep glow radius tight so particles stay distinct.
  const glowR  = ring === 0
    ? 3  + Math.random() * 5
    : ring === 1
      ? 4  + Math.random() * 7
      : ring === 2
        ? 5  + Math.random() * 8
        : 6  + Math.random() * 10; // sparks get slightly larger glow

  const baseAlpha = ring === 0
    ? 0.7 + Math.random() * 0.3   // inner: very bright
    : ring === 1
      ? 0.4 + Math.random() * 0.4  // mid: medium
      : ring === 2
        ? 0.15 + Math.random() * 0.25 // outer: dimmer
        : 0.5 + Math.random() * 0.5;  // sparks: semi-random

  const orbitSpeed = (0.008 + Math.random() * 0.022) * (Math.random() > 0.5 ? 1 : -1);
  const orbitRx    = (ring === 3 ? 8 : 2) + Math.random() * ([6, 10, 14, 20][ring]);
  const orbitRy    = orbitRx * (0.5 + Math.random() * 0.8); // elliptical

  return {
    x: ax, y: ay, ax, ay,
    driftAngle: Math.random() * Math.PI * 2,
    driftSpeed: (0.001 + Math.random() * 0.002) * (Math.random() > 0.5 ? 1 : -1),
    driftR:  r * ([0.18, 0.22, 0.28, 0.55][ring]),
    orbitAngle: Math.random() * Math.PI * 2,
    orbitSpeed,
    orbitRx, orbitRy,
    radius, glowR, baseAlpha,
    phase: Math.random() * Math.PI * 2,
    phaseSpeed: 0.008 + Math.random() * 0.022,
    ring,
    vx: 0, vy: 0,
  };
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }

// ── Component ─────────────────────────────────────────────────────────────────
interface Props {
  state:       VoiceStatus;
  audioLevel?: number;
}

export function OrbParticles({ state, audioLevel = 0 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef    = useRef<number>(0);
  const stateRef  = useRef({ state, audioLevel });
  const psRef     = useRef<Particle[]>([]);
  const tRef      = useRef(0);

  useEffect(() => { stateRef.current = { state, audioLevel }; }, [state, audioLevel]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width  = SIZE;
    canvas.height = SIZE;

    // Pre-allocate full pool at max counts
    psRef.current = [
      ...Array.from({ length: MAX_POP[0] }, () => makeParticle(0)),
      ...Array.from({ length: MAX_POP[1] }, () => makeParticle(1)),
      ...Array.from({ length: MAX_POP[2] }, () => makeParticle(2)),
      ...Array.from({ length: MAX_POP[3] }, () => makeParticle(3)),
    ];

    const ctx = canvas.getContext('2d', { alpha: true })!;

    // ── Main loop ────────────────────────────────────────────────────────────
    function loop() {
      const { state: st, audioLevel: al } = stateRef.current;
      const [ic, mc, oc, sc] = STATE_POP[st];
      const speed = STATE_SPEED[st] * (1 + al * 1.2);
      const { main, hot, edge } = PALETTE[st];

      tRef.current += 0.016;
      const t = tRef.current;

      // ── Breath scale per state ──────────────────────────────────────────
      let breath = 1.0;
      if (st === 'speaking') {
        breath = 1 + 0.13 * Math.sin(t * 3.2)
                   + 0.05 * Math.sin(t * 7.8)
                   + al * 0.18;
      } else if (st === 'listening') {
        breath = 1 + 0.04 * Math.sin(t * 2.1) + 0.02 * Math.sin(t * 5.5);
      } else if (st === 'processing') {
        // Asymmetric wobble — feels alive and computing
        breath = 1 + 0.06 * Math.sin(t * 4.0) + 0.03 * Math.sin(t * 9.3 + 1.1);
      } else {
        breath = 1 + 0.015 * Math.sin(t * 0.8);
      }

      ctx.clearRect(0, 0, SIZE, SIZE);

      const ps = psRef.current;

      // ── Partition offsets into rings ───────────────────────────────────
      // Layout in array: [0..MAX_POP[0]-1]=inner, [MAX_POP[0]..]=mid, etc.
      const offsets = [0, MAX_POP[0], MAX_POP[0]+MAX_POP[1], MAX_POP[0]+MAX_POP[1]+MAX_POP[2]];
      const counts  = [ic, mc, oc, sc];

      // ── Draw soft ambient glow FIRST (source-over, very faint) ─────────
      // This creates the vague "presence" without looking like a solid sphere.
      // We draw it separately with screen blend and very low alpha so it
      // never flattens into a solid blob.
      ctx.globalCompositeOperation = 'source-over';

      // Ambient breath halo (single soft radial — NOT a sphere, just warmth)
      {
        const haloR  = RING_R[1] * breath * 1.15;
        const haloA  = st === 'disconnected' ? 0.04 : 0.07;
        const hg = ctx.createRadialGradient(CX, CY, 0, CX, CY, haloR);
        hg.addColorStop(0,    `rgba(${main[0]},${main[1]},${main[2]},${haloA})`);
        hg.addColorStop(0.5,  `rgba(${main[0]},${main[1]},${main[2]},${haloA * 0.4})`);
        hg.addColorStop(1,    `rgba(${main[0]},${main[1]},${main[2]},0)`);
        ctx.beginPath();
        ctx.arc(CX, CY, haloR, 0, Math.PI * 2);
        ctx.fillStyle = hg;
        ctx.fill();
      }

      // ── Draw particles using SCREEN blend ──────────────────────────────
      // Screen blend: makes overlapping glows ADD brightness without
      // ever saturating into a uniform blob — partial overlaps stay distinct.
      ctx.globalCompositeOperation = 'screen';

      for (let ring = 0; ring < 4; ring++) {
        const base  = offsets[ring];
        const count = counts[ring];
        const rr    = ring as 0 | 1 | 2 | 3;
        const maxBoundary = RING_R[ring] * breath * ([1.05, 1.10, 1.18, 1.6][ring]);

        for (let j = 0; j < count; j++) {
          const p = ps[base + j];

          // ── Advance physics ─────────────────────────────────────────
          p.orbitAngle += p.orbitSpeed * speed;
          p.driftAngle += p.driftSpeed;

          // Processing: add turbulence to inner rings (swirling streams)
          if (st === 'processing' && ring <= 1) {
            const noiseX = Math.sin(p.orbitAngle * 3.1 + t * 2.3) * 0.4;
            const noiseY = Math.cos(p.orbitAngle * 2.7 + t * 1.8) * 0.4;
            p.vx += noiseX;
            p.vy += noiseY;
          } else {
            p.vx *= 0.85;
            p.vy *= 0.85;
          }

          // Sparks: they drift outward then gently return
          let targetAx = p.ax;
          let targetAy = p.ay;
          if (ring === 3) {
            const sparkPhase = Math.sin(t * 0.7 + p.phase * 2);
            targetAx = p.ax + (p.ax - CX) * sparkPhase * 0.3;
            targetAy = p.ay + (p.ay - CY) * sparkPhase * 0.3;
          }

          const driftX = Math.cos(p.driftAngle) * p.driftR;
          const driftY = Math.sin(p.driftAngle) * p.driftR;

          const orbitX = Math.cos(p.orbitAngle) * p.orbitRx;
          const orbitY = Math.sin(p.orbitAngle) * p.orbitRy;

          const targetX = targetAx + driftX + orbitX + p.vx;
          const targetY = targetAy + driftY + orbitY + p.vy;

          // Smooth chase
          p.x += (targetX - p.x) * 0.06;
          p.y += (targetY - p.y) * 0.06;

          // Soft boundary — push back gently, don't clamp hard
          const dx   = p.x - CX;
          const dy   = p.y - CY;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > maxBoundary) {
            const over = dist - maxBoundary;
            p.x -= (dx / dist) * over * 0.3;
            p.y -= (dy / dist) * over * 0.3;
          }

          // Apply breath from centre
          const bx = CX + (p.x - CX) * (ring === 3 ? 1 : breath);
          const by = CY + (p.y - CY) * (ring === 3 ? 1 : breath);

          // ── Alpha flicker ────────────────────────────────────────────
          p.phase += p.phaseSpeed * speed;

          // Different flicker patterns per ring
          let pulse: number;
          let sparkFlash = 0;
          if (ring === 0) {
            // Inner: slow strong pulse
            pulse = 0.6 + 0.4 * Math.sin(p.phase);
          } else if (ring === 1) {
            // Mid: medium flicker
            pulse = 0.45 + 0.55 * Math.sin(p.phase + 0.8);
          } else if (ring === 2) {
            // Outer: irregular fade in/out
            pulse = Math.max(0, Math.sin(p.phase * 0.7)) * (0.5 + 0.5 * Math.sin(p.phase * 2.3));
          } else {
            // Sparks: sharp random flashes
            sparkFlash = Math.pow(Math.max(0, Math.sin(p.phase * 1.5)), 3);
            pulse = sparkFlash;
          }
          const alpha = p.baseAlpha * pulse;
          if (alpha < 0.01) continue;

          // ── Color: gradient from hot (centre) to edge (outer) ───────
          const distFrac = Math.min(dist / (RING_R[3] * 1.2), 1);
          const cr = lerp(hot[0], edge[0], distFrac * 0.8);
          const cg = lerp(hot[1], edge[1], distFrac * 0.8);
          const cb = lerp(hot[2], edge[2], distFrac * 0.8);

          // ── Draw: hard dot + soft glow ───────────────────────────────
          // The glow is SMALL and tight — this prevents blobs
          const gr = p.glowR * (ring === 3 ? 1.3 + sparkFlash : 1);

          // Pass 1 — dot glow (screen blend)
          const grad = ctx.createRadialGradient(bx, by, 0, bx, by, gr);
          grad.addColorStop(0,    `rgba(${cr|0},${cg|0},${cb|0},${alpha})`);
          grad.addColorStop(0.35, `rgba(${cr|0},${cg|0},${cb|0},${alpha * 0.55})`);
          grad.addColorStop(0.7,  `rgba(${main[0]},${main[1]},${main[2]},${alpha * 0.15})`);
          grad.addColorStop(1,    `rgba(${main[0]},${main[1]},${main[2]},0)`);
          ctx.beginPath();
          ctx.arc(bx, by, gr, 0, Math.PI * 2);
          ctx.fillStyle = grad;
          ctx.fill();

          // Pass 2 — bright hard dot (makes particles feel SOLID, not blobby)
          ctx.beginPath();
          ctx.arc(bx, by, p.radius, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${Math.min(255,cr+60)|0},${Math.min(255,cg+60)|0},${Math.min(255,cb+60)|0},${Math.min(1, alpha * 1.8)})`;
          ctx.fill();
        }
      }

      // ── Processing: draw swirling stream lines ──────────────────────────
      if (st === 'processing') {
        ctx.globalCompositeOperation = 'screen';
        const streamAlpha = 0.03 + 0.02 * Math.sin(t * 1.5);
        const streamCount = 3;
        for (let s = 0; s < streamCount; s++) {
          const baseAngle = (t * 0.6 + (s * Math.PI * 2) / streamCount);
          ctx.beginPath();
          for (let i = 0; i <= 60; i++) {
            const a   = baseAngle + (i / 60) * Math.PI * 2.4;
            const rad = RING_R[0] + (RING_R[2] - RING_R[0]) * (i / 60);
            const sx  = CX + Math.cos(a) * rad;
            const sy  = CY + Math.sin(a) * rad;
            i === 0 ? ctx.moveTo(sx, sy) : ctx.lineTo(sx, sy);
          }
          ctx.strokeStyle = `rgba(${main[0]},${main[1]},${main[2]},${streamAlpha})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }

      // ── Speaking: add ripple rings emanating from centre ───────────────
      if (st === 'speaking' || al > 0.3) {
        ctx.globalCompositeOperation = 'screen';
        const rippleCount = st === 'speaking' ? 3 : 2;
        for (let r = 0; r < rippleCount; r++) {
          const phase    = ((t * 1.2 + r * 0.55) % 1);
          const rippleR  = RING_R[1] * (0.6 + phase * 1.0) * breath;
          const rippleA  = (1 - phase) * (st === 'speaking' ? 0.12 : 0.06) * (1 + al);
          ctx.beginPath();
          ctx.arc(CX, CY, rippleR, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(${main[0]},${main[1]},${main[2]},${rippleA})`;
          ctx.lineWidth   = 1.2;
          ctx.stroke();
        }
      }

      ctx.globalCompositeOperation = 'source-over';
      rafRef.current = requestAnimationFrame(loop);
    }

    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top:       '50%',
        left:      '50%',
        transform: 'translate(-50%, -50%)',
        width:     SIZE,
        height:    SIZE,
        pointerEvents: 'none',
        zIndex: 2,
      }}
    />
  );
}
