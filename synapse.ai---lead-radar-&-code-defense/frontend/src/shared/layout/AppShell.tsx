import React, { ReactNode, useCallback, useEffect, useState } from 'react';
import { Menu } from 'lucide-react';
import { SideNav } from './SideNav';
import { useBackendStatus } from './useBackendStatus';
import type { NavSection } from './types';

interface AppShellProps {
  children: ReactNode;
  sections: NavSection[];
  breadcrumb: { section: string; page: string };
}

/** Application chrome: top bar, responsive navigation and the scrolling content area. */
export const AppShell: React.FC<AppShellProps> = ({ children, sections, breadcrumb }) => {
  const [isNavOpen, setIsNavOpen] = useState(false);
  const closeNav = useCallback(() => setIsNavOpen(false), []);
  const status = useBackendStatus();

  // Close the mobile drawer with Escape.
  useEffect(() => {
    if (!isNavOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closeNav();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isNavOpen, closeNav]);

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-canvas text-ink font-sans">
      <SideNav sections={sections} isOpen={isNavOpen} onClose={closeNav} status={status.items} />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="z-20 flex h-14 shrink-0 items-center justify-between gap-3 border-b border-line bg-canvas/90 px-4 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              id="open-nav-btn"
              onClick={() => setIsNavOpen(true)}
              className="btn btn-secondary btn-icon lg:hidden"
              aria-label="Open navigation menu"
              aria-expanded={isNavOpen}
              aria-controls="left-navbar"
            >
              <Menu className="h-5 w-5" />
            </button>
            <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-2 text-sm">
              <span className="hidden truncate text-ink-soft sm:inline">{breadcrumb.section}</span>
              <span className="hidden text-ink-soft sm:inline" aria-hidden="true">/</span>
              <span className="truncate font-semibold text-ink">{breadcrumb.page}</span>
            </nav>
          </div>

          {/* Live backend status; never a static "demo" claim. */}
          <span
            role="status"
            className={`badge shrink-0 ${
              status.summary.tone === 'success' ? 'badge-success' : status.summary.tone === 'danger' ? 'badge-danger' : 'badge-warm'
            }`}
            title={status.items.map((i) => `${i.label}: ${i.value}`).join(' · ')}
          >
            {status.summary.label}: {status.summary.value}
          </span>
        </header>

        <main className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6 lg:p-8">
          <div className="mx-auto w-full max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
};
