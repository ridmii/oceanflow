/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Fira Mono', 'monospace'],
      },
      colors: {
        ocean: {
          950: '#050810',
          900: '#080d1a',
          800: '#0d1528',
          700: '#152040',
        },
        particle: {
          slow: '#1a3a5c',
          mid: '#2e7fb8',
          fast: '#6ec6e8',
          max: '#f2f2f2',
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
