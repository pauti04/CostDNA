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
        bg: "var(--bg)",
        "bg-section": "var(--bg-section)",
        "bg-soft": "var(--bg-soft)",
        "bg-card": "var(--bg-card)",
        "bg-deep": "var(--bg-deep)",
        "bg-deep-soft": "var(--bg-deep-soft)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        text: "var(--text)",
        "text-soft": "var(--text-soft)",
        "text-muted": "var(--text-muted)",
        "text-on-deep": "var(--text-on-deep)",
        accent: "var(--accent)",
        "accent-2": "var(--accent-2)",
        good: "var(--good)",
        bad: "var(--bad)",
        "code-bg": "var(--code-bg)",
        "code-bg-soft": "var(--code-bg-soft)",
        "code-text": "var(--code-text)",
        "code-text-soft": "var(--code-text-soft)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      animation: {
        "fade-up": "fade-up 0.6s ease-out forwards",
        "blink": "blink 1s step-end infinite",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "blink": {
          "0%, 50%": { opacity: "1" },
          "51%, 100%": { opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
