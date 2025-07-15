// src/contexts/ThemeContext.js
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
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(isDarkMode));
    
    if (isDarkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
  };

  // Professional dark mode styles
  const darkModeStyles = `
    /* Dark Mode Variables */
    body.dark-mode {
      --primary-dark: #0f0f0f;
      --primary: #1a1a1a;
      --accent: #5a9fd4;
      --bg-primary: #2d2d30;
      --bg-secondary: #252526;
      --bg-tertiary: #1e1e1e;
      --text-primary: #d4d4d4;
      --text-secondary: #cccccc;
      --text-muted: #858585;
      --border-light: #3e3e42;
      --border-medium: #464647;
      --success: #4ec9b0;
      --warning: #dcdcaa;
      --danger: #f48771;
      --info: #3794ff;
    }

    /* Dark Mode Base Styles */
    body.dark-mode {
      background-color: var(--bg-tertiary);
      color: var(--text-primary);
    }

    /* Header in dark mode */
    body.dark-mode header {
      background-color: var(--primary-dark) !important;
      border-bottom: 1px solid var(--border-light);
    }

    /* Cards in dark mode */
    body.dark-mode .card,
    body.dark-mode > div > div > div > div[style*="background: white"] {
      background-color: var(--bg-primary) !important;
      border-color: var(--border-light) !important;
      color: var(--text-primary) !important;
    }

    /* Main chat area */
    body.dark-mode > div > div > div > div[style*="background: white"][style*="flexDirection: column"] {
      background-color: var(--bg-primary) !important;
      border-color: var(--border-light) !important;
    }

    /* Chat header */
    body.dark-mode div[style*="borderBottom"][style*="padding: 1rem"] {
      background-color: var(--bg-secondary) !important;
      border-color: var(--border-light) !important;
    }

    /* Input area background */
    body.dark-mode div[style*="borderTop"][style*="padding: 1rem"] {
      background-color: var(--bg-secondary) !important;
      border-color: var(--border-light) !important;
    }

    /* All text elements */
    body.dark-mode h1,
    body.dark-mode h2,
    body.dark-mode h3,
    body.dark-mode p,
    body.dark-mode span,
    body.dark-mode div {
      color: var(--text-primary);
    }

    /* Muted text */
    body.dark-mode span[style*="color: rgb(108, 117, 125)"],
    body.dark-mode div[style*="color: rgb(108, 117, 125)"] {
      color: var(--text-muted) !important;
    }

    /* Secondary text */
    body.dark-mode span[style*="color: rgb(73, 80, 87)"],
    body.dark-mode div[style*="color: rgb(73, 80, 87)"] {
      color: var(--text-secondary) !important;
    }

    /* Input fields */
    body.dark-mode input,
    body.dark-mode textarea,
    body.dark-mode select {
      background-color: var(--bg-tertiary) !important;
      color: var(--text-primary) !important;
      border-color: var(--border-medium) !important;
    }

    body.dark-mode input:focus,
    body.dark-mode textarea:focus,
    body.dark-mode select:focus {
      border-color: var(--accent) !important;
      box-shadow: 0 0 0 2px rgba(90, 159, 212, 0.2) !important;
    }

    /* Buttons */
    body.dark-mode button {
      color: var(--text-primary);
    }

    body.dark-mode button[style*="background: rgb(15, 76, 129)"] {
      background-color: var(--accent) !important;
    }

    body.dark-mode button[style*="background: rgb(15, 76, 129)"]:hover {
      background-color: #4a8fc4 !important;
    }

    body.dark-mode button[style*="border: 1px solid"] {
      border-color: var(--border-medium) !important;
      background-color: var(--bg-secondary) !important;
      color: var(--text-primary) !important;
    }

    /* Upload area */
    body.dark-mode div[style*="border: 2px dashed"] {
      border-color: var(--border-medium) !important;
      background-color: var(--bg-tertiary) !important;
    }

    body.dark-mode div[style*="border: 2px dashed"]:hover {
      border-color: var(--accent) !important;
      background-color: var(--bg-secondary) !important;
    }

    /* Chat messages */
    body.dark-mode div[style*="background: rgb(248, 249, 250)"] {
      background-color: var(--bg-secondary) !important;
      border-color: var(--border-light) !important;
    }

    /* System messages */
    body.dark-mode div[style*="display: flex"][style*="background: rgb(248, 249, 250)"] {
      background-color: var(--bg-secondary) !important;
      border-color: var(--border-light) !important;
      color: var(--text-secondary) !important;
    }

    /* Assistant messages */
    body.dark-mode div[style*="maxWidth: 75%"] > div[style*="background: rgb(248, 249, 250)"] {
      background-color: var(--bg-secondary) !important;
      border-color: var(--border-light) !important;
      color: var(--text-primary) !important;
    }

    /* User messages stay blue */
    body.dark-mode div[style*="background: rgb(15, 76, 129)"] {
      background-color: var(--accent) !important;
      color: white !important;
    }

    /* Sources section */
    body.dark-mode div[style*="background: rgb(233, 236, 239)"] {
      background-color: var(--bg-tertiary) !important;
      color: var(--text-primary) !important;
    }

    /* Dropdown menus */
    body.dark-mode div[style*="position: absolute"][style*="background: white"] {
      background-color: var(--bg-primary) !important;
      border-color: var(--border-light) !important;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5) !important;
    }

    /* Chat session items */
    body.dark-mode div[style*="backgroundColor: rgb(219, 234, 254)"] {
      background-color: rgba(90, 159, 212, 0.2) !important;
      border-color: var(--accent) !important;
    }

    body.dark-mode div[style*="backgroundColor: rgb(249, 250, 251)"] {
      background-color: var(--bg-secondary) !important;
    }

    /* File items */
    body.dark-mode div[style*="background: rgb(248, 249, 250)"][style*="borderRadius: 3px"] {
      background-color: var(--bg-secondary) !important;
      border-color: var(--border-light) !important;
    }

    /* Loading spinner */
    body.dark-mode div[style*="border: 3px solid rgb(233, 236, 239)"] {
      border-color: var(--border-medium) !important;
      border-top-color: var(--accent) !important;
    }

    /* Icons color fix */
    body.dark-mode svg {
      color: currentColor;
    }

    /* Scrollbar */
    body.dark-mode ::-webkit-scrollbar {
      background-color: var(--bg-tertiary);
    }

    body.dark-mode ::-webkit-scrollbar-track {
      background-color: var(--bg-tertiary);
    }

    body.dark-mode ::-webkit-scrollbar-thumb {
      background-color: var(--border-medium);
      border-radius: 4px;
    }

    body.dark-mode ::-webkit-scrollbar-thumb:hover {
      background-color: var(--text-muted);
    }

    /* DocumentManager specific styles */
    body.dark-mode .document-item {
      background-color: var(--bg-secondary) !important;
      border-color: var(--border-light) !important;
      color: var(--text-primary) !important;
    }

    body.dark-mode .document-item:hover {
      background-color: var(--bg-tertiary) !important;
    }

    /* Transitions for smooth theme switching */
    body * {
      transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
    }
  `;

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleDarkMode }}>
      <style>{darkModeStyles}</style>
      {children}
    </ThemeContext.Provider>
  );
};