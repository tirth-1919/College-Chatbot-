import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--bg-main)",
        panel: "var(--bg-panel)",
        sidebar: "var(--bg-sidebar)",
        inputBg: "var(--bg-input)",
        borderLine: "var(--border-color)",
        primaryText: "var(--text-primary)",
        secondaryText: "var(--text-secondary)",
        mutedText: "var(--text-muted)",
        brandIndigo: "#6366F1",
        verifiedGreen: "#10B981",
        warningAmber: "#F59E0B",
        dangerRed: "#EF4444",
      },
    },
  },
  plugins: [],
};

export default config;
