/** @type {import('tailwindcss').Config */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'space-blue': '#0A1628',
        'cyber-cyan': '#00F5FF',
        'neon-purple': '#7B2FFD',
        'warning-orange': '#FF6B35',
      },
      fontFamily: {
        'orbitron': ['Orbitron', 'sans-serif'],
        'jetbrains': ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 5px #00F5FF, ' },
          '50%': { boxShadow: '0 0 20px #00F5FF, 0 0 30px #00F5FF' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [],
}
