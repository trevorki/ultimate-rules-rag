import React from 'react';
import { useTheme } from '../contexts/ThemeContext';
import ThemeToggle from './ThemeToggle';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { isDarkMode, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen chat-background-light dark:chat-background-dark">
      <div className="fixed top-4 left-4 z-50">
        <ThemeToggle isDarkMode={isDarkMode} onToggle={toggleTheme} />
      </div>
      {children}
    </div>
  );
};

export default Layout; 