// Sistema de diseño: ver DESIGN.md (tinta navy sobre mármol frío, un solo azul de acción, sombras teñidas de azul).
// La escala «slate» se redefine con los grises azulados de la guía: toda la interfaz hereda la paleta.
module.exports = {
  content: ['./app/static/*.html', './app/static/*.js', './app/static/js/*.js', './app/static/parciales/**/*.html'],
  theme: {
    extend: {
      colors: {
        ink: '#0b3558',                                           // Ink Navy: texto, iconos, botones oscuros
        brand: { DEFAULT: '#006bff', dark: '#0057d1', light: '#e6f0ff' },   // Signal Blue: acción primaria y estados activos
        cobalt: '#004eba',                                        // Deep Cobalt: texto informativo sobre fondo azul claro
        magenta: '#e55cff',                                       // acentos decorativos (solo atmósfera, nunca UI funcional)
        cyan: '#0099ff',
        slate: { 50: '#f8f9fb', 100: '#f0f3f8', 200: '#d4e0ed', 300: '#bccddf', 400: '#a6bbd1', 500: '#52718f',
                 600: '#476788', 700: '#2f5276', 800: '#1b4163', 900: '#0b3558' },
      },
      fontFamily: {
        sans: ['Manrope', 'ui-sans-serif', 'system-ui', '-apple-system', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
      },
      // Toda elevación usa sombras teñidas de azul (rgba(71,103,136)), nunca negro neutro.
      boxShadow: {
        sm: '0 1px 2px rgba(71,103,136,.06)',
        DEFAULT: '0 4px 5px rgba(71,103,136,.04), 0 4px 10px rgba(71,103,136,.03), 0 10px 20px rgba(71,103,136,.05)',
        md: '0 4px 5px rgba(71,103,136,.04), 0 8px 15px rgba(71,103,136,.03), 0 15px 30px rgba(71,103,136,.06)',
        lg: '0 4px 5px rgba(71,103,136,.04), 0 8px 15px rgba(71,103,136,.03), 0 30px 50px rgba(71,103,136,.08)',
        soft: '0 4px 5px rgba(71,103,136,.04), 0 4px 10px rgba(71,103,136,.03), 0 10px 20px rgba(71,103,136,.05)',
        float: '0 4px 5px rgba(71,103,136,.04), 0 8px 15px rgba(71,103,136,.03), 0 30px 50px rgba(71,103,136,.08)',
      },
    },
  },
};
