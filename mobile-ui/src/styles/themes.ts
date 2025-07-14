// 🎨 Vritti Theme System Types & Definitions

export interface Theme {
  name: string;
  colors: {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
    accent: string;
    success: string;
    warning: string;
    error: string;
    gradient: string;
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  borderRadius: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
  };
}

export const themes: Record<string, Theme> = {
  zen: {
    name: '🕉️ Zen Mode',
    colors: {
      primary: '#2563eb',
      secondary: '#f97316',
      background: '#f9fafb',
      surface: '#ffffff',
      text: '#1f2937',
      textSecondary: '#6b7280',
      accent: '#10b981',
      success: '#059669',
      warning: '#d97706',
      error: '#dc2626',
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    },
    spacing: {
      xs: '0.25rem',
      sm: '0.5rem',
      md: '1rem',
      lg: '1.5rem',
      xl: '2rem'
    },
    borderRadius: {
      sm: '0.25rem',
      md: '0.5rem',
      lg: '0.75rem',
      xl: '1rem'
    },
    shadows: {
      sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
      md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
      lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)'
    }
  },
  corporate: {
    name: '🏢 Corporate',
    colors: {
      primary: '#1e40af',
      secondary: '#dc2626',
      background: '#f8fafc',
      surface: '#ffffff',
      text: '#0f172a',
      textSecondary: '#475569',
      accent: '#059669',
      success: '#047857',
      warning: '#b45309',
      error: '#b91c1c',
      gradient: 'linear-gradient(135deg, #1e3a8a 0%, #3730a3 100%)'
    },
    spacing: {
      xs: '0.25rem',
      sm: '0.5rem',
      md: '1rem',
      lg: '1.5rem',
      xl: '2rem'
    },
    borderRadius: {
      sm: '0.125rem',
      md: '0.25rem',
      lg: '0.375rem',
      xl: '0.5rem'
    },
    shadows: {
      sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
      md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
      lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)'
    }
  },
  dark: {
    name: '🌙 Dark Mode',
    colors: {
      primary: '#3b82f6',
      secondary: '#f59e0b',
      background: '#0f172a',
      surface: '#1e293b',
      text: '#f1f5f9',
      textSecondary: '#94a3b8',
      accent: '#06d6a0',
      success: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444',
      gradient: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)'
    },
    spacing: {
      xs: '0.25rem',
      sm: '0.5rem',
      md: '1rem',
      lg: '1.5rem',
      xl: '2rem'
    },
    borderRadius: {
      sm: '0.25rem',
      md: '0.5rem',
      lg: '0.75rem',
      xl: '1rem'
    },
    shadows: {
      sm: '0 1px 2px 0 rgb(0 0 0 / 0.2)',
      md: '0 4px 6px -1px rgb(0 0 0 / 0.3)',
      lg: '0 10px 15px -3px rgb(0 0 0 / 0.4)'
    }
  },
  neon: {
    name: '⚡ Neon',
    colors: {
      primary: '#8b5cf6',
      secondary: '#06ffa5',
      background: '#000000',
      surface: '#1a1a2e',
      text: '#eee6ff',
      textSecondary: '#a78bfa',
      accent: '#ff006e',
      success: '#00f5ff',
      warning: '#ffbe0b',
      error: '#fb5607',
      gradient: 'linear-gradient(135deg, #8b5cf6 0%, #06ffa5 100%)'
    },
    spacing: {
      xs: '0.25rem',
      sm: '0.5rem',
      md: '1rem',
      lg: '1.5rem',
      xl: '2rem'
    },
    borderRadius: {
      sm: '0.25rem',
      md: '0.5rem',
      lg: '0.75rem',
      xl: '1rem'
    },
    shadows: {
      sm: '0 0 5px rgba(139, 92, 246, 0.3)',
      md: '0 0 15px rgba(139, 92, 246, 0.4)',
      lg: '0 0 30px rgba(139, 92, 246, 0.5)'
    }
  }
};

