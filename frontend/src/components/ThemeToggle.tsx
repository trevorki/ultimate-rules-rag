import React from 'react';
import { FaSun, FaMoon } from 'react-icons/fa';

interface ThemeToggleProps {
  isDarkMode: boolean;
  onToggle: () => void;
}

const ThemeToggle: React.FC<ThemeToggleProps> = ({ isDarkMode, onToggle }) => {
  return (
    <button
      onClick={onToggle}
      className="p-2 rounded-full 
        header-footer-light dark:header-footer-dark
        text-light-theme dark:text-dark-theme
        hover:opacity-80 transition-opacity"
      aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDarkMode ? <FaSun size={20} /> : <FaMoon size={20} />}
    </button>
  );
};

export default ThemeToggle; 