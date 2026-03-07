import { VoiceStatus } from '../hooks/useVoice';

const STATUS_CAPTION: Record<VoiceStatus, string> = {
  disconnected: 'offline',
  connecting:   'conectando',
  idle:         'aguardando',
  listening:    'ouvindo',
  processing:   'processando',
  speaking:     'falando',
};

interface Props {
  status: VoiceStatus;
}

export function VoiceOrb({ status }: Props) {
  return (
    <div className="orb-scene" data-status={status}>
      <div className="orb-ambient" />
      <div className="orb-rings">
        <span className="orb-ring" />
        <span className="orb-ring" />
        <span className="orb-ring" />
      </div>
      <div className="orb-arc" />
      <div className="orb-body" />
      <span className="orb-caption">{STATUS_CAPTION[status]}</span>
    </div>
  );
}
