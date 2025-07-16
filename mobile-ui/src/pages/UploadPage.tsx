import React from 'react';

interface UploadPageProps {
  apiStatus?: string;
  isTestingAPI?: boolean;
  onTestAPI?: () => Promise<void>;
  onScanInvoice?: () => void;
}

export const UploadPage: React.FC<UploadPageProps> = ({
  apiStatus = 'Ready to Connect',
  isTestingAPI = false,
  onTestAPI,
  onScanInvoice
}) => {
  return (
    <div style={{
      padding: '2rem',
      minHeight: '100vh',
      background: 'var(--color-background)',
      color: 'var(--color-text)'
    }}>
      {/* Header */}
      <div style={{
        background: 'var(--color-primary)',
        color: 'white',
        padding: '1.5rem',
        borderRadius: 'var(--radius-xl)',
        textAlign: 'center',
        marginBottom: '2rem'
      }}>
        <h1 style={{ fontSize: '2rem', margin: 0 }}>🕉️ Vritti</h1>
        <p style={{ margin: '0.5rem 0 0 0', opacity: 0.9 }}>AI Invoice Processing</p>
      </div>

      {/* Main Content */}
      <div style={{
        background: 'var(--color-surface)',
        borderRadius: 'var(--radius-xl)',
        padding: '2rem',
        boxShadow: 'var(--shadow-lg)',
        textAlign: 'center'
      }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>📱</div>
        <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>Vritti Mobile App</h2>
        <p style={{ color: 'var(--color-textSecondary)', marginBottom: '2rem' }}>
          AI-powered invoice processing with camera scanning
        </p>

        {/* API Status */}
        <div style={{
          background: 'var(--color-background)',
          padding: '1rem',
          borderRadius: 'var(--radius-lg)',
          marginBottom: '2rem'
        }}>
          <p style={{ margin: 0 }}>
            API Status: <strong style={{ color: 'var(--color-primary)' }}>{apiStatus}</strong>
          </p>
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '400px', margin: '0 auto' }}>
          <button
            onClick={onScanInvoice}
            style={{
              background: 'var(--color-success)',
              color: 'white',
              padding: '1rem 2rem',
              borderRadius: 'var(--radius-lg)',
              border: 'none',
              fontSize: '1.1rem',
              fontWeight: 'bold',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            📷 Scan Invoice
          </button>

          <button
            onClick={onTestAPI}
            disabled={isTestingAPI}
            style={{
              background: 'var(--color-primary)',
              color: 'white',
              padding: '0.75rem 2rem',
              borderRadius: 'var(--radius-lg)',
              border: 'none',
              cursor: isTestingAPI ? 'not-allowed' : 'pointer',
              opacity: isTestingAPI ? 0.7 : 1
            }}
          >
            {isTestingAPI ? '🔄 Testing...' : '🔗 Test API Connection'}
          </button>
        </div>
      </div>
    </div>
  );
};