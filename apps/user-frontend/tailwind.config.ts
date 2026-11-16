import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B0B0D",
        panel: "#111114",
        inputBg: "#1F1F23",
        borderLine: "#2A2A30",
        primaryText: "#F5F5F5",
        secondaryText: "#A1A1AA",
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

