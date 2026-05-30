/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        brand: {
          dark: '#0F172A',
          deeper: '#060D1B',
          cyan: '#06D6A0',
          'cyan-dim': '#04A87D',
          orange: '#FF6B35',
          'orange-dim': '#CC5529',
          blue: '#3B82F6',
          purple: '#8B5CF6',
          surface: '#1E293B',
          'surface-light': '#334155',
          border: '#2D3B4F',
        },
      },
      fontFamily: {
        orbitron: ['Orbitron', 'monospace'],
        body: ['Noto Sans SC', 'sans-serif'],
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'count-up': 'countUp 0.3s ease-out',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 5px rgba(6, 214, 160, 0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(6, 214, 160, 0.6)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
