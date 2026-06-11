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
        border: "rgb(var(--border) / <alpha-value>)",
        "border-subtle": "rgb(var(--border-subtle) / <alpha-value>)",
        surface: {
          DEFAULT: "rgb(var(--background) / <alpha-value>)",
          raised: "rgb(var(--card) / <alpha-value>)",
        },
        foreground: "rgb(var(--foreground) / <alpha-value>)",
        muted: {
          DEFAULT: "rgb(var(--muted) / <alpha-value>)",
          foreground: "rgb(var(--muted-foreground) / <alpha-value>)",
        },
        sidebar: {
          DEFAULT: "#0a0a0a",
          hover: "#171717",
          border: "#262626",
          active: "#1f1f1f",
          muted: "#a3a3a3",
        },
        brand: {
          DEFAULT: "#7c3aed",
          hover: "#6d28d9",
          muted: "#f5f3ff",
          subtle: "#ede9fe",
          rose: "#db2777",
          amber: "#f59e0b",
        },
        success: {
          DEFAULT: "#059669",
          muted: "#ecfdf5",
          border: "#6ee7b7",
        },
        warning: {
          DEFAULT: "#d97706",
          muted: "#fffbeb",
          border: "#fcd34d",
        },
        danger: {
          DEFAULT: "#dc2626",
          muted: "#fef2f2",
          border: "#fca5a5",
        },
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        lg: "var(--radius-lg)",
        xl: "calc(var(--radius-lg) + 4px)",
        "2xl": "1.25rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        glass: "var(--shadow-glass)",
        float: "var(--shadow-float)",
        card: "var(--shadow-soft)",
        elevated: "var(--shadow-float)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
      },
      spacing: {
        sidebar: "var(--sidebar-width)",
      },
      animation: {
        "fade-in": "fadeIn 0.35s ease-out",
        "slide-up": "slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)",
        shimmer: "shimmer 3s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%, 100%": { opacity: "0.5" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
