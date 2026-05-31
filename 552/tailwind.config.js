/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: {
        "2xl": "1280px",
      },
    },
    extend: {
      colors: {
        primary: {
          50: "#E8F1FF",
          100: "#D1E3FF",
          200: "#A8C7FF",
          300: "#7EABFF",
          400: "#558FFF",
          500: "#2B73FF",
          600: "#165DFF",
          700: "#0E4ACC",
          800: "#0A3799",
          900: "#062566",
          950: "#021233",
        },
        success: {
          50: "#E8FFF0",
          100: "#CFF7D8",
          200: "#9FEFB1",
          300: "#6FE78B",
          400: "#3FDF64",
          500: "#0FD73D",
          600: "#00B42A",
          700: "#009022",
          800: "#006C19",
          900: "#004811",
        },
        warning: {
          50: "#FFF5E8",
          100: "#FFEBD1",
          200: "#FFD6A3",
          300: "#FFC275",
          400: "#FFAD47",
          500: "#FF9919",
          600: "#FF7D00",
          700: "#CC6400",
          800: "#994B00",
          900: "#663200",
        },
        danger: {
          50: "#FFEBE8",
          100: "#FFD6D1",
          200: "#FFADA3",
          300: "#FF8575",
          400: "#FF5C47",
          500: "#F53F3F",
          600: "#F53F3F",
          700: "#CC3333",
          800: "#992626",
          900: "#661A1A",
        },
      },
      fontFamily: {
        sans: ["Noto Sans SC", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.4s ease-out",
        "slide-down": "slideDown 0.4s ease-out",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "gradient": "gradient 8s ease infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideDown: {
          "0%": { opacity: "0", transform: "translateY(-20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        gradient: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "hero-gradient": "linear-gradient(135deg, #165DFF 0%, #0E4ACC 50%, #0A3799 100%)",
        "card-gradient": "linear-gradient(135deg, #FFFFFF 0%, #F8FAFF 100%)",
      },
      boxShadow: {
        "card": "0 4px 20px rgba(22, 93, 255, 0.08)",
        "card-hover": "0 8px 30px rgba(22, 93, 255, 0.12)",
        "glow": "0 0 40px rgba(22, 93, 255, 0.2)",
      },
    },
  },
  plugins: [],
};
