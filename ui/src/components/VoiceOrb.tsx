import { VoiceStatus, AgentState } from '../hooks/useVoice';
import { OrbCore } from './orb/OrbCore';

interface Props {
  status: VoiceStatus;
  agentState?: AgentState;
  audioLevel?: number;
}

export function VoiceOrb({ status, agentState, audioLevel = 0 }: Props) {
  return <OrbCore state={status} agentState={agentState} audioLevel={audioLevel} />;
}
