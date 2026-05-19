/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        surface: {
          light: '#ffffff',
          dark: '#1f2937',
        },
        text: {
          light: '#111827',
          dark: '#f9fafb',
        },
        muted: {
          light: '#6b7280',
          dark: '#9ca3af',
        },
        border: {
          light: '#e5e7eb',
          dark: '#374151',
        },
        hover: {
          light: '#f3f4f6',
          dark: '#374151',
        },
        card: {
          light: '#f9fafb',
          dark: '#374151',
        },
      }
    },
  },
  plugins: [],
}
