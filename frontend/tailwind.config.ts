import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: { ink: "#11101a", lilac: "#a993ff", cream: "#f7f5ef" },
      boxShadow: { glow: "0 24px 80px rgba(169,147,255,.18)" },
    },
  },
  plugins: [],
} satisfies Config;
