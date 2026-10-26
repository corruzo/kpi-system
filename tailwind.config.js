module.exports = {
  content: ['./app/static/*.{html,js}'],
  theme: {
    extend: {
      colors: { navy: '#0f172a', brand: { DEFAULT: '#0284c7', dark: '#0369a1', light: '#e0f2fe' } },
      fontFamily: { sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'] },
    },
  },
};
