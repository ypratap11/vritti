import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface Theme {
  name: string;
  primary: string;
  secondary: string;
  accent: string;
  bg: string;
}

const themes: Theme[] = [
  {
    name: 'Zen Garden',
    primary: 'from-green-500 to-blue-600',
    secondary: 'from-green-50 to-blue-50',
    accent: 'green',
    bg: 'from-slate-50 via-green-50 to-blue-50'
  },
  {
    name: 'Sunset Vibes',
    primary: 'from-orange-500 to-pink-600',
    secondary: 'from-orange-50 to-pink-50',
    accent: 'orange',
    bg: 'from-orange-50 via-pink-50 to-red-50'
  },
  // ... more themes
];

interface ThemeContextType {
  currentTheme: Theme;
  setTheme: (theme: Theme) => void;
  themes: Theme[];
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currentTheme, setCurrentTheme] = useState(themes[0]);

  return (
    <ThemeContext.Provider value={{ currentTheme, setTheme: setCurrentTheme, themes }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};