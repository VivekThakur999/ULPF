/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // dark-first SOC surfaces
        base: {
          bg: "#080b11",
          panel: "#0f141d",
          "panel-2": "#141b26",
          elevated: "#18202d",
          border: "#1f2734",
          "border-strong": "#2b3546",
        },
        brand: {
          DEFAULT: "#3b82f6",
          fg: "#7ca9f9",
          dim: "#1d3a6b",
        },
        // semantic status palette (single source of truth)
        sev: {
          info: "#64748b",
          low: "#38bdf8",
          medium: "#fbbf24",
          high: "#fb923c",
          critical: "#f87171",
        },
        ok: "#34d399",
        ai: "#a78bfa",
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
        panel: "0 1px 2px rgba(0,0,0,0.4), 0 8px 24px -12px rgba(0,0,0,0.6)",
        glow: "0 0 0 1px rgba(59,130,246,0.35), 0 0 22px -4px rgba(59,130,246,0.35)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
        "surface-sheen":
          "linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0) 40%)",
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
