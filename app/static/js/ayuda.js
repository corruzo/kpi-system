/* Ayuda contextual: botones «i» que despliegan la explicación de cada campo o concepto. */
SIGT.modulos.ayuda = () => ({
    ay: '',

    toggleAyuda(k) { this.ay = this.ay === k ? '' : k; },
    ayudaHtml(k) { const [t, d] = AYUDA[k] || ['', '']; return `<div class="font-semibold text-sky-900">${t}</div><div class="mt-0.5">${d}</div>`; },
});
