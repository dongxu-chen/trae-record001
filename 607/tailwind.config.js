/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: '1rem',
        sm: '2rem',
        lg: '4rem',
        xl: '5rem',
        '2xl': '6rem',
      },
    },
    extend: {
      colors: {
        primary: {
          50: '#f0f5fa',
          100: '#d9e5f2',
          200: '#b3cae5',
          300: '#7ea7d2',
          400: '#477fb8',
          500: '#1e3a5f',
          600: '#1a3352',
          700: '#152a43',
          800: '#102034',
          900: '#0a1522',
        },
        accent: {
          50: '#faf6ed',
          100: '#f3e8c8',
          200: '#e7d191',
          300: '#d4a855',
          400: '#c9963d',
          500: '#b88430',
          600: '#9a6b27',
          700: '#7a5320',
          800: '#5a3d18',
          900: '#3a2710',
        },
        data: {
          blue: '#3b82f6',
          teal: '#14b8a6',
          green: '#22c55e',
          orange: '#f97316',
          red: '#ef4444',
          purple: '#8b5cf6',
        }
      },
      fontFamily: {
        display: ['Cormorant Garamond', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      backgroundImage: {
        'grid-pattern': "linear-gradient(rgba(30, 58, 95, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(30, 58, 95, 0.05) 1px, transparent 1px)",
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
};
