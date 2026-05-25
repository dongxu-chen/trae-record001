/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        display: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        space: {
          50: "#e6f1ff",
          100: "#b3d4ff",
          200: "#80b7ff",
          300: "#4d9aff",
          400: "#1a7dff",
          500: "#0a2463",
          600: "#081c4f",
          700: "#06153b",
          800: "#040e27",
          900: "#020713",
          950: "#01040a",
        },
        cyber: {
          50: "#e6fffc",
          100: "#b3fff3",
          200: "#80ffea",
          300: "#4dffe1",
          400: "#1affd8",
          500: "#00f5d4",
          600: "#00c4aa",
          700: "#00937f",
          800: "#006255",
          900: "#00312a",
        },
        neon: {
          pink: "#ec4899",
          amber: "#f59e0b",
          red: "#ef4444",
          green: "#22c55e",
          blue: "#3b82f6",
        },
      },
      boxShadow: {
        "cyber-glow": "0 0 20px rgba(0, 245, 212, 0.3)",
        "cyber-glow-sm": "0 0 10px rgba(0, 245, 212, 0.2)",
        "pink-glow": "0 0 20px rgba(236, 72, 153, 0.3)",
        "amber-glow": "0 0 15px rgba(245, 158, 11, 0.4)",
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(0, 245, 212, 0.2)' },
          '100%': { boxShadow: '0 0 20px rgba(0, 245, 212, 0.5)' },
        },
      },
    },
  },
  plugins: [],
};
