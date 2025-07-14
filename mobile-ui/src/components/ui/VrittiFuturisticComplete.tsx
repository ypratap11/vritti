import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { UploadPage } from '../../pages/UploadPage.tsx';
import { ApprovalPage } from '../../pages/ApprovalPage.tsx';
import { AnalyticsPage } from '../../pages/AnalyticsPage.tsx';
import { ThemeCustomizer } from './ThemeCustomizer.tsx';

interface VrittiFuturisticCompleteProps {
  apiStatus: string;
  isTestingAPI: boolean;
  onTestAPI: () => Promise<void>;
  onScanInvoice: () => void;
}

export const VrittiFuturisticComplete: React.FC<VrittiFuturisticCompleteProps> = ({
  apiStatus,
  isTestingAPI,
  onTestAPI,
  onScanInvoice
}) => {
  return (
    <Router>
      <div className="min-h-screen">
        <Routes>
          <Route path="/" element={
            <UploadPage
              apiStatus={apiStatus}
              isTestingAPI={isTestingAPI}
              onTestAPI={onTestAPI}
              onScanInvoice={onScanInvoice}
            />
          } />
          <Route path="/approval" element={<ApprovalPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Routes>
      </div>
    </Router>
  );
};