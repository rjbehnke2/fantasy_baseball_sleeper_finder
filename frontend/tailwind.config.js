/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sleeper: {
          50: "#f0fdf4",
          500: "#22c55e",
          700: "#15803d",
        },
        bust: {
          50: "#fef2f2",
          500: "#ef4444",
          700: "#b91c1c",
        },
        dynasty: {
          50: "#eff6ff",
          500: "#3b82f6",
          700: "#1d4ed8",
        },
      },
    },
  },
  plugins: [],
};
