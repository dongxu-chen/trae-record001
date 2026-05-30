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
        'brand-dark': '#0a0e17',
        'brand-surface': '#111827',
        'brand-card': '#1a1f2e',
        'brand-border': '#2a3040',
        'brand-cyan': '#00d4ff',
        'brand-amber': '#f59e0b',
        'brand-red': '#ef4444',
        'brand-green': '#10b981',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['DM Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      animation: {
        'alert-pulse': 'alert-pulse 2s ease-in-out infinite',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'fade-in-up': 'fade-in-up 0.4s ease-out',
        'pulse-glow-amber': 'pulse-glow-amber 2s ease-in-out infinite',
        'pulse-glow-red': 'pulse-glow-red 2s ease-in-out infinite',
        'fade-in': 'fade-in 0.2s ease-out',
        'slide-up': 'slide-up 0.3s ease-out',
      },
      keyframes: {
        'alert-pulse': {
          '0%, 100%': {
            opacity: '1',
            boxShadow: '0 0 0 0 rgba(239, 68, 68, 0.4)',
          },
          '50%': {
            opacity: '0.85',
            boxShadow: '0 0 0 8px rgba(239, 68, 68, 0)',
          },
        },
        'slide-in-right': {
          from: {
            transform: 'translateX(100%)',
            opacity: '0',
          },
          to: {
            transform: 'translateX(0)',
            opacity: '1',
          },
        },
        'fade-in-up': {
          from: {
            transform: 'translateY(12px)',
            opacity: '0',
          },
          to: {
            transform: 'translateY(0)',
            opacity: '1',
          },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: {
            transform: 'translateY(24px)',
            opacity: '0',
          },
          to: {
            transform: 'translateY(0)',
            opacity: '1',
          },
        },
        'pulse-glow-amber': {
          '0%, 100%': {
            boxShadow: '0 0 0 0 rgba(245, 158, 11, 0.3)',
          },
          '50%': {
            boxShadow: '0 0 12px 2px rgba(245, 158, 11, 0.15)',
          },
        },
        'pulse-glow-red': {
          '0%, 100%': {
            boxShadow: '0 0 0 0 rgba(239, 68, 68, 0.3)',
          },
          '50%': {
            boxShadow: '0 0 12px 2px rgba(239, 68, 68, 0.15)',
          },
        },
      },
    },
  },
  plugins: [],
};
