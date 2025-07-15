// src/components/DarkModeToggle.js
import React from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { Sun, Moon } from 'lucide-react';

const DarkModeToggle = () => {
  const { isDarkMode, toggleDarkMode } = useTheme();

  const colors = {
    light: {
      bg: '#ffffff',
      border: '#ced4da',
      icon: '#f59e0b'
    },
    dark: {
      bg: '#2d2d30',
      border: '#464647',
      icon: '#fbbf24'
    }
  };

  const currentColors = isDarkMode ? colors.dark : colors.light;

  return (
    <button
      onClick={toggleDarkMode}
      className="dark-mode-toggle"
      style={{
        position: 'fixed',
        bottom: '2rem',
        right: '2rem',
        width: '48px',
        height: '48px',
        borderRadius: '4px',
        backgroundColor: currentColors.bg,
        border: `1px solid ${currentColors.border}`,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '0 2px 6px rgba(0, 0, 0, 0.12)',
        transition: 'all 0.2s ease',
        zIndex: 100
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = '0 2px 6px rgba(0, 0, 0, 0.12)';
      }}
      title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
      aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDarkMode ? (
        <Sun size={20} color={currentColors.icon} />
      ) : (
        <Moon size={20} color={currentColors.icon} />
      )}
    </button>
  );
};

export default DarkModeToggle;