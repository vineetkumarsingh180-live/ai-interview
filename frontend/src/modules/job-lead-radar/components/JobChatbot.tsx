import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Send,
  User,
  Bot,
  RefreshCw,
  Briefcase,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  Globe,
  Twitter,
  Linkedin,
  MessageSquare,
} from 'lucide-react';
import { chatSearchLeads } from '../api';
import { JobLead } from '../types';
import { LeadCard } from './LeadCard';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  matchedLeads?: JobLead[];
  suggestions?: string[];
}

interface JobChatbotProps {
  onDraftOutreach: (lead: JobLead) => void;
  onSwitchToFeed?: () => void;
}

const DEFAULT_SUGGESTIONS = [
  'Search Twitter for remote Python or AI engineer roles',
  'Find Reddit r/forhire high-paying full-stack gigs',
  'Search LinkedIn for Senior Backend positions',
  'Find Telegram remote developer contract roles',
];


export const JobChatbot: React.FC<JobChatbotProps> = ({ onDraftOutreach, onSwitchToFeed }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: "Hello! I am your AI Job Radar & Multi-Platform Crawler powered by Gemini. Whatever job profile you search for, I search across Twitter/X, LinkedIn, Reddit, Telegram, and the internet to find active hiring opportunities with roles, compensation, and direct links.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      suggestions: DEFAULT_SUGGESTIONS,
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [candidateContext, setCandidateContext] = useState('');
  const [showContextDrawer, setShowContextDrawer] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend ?? inputValue).trim();
    if (!text || isLoading) return;

    setError(null);
    const userMsgId = `usr_${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await chatSearchLeads({
        message: text,
        candidateContext: candidateContext.trim() || undefined,
      });

      const assistantMsg: ChatMessage = {
        id: `ast_${Date.now()}`,
        sender: 'assistant',
        text: response.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        matchedLeads: response.matchedLeads || [],
        suggestions: response.suggestions && response.suggestions.length > 0 ? response.suggestions : undefined,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorText = err?.message || 'Failed to communicate with AI Job Radar backend.';
      setError(errorText);
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        sender: 'assistant',
        text: `Sorry, I encountered an issue querying the job database: ${errorText}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggestions: ['Try searching again', 'Show all available leads'],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleResetChat = () => {
    setMessages([
      {
        id: `welcome_${Date.now()}`,
        sender: 'assistant',
        text: "Conversation reset. What kind of job profile or technology would you like to search across Twitter, LinkedIn, Reddit, or Telegram?",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        suggestions: DEFAULT_SUGGESTIONS,
      },
    ]);
    setError(null);
  };

  return (
    <div className="card flex flex-col overflow-hidden" style={{ minHeight: '680px' }}>
      {/* Chat Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface p-4 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-warm-tint text-warm-strong">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-ink">AI Job Radar & Social Crawler</h2>
              <span className="badge badge-neutral text-xs">Powered by Gemini</span>
            </div>
            <p className="text-xs text-ink-soft">
              Real-time multi-platform search across Twitter/X, LinkedIn, Reddit, Telegram & the web
            </p>
          </div>
        </div>


        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowContextDrawer((prev) => !prev)}
            className={`btn text-xs ${candidateContext.trim() ? 'btn-primary' : 'btn-secondary'}`}
            title="Provide your skills or background to personalize matches"
          >
            <User className="h-3.5 w-3.5" />
            <span>{candidateContext.trim() ? 'Profile active' : 'Add candidate profile'}</span>
            {showContextDrawer ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>

          <button
            type="button"
            onClick={handleResetChat}
            className="btn btn-secondary btn-icon"
            title="Reset chat conversation"
            aria-label="Reset chat"
          >
            <RefreshCw className="h-4 w-4" />
          </button>

          {onSwitchToFeed && (
            <button
              type="button"
              onClick={onSwitchToFeed}
              className="btn btn-secondary text-xs"
              title="Return to standard lead feed"
            >
              <span>View lead feed</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Candidate Context Drawer (Collapsible) */}
      {showContextDrawer && (
        <div className="border-b border-line bg-canvas-alt/60 p-4 transition-all">
          <div className="mx-auto max-w-3xl space-y-2">
            <div className="flex items-center justify-between">
              <label htmlFor="candidate-context-input" className="text-xs font-semibold text-ink">
                Candidate Profile & Background Context (Optional)
              </label>
              <span className="text-[11px] text-ink-soft">Helps Gemini score relevance to your skills</span>
            </div>
            <textarea
              id="candidate-context-input"
              rows={2}
              value={candidateContext}
              onChange={(e) => setCandidateContext(e.target.value)}
              placeholder="e.g., Senior Full-Stack Engineer with 5 years in Python, FastAPI, React, and PostgreSQL. Interested in remote roles."
              className="field resize-none text-xs"
            />
          </div>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6" style={{ maxHeight: '600px' }}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            {/* Sender and timestamp header */}
            <div className="mb-1 flex items-center gap-1.5 px-1 text-[11px] text-ink-soft">
              {msg.sender === 'user' ? (
                <>
                  <span className="font-semibold text-ink">You</span>
                  <span>•</span>
                  <span>{msg.timestamp}</span>
                  <User className="h-3 w-3 text-mocha" />
                </>
              ) : (
                <>
                  <Bot className="h-3.5 w-3.5 text-warm" />
                  <span className="font-semibold text-ink">Radar Gemini AI</span>
                  <span>•</span>
                  <span>{msg.timestamp}</span>
                </>
              )}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-2xl rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                msg.sender === 'user'
                  ? 'bg-mocha text-surface rounded-tr-sm'
                  : 'well bg-surface text-ink rounded-tl-sm border border-line'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>
            </div>

            {/* Matched Lead Cards (if any) */}
            {msg.matchedLeads && msg.matchedLeads.length > 0 && (
              <div className="mt-3 w-full max-w-4xl space-y-3">
                <div className="flex items-center gap-2 px-1 text-xs font-bold text-ink">
                  <Briefcase className="h-4 w-4 text-warm" />
                  <span>
                    Matched Opportunities ({msg.matchedLeads.length})
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {msg.matchedLeads.map((lead) => (
                    <LeadCard
                      key={lead.id}
                      lead={lead}
                      onDraftOutreach={onDraftOutreach}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Suggestion Chips */}
            {msg.suggestions && msg.suggestions.length > 0 && (
              <div className="mt-2.5 flex flex-wrap items-center gap-1.5 px-1">
                <span className="flex items-center gap-1 text-[11px] font-medium text-ink-soft">
                  <HelpCircle className="h-3 w-3 text-warm" />
                  Suggested:
                </span>
                {msg.suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSend(suggestion)}
                    disabled={isLoading}
                    className="chip text-xs hover:border-warm hover:text-warm-strong transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex flex-col items-start space-y-2">
            <div className="flex items-center gap-1.5 px-1 text-[11px] text-ink-soft">
              <Bot className="h-3.5 w-3.5 text-warm animate-pulse" />
              <span className="font-semibold text-ink">Radar Gemini AI Crawler</span>
              <span>is crawling Twitter, LinkedIn, Reddit, Telegram & web...</span>
            </div>
            <div className="well flex items-center gap-3 rounded-2xl rounded-tl-sm border border-line bg-surface px-4 py-3 text-sm text-ink-soft">
              <span className="flex h-4 w-4 animate-spin rounded-full border-2 border-warm border-t-transparent" />
              <span>Searching multi-platform channels for live job postings and compensation data...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box Footer */}
      <div className="border-t border-line bg-surface p-3 sm:p-4">
        {/* Quick channel presets */}
        <div className="mb-2.5 flex flex-wrap items-center gap-1.5">
          <span className="flex items-center gap-1 text-[11px] font-semibold text-ink-soft">
            <Globe className="h-3 w-3 text-warm" />
            Channel presets:
          </span>
          <button
            type="button"
            onClick={() => setInputValue('Search Twitter/X for remote ')}
            className="chip text-[11px] hover:border-mocha hover:text-ink transition-colors"
          >
            <Twitter className="h-3 w-3 text-mocha" />
            <span>Twitter / X</span>
          </button>
          <button
            type="button"
            onClick={() => setInputValue('Search LinkedIn for ')}
            className="chip text-[11px] hover:border-mocha hover:text-ink transition-colors"
          >
            <Linkedin className="h-3 w-3 text-mocha" />
            <span>LinkedIn</span>
          </button>
          <button
            type="button"
            onClick={() => setInputValue('Search Reddit r/forhire and r/remotework for ')}
            className="chip text-[11px] hover:border-mocha hover:text-ink transition-colors"
          >
            <MessageSquare className="h-3 w-3 text-mocha" />
            <span>Reddit</span>
          </button>
          <button
            type="button"
            onClick={() => setInputValue('Search Telegram tech channels for ')}
            className="chip text-[11px] hover:border-mocha hover:text-ink transition-colors"
          >
            <Send className="h-3 w-3 text-mocha" />
            <span>Telegram</span>
          </button>
        </div>

        {error && (
          <div className="mb-2 flex items-center gap-2 rounded-lg bg-danger-tint px-3 py-1.5 text-xs text-danger">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{error}</span>
          </div>
        )}

        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Search any job profile (e.g. 'React developer', 'Solidity engineer', 'Twitter AI roles')..."
            className="field flex-1"
          />
          <button
            type="button"
            onClick={() => handleSend()}
            disabled={isLoading || !inputValue.trim()}
            className="btn btn-primary shrink-0"
            aria-label="Search jobs"
          >
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">Search</span>
          </button>
        </div>
      </div>
    </div>
  );
};

