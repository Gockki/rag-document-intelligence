// contexts/ThemeContext.js
import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Tarkista tallennettu teema
    const saved = localStorage.getItem('darkMode');
    if (saved !== null) {
      return JSON.parse(saved);
    }
    // Tai käytä järjestelmän teemaa
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    // Tallenna valinta
    localStorage.setItem('darkMode', JSON.stringify(isDarkMode));
    
    // Päivitä body-luokka
    if (isDarkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    setIsDarkMode(prev => !prev);
  };

  // Dark Mode CSS
  const darkModeStyles = `
    /* Dark Mode Variables */
    :root {
      --bg-primary: #ffffff;
      --bg-secondary: #f9fafb;
      --bg-tertiary: #f3f4f6;
      --text-primary: #111827;
      --text-secondary: #4b5563;
      --text-tertiary: #6b7280;
      --border-color: #e5e7eb;
      --shadow-color: rgba(0, 0, 0, 0.1);
      --accent-blue: #3b82f6;
      --accent-blue-dark: #2563eb;
      --success-color: #10b981;
      --error-color: #ef4444;
      --code-bg: #f3f4f6;
    }

    body.dark-mode {
      --bg-primary: #111827;
      --bg-secondary: #1f2937;
      --bg-tertiary: #374151;
      --text-primary: #f9fafb;
      --text-secondary: #d1d5db;
      --text-tertiary: #9ca3af;
      --border-color: #374151;
      --shadow-color: rgba(0, 0, 0, 0.3);
      --accent-blue: #60a5fa;
      --accent-blue-dark: #3b82f6;
      --success-color: #34d399;
      --error-color: #f87171;
      --code-bg: #1f2937;
    }

    /* Apply dark mode to all elements */
    body.dark-mode {
      background-color: var(--bg-primary);
      color: var(--text-primary);
    }

    body.dark-mode .min-h-screen {
      background: linear-gradient(135deg, #111827 0%, #1f2937 50%, #111827 100%) !important;
    }

    body.dark-mode .header {
      background-color: var(--bg-secondary) !important;
      border-bottom-color: var(--border-color) !important;
    }

    body.dark-mode .card {
      background-color: var(--bg-secondary) !important;
      border-color: var(--border-color) !important;
      color: var(--text-primary) !important;
    }

    body.dark-mode .message {
      background-color: var(--bg-secondary) !important;
      border-color: var(--border-color) !important;
      color: var(--text-primary) !important;
    }

    body.dark-mode .message.user {
      background-color: #1e40af !important;
      color: white !important;
    }

    body.dark-mode input,
    body.dark-mode textarea {
      background-color: var(--bg-tertiary) !important;
      color: var(--text-primary) !important;
      border-color: var(--border-color) !important;
    }

    body.dark-mode button {
      background-color: var(--bg-tertiary) !important;
      color: var(--text-primary) !important;
      border-color: var(--border-color) !important;
    }

    body.dark-mode .sidebar {
      background-color: var(--bg-secondary) !important;
    }
  `;

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleDarkMode }}>
      <style>{darkModeStyles}</style>
      {children}
    </ThemeContext.Provider>
  );
};