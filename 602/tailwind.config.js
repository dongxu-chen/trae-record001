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
        bg: {
          primary: '#1a1a2e',
          secondary: '#16213e',
          tertiary: '#0f3460',
        },
        accent: {
          primary: '#e94560',
          secondary: '#00d9ff',
          success: '#00ff88',
        },
        text: {
          primary: '#ffffff',
          secondary: '#a0aec0',
          muted: '#718096',
        },
        border: {
          primary: '#2d3748',
          hover: '#4a5568',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
