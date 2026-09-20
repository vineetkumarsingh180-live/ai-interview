import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { ActiveTab, SubView } from './components/LeftNavbar';
import { LeadsView } from './tab1-leads/LeadsView';
import { AssessmentView } from './tab2-assessment/AssessmentView';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
    },
  },
});

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('leads');
  const [activeSubView, setActiveSubView] = useState<SubView>('radar');

  return (
    <QueryClientProvider client={queryClient}>
      <Layout
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeSubView={activeSubView}
        setActiveSubView={setActiveSubView}
      >
        {activeTab === 'leads' ? (
          <LeadsView />
        ) : (
          <AssessmentView
            activeSubView={activeSubView}
            setActiveSubView={setActiveSubView}
          />
        )}
      </Layout>
    </QueryClientProvider>
  );
}
