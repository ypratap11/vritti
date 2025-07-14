// Add to your existing API utils

export const processInvoiceWithAR = async (imageData: string) => {
  const response = await fetch('/api/v1/mobile/process-invoice-ar', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ image: imageData }),
  });

  return response.json();
};

export const getRealtimeStats = async () => {
  const response = await fetch('/api/v1/analytics/realtime');
  return response.json();
};

export const approveInvoice = async (invoiceId: string) => {
  const response = await fetch(`/api/v1/invoices/${invoiceId}/approve`, {
    method: 'POST',
  });
  return response.json();
};

export const rejectInvoice = async (invoiceId: string, reason?: string) => {
  const response = await fetch(`/api/v1/invoices/${invoiceId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ reason }),
  });
  return response.json();
};