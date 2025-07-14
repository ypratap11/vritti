import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { themes, Theme, ThemeName } from '../../styles/themes.ts';

interface ThemeContextType {
  currentTheme: Theme;
  themeName: ThemeName;
  setTheme: (themeName: ThemeName) => void;
  isTransitioning: boolean;
  availableThemes: ThemeName[];
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: ThemeName;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  defaultTheme = 'zen'
}) => {
  const [themeName, setThemeName] = useState<ThemeName>(defaultTheme);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Load saved theme from localStorage
  useEffect(() => {
    const savedTheme = localStorage.getItem('vritti-theme') as ThemeName;
    if (savedTheme && themes[savedTheme]) {
      setThemeName(savedTheme);
    }
  }, []);

  // Apply CSS custom properties when theme changes
  useEffect(() => {
    const root = document.documentElement;
    const theme = themes[themeName];

    // Set CSS custom properties for colors
    Object.entries(theme.colors).forEach(([key, value]) => {
      root.style.setProperty(`--color-${key}`, value);
    });

    // Set spacing variables
    Object.entries(theme.spacing).forEach(([key, value]) => {
      root.style.setProperty(`--spacing-${key}`, value);
    });

    // Set border radius variables
    Object.entries(theme.borderRadius).forEach(([key, value]) => {
      root.style.setProperty(`--radius-${key}`, value);
    });

    // Set shadow variables
    Object.entries(theme.shadows).forEach(([key, value]) => {
      root.style.setProperty(`--shadow-${key}`, value);
    });

    // Add theme class to body
    document.body.className = document.body.className.replace(/theme-\w+/g, '');
    document.body.classList.add(`theme-${themeName}`);

  }, [themeName]);

  const setTheme = (newTheme: ThemeName) => {
    setIsTransitioning(true);

    // Save to localStorage
    localStorage.setItem('vritti-theme', newTheme);

    // Smooth transition
    setTimeout(() => {
      setThemeName(newTheme);
      setTimeout(() => setIsTransitioning(false), 300);
    }, 100);
  };

  const value: ThemeContextType = {
    currentTheme: themes[themeName],
    themeName,
    setTheme,
    isTransitioning,
    availableThemes: Object.keys(themes) as ThemeName[]
  };

  return (
    <ThemeContext.Provider value={value}>
      <div className={`theme-root theme-${themeName} ${isTransitioning ? 'theme-transitioning' : ''}`}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};