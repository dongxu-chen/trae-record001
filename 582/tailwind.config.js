export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: { center: true },
    extend: {
      colors: {
        dark: { 900: '#0a0a0f', 800: '#12121a', 700: '#1a1a2e', 600: '#2a2a3e' },
        gold: { 400: '#e8c36a', 500: '#d4a853', 600: '#b8923e', 700: '#9a7a2f' },
        crimson: { 500: '#8b2252', 600: '#6e1a40' },
        parchment: { 100: '#faf3e6', 200: '#f5e6c8', 300: '#e8d5a8' },
      },
      fontFamily: {
        cinzel: ['Cinzel', 'serif'],
        crimson: ['Crimson Text', 'serif'],
        rajdhani: ['Rajdhani', 'sans-serif'],
      },
      animation: {
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        glow: { '0%': { boxShadow: '0 0 5px #d4a853, 0 0 10px #d4a853' }, '100%': { boxShadow: '0 0 20px #d4a853, 0 0 30px #d4a853' } },
        float: { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-5px)' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
    },
  },
  plugins: [],
};
