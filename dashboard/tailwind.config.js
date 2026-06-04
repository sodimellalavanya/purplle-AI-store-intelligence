/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        ink: {
          900: "#0A0A0F",
          800: "#111118",
          700: "#1A1A24",
          600: "#23232F",
          500: "#2D2D3D",
          400: "#3D3D52",
        },
        signal: {
          green:  "#00FF87",
          amber:  "#FFB800",
          red:    "#FF3B5C",
          blue:   "#4D9EFF",
          purple: "#A855F7",
        }
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: "translateY(12px)" }, to: { opacity: 1, transform: "translateY(0)" } }
      }
    },
  },
  plugins: [],
}
