/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b0e14",
        panel: "#141925",
        panel2: "#1b2230",
        edge: "#273042",
        muted: "#8b97ad",
        pos: "#2ecc71",
        neg: "#ff5d5d",
        accent: "#5b8cff",
      },
    },
  },
  plugins: [],
};
