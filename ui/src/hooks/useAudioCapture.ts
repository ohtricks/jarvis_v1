/**
 * useAudioCapture — Captura áudio do microfone e envia PCM 16kHz via WebSocket.
 *
 * Expõe:
 *   startCapture(ws)    — inicia captura e envia chunks via ws
 *   stopCapture()       — destroi o pipeline de captura
 *   isCapturing         — true se o mic está ativo
 *   isMuted             — true se o mic está silenciado (não envia bytes)
 *   setMuted(bool)      — muta/desmuta sem destruir o pipeline
 *   audioLevel          — nível de áudio RMS normalizado 0-1
 */
import { useCallback, useRef, useState } from 'react';

const CAPTURE_SAMPLE_RATE = 16000;
const BUFFER_SIZE = 2048; // 128ms @16kHz (reduzido de 4096)

export function useAudioCapture() {
  const captureCtxRef = useRef<AudioContext | null>(null);
  const streamRef     = useRef<MediaStream | null>(null);
  const processorRef  = useRef<ScriptProcessorNode | null>(null);
  const sourceRef     = useRef<MediaStreamAudioSourceNode | null>(null);
  const isCapturingRef = useRef(false);
  const isMutedRef    = useRef(false);

  const [isCapturing, setIsCapturing] = useState(false);
  const [isMuted, setIsMutedState]    = useState(false);
  const [audioLevel, setAudioLevel]   = useState(0);

  const stopCapture = useCallback(() => {
    isCapturingRef.current = false;
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach(t => t.stop());
    captureCtxRef.current?.close().catch(() => {});
    processorRef.current = null;
    sourceRef.current    = null;
    streamRef.current    = null;
    captureCtxRef.current = null;
    setIsCapturing(false);
    setAudioLevel(0);
  }, []);

  const startCapture = useCallback(async (ws: WebSocket) => {
    if (isCapturingRef.current) return;
    isCapturingRef.current = true;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: CAPTURE_SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
    } catch (e) {
      isCapturingRef.current = false;
      throw e;
    }

    streamRef.current = stream;

    const ctx = new AudioContext({ sampleRate: CAPTURE_SAMPLE_RATE });
    captureCtxRef.current = ctx;

    const source    = ctx.createMediaStreamSource(stream);
    sourceRef.current = source;

    // eslint-disable-next-line @typescript-eslint/no-deprecated
    const processor = ctx.createScriptProcessor(BUFFER_SIZE, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (e) => {
      const f32 = e.inputBuffer.getChannelData(0);

      // Cálculo de audioLevel (RMS)
      let sumSq = 0;
      for (let i = 0; i < f32.length; i++) sumSq += f32[i] * f32[i];
      const rms = Math.sqrt(sumSq / f32.length);
      setAudioLevel(Math.min(1, rms * 8));

      if (isMutedRef.current) return;
      if (ws.readyState !== WebSocket.OPEN) return;

      // Converte Float32 → Int16 PCM
      const int16 = new Int16Array(f32.length);
      for (let i = 0; i < f32.length; i++) {
        int16[i] = Math.max(-32768, Math.min(32767, f32[i] * 32768));
      }
      ws.send(int16.buffer);
    };

    source.connect(processor);
    processor.connect(ctx.destination);

    setIsCapturing(true);
  }, []);

  const setMuted = useCallback((muted: boolean) => {
    isMutedRef.current = muted;
    setIsMutedState(muted);
    if (muted) setAudioLevel(0);
  }, []);

  return { startCapture, stopCapture, isCapturing, isMuted, setMuted, audioLevel };
}
