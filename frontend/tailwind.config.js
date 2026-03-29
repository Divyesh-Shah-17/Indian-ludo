/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        theme: {
          green: "#2E7D32",
          light: "#F3F4F6", // Clean light gray
          accent: "#F59E0B",
          red: "#EF4444",
          yellow: "#FBBF24",
          blue: "#3B82F6",
          pGreen: "#10B981",
        }
      }
    },
  },
  plugins: [],
}
