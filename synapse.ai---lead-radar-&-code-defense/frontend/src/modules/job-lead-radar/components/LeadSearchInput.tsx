import React from 'react';
import { Search, X } from 'lucide-react';

interface LeadSearchInputProps {
  value: string;
  onChange: (val: string) => void;
  onSearchSubmit?: () => void;
  isLoading?: boolean;
}

export const LeadSearchInput: React.FC<LeadSearchInputProps> = ({ value, onChange, onSearchSubmit }) => {
  return (
    <div className="relative w-full sm:max-w-xl">
      <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft" aria-hidden="true" />
      <input
        id="lead-semantic-search-input"
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && onSearchSubmit?.()}
        placeholder="Filter title, company or stack"
        aria-label="Filter leads by title, company or tech stack"
        className="field pl-10 pr-10 [&::-webkit-search-cancel-button]:hidden"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 cursor-pointer items-center justify-center rounded-lg text-ink-soft hover:bg-canvas-alt hover:text-ink"
          aria-label="Clear search"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
};
