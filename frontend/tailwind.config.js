/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#faf5ff",
          100: "#f3e8ff",
          200: "#e9d5ff",
          300: "#d8b4fe",
          400: "#c084fc",
          500: "#a855f7",
          600: "#9333ea",
          700: "#7e22ce",
          800: "#6b21a8",
          900: "#581c87",
        },
        surface: {
          50:  "rgb(var(--s50)  / <alpha-value>)",
          100: "rgb(var(--s100) / <alpha-value>)",
          200: "rgb(var(--s200) / <alpha-value>)",
          300: "rgb(var(--s300) / <alpha-value>)",
          400: "rgb(var(--s400) / <alpha-value>)",
          500: "rgb(var(--s500) / <alpha-value>)",
          600: "rgb(var(--s600) / <alpha-value>)",
          700: "rgb(var(--s700) / <alpha-value>)",
          800: "rgb(var(--s800) / <alpha-value>)",
          900: "rgb(var(--s900) / <alpha-value>)",
          950: "rgb(var(--s950) / <alpha-value>)",
        },
        accent: {
          pink: "#ec4899",
          blue: "#3b82f6",
          cyan: "#06b6d4",
          amber: "#f59e0b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "slide-up": "slide-up 0.3s ease-out",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(168, 85, 247, 0.4)" },
          "50%": { boxShadow: "0 0 20px 4px rgba(168, 85, 247, 0.2)" },
        },
        "slide-up": {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};
