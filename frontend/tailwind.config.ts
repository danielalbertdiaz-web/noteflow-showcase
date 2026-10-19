import type { Config } from "tailwindcss";
import plugin from "tailwindcss/plugin";

const config: Config = {
  content: [
    // App-router and pages-router under src/
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    // Root-level app/ and components/ (Next.js 14 app-router without src/)
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    // Shared lib (for class strings in utility files)
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ── Medical color palette ─────────────────────────────────────────────
      colors: {
        // Primary: teal-600 (#0D9488) — matches manifest theme_color
        primary: {
          DEFAULT: "#0D9488",
          50: "#F0FDFA",
          100: "#CCFBF1",
          200: "#99F6E4",
          300: "#5EEAD4",
          400: "#2DD4BF",
          500: "#14B8A6",
          600: "#0D9488",
          700: "#0F766E",
          800: "#115E59",
          900: "#134E4A",
          950: "#042F2E",
        },
        // Blue accents
        accent: {
          DEFAULT: "#3B82F6",
          50: "#EFF6FF",
          100: "#DBEAFE",
          200: "#BFDBFE",
          300: "#93C5FD",
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",
          700: "#1D4ED8",
          800: "#1E40AF",
          900: "#1E3A8A",
        },
        // Legacy brand palette (keep for backward compat)
        brand: {
          50: "#ecfeff",
          100: "#cffafe",
          200: "#a5f3fc",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
          700: "#0e7490",
          800: "#155e75",
          900: "#164e63",
          950: "#083344",
        },
        // Named medical semantic colors
        medical: {
          blue: "#1d4ed8",
          teal: "#0D9488",
          green: "#059669",
          amber: "#d97706",
          red: "#dc2626",
        },
        // Note status semantic colors
        status: {
          draft: "#6b7280",
          processing: "#3b82f6",
          reviewed: "#f59e0b",
          approved: "#10b981",
          submitted: "#0D9488",
          failed: "#ef4444",
        },
      },

      // ── Typography ────────────────────────────────────────────────────────
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },

      // ── Animations ────────────────────────────────────────────────────────
      animation: {
        // Legacy animations
        "pulse-ring": "pulse-ring 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        wave: "wave 1.2s ease-in-out infinite",
        // Recording indicator: pulsing red ring
        "pulse-record":
          "pulse-record 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        // Fade in with upward slide
        "fade-in": "fade-in 0.25s ease-out forwards",
        // Slide up from bottom (bottom-sheets, drawers)
        "slide-up": "slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        // Slide down (dismiss)
        "slide-down": "slide-down 0.25s ease-in forwards",
      },

      keyframes: {
        // Legacy keyframes
        "pulse-ring": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.5", transform: "scale(1.1)" },
        },
        wave: {
          "0%, 100%": { transform: "scaleY(0.5)" },
          "50%": { transform: "scaleY(1.5)" },
        },
        // Recording ring: red glow expands outward
        "pulse-record": {
          "0%, 100%": {
            boxShadow: "0 0 0 0 rgba(239, 68, 68, 0.7)",
            transform: "scale(1)",
          },
          "50%": {
            boxShadow: "0 0 0 12px rgba(239, 68, 68, 0)",
            transform: "scale(1.05)",
          },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(100%)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-down": {
          "0%": { opacity: "1", transform: "translateY(0)" },
          "100%": { opacity: "0", transform: "translateY(100%)" },
        },
      },

      // ── Responsive breakpoints ────────────────────────────────────────────
      screens: {
        xs: "375px",
      },
    },
  },
  plugins: [
    // Safe-area-inset utilities for iOS PWA (notch / home indicator)
    plugin(({ addUtilities }) => {
      addUtilities({
        ".pt-safe": { paddingTop: "env(safe-area-inset-top)" },
        ".pb-safe": { paddingBottom: "env(safe-area-inset-bottom)" },
        ".pl-safe": { paddingLeft: "env(safe-area-inset-left)" },
        ".pr-safe": { paddingRight: "env(safe-area-inset-right)" },
        ".px-safe": {
          paddingLeft: "env(safe-area-inset-left)",
          paddingRight: "env(safe-area-inset-right)",
        },
        ".py-safe": {
          paddingTop: "env(safe-area-inset-top)",
          paddingBottom: "env(safe-area-inset-bottom)",
        },
        ".p-safe": {
          paddingTop: "env(safe-area-inset-top)",
          paddingRight: "env(safe-area-inset-right)",
          paddingBottom: "env(safe-area-inset-bottom)",
          paddingLeft: "env(safe-area-inset-left)",
        },
        ".mt-safe": { marginTop: "env(safe-area-inset-top)" },
        ".mb-safe": { marginBottom: "env(safe-area-inset-bottom)" },
        ".ml-safe": { marginLeft: "env(safe-area-inset-left)" },
        ".mr-safe": { marginRight: "env(safe-area-inset-right)" },
        ".h-screen-safe": {
          height:
            "calc(100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom))",
        },
        ".min-h-screen-safe": {
          minHeight:
            "calc(100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom))",
        },
      });
    }),
  ],
};

export default config;
