// Public API of the Voice Defense module. Other code imports from "@modules/voice-defense" only.
export { VoiceDefenseView } from './VoiceDefenseView';
export { useVoiceStream } from './hooks/useVoiceStream';
export type { VoiceInterviewState, VoiceStreamOptions } from './hooks/useVoiceStream';
export type { VoiceCandidate, TranscriptTurn } from './types';
