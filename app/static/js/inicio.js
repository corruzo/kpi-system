/* Inicio: pantalla de bienvenida con lo que hay que hacer ahora y accesos directos a cada sección del rol. */
SIGT.modulos.inicio = () => ({
    resumenInicio: null,

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { inicio() { return this.cargarInicio(); } },
      salida() { this.resumenInicio = null; },
    },

    get esRevisor() { return ['gerente', 'admin'].includes(this.user.rol); },
    saludo() { const h = new Date().getHours(); return (h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches') + ', ' + this.user.nombre.split(' (')[0].split(' ')[0]; },
    // Resumen del ejercicio (solo gerencia/administración: el jefe no accede al panel analítico)
    async cargarInicio() {
      if (!this.esRevisor) return;
      const q = this.ejSel ? '?ejercicio=' + this.ejSel : '';
      try { this.resumenInicio = (await this.api('/api/dashboard' + q, {}, true)).resumen; } catch { this.resumenInicio = null; }
    },
    // Tareas pendientes del usuario, de la más urgente a la menos urgente
    tareas() {
      const t = [], n = this.pendientesTotal();
      if (this.esRevisor && this.bandeja.length) t.push({ id: 'bandeja', n: this.bandeja.length, texto: 'cargas del ejercicio esperan su aprobación', boton: 'Revisar' });
      if (n && (this.user.rol === 'jefe' || this.user.rol === 'admin')) t.push({ id: 'carga', n, texto: 'períodos pendientes de cargar en este ejercicio', boton: 'Cargar' });
      for (const o of this.otrosEjercicios()) t.push({ ejercicio: o.ejercicio, id: 'otro:' + o.ejercicio, n: o.n, texto: `pendientes en el ejercicio ${o.etiqueta} (ya terminado)`, boton: 'Ver ese ejercicio' });
      const r = this.resumenInicio;
      if (r && r.rojo) t.push({ id: 'panel', n: r.rojo, texto: 'indicadores en estado crítico', boton: 'Ver panel' });
      return t;
    },
    // Pendientes (por cargar o por aprobar) que quedaron en otros ejercicios: se avisan aparte para no mezclarlos
    otrosEjercicios() {
      const t = {};
      const sumar = (a, etiqueta, n) => { (t[a] ||= { ejercicio: a, etiqueta, n: 0 }).n += n; };
      if (this.user.rol !== 'gerente') for (const o of this.pendientesOtros) sumar(o.ejercicio, o.etiqueta, o.n);
      if (this.esRevisor) for (const o of this.bandejaOtros) sumar(o.ejercicio, o.etiqueta, o.n);
      return Object.values(t).sort((a, b) => b.ejercicio - a.ejercicio);
    },
    irATarea(t) { return t.ejercicio ? this.irAEjercicio(t.ejercicio) : this.go(t.id); },
    accesos() { return this.nav().filter(n => n.id !== 'inicio'); },
    descripcionAcceso(id) {
      return { carga: 'Registre los datos del período y obtenga el semáforo al instante.', historial: 'Consulte el estado de cada carga y sus observaciones.',
        reportes: 'Descargue informes y fichas técnicas en Excel.', panel: 'Resultados, tendencias y mapa de calor del ejercicio.',
        bandeja: 'Apruebe o devuelva las cargas enviadas.', ejercicios: 'Estado, cierre y archivo de cada año fiscal.',
        fichas: 'Cree y mantenga las fichas técnicas de los indicadores.', org: 'Áreas, usuarios, listas y parámetros del sistema.',
        importar: 'Traiga las fichas de años anteriores desde Excel.', bitacora: 'Registro inalterable de todo lo que ocurre.' }[id] || '';
    },
});
