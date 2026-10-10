import { useState, useEffect, useRef, useCallback } from 'react';
import { startVoiceSession, submitVoiceTurn } from '../api';
import type { TranscriptTurn } from '../types';

export type { TranscriptTurn };

export interface VoiceStreamOptions {
  /** Called after the server accepted a turn (e.g. so the host can refresh dependent views). */
  onTurnCompleted?: () => void;
}

const clock = () => {
  const now = new Date();
  return `${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
};

/**
 * Interview state. Everything shown comes from the server:
 *  - the session and opening question come from POST /voice/init,
 *  - answers are stored via POST /voice/turn,
 *  - there are no client-side scores, verdicts or canned replies. If the server is unavailable the
 *    hook surfaces `error`; it never invents interviewer text.
 */
export function useVoiceStream(
  candidateName?: string,
  repoId?: string,
  options: VoiceStreamOptions = {}
) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSessionActive, setIsSessionActive] = useState<boolean>(false);
  const [isStarting, setIsStarting] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const [userSpeechInput, setUserSpeechInput] = useState<string>('');
  const [verdict, setVerdict] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState<number>(0.2);
  const [transcript, setTranscript] = useState<TranscriptTurn[]>([]);

  const recognitionRef = useRef<any>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Browser speech recognition (optional; typing always works).
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      recognition.onresult = (event: any) => {
        let currentText = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          currentText += event.results[i][0].transcript;
        }
        setUserSpeechInput(currentText);
      };
      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);
      recognitionRef.current = recognition;
    }
    return () => {
      recognitionRef.current?.stop();
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    };
  }, []);

  // Decorative orb animation (not a microphone measurement). Cleans up its own frame loop.
  useEffect(() => {
    if (!(isAiSpeaking || isListening)) {
      setAudioLevel(0.15);
      return;
    }
    let phase = 0;
    let frame = 0;
    const animate = () => {
      phase += 0.1;
      const level = isAiSpeaking
        ? 0.4 + Math.sin(phase) * 0.35 + Math.random() * 0.25
        : 0.3 + Math.sin(phase * 1.5) * 0.2 + Math.random() * 0.15;
      setAudioLevel(Math.max(0.1, Math.min(1.0, level)));
      frame = requestAnimationFrame(animate);
      animationFrameRef.current = frame;
    };
    frame = requestAnimationFrame(animate);
    animationFrameRef.current = frame;
    return () => cancelAnimationFrame(frame);
  }, [isAiSpeaking, isListening]);

  const speakText = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 0.95;
    utterance.onstart = () => setIsAiSpeaking(true);
    utterance.onend = () => setIsAiSpeaking(false);
    utterance.onerror = () => setIsAiSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }, []);

  /** Starts a real server-side session; the opening question comes from the server. */
  const startSession = async () => {
    setError(null);
    setNotice(null);
    setIsStarting(true);
    try {
      const session = await startVoiceSession({ repoId, candidateName });
      setSessionId(session.id);
      setVerdict(session.defenseVerdict);
      setTranscript(session.transcriptTurns);
      setIsSessionActive(true);
      const opening = session.transcriptTurns.find((t) => t.speaker === 'ai_interviewer');
      if (opening) speakText(opening.text);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The interview session could not be started.');
    } finally {
      setIsStarting(false);
    }
  };

  const submitCandidateTurn = async (speechText: string) => {
    const text = speechText.trim();
    if (!text || !sessionId) return;

    try {
      recognitionRef.current?.stop();
    } catch {
      /* not started */
    }
    setIsListening(false);
    setError(null);
    setNotice(null);
    setUserSpeechInput('');

    setTranscript((prev) => [...prev, { speaker: 'candidate', text, timestamp: clock() }]);
    setIsSubmitting(true);
    try {
      const result = await submitVoiceTurn({ sessionId, speechText: text });
      setVerdict(result.currentVerdict);
      if (result.aiStatus === 'generated' && result.interviewerReplyText) {
        setTranscript((prev) => [
          ...prev,
          { speaker: 'ai_interviewer', text: result.interviewerReplyText as string, timestamp: clock() },
        ]);
        speakText(result.interviewerReplyText);
      } else {
        setNotice(
          'Your answer was recorded for human review. The AI interviewer is unavailable, so there is no follow-up question.'
        );
      }
      options.onTurnCompleted?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Your answer could not be saved.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      try {
        recognitionRef.current?.stop();
      } catch {
        /* already stopped */
      }
      setIsListening(false);
      if (userSpeechInput.trim()) void submitCandidateTurn(userSpeechInput);
    } else {
      setUserSpeechInput('');
      setIsListening(true);
      try {
        recognitionRef.current?.start();
      } catch {
        // already started
      }
    }
  };

  const endSession = () => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    try {
      recognitionRef.current?.stop();
    } catch {
      /* not started */
    }
    setIsListening(false);
    setIsAiSpeaking(false);
    setIsSessionActive(false);
  };

  return {
    sessionId,
    isSessionActive,
    isStarting,
    isSubmitting,
    startSession,
    endSession,
    isListening,
    toggleListening,
    isAiSpeaking,
    userSpeechInput,
    setUserSpeechInput,
    submitCandidateTurn,
    verdict,
    error,
    notice,
    audioLevel,
    transcript,
    /** True when the browser can capture speech (otherwise the answer box is the only input). */
    canListen: typeof window !== 'undefined' && !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition),
  };
}

/** The hook's result. The host keeps it alive across tab switches and passes it to the view. */
export type VoiceInterviewState = ReturnType<typeof useVoiceStream>;
