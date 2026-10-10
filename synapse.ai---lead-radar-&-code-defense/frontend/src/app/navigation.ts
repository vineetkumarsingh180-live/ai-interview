import { Radar, ShieldCheck, Mic, Trophy } from 'lucide-react';
import type { NavSection } from '@shared/layout/types';

/** Top-level product areas and the assessment sub-views. */
export type ActiveTab = 'leads' | 'assessment';
export type SubView = 'radar' | 'code-verifier' | 'voice-defense' | 'leaderboard';

interface NavState {
  activeTab: ActiveTab;
  activeSubView: SubView;
  go: (tab: ActiveTab, view: SubView) => void;
}

/** The navigation shown in the side bar. Element ids are kept stable for tests/automation. */
export function buildNavSections({ activeTab, activeSubView, go }: NavState): NavSection[] {
  const inAssessment = activeTab === 'assessment';
  return [
    {
      label: 'Lead radar',
      entries: [
        {
          id: 'nav-tab-leads',
          icon: Radar,
          title: 'Job Lead Radar',
          subtitle: 'Social ingest & outreach',
          active: activeTab === 'leads',
          onSelect: () => go('leads', 'radar'),
        },
      ],
    },
    {
      label: 'Assessment',
      entries: [
        {
          id: 'nav-tab-assessment',
          icon: ShieldCheck,
          title: 'Code Verifier',
          subtitle: 'Repository review',
          active: inAssessment && activeSubView === 'code-verifier',
          onSelect: () => go('assessment', 'code-verifier'),
        },
        {
          id: 'nav-subview-voice',
          icon: Mic,
          title: 'Voice Interview',
          subtitle: 'Spoken code defense',
          active: inAssessment && activeSubView === 'voice-defense',
          onSelect: () => go('assessment', 'voice-defense'),
        },
        {
          id: 'nav-subview-leaderboard',
          icon: Trophy,
          title: 'Leaderboard',
          subtitle: 'Assessment results',
          active: inAssessment && activeSubView === 'leaderboard',
          onSelect: () => go('assessment', 'leaderboard'),
        },
      ],
    },
  ];
}

export function getBreadcrumb(activeTab: ActiveTab, activeSubView: SubView): { section: string; page: string } {
  if (activeTab === 'leads') return { section: 'Job Lead Radar', page: 'Lead Stream' };
  const page =
    activeSubView === 'code-verifier' ? 'Code Verifier' : activeSubView === 'voice-defense' ? 'Voice Defense' : 'Leaderboard';
  return { section: 'Assessment Hub', page };
}
