/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        base: {
          bg: "#0b0f17",
          panel: "#121826",
          border: "#1f2937",
        },
        brand: {
          DEFAULT: "#2563eb",
          fg: "#60a5fa",
        },
        sev: {
          info: "#64748b",
          low: "#0ea5e9",
          medium: "#f59e0b",
          high: "#f97316",
          critical: "#ef4444",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
