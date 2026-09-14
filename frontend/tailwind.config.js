/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Light enterprise surfaces — matches stitch_*/DESIGN.md's "Base Canvases &
        // Structural Neutrals": white cards inset within a very light slate frame.
        base: {
          bg: "#f8fafc", // page canvas / global frame
          panel: "#ffffff", // cards, tables, drawers — always pure white
          "panel-2": "#f1f5f9", // sunken/inset sub-panels inside a card
          elevated: "#ffffff",
          border: "#e2e8f0",
          "border-strong": "#cbd5e1",
        },
        // Light structural chrome — sidebar / header rail (NOT dark; DESIGN.md treats
        // the nav rail as "Canvas Alternate", one step off pure white).
        nav: {
          bg: "#f8fafc",
          panel: "#ffffff",
          border: "#e2e8f0",
          text: "#64748b",
          "text-active": "#ffffff",
        },
        // Crimson — primary brand + interaction (buttons, active nav, selection).
        // Kept visually distinct from `sev.critical` by *treatment*: brand is always
        // a solid fill (button, active pill, ring); critical is always a soft wash
        // (badge, accent bar, left-stripe) — never the other way around.
        brand: {
          DEFAULT: "#dc2626",
          hover: "#be123c",
          fg: "#dc2626",
          dim: "#fef2f2",
        },
        // Purple — AI / intelligence, exclusively.
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
        // DESIGN.md "Level 1 (Card & Module Resting)"
        panel: "0 1px 3px 0 rgba(15,23,42,0.05), 0 1px 2px -1px rgba(15,23,42,0.03)",
        // "Level 2 (Interactive Floating / Active Hover)"
        hover: "0 4px 6px -1px rgba(15,23,42,0.07), 0 2px 4px -2px rgba(15,23,42,0.05)",
        // "Level 3 (Overlays & Slide-out Panels)"
        overlay: "0 10px 15px -3px rgba(15,23,42,0.08), 0 4px 6px -4px rgba(15,23,42,0.03)",
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
