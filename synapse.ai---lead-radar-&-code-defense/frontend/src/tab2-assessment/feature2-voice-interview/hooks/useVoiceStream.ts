import { useState, useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export interface TranscriptTurn {
  speaker: 'ai_interviewer' | 'candidate';
  text: string;
  timestamp: string;
  technicalAssessmentNote?: string;
}

export function useVoiceStream(candidateName: string = 'Alex Vance', repoId?: string) {
  const queryClient = useQueryClient();
  const [isSessionActive, setIsSessionActive] = useState<boolean>(false);
  const [sessionId, setSessionId] = useState<string>('demo-voice-session-1');
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const [userSpeechInput, setUserSpeechInput] = useState<string>('');
  const [compositeScore, setCompositeScore] = useState<number>(89.0);
  const [verdict, setVerdict] = useState<string>('HUMAN_REVIEW');
  const [audioLevel, setAudioLevel] = useState<number>(0.2);

  const [transcript, setTranscript] = useState<TranscriptTurn[]>([
    {
      speaker: 'ai_interviewer',
      text: "I see in your Raft implementation you've configured election timeouts between 150ms and 300ms. Under a partial cross-rack network split where heartbeats are intermittently dropped, how does your state machine prevent split-vote thrashing and uncommitted log divergence?",
      timestamp: '00:02',
      technicalAssessmentNote: 'Initial architectural probe regarding Raft election jitter and partition safety',
    },
  ]);

  const recognitionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Initialize Speech Recognition if supported in browser
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
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

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  // Audio wave pulse simulator
  useEffect(() => {
    if (isAiSpeaking || isListening) {
      let phase = 0;
      const animate = () => {
        phase += 0.1;
        const level = isAiSpeaking
          ? 0.4 + Math.sin(phase) * 0.35 + Math.random() * 0.25
          : 0.3 + Math.sin(phase * 1.5) * 0.2 + Math.random() * 0.15;
        setAudioLevel(Math.max(0.1, Math.min(1.0, level)));
        animationFrameRef.current = requestAnimationFrame(animate);
      };
      animationFrameRef.current = requestAnimationFrame(animate);
    } else {
      setAudioLevel(0.15);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    }
  }, [isAiSpeaking, isListening]);

  const speakText = useCallback((text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 0.95;

      utterance.onstart = () => setIsAiSpeaking(true);
      utterance.onend = () => setIsAiSpeaking(false);
      utterance.onerror = () => setIsAiSpeaking(false);

      window.speechSynthesis.speak(utterance);
    } else {
      // Fallback timer simulation
      setIsAiSpeaking(true);
      setTimeout(() => setIsAiSpeaking(false), 4000);
    }
  }, []);

  // Start Session
  const startSession = async () => {
    setIsSessionActive(true);
    speakText(transcript[0].text);
  };

  // Toggle Microphone
  const toggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) recognitionRef.current.stop();
      setIsListening(false);
      if (userSpeechInput.trim()) {
        submitCandidateTurn(userSpeechInput);
      }
    } else {
      setUserSpeechInput('');
      setIsListening(true);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch {
          // Already started
        }
      }
    }
  };

  // Submit Candidate Turn
  const submitCandidateTurn = async (speechText: string) => {
    if (!speechText.trim()) return;

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    setIsListening(false);

    const now = new Date();
    const ts = `${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

    // Add candidate turn
    setTranscript((prev) => [
      ...prev,
      {
        speaker: 'candidate',
        text: speechText,
        timestamp: ts,
      },
    ]);
    setUserSpeechInput('');

    try {
      const res = await fetch('/api/v1/assessment/voice/turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          candidate_speech_text: speechText,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setCompositeScore(data.current_composite_score);
        setVerdict(data.current_verdict);

        // Add AI response turn
        setTranscript((prev) => [
          ...prev,
          {
            speaker: 'ai_interviewer',
            text: data.interviewer_reply_text,
            timestamp: ts,
            technicalAssessmentNote: `Technical depth adjusted to ${data.current_composite_score}% (${data.current_verdict})`,
          },
        ]);

        speakText(data.interviewer_reply_text);
        queryClient.invalidateQueries({ queryKey: ['leaderboard'] });
      } else {
        fallbackAiTurn(speechText, ts);
      }
    } catch {
      fallbackAiTurn(speechText, ts);
    }
  };

  const fallbackAiTurn = (candidateText: string, ts: string) => {
    const boost = candidateText.toLowerCase().includes('raft') ? 2.5 : 1.2;
    const newScore = Math.min(99.2, compositeScore + boost);
    setCompositeScore(Number(newScore.toFixed(1)));
    const newVerdict = newScore >= 90.0 ? 'AUTO_HIRE' : 'HUMAN_REVIEW';
    setVerdict(newVerdict);

    const reply =
      'Good articulation on the pre-vote phase and heartbeat isolation. Next: how does your persistence log handle WAL fsync latency spikes when the disk buffer is saturated without blocking the main event loop?';

    setTranscript((prev) => [
      ...prev,
      {
        speaker: 'ai_interviewer',
        text: reply,
        timestamp: ts,
        technicalAssessmentNote: `Defense depth score evaluated at ${newScore.toFixed(1)}%`,
      },
    ]);
    speakText(reply);
  };

  const endSession = () => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    if (recognitionRef.current) recognitionRef.current.stop();
    setIsListening(false);
    setIsAiSpeaking(false);
    setIsSessionActive(false);
  };

  return {
    isSessionActive,
    startSession,
    endSession,
    isListening,
    toggleListening,
    isAiSpeaking,
    userSpeechInput,
    setUserSpeechInput,
    submitCandidateTurn,
    compositeScore,
    verdict,
    audioLevel,
    transcript,
  };
}
