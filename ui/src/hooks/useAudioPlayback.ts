/**
 * useAudioPlayback — Gerencia a reprodução de áudio PCM 24kHz via AudioContext.
 *
 * Expõe:
 *   playChunk(base64)   — agenda um chunk de áudio para tocar sequencialmente
 *   cancelPlayback()    — cancela imediatamente todo o áudio pendente (barge-in)
 *   isPlaying           — true enquanto há áudio agendado
 */
import { useCallback, useRef, useState } from 'react';

const SAMPLE_RATE = 24000;

export function useAudioPlayback() {
  const playbackCtxRef  = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef(0);
  const speakTimerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const _ensurePlayback = useCallback(() => {
    if (!playbackCtxRef.current || playbackCtxRef.current.state === 'closed') {
      playbackCtxRef.current = new AudioContext({ sampleRate: SAMPLE_RATE });
      nextPlayTimeRef.current = 0;
    }
    if (playbackCtxRef.current.state === 'suspended') {
      playbackCtxRef.current.resume().catch(() => {});
    }
  }, []);

  const playChunk = useCallback((base64: string, onSpeakStart: () => void, onSpeakEnd: () => void) => {
    try {
      _ensurePlayback();
      const ctx = playbackCtxRef.current!;

      const raw    = atob(base64);
      const bytes  = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);

      // PCM 16-bit little-endian → Float32
      const samples = new Float32Array(bytes.length / 2);
      const view    = new DataView(bytes.buffer);
      for (let i = 0; i < samples.length; i++) {
        samples[i] = view.getInt16(i * 2, true) / 32768;
      }

      const buffer  = ctx.createBuffer(1, samples.length, SAMPLE_RATE);
      buffer.copyToChannel(samples, 0);

      const source  = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);

      const startAt = Math.max(ctx.currentTime, nextPlayTimeRef.current);
      source.start(startAt);
      nextPlayTimeRef.current = startAt + buffer.duration;

      // Controla estado isPlaying
      if (speakTimerRef.current) clearTimeout(speakTimerRef.current);
      setIsPlaying(true);
      onSpeakStart();

      speakTimerRef.current = setTimeout(() => {
        setIsPlaying(false);
        onSpeakEnd();
      }, (nextPlayTimeRef.current - ctx.currentTime) * 1000 + 200);
    } catch (e) {
      console.warn('[useAudioPlayback] playChunk error:', e);
    }
  }, [_ensurePlayback]);

  const cancelPlayback = useCallback(() => {
    if (speakTimerRef.current) {
      clearTimeout(speakTimerRef.current);
      speakTimerRef.current = null;
    }
    if (playbackCtxRef.current) {
      playbackCtxRef.current.close().catch(() => {});
      playbackCtxRef.current = null;
    }
    nextPlayTimeRef.current = 0;
    setIsPlaying(false);
  }, []);

  return { playChunk, cancelPlayback, isPlaying };
}
