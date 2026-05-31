export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        dep: {
          bg: '#060E1A',
          secondary: '#0A2540',
          card: '#0D1F35',
          hover: '#122D4A',
          border: '#1A3A5C',
          accent: '#00D4AA',
          'accent-dim': '#00D4AA66',
          text: '#E8EDF3',
          muted: '#7B8FA3',
          critical: '#FF4757',
          high: '#FF6B35',
          medium: '#FFA502',
          low: '#54A0FF',
          safe: '#00D4AA',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['DM Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
