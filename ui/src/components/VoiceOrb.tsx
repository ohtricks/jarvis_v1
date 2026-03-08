import { VoiceStatus } from '../hooks/useVoice';
import { OrbCore } from './orb/OrbCore';

interface Props {
  status: VoiceStatus;
  audioLevel?: number;
}

export function VoiceOrb({ status, audioLevel = 0 }: Props) {
  return <OrbCore state={status} audioLevel={audioLevel} />;
}
