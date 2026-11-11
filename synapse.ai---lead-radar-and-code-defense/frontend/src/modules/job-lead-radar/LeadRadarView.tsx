import React, { useState } from 'react';
import { JobChatbot } from './components/JobChatbot';
import { OutreachModal } from './components/OutreachModal';
import { JobLead } from './types';

export const LeadRadarView: React.FC = () => {
  const [selectedLeadForOutreach, setSelectedLeadForOutreach] = useState<JobLead | null>(null);

  return (
    <div className="space-y-5">
      <JobChatbot
        onDraftOutreach={(l) => setSelectedLeadForOutreach(l)}
      />

      <OutreachModal
        lead={selectedLeadForOutreach}
        isOpen={!!selectedLeadForOutreach}
        onClose={() => setSelectedLeadForOutreach(null)}
      />
    </div>
  );
};
