/* Inicio: pantalla de bienvenida con lo que hay que hacer ahora y accesos directos a cada sección del rol. */
SIGT.modulos.inicio = () => ({
    resumenInicio: null, marcha: null,

    // Ganchos: el núcleo los invoca al ingresar, al entrar a una vista y al salir.
    ganchos: {
      entrar: { inicio() { return this.cargarInicio(); } },
      salida() { this.resumenInicio = null; this.marcha = null; },
    },

    // Guía de puesta en marcha: los pasos, en orden, con su estado (hecho / ahora / espera)
    get pasosMarcha() {
      if (!this.marcha) return [];
      const txt = {
        estructura: { t: 'Estructura de la empresa', d: 'Arme el árbol: gerencias, departamentos y jefaturas. De él depende quién ve qué. Al crear una, el formulario queda listo para lo que cuelga de ella.', b: 'Armar la estructura', ir: () => this.go('estructura') },
        roles: { t: 'Roles y permisos', d: 'Cree los roles (qué puede hacer cada cargo). Con un clic puede crear los típicos: Analista, Jefe, Gerente y Gerente general, y ajustarlos en la matriz.', b: 'Crear roles', ir: () => this.go('roles') },
        personas: { t: 'Personas', d: 'Cree la cuenta de cada persona; al guardarla se abre su rol y su posición en la estructura. Una cuenta sin rol no accede a nada.', b: 'Crear y asignar personas', ir: () => this.go('personas') },
        fichas: { t: 'Indicadores', d: 'Cree la ficha de cada indicador: qué mide, su fórmula, su frecuencia, su semáforo, su responsable y quiénes lo cargan.', b: 'Crear indicadores', ir: () => this.go('fichas') },
        periodo: { t: 'Período fiscal ' + this.marcha.etiqueta, d: 'Abra el año de gestión. Sin período fiscal no se pueden fijar metas ni cargar datos.', b: 'Crear el período ' + this.marcha.etiqueta, ir: () => this.crearPeriodo(this.marcha.ejercicio) },
        meta: { t: 'Meta del año', d: 'Para cada indicador, escriba cuánto se espera lograr en cada período (o un valor anual repartido).', b: 'Ingresar metas', ir: () => this.go('meta') },
        carga: { t: 'Carga mensual de datos', d: 'Cada mes quien carga ingresa su dato real; el sistema lo compara con la meta y su superior directo lo aprueba.', b: 'Ver cargas', ir: () => this.go('historial') },
      };
      let ahora = true;
      return this.marcha.pasos.map((p, i) => {
        const estado = p.hecho ? 'hecho' : ahora ? 'ahora' : 'espera';
        if (!p.hecho) ahora = false;
        return { ...p, n: i + 1, estado, ...txt[p.id] };
      });
    },
    get marchaCompleta() { return this.marcha && this.marcha.pasos.every(p => p.hecho); },
    get veMarcha() { return this.puedeAlguno(['sistema.puesta_en_marcha', 'usuarios.asignar']); },
    // «Siguiente paso»: el primero que falta; la barra de pasos (en las pantallas de configuración) lo ofrece con un botón
    get siguientePaso() { return this.pasosMarcha.find(p => p.estado !== 'hecho') || null; },
    get enConfiguracion() { return this.veMarcha && this.marcha && !this.marchaCompleta && ['estructura', 'roles', 'personas', 'fichas', 'meta'].includes(this.view); },
    get esRevisor() { return this.puede('cargas.aprobar'); },
    get veResumen() { return this.puede('panel.ver'); },
    saludo() { const h = new Date().getHours(); return (h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches') + ', ' + this.user.nombre.split(' (')[0].split(' ')[0]; },
    // Resumen del ejercicio (solo quien tiene el permiso del panel)
    async cargarInicio() {
      if (!this.veResumen && !this.veMarcha) return;
      if (this._inicioListo) { this._inicioListo = false; return; }   // primera entrada: los datos llegaron con el arranque
      const q = this.ejSel ? '?ejercicio=' + this.ejSel : '';
      await Promise.all([   // en paralelo: antes una petición esperaba a la otra
        this.veMarcha ? this.api('/api/puesta-en-marcha', {}, true).then(m => { this.marcha = m; }, () => { this.marcha = null; }) : null,
        this.veResumen ? this.api('/api/dashboard' + q, {}, true).then(r => { this.resumenInicio = r.resumen; }, () => { this.resumenInicio = null; }) : null]);
    },
    // Tareas pendientes del usuario, de la más urgente a la menos urgente
    tareas() {
      const t = [], n = this.pendientesTotal();
      if (this.esRevisor && this.bandejaDelEjercicio) t.push({ id: 'bandeja', n: this.bandejaDelEjercicio, texto: 'cargas del ejercicio esperan su aprobación', boton: 'Revisar' });
      if (n && this.puede('cargas.cargar')) t.push({ id: 'carga', n, texto: 'períodos pendientes de cargar en este ejercicio', boton: 'Cargar' });
      for (const o of this.otrosEjercicios()) t.push({ ejercicio: o.ejercicio, id: 'otro:' + o.ejercicio, n: o.n, texto: `pendientes en el ejercicio ${o.etiqueta} (ya terminado)`, boton: 'Ver ese ejercicio' });
      const r = this.resumenInicio;
      if (r && r.rojo) t.push({ id: 'panel', n: r.rojo, texto: 'indicadores en estado crítico', boton: 'Ver panel' });
      return t;
    },
    // Pendientes (por cargar o por aprobar) que quedaron en otros ejercicios: se avisan aparte para no mezclarlos
    otrosEjercicios() {
      const t = {};
      const sumar = (a, etiqueta, n) => { (t[a] ||= { ejercicio: a, etiqueta, n: 0 }).n += n; };
      if (this.puede('cargas.cargar')) for (const o of this.pendientesOtros) sumar(o.ejercicio, o.etiqueta, o.n);
      if (this.esRevisor) for (const o of this.bandejaOtros) sumar(o.ejercicio, o.etiqueta, o.n);
      return Object.values(t).sort((a, b) => b.ejercicio - a.ejercicio);
    },
    irATarea(t) { return t.ejercicio ? this.irAEjercicio(t.ejercicio) : this.go(t.id); },
    accesos() { return this.nav().filter(n => n.id !== 'inicio'); },
    descripcionAcceso(id) {
      return { meta: 'Cree el año fiscal y fije la meta de cada indicador.', carga: 'Registre los datos del período y obtenga el semáforo al instante.', historial: 'Consulte el estado de cada carga y sus observaciones.',
        reportes: 'Descargue informes y fichas técnicas en Excel.', panel: 'Resultados, tendencias y mapa de calor del ejercicio.',
        bandeja: 'Apruebe o devuelva las cargas que le corresponden.', ejercicios: 'Verifique, cierre y archive cada año fiscal.',
        fichas: 'Consulte y mantenga las fichas técnicas de los indicadores.', estructura: 'Gerencias, departamentos y jefaturas de la empresa.',
        personas: 'Rol, posición e indicadores de cada persona.', roles: 'Qué puede hacer cada rol: la matriz de permisos.', config: 'Empresa, listas, respaldo y soporte.',
        recordatorios: 'Avise por Outlook a quien tiene cargas pendientes.',
        importar: 'Traiga las fichas de años anteriores desde Excel.', bitacora: 'Registro inalterable de todo lo que ocurre.' }[id] || '';
    },
});
