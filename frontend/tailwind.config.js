/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070b14",
          900: "#0b1220",
          850: "#0f1729",
          800: "#141d33",
          700: "#1e293f",
          600: "#2b3852",
        },
        attention: {
          DEFAULT: "#f5a524",
          soft: "#fbbf24",
          deep: "#b45309",
        },
        neutralc: {
          DEFAULT: "#22d3ee",
          soft: "#67e8f9",
        },
        risk: "#f43f5e",
        gain: "#34d399",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glass: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 12px 40px -12px rgba(0,0,0,0.6)",
        glow: "0 0 0 1px rgba(245,165,36,0.25), 0 0 32px -4px rgba(245,165,36,0.35)",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { boxShadow: "0 0 0 0 rgba(244,63,94,0.5)" },
          "70%": { boxShadow: "0 0 0 12px rgba(244,63,94,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(244,63,94,0)" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-ring": "pulse-ring 2s cubic-bezier(0.4,0,0.6,1) infinite",
        "fade-up": "fade-up 0.4s ease-out",
      },
    },
  },
  plugins: [],
};
