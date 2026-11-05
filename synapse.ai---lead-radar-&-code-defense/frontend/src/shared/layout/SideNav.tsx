import React from 'react';
import { Info, X } from 'lucide-react';
import type { NavSection } from './types';
import type { BackendStatusItem } from './useBackendStatus';

interface SideNavProps {
  sections: NavSection[];
  /** Mobile drawer state. On lg+ the sidebar is always visible. */
  isOpen: boolean;
  onClose: () => void;
  /** Live backend status lines shown at the bottom of the navigation. */
  status: BackendStatusItem[];
}

/**
 * Generic navigation sidebar / mobile drawer. It knows nothing about product modules:
 * the app supplies the sections and entries.
 */
export const SideNav: React.FC<SideNavProps> = ({ sections, isOpen, onClose, status }) => {
  return (
    <>
      {/* Mobile backdrop */}
      <div
        className={`fixed inset-0 z-30 bg-scrim transition-opacity duration-200 lg:hidden ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        id="left-navbar"
        aria-label="Primary navigation"
        className={`fixed inset-y-0 left-0 z-40 flex w-72 max-w-[85vw] select-none flex-col justify-between overflow-y-auto border-r border-line bg-canvas-alt p-4 transition-transform duration-200 lg:static lg:z-auto lg:w-64 lg:max-w-none lg:translate-x-0 lg:shrink-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="space-y-6">
          {/* Brand */}
          <div className="flex items-center justify-between gap-2 px-1">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-mocha text-base font-extrabold text-surface shadow-clay">
                S
              </span>
              <div className="min-w-0">
                <div className="truncate text-lg font-bold leading-tight tracking-tight text-ink">Synapse.AI</div>
                <p className="truncate text-xs text-ink-alt">Talent assessment</p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary btn-icon lg:hidden"
              aria-label="Close navigation menu"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <nav className="space-y-5" aria-label="Sections">
            {sections.map((section) => (
              <div key={section.label} className="space-y-1">
                <div className="eyebrow px-3 pb-1 text-ink-alt">{section.label}</div>
                {section.entries.map((entry) => {
                  const Icon = entry.icon;
                  return (
                    <button
                      key={entry.id}
                      id={entry.id}
                      type="button"
                      onClick={() => {
                        entry.onSelect();
                        onClose();
                      }}
                      aria-current={entry.active ? 'page' : undefined}
                      className={`flex w-full cursor-pointer items-center gap-3 rounded-xl border p-3 text-left transition-colors focus-visible:shadow-focus ${
                        entry.active
                          ? 'border-line-strong bg-sand text-ink shadow-clay'
                          : 'border-transparent text-ink-alt hover:bg-sand/60 hover:text-ink'
                      }`}
                    >
                      <span
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                          entry.active ? 'bg-mocha text-surface' : 'bg-canvas-alt text-mocha'
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-semibold leading-tight">{entry.title}</span>
                        <span className={`block truncate text-xs ${entry.active ? 'text-ink' : 'text-ink-alt'}`}>
                          {entry.subtitle}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            ))}
          </nav>
        </div>

        {/* Live environment status */}
        <div className="well mt-6 space-y-1.5 p-3" aria-label="System status">
          <div className="flex items-center gap-2 text-xs font-semibold text-ink">
            <Info className="h-4 w-4 shrink-0 text-warm" aria-hidden="true" />
            System status
          </div>
          <dl className="space-y-1 text-xs">
            {status.map((item) => (
              <div key={item.label} className="flex items-center justify-between gap-2">
                <dt className="text-ink-alt">{item.label}</dt>
                <dd
                  className={`font-semibold ${
                    item.tone === 'success' ? 'text-success' : item.tone === 'danger' ? 'text-danger' : 'text-warm-strong'
                  }`}
                >
                  {item.value}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </aside>
    </>
  );
};
