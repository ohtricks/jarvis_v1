import { useState, useEffect, useCallback, useRef } from 'react';
import type { SkillEvent } from './useVoice';

export type BubbleStatus = 'running' | 'completed' | 'failed';

export interface SkillBubble {
  id: string;
  skillId?: string;    // liga ao ActiveSkill para coordenar fases
  label: string;
  offsetX: number;     // px from center — posição de spawn horizontal
  driftX: number;      // px de sway lateral durante a saída
  spawnY: number;      // variação vertical leve no spawn
  duration: number;    // duração da animação de saída (ms)
  createdAt: number;
  status: BubbleStatus;
}

// Labels usados no modo dev/mock
export const MOCK_SKILLS = [
  'open_url',
  'run_shell',
  'git.status',
  'gmail.read',
  'git.commit',
  'open_app',
  'planner.step',
  'gmail.send',
  'git.push',
  'gmail.archive',
];

function formatLabel(action: string): string {
  return action
    .replace(/^google_/, '')
    .replace(/_/g, '.');
}

function rand(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function makeBubble(action: string, skillId?: string): SkillBubble {
  return {
    id:        `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    skillId,
    label:     formatLabel(action),
    offsetX:   Math.round(rand(-58, 58)),
    driftX:    Math.round(rand(-24, 24)),
    spawnY:    Math.round(rand(-18, 18)),
    duration:  Math.round(rand(900, 1400)),  // saída mais rápida (era 2200–3400)
    createdAt: Date.now(),
    status:    'running',
  };
}

export function useSkillBubbles(skillEvent: SkillEvent | null) {
  const [bubbles, setBubbles] = useState<SkillBubble[]>([]);
  const prevTsRef = useRef<number>(-1);

  useEffect(() => {
    if (!skillEvent || skillEvent.ts === prevTsRef.current) return;
    prevTsRef.current = skillEvent.ts;

    const { action, skillId, phase } = skillEvent;

    if (phase === 'started') {
      // Nasce em running — fica pulsando enquanto a skill executa
      setBubbles(prev => [...prev, makeBubble(action, skillId)]);
    } else if (phase === 'completed') {
      // Transição para completed → animação de saída com sucesso
      setBubbles(prev =>
        prev.map(b =>
          b.skillId === skillId ? { ...b, status: 'completed' as BubbleStatus } : b
        )
      );
    } else if (phase === 'failed') {
      // Transição para failed → animação de saída com erro
      setBubbles(prev =>
        prev.map(b =>
          b.skillId === skillId ? { ...b, status: 'failed' as BubbleStatus } : b
        )
      );
    } else {
      // Evento legado (tool_result sem phase) — spawn direto como completed
      setBubbles(prev => [...prev, { ...makeBubble(action, skillId), status: 'completed' }]);
    }
  }, [skillEvent]);

  // Remove bubble quando a animação de saída termina
  const removeBubble = useCallback((id: string) => {
    setBubbles(prev => prev.filter(b => b.id !== id));
  }, []);

  // Spawn manual — usado por botões de debug e mocks
  const spawnBubble = useCallback((label?: string) => {
    const skill = label ?? MOCK_SKILLS[Math.floor(Math.random() * MOCK_SKILLS.length)];
    // Simula ciclo completo: running → completed após 1.5s
    const bubble = makeBubble(skill);
    setBubbles(prev => [...prev, bubble]);
    setTimeout(() => {
      setBubbles(prev =>
        prev.map(b => b.id === bubble.id ? { ...b, status: 'completed' as BubbleStatus } : b)
      );
    }, 1500);
  }, []);

  return { bubbles, removeBubble, spawnBubble };
}
