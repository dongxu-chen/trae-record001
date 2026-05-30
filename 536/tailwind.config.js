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
        monitor: {
          bg: '#0B1120',
          surface: '#111827',
          card: '#1A2332',
          border: '#1E2D3D',
          hover: '#243447',
          accent: '#06D6A0',
          'accent-dim': '#06D6A033',
          warning: '#FFB800',
          'warning-dim': '#FFB80033',
          danger: '#EF4444',
          'danger-dim': '#EF444433',
          info: '#3B82F6',
          'info-dim': '#3B82F633',
          text: '#E2E8F0',
          'text-dim': '#94A3B8',
          'text-muted': '#64748B',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Outfit', 'sans-serif'],
      }
    },
  },
  plugins: [],
};
