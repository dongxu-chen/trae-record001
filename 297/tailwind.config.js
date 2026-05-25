/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e6f0ff',
          100: '#c9dfff',
          200: '#94bfff',
          300: '#5e9eff',
          400: '#2d7eff',
          500: '#165DFF',
          600: '#0e4ad9',
          700: '#0837b3',
          800: '#05278c',
          900: '#031a66',
        },
        ground: '#00B42A',
        vehicle: '#F53F3F',
        pedestrian: '#FF7D00',
      },
      fontFamily: {
        inter: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
