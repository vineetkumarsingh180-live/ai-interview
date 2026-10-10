import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from '@shared/layout/AppShell';
import { LeadRadarView } from '@modules/job-lead-radar';
import { AssessmentWorkspace } from './AssessmentWorkspace';
import { ActiveTab, SubView, buildNavSections, getBreadcrumb } from './navigation';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
    },
  },
});

/** Composition root of the UI: wires navigation, shared chrome and the four modules together. */
export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('leads');
  const [activeSubView, setActiveSubView] = useState<SubView>('radar');

  const sections = buildNavSections({
    activeTab,
    activeSubView,
    go: (tab, view) => {
      setActiveTab(tab);
      setActiveSubView(view);
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <AppShell sections={sections} breadcrumb={getBreadcrumb(activeTab, activeSubView)}>
        {activeTab === 'leads' ? (
          <LeadRadarView />
        ) : (
          <AssessmentWorkspace activeSubView={activeSubView} setActiveSubView={setActiveSubView} />
        )}
      </AppShell>
    </QueryClientProvider>
  );
}
