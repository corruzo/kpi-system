/* Lista desplegable con buscador (reemplaza a <datalist> y a <select> en los campos donde se elige una persona, un nodo, un rol…).

   Dos modos, según `texto`:
     · elegir (por defecto): el campo guarda el `valor` de la opción (un id). Si hay más de 7 opciones se puede escribir para filtrar.
     · texto: el campo es texto libre y la lista solo sugiere (p. ej. nombres de personas); lo escrito se conserva tal cual.

   Uso (dentro de cualquier pantalla; los cierres leen y escriben el estado de la pantalla):
     <div x-data="combo({ id: 'ficha-nodo', opciones: () => opcionesNodos, valor: () => ficha.nodo_id,
                          elegir: v => ficha.nodo_id = v, requerido: true, deshabilitado: () => !puedeAsignarFicha })"></div>

   Cada opción: { valor, etiqueta, detalle?, chip?, nivel? (sangría del árbol), tenue? }.
   La lista es un panel flotante (position: fixed) para que no la recorte el scroll de las ventanas modales. */
document.addEventListener('alpine:init', () => {
  let contador = 0;
  const norm = t => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const FLECHA = '<svg class="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 transition-transform duration-200" :class="{ \'rotate-180\': abierto }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
  const MARCA = '<svg x-show="esActual(o)" class="h-4 w-4 shrink-0 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10"/></svg>';
  const PLANTILLA = `
    <div class="relative" @click.outside="cerrar()" @scroll.window.capture="abierto && colocar()" @resize.window="abierto && colocar()">
      <input type="text" x-ref="campo" :id="idCampo" class="inp pr-11" :class="{ 'cursor-pointer caret-transparent': !escribible }"
        role="combobox" aria-autocomplete="list" :aria-expanded="abierto" :aria-controls="uid + '-lista'" :aria-activedescendant="activo >= 0 ? uid + '-' + activo : null"
        :aria-label="etiquetaAria" :placeholder="marcador" :maxlength="maximo" :readonly="!escribible" :disabled="bloqueado" autocomplete="off"
        :value="textoCampo" @input="escribir($event.target.value)" @focus="abrir()" @click="abrir()" @keydown="teclas($event)">
      ${FLECHA}
      <template x-if="esRequerido"><input type="text" tabindex="-1" aria-hidden="true" class="pointer-events-none absolute inset-x-0 bottom-0 h-px opacity-0" required :disabled="bloqueado" :value="valorActual ?? ''"></template>
      <ul :id="uid + '-lista'" role="listbox" x-show="abierto && (visibles.length || !modoTexto)" x-cloak x-transition.opacity.duration.100ms :style="estilo" @mousedown.prevent
        class="fixed z-[60] overflow-y-auto overscroll-contain rounded-2xl border border-slate-200 bg-white p-1.5 shadow-float">
        <template x-for="(o, i) in visibles" :key="i">
          <li role="option" :id="uid + '-' + i" :aria-selected="esActual(o)" @mouseenter="activo = i" @click="elegirOpcion(o)"
            class="flex cursor-pointer items-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors"
            :class="{ 'bg-brand-light text-ink': i === activo, 'text-slate-700': i !== activo && !o.tenue, 'text-slate-400': i !== activo && o.tenue }"
            :style="!q && o.nivel ? 'padding-left:' + (0.75 + o.nivel * 1.1) + 'rem' : ''">
            <span class="min-w-0 flex-1"><span class="block truncate" :class="{ 'font-bold': esActual(o) }" x-text="o.etiqueta"></span><span class="block truncate text-xs text-slate-500" x-show="o.detalle" x-text="o.detalle"></span></span>
            <span class="chip shrink-0 border-slate-200 bg-slate-50 !px-2 !py-0.5 text-[10px] text-slate-500" x-show="o.chip" x-text="o.chip"></span>
            ${MARCA}
          </li>
        </template>
        <li class="px-3 py-3 text-center text-sm text-slate-500" x-show="!visibles.length">Sin resultados</li>
      </ul>
    </div>`;

  Alpine.data('combo', (cfg) => ({
    uid: 'cb' + (++contador), abierto: false, q: '', tocado: false, activo: -1, estilo: '',
    idCampo: cfg.id || null, etiquetaAria: cfg.etiqueta || null, modoTexto: !!cfg.texto, maximo: cfg.maxlength || null,
    // Alpine no recorre lo que se inserta durante init(): se inicializa a mano
    init() { this.$el.innerHTML = PLANTILLA; Alpine.initTree(this.$el.firstElementChild); },

    // ---- estado derivado
    get opciones() { return (cfg.opciones ? cfg.opciones() : []) || []; },
    get valorActual() { return cfg.valor(); },
    get bloqueado() { return !!(cfg.deshabilitado && cfg.deshabilitado()); },
    get esRequerido() { return !!cfg.requerido; },
    get escribible() { return this.modoTexto || cfg.buscable === true || (cfg.buscable !== false && this.opciones.length > 7); },
    get marcador() { return this.modoTexto ? (cfg.marcador || '') : (this.abierto && this.seleccionada ? this.seleccionada.etiqueta : (cfg.marcador || 'Seleccione…')); },
    get seleccionada() { const v = this.valorActual; return v === null || v === undefined ? null : this.opciones.find(o => String(o.valor) === String(v)) || null; },
    get textoCampo() {
      if (this.modoTexto) return this.valorActual ?? '';
      return this.abierto && this.escribible ? this.q : (this.seleccionada ? this.seleccionada.etiqueta : '');
    },
    get visibles() {
      const palabras = norm(this.q).split(/\s+/).filter(Boolean);
      if (!palabras.length || (this.modoTexto && !this.tocado)) return this.opciones;
      return this.opciones.filter(o => { const t = norm([o.etiqueta, o.detalle, o.chip].join(' ')); return palabras.every(p => t.includes(p)); });
    },
    esActual(o) { const v = this.valorActual; return v !== null && v !== undefined && String(o.valor) === String(v); },

    // ---- abrir, cerrar y colocar
    abrir() {
      if (this.bloqueado || this.abierto) return;
      this.q = ''; this.tocado = false; this.abierto = true;
      this.activo = this.modoTexto ? -1 : Math.max(0, this.visibles.findIndex(o => this.esActual(o)));
      this.colocar(); this.verActivo();
    },
    cerrar() { this.abierto = false; this.q = ''; this.tocado = false; this.activo = -1; },
    colocar() {
      const campo = this.$refs.campo; if (!campo) return;
      const r = campo.getBoundingClientRect(), alto = window.innerHeight;
      if (r.bottom < 0 || r.top > alto) { this.cerrar(); return; }   // el campo salió de la pantalla al hacer scroll
      const abajo = alto - r.bottom - 12, arriba = r.top - 12, sube = abajo < 200 && arriba > abajo;
      const maximo = Math.max(120, Math.min(288, sube ? arriba : abajo));
      this.estilo = `left:${r.left}px;width:${r.width}px;max-height:${maximo}px;` + (sube ? `bottom:${alto - r.top + 6}px` : `top:${r.bottom + 6}px`);
    },
    verActivo() { this.$nextTick(() => { const el = this.activo >= 0 ? document.getElementById(this.uid + '-' + this.activo) : null; if (el) el.scrollIntoView({ block: 'nearest' }); }); },

    // ---- interacción
    escribir(texto) {
      if (this.modoTexto) { cfg.elegir(texto); this.tocado = true; this.q = texto; this.activo = -1; if (!this.abierto) { this.abierto = true; this.colocar(); } return; }
      this.q = texto; this.activo = 0; if (!this.abierto) this.abrir(); this.colocar();
    },
    elegirOpcion(o) { cfg.elegir(o.valor); this.cerrar(); },
    teclas(e) {
      const n = this.visibles.length;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (!this.abierto) { this.abrir(); return; }
        if (!n) return;
        this.activo = e.key === 'ArrowDown' ? (this.activo + 1) % n : (this.activo <= 0 ? n - 1 : this.activo - 1);
        this.verActivo();
      } else if (e.key === 'Enter' && this.abierto && this.activo >= 0 && this.visibles[this.activo]) {
        e.preventDefault(); this.elegirOpcion(this.visibles[this.activo]);
      } else if (e.key === 'Escape' && this.abierto) {
        e.stopPropagation(); this.cerrar();   // cierra la lista, no la ventana que la contiene
      } else if (e.key === 'Tab') this.cerrar();
    },
  }));
});
