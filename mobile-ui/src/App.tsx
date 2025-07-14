import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './components/contexts/ThemeContext.tsx';
import { ThemeCustomizer } from './components/ui/ThemeCustomizer.tsx';
import { VrittiFuturisticComplete } from './components/ui/VrittiFuturisticComplete.tsx';
import './styles/animations.css';

interface VrittiAppProps {}

const VrittiApp: React.FC<VrittiAppProps> = () => {
  const [apiStatus, setApiStatus] = useState<string>('Detecting backend...');
  const [isTestingAPI, setIsTestingAPI] = useState<boolean>(false);
  const [backendUrl, setBackendUrl] = useState<string>('');

  // Auto-detect available backend port on component mount
  useEffect(() => {
    detectBackendPort();
  }, []);

  const detectBackendPort = async (): Promise<void> => {
    const possibleUrls = [
      'http://localhost:8000',
      'http://localhost:8001',
      'http://192.168.4.185:8000',
      'http://192.168.4.185:8001'
    ];

    setApiStatus('🔍 Scanning for backend...');

    for (const url of possibleUrls) {
      try {
        const response = await fetch(`${url}/api/v1/mobile/dashboard`, {
          method: 'GET',
          signal: AbortSignal.timeout(3000) // 3 second timeout
        });

        if (response.ok) {
          const data = await response.json();
          if (data.status === 'healthy') {
            setBackendUrl(url);
            setApiStatus(`✅ Found backend at ${url}`);
            console.log(`🎉 Backend detected at: ${url}`);
            return;
          }
        }
      } catch (error) {
        // Continue to next URL
        console.log(`❌ No backend at ${url}`);
      }
    }

    // If no backend found
    setApiStatus('❌ No backend found on common ports');
    console.warn('⚠️ Backend not detected on ports 8000 or 8001');
  };

  const testAPI = async (): Promise<void> => {
    if (!backendUrl) {
      setApiStatus('❌ No backend URL detected');
      return;
    }

    setIsTestingAPI(true);
    setApiStatus('Testing connection...');

    try {
      const response = await fetch(`${backendUrl}/api/v1/mobile/dashboard`);
      const data = await response.json();

      if (data.status === 'healthy') {
        setApiStatus('✅ Connected to Vritti Backend!');
      } else {
        setApiStatus('❌ Backend Error');
      }
    } catch (error) {
      setApiStatus('❌ Connection Failed');
      // Try to re-detect backend
      await detectBackendPort();
    }

    setIsTestingAPI(false);
  };

  const scanInvoice = (): void => {
    if (!backendUrl) {
      alert('❌ No backend detected. Please start your backend server.');
      return;
    }

    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    input.onchange = async (event: any) => {
      const file = event.target.files?.[0];
      if (file) {
        await processInvoice(file);
      }
    };
    input.click();
  };

  const processInvoice = async (file: File): Promise<void> => {
    if (!backendUrl) {
      alert('❌ No backend detected. Please start your backend server.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${backendUrl}/api/v1/mobile/process-invoice`, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.success) {
        alert(`🎉 Invoice Processed!\n\nVendor: ${result.extracted_data?.vendor_info?.name || 'Unknown'}\nAmount: ${result.extracted_data?.totals?.total_amount || 'Unknown'}\nConfidence: ${(result.confidence_score * 100).toFixed(1)}%`);
      } else {
        alert(`❌ Processing failed: ${result.message}`);
      }
    } catch (error: any) {
      alert(`❌ Error: ${error.message}`);
      // Try to re-detect backend if request fails
      await detectBackendPort();
    }
  };

  // Manual refresh backend detection
  const refreshBackend = async (): Promise<void> => {
    await detectBackendPort();
  };

  return (
    <div
      className="App theme-root"
      style={{
        minHeight: '100vh',
        background: 'var(--color-background)',
        color: 'var(--color-text)',
        transition: 'all 0.3s ease'
      }}
    >
      {/* Theme Customizer - Fixed in top-right corner */}
      <ThemeCustomizer />

      {/* Backend status indicator */}
      <div style={{
        position: 'fixed',
        top: '1rem',
        left: '1rem',
        background: backendUrl ? 'var(--color-success)' : 'var(--color-error)',
        color: 'white',
        padding: '0.5rem 1rem',
        borderRadius: 'var(--radius-md)',
        fontSize: '0.75rem',
        fontWeight: 600,
        zIndex: 999,
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem'
      }}>
        <span>{backendUrl ? '🟢' : '🔴'}</span>
        <span>{backendUrl ? `Backend: ${backendUrl.split('//')[1]}` : 'No Backend'}</span>
        <button
          onClick={refreshBackend}
          style={{
            background: 'rgba(255,255,255,0.2)',
            border: 'none',
            borderRadius: '0.25rem',
            padding: '0.25rem 0.5rem',
            color: 'white',
            cursor: 'pointer',
            fontSize: '0.7rem'
          }}
          title="Refresh backend detection"
        >
          🔄
        </button>
      </div>

      {/* Your existing futuristic component */}
      <VrittiFuturisticComplete
        apiStatus={apiStatus}
        isTestingAPI={isTestingAPI}
        onTestAPI={testAPI}
        onScanInvoice={scanInvoice}
        backendUrl={backendUrl}
        onRefreshBackend={refreshBackend}
      />
    </div>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider defaultTheme="zen">
      <VrittiApp />
    </ThemeProvider>
  );
};

export default App;