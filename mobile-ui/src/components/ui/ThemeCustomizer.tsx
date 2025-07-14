import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext.tsx';
import { themes, ThemeName } from '../../styles/themes.ts';

export const ThemeCustomizer: React.FC = () => {
  const { themeName, setTheme, availableThemes, isTransitioning } = useTheme();
  const [isOpen, setIsOpen] = useState<boolean>(false);

  const handleThemeChange = (newTheme: ThemeName): void => {
    setTheme(newTheme);
    setIsOpen(false);
  };

  const getThemeEmoji = (theme: ThemeName): string => {
    const emojis: Record<ThemeName, string> = {
      zen: '🕉️',
      corporate: '🏢',
      dark: '🌙',
      neon: '⚡'
    };
    return emojis[theme] || '🎨';
  };

  const getThemeDescription = (theme: ThemeName): string => {
    const descriptions: Record<ThemeName, string> = {
      zen: 'Calm, mindful interface',
      corporate: 'Professional business look',
      dark: 'Easy on the eyes',
      neon: 'Vibrant and futuristic'
    };
    return descriptions[theme] || '';
  };

  return (
    <div style={{
      position: 'fixed',
      top: '1rem',
      right: '1rem',
      zIndex: 1000
    }}>
      {/* Theme Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isTransitioning}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 1rem',
          background: 'var(--color-surface)',
          border: '2px solid var(--color-primary)',
          borderRadius: 'var(--radius-lg)',
          color: 'var(--color-text)',
          fontWeight: 600,
          cursor: isTransitioning ? 'not-allowed' : 'pointer',
          boxShadow: 'var(--shadow-md)',
          transition: 'all 0.2s ease',
          opacity: isTransitioning ? 0.7 : 1
        }}
        onMouseOver={(e) => {
          if (!isTransitioning) {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
            e.currentTarget.style.background = 'var(--color-primary)';
            e.currentTarget.style.color = 'white';
          }
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = 'var(--shadow-md)';
          e.currentTarget.style.background = 'var(--color-surface)';
          e.currentTarget.style.color = 'var(--color-text)';
        }}
      >
        {getThemeEmoji(themeName)}
        <span style={{ textTransform: 'capitalize' }}>{themeName}</span>
      </button>

      {/* Theme Selector Modal */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1001,
            animation: 'fadeIn 0.2s ease'
          }}
          onClick={() => setIsOpen(false)}
        >
          <div
            style={{
              background: 'var(--color-surface)',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-lg)',
              maxWidth: '90vw',
              maxHeight: '90vh',
              overflow: 'hidden',
              animation: 'slideIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: 'var(--spacing-lg)',
              borderBottom: '1px solid var(--color-textSecondary)'
            }}>
              <h3 style={{
                margin: 0,
                color: 'var(--color-text)',
                fontSize: '1.25rem'
              }}>
                🎨 Choose Your Theme
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  color: 'var(--color-textSecondary)',
                  padding: 'var(--spacing-xs)',
                  borderRadius: 'var(--radius-sm)',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'var(--color-error)';
                  e.currentTarget.style.color = 'white';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'none';
                  e.currentTarget.style.color = 'var(--color-textSecondary)';
                }}
              >
                ×
              </button>
            </div>

            {/* Theme Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 'var(--spacing-md)',
              padding: 'var(--spacing-lg)'
            }}>
              {availableThemes.map((theme) => (
                <div
                  key={theme}
                  style={{
                    position: 'relative',
                    cursor: 'pointer',
                    borderRadius: 'var(--radius-lg)',
                    overflow: 'hidden',
                    transition: 'all 0.2s ease',
                    border: `2px solid ${theme === themeName ? 'var(--color-primary)' : 'transparent'}`,
                    boxShadow: theme === themeName ? '0 0 0 4px rgba(37, 99, 235, 0.1)' : 'none'
                  }}
                  onClick={() => handleThemeChange(theme)}
                  onMouseOver={(e) => {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = theme === themeName ? '0 0 0 4px rgba(37, 99, 235, 0.1)' : 'none';
                  }}
                >
                  {/* Theme Preview */}
                  <div style={{
                    height: '120px',
                    background: themes[theme].colors.background
                  }}>
                    <div style={{
                      height: '30px',
                      background: themes[theme].colors.primary
                    }}></div>
                    <div style={{
                      padding: '0.5rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.25rem'
                    }}>
                      <div style={{
                        height: '40px',
                        background: themes[theme].colors.surface,
                        borderRadius: '4px',
                        border: `1px solid ${themes[theme].colors.textSecondary}`,
                        opacity: 0.8
                      }}></div>
                      <div style={{
                        height: '20px',
                        width: '60px',
                        background: themes[theme].colors.accent,
                        borderRadius: '4px',
                        opacity: 0.6
                      }}></div>
                    </div>
                  </div>

                  {/* Theme Info */}
                  <div style={{
                    padding: 'var(--spacing-md)',
                    background: 'var(--color-surface)'
                  }}>
                    <div style={{
                      fontWeight: 600,
                      fontSize: '0.9rem',
                      color: 'var(--color-text)',
                      textTransform: 'capitalize' as const
                    }}>
                      {getThemeEmoji(theme)} {theme}
                    </div>
                    <div style={{
                      fontSize: '0.75rem',
                      color: 'var(--color-textSecondary)',
                      marginTop: 'var(--spacing-xs)'
                    }}>
                      {getThemeDescription(theme)}
                    </div>
                  </div>

                  {/* Active Indicator */}
                  {theme === themeName && (
                    <div style={{
                      position: 'absolute',
                      top: 'var(--spacing-sm)',
                      right: 'var(--spacing-sm)',
                      background: 'var(--color-success)',
                      color: 'white',
                      borderRadius: '50%',
                      width: '24px',
                      height: '24px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.75rem',
                      fontWeight: 'bold'
                    }}>
                      ✓
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};