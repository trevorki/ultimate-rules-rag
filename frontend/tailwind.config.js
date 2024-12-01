/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      keyframes: {
        'typing-dot': {
          '0%, 100%': { opacity: '.2' },
          '50%': { opacity: '1' },
        },
      },
      animation: {
        'typing-dot': 'typing-dot 1s infinite ease-in-out',
      },
    },
  },
  plugins: [],
}