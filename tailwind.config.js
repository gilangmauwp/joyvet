/** @type {import('tailwindcss').Config} */
module.exports = {
  // Class-based dark mode — toggled by Alpine.js on <html> element
  darkMode: 'class',

  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
    './apps/**/templates/**/*.html',
    './frontend/**/*.py',
  ],

  theme: {
    extend: {
      colors: {
        // Clinical teal — primary brand colour
        primary: {
          50:  '#f0fdf9',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
        // Amber — alerts and accent
        amber: {
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
        },
        // Danger
        danger: {
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
        },
        // Surface tokens (dark mode aware)
        surface: {
          card: '#ffffff',
          'card-dark': '#1e293b',
          dark: '#0f172a',
        },
      },

      fontFamily: {
        sans: ['DM Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['DM Mono', 'ui-monospace', 'monospace'],
      },

      borderRadius: {
        xl: '0.75rem',
        '2xl': '1rem',
      },

      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s infinite',
      },

      keyframes: {
        fadeIn:  { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideUp: { '0%': { transform: 'translateY(8px)', opacity: 0 },
                  '100%': { transform: 'translateY(0)', opacity: 1 } },
      },
    },
  },

  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
