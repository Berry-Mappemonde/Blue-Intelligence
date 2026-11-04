module.exports = {
  content: ["./src/**/*.{js,jsx}", "./public/index.html"],
  theme: {
    extend: {
      fontFamily: {
        heading: ["'IBM Plex Sans'", "sans-serif"],
        body: ["Manrope", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
        // Meridian UI face (top nav + Ports of entry screens)
        ui: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "'Segoe UI'", "Roboto", "sans-serif"],
      },
      colors: {
        abyss: "#020617",
        // These 3 are now bound to CSS variables that switch with data-mode
        // (see index.css: [data-mode="marinas"] and [data-mode="formalities"]).
        // The old static hex values remain the fallback for the projects mode.
        surface: "rgb(var(--surface-rgb, 15 23 42) / <alpha-value>)",
        raised:  "rgb(var(--raised-rgb, 30 41 59) / <alpha-value>)",
        line:    "rgb(var(--line-rgb, 51 65 85) / <alpha-value>)",
        sonar: "#00f0ff",
        bio: "#39ff14",
        alert: "#ff4a4a",
        amberx: "#fbbf24",
        funder: "#c084fc",
        // Semantic "accent" — RGB channels come from --accent-rgb which switches
        // between projects (cyan) / marinas (red) / formalities (amberx) via [data-mode].
        accent: "rgb(var(--accent-rgb) / <alpha-value>)",
        // Meridian tokens (dark only), defined in index.css as RGB triplets.
        m: {
          rail: "rgb(var(--m-rail) / <alpha-value>)",
          canvas: "rgb(var(--m-canvas) / <alpha-value>)",
          shell: "rgb(var(--m-shell) / <alpha-value>)",
          panel: "rgb(var(--m-panel) / <alpha-value>)",
          raised: "rgb(var(--m-raised) / <alpha-value>)",
          selected: "rgb(var(--m-selected) / <alpha-value>)",
          overlay: "rgb(var(--m-overlay) / <alpha-value>)",
          line: "rgb(var(--m-line) / <alpha-value>)",
          "line-soft": "rgb(var(--m-line-soft) / <alpha-value>)",
          "line-strong": "rgb(var(--m-line-strong) / <alpha-value>)",
          fg: "rgb(var(--m-fg) / <alpha-value>)",
          fg2: "rgb(var(--m-fg-2) / <alpha-value>)",
          fg3: "rgb(var(--m-fg-3) / <alpha-value>)",
          fg4: "rgb(var(--m-fg-4) / <alpha-value>)",
          accent: "rgb(var(--m-accent) / <alpha-value>)",
          "accent-fg": "rgb(var(--m-accent-fg) / <alpha-value>)",
          danger: "rgb(var(--m-danger) / <alpha-value>)",
          "danger-fg": "rgb(var(--m-danger-fg) / <alpha-value>)",
          success: "rgb(var(--m-success) / <alpha-value>)",
          "success-fg": "rgb(var(--m-success-fg) / <alpha-value>)",
        },
      },
    },
  },
  plugins: [],
};
