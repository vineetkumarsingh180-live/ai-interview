import React, { useState } from 'react';
import { Search, Sparkles, X } from 'lucide-react';

interface LeadSearchInputProps {
  value: string;
  onChange: (val: string) => void;
  onSearchSubmit?: () => void;
  isLoading?: boolean;
}

export const LeadSearchInput: React.FC<LeadSearchInputProps> = ({
  value,
  onChange,
  onSearchSubmit,
  isLoading,
}) => {
  return (
    <div className="relative w-full max-w-xl">
      <div className="relative flex items-center">
        <Search className="absolute left-3.5 w-4 h-4 text-[#938ea1]" />
        <input
          id="lead-semantic-search-input"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearchSubmit?.()}
          placeholder="Semantic radar search (e.g., 'Rust distributed systems Raft', 'Series A $200k+')..."
          className="w-full pl-10 pr-24 py-2.5 rounded-xl inset-well border border-white/5 text-xs font-mono text-[#e0e2ef] placeholder-[#938ea1] focus:outline-none focus:border-[#7952ff] transition-all"
        />
        {value && (
          <button
            onClick={() => onChange('')}
            className="absolute right-14 p-1 text-[#938ea1] hover:text-white transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
        <div className="absolute right-2 flex items-center gap-1 px-2 py-1 rounded-md bg-[#272a33] border border-white/5 text-[10px] font-mono text-[#cbbeff]">
          <Sparkles className={`w-3 h-3 text-[#00e4b2] ${isLoading ? 'animate-spin' : ''}`} />
          <span>Vector</span>
        </div>
      </div>
    </div>
  );
};
