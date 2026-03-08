import { useState, useEffect, useCallback, useRef } from 'react';
import type { SkillEvent } from './useVoice';

export interface SkillBubble {
  id: string;
  label: string;
  offsetX: number;   // px from center (-60..+60) — horizontal spawn position
  driftX: number;    // px of lateral sway during flight (-25..+25)
  spawnY: number;    // slight vertical variation (-20..+20)
  duration: number;  // animation duration in ms (2200..3400)
  createdAt: number;
}

// Labels used in mock/dev mode
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
    .replace(/^google_/, '')   // google_gmail_... → gmail_...
    .replace(/_/g, '.');       // underscores → dots
}

function rand(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function makeBubble(action: string): SkillBubble {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    label:    formatLabel(action),
    offsetX:  Math.round(rand(-58, 58)),
    driftX:   Math.round(rand(-24, 24)),
    spawnY:   Math.round(rand(-18, 18)),
    duration: Math.round(rand(2200, 3400)),
    createdAt: Date.now(),
  };
}

export function useSkillBubbles(skillEvent: SkillEvent | null) {
  const [bubbles, setBubbles] = useState<SkillBubble[]>([]);
  const prevTsRef = useRef<number>(-1);

  // Spawn a bubble when a new real WS skill event arrives
  useEffect(() => {
    if (!skillEvent || skillEvent.ts === prevTsRef.current) return;
    prevTsRef.current = skillEvent.ts;
    setBubbles(prev => [...prev, makeBubble(skillEvent.action)]);
  }, [skillEvent]);

  // Called by onAnimationEnd to clean up finished bubbles
  const removeBubble = useCallback((id: string) => {
    setBubbles(prev => prev.filter(b => b.id !== id));
  }, []);

  // Manual spawn — used by dev mock buttons and future external triggers
  const spawnBubble = useCallback((label?: string) => {
    const skill = label ?? MOCK_SKILLS[Math.floor(Math.random() * MOCK_SKILLS.length)];
    setBubbles(prev => [...prev, makeBubble(skill)]);
  }, []);

  return { bubbles, removeBubble, spawnBubble };
}
