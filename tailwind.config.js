// Paleta cálida (grises con matiz crema) + acentos corporativos navy #0f172a y azul #0284c7.
module.exports = {
  content: ['./app/static/*.{html,js}'],
  theme: {
    extend: {
      colors: {
        navy: '#0f172a',
        ink: '#141413',
        brand: { DEFAULT: '#0284c7', dark: '#0369a1', light: '#e6f3fb' },
        // Se redefine la escala «slate» con grises cálidos: toda la interfaz hereda el nuevo tono.
        slate: { 50: '#faf9f5', 100: '#f3f1ea', 200: '#e8e5da', 300: '#d8d4c6', 400: '#a9a597', 500: '#7b786b',
                 600: '#5f5d52', 700: '#44423a', 800: '#2c2b26', 900: '#141413' },
      },
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
        serif: ['"Iowan Old Style"', '"Palatino Linotype"', 'Palatino', 'Georgia', 'ui-serif', 'serif'],
      },
      boxShadow: {
        soft: '0 1px 2px rgba(20,20,19,.04), 0 4px 16px rgba(20,20,19,.04)',
        float: '0 8px 30px rgba(20,20,19,.12)',
      },
    },
  },
};
