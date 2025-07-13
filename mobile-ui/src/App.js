import React, { useState } from 'react';
import './App.css';

function App() {
  const [apiStatus, setApiStatus] = useState('Ready to Connect');
  const [isTestingAPI, setIsTestingAPI] = useState(false);

  const testAPI = async () => {
    setIsTestingAPI(true);
    setApiStatus('Testing...');

    try {
      const response = await fetch('http://192.168.4.185:8001/api/v1/mobile/dashboard');
      const data = await response.json();

      if (data.status === 'healthy') {
        setApiStatus('✅ Connected to Vritti Backend!');
      } else {
        setApiStatus('❌ Backend Error');
      }
    } catch (error) {
      setApiStatus('❌ Connection Failed');
    }

    setIsTestingAPI(false);
  };

  const scanInvoice = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment'; // Use back camera on mobile
    input.onchange = async (event) => {
      const file = event.target.files[0];
      if (file) {
        await processInvoice(file);
      }
    };
    input.click();
  };

  const processInvoice = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://192.168.4.185:8001/api/v1/mobile/process-invoice', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.success) {
        alert(`🎉 Invoice Processed!\n\nVendor: ${result.extracted_data?.vendor_info?.name || 'Unknown'}\nAmount: ${result.extracted_data?.totals?.total_amount || 'Unknown'}\nConfidence: ${(result.confidence_score * 100).toFixed(1)}%`);
      } else {
        alert(`❌ Processing failed: ${result.message}`);
      }
    } catch (error) {
      alert(`❌ Error: ${error.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-blue-600 text-white p-6">
        <h1 className="text-2xl font-bold text-center">🕉️ Vritti</h1>
        <p className="text-center opacity-90">AI Invoice Processing</p>
      </div>

      {/* Content */}
      <div className="p-6">
        <div className="bg-white rounded-xl shadow-lg p-6 text-center">
          <div className="text-6xl mb-4">📱</div>
          <h2 className="text-xl font-bold mb-4">Vritti Mobile App</h2>
          <p className="text-gray-600 mb-6">
            AI-powered invoice processing with camera scanning
          </p>

          {/* API Status */}
          <div className="bg-gray-50 p-4 rounded-xl mb-6">
            <p className="text-sm text-gray-600">
              API Status: <span className="text-blue-600 font-semibold">{apiStatus}</span>
            </p>
          </div>

          {/* Action Buttons */}
          <div className="space-y-4">
            {/* Camera Scan Button - Primary Action */}
            <button
              onClick={scanInvoice}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-4 px-6 rounded-xl transition-all text-lg"
            >
              📷 Scan Invoice
            </button>

            {/* Test API Button */}
            <button
              onClick={testAPI}
              disabled={isTestingAPI}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-xl transition-all"
            >
              {isTestingAPI ? '🔄 Testing...' : '🔗 Test API Connection'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;