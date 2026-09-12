/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Light enterprise content surfaces (cards, tables, drawers, main canvas).
        base: {
          bg: "#f2f5fa",
          panel: "#ffffff",
          "panel-2": "#f6f8fc",
          elevated: "#ffffff",
          border: "#e2e8f0",
          "border-strong": "#cbd5e1",
        },
        // Deep navy structural chrome — sidebar / nav rail only.
        nav: {
          bg: "#0b1220",
          panel: "#101a2e",
          border: "rgba(255,255,255,0.08)",
          text: "#93a4bd",
          "text-active": "#ffffff",
        },
        // Electric blue — primary interaction / brand.
        brand: {
          DEFAULT: "#2563eb",
          fg: "#2563eb",
          dim: "#dbeafe",
        },
        // Purple — AI / intelligence.
        ai: {
          DEFAULT: "#7c3aed",
          fg: "#7c3aed",
          dim: "#ede9fe",
        },
        // Semantic status accents (dot / text colour — badges built from these in status.ts).
        sev: {
          info: "#64748b",
          low: "#0284c7",
          medium: "#d97706",
          high: "#ea580c",
          critical: "#dc2626",
        },
        ok: "#059669",
      },
      fontFamily: {
        sans: [
          "Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI",
          "Roboto", "Helvetica Neue", "Arial", "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(15,23,42,0.04), 0 8px 20px -14px rgba(15,23,42,0.16)",
        glow: "0 0 0 1px rgba(37,99,235,0.35), 0 0 16px -4px rgba(37,99,235,0.35)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(rgba(15,23,42,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(15,23,42,0.025) 1px, transparent 1px)",
        "surface-sheen":
          "linear-gradient(180deg, rgba(255,255,255,0.7), rgba(255,255,255,0) 40%)",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in-right": {
          "0%": { opacity: "0", transform: "translateX(24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "flow-dash": {
          to: { "stroke-dashoffset": "-16" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.28s ease-out both",
        "slide-in-right": "slide-in-right 0.25s ease-out both",
        shimmer: "shimmer 1.6s infinite",
        "flow-dash": "flow-dash 0.8s linear infinite",
      },
    },
  },
  plugins: [],
};
