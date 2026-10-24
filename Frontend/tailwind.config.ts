import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        dark: {
          bg: "#080A0F",
          panel: "#0D111A",
          card: "#121724",
          surface: "#171D2D",
          hover: "#1D2438",
          border: "#1C2436",
          "border-subtle": "#141A28",
          text: "#F1F5F9",
          muted: "#94A3B8",
          dim: "#64748B",
        },
        brand: {
          50: "#EEF2FF",
          100: "#E0E7FF",
          400: "#818CF8",
          500: "#5E6AD2",
          600: "#4F59C7",
          700: "#434BA6",
          900: "#2B2F6E",
          950: "#1A1D47",
        },
        storm: {
          bg: "#10171B",
          conversation: "#151E23",
          surface: "#202C32",
          hover: "#2A3940",
          border: "#3A4A50",
          text: "#EDF1EE",
          secondary: "#ADBAB9",
          sage: "#C3D1B8",
          "sage-hover": "#D5DFCD",
          "sage-text": "#17201C",
          focus: "#AEC8D0",
          success: "#A7C4A2",
          warning: "#DDC38A",
          error: "#E3A29E",
        },
      },
      fontFamily: {
        syne: ["var(--font-syne)", "Syne", "sans-serif"],
        sans: ["'Uncut Sans'", "var(--font-sans)", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["var(--font-mono)", "'IBM Plex Mono'", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
