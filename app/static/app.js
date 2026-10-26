/* SIGT · lógica de interfaz (Alpine.js) */
const SEM = { verde: '#16a34a', amarillo: '#f59e0b', rojo: '#dc2626', sin_datos: '#94a3b8' };
const NAVY = '#0f172a', BRAND = '#0284c7';
const ACCIONES = ['PARAMETROS_EDITADOS', 'CATALOGO_CREADO', 'CATALOGO_EDITADO', 'CATALOGO_ELIMINADO', 'IMPORTACION', 'CARGA', 'REENVIO', 'APROBACION', 'OBSERVACION', 'NOTA_AUDITORIA', 'INDICADOR_CREADO', 'INDICADOR_EDITADO', 'INDICADOR_ARCHIVADO', 'INDICADOR_ELIMINADO', 'AREA_CREADA', 'AREA_EDITADA', 'AREA_ELIMINADA', 'USUARIO_CREADO', 'USUARIO_EDITADO', 'CLAVE_CAMBIADA', 'REAPERTURA', 'REPORTE_EXPORTADO', 'INICIO_SESION'];
const ICONOS = {
  carga: 'M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z',
  historial: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  bandeja: 'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-4l-1 2H9l-1-2H4',
  panel: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  fichas: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
  org: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  importar: 'M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M17 8l-5-5m0 0L7 8m5-5v12',
  ficha: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  reportes: 'M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4',
  bitacora: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
};
const AYUDA = {
  codigo: ['Código', 'Identificador corto y único del indicador, normalmente con el prefijo del área. Ej.: <b>SIS-01</b>, <b>PRO-03</b>. No puede repetirse.'],
  nombre: ['Nombre', 'Nombre completo y claro tal como aparece en el Sistema de Gestión de la Calidad. Ej.: <i>Cumplimiento de solicitudes de soporte</i>.'],
  objetivo: ['Objetivo', 'Para qué se mide: qué decisión o mejora busca apoyar. Se muestra al jefe de área al cargar el dato.'],
  area: ['Área responsable', 'Departamento dueño del indicador. Solo los jefes de esa área (y el administrador) pueden cargarlo.'],
  unidad: ['Unidad de medida', 'Cómo se expresa el resultado: <b>%</b>, <b>días</b>, <b>TM</b>, <b>USD</b>, <b>cantidad</b>… Puede escribir cualquier otra (horas, kg, m³, ppm).'],
  frecuencia: ['Frecuencia', 'Cada cuánto se mide: <b>mensual</b>, <b>trimestral</b>, <b>semestral</b> o <b>anual</b>. Determina los períodos que el jefe verá para cargar. No puede cambiarse cuando ya existen cargas.'],
  decimales: ['Decimales', 'Cantidad de decimales del resultado (0 a 6). Ej.: 1 → 93,5%. El resultado se redondea a esta precisión antes de evaluar el semáforo.'],
  sentido: ['Sentido de la meta', '<b>Mayor es mejor</b>: entre más alto, mejor (cumplimiento, disponibilidad). <b>Menor es mejor</b>: entre más bajo, mejor (obsolescencia, tiempo de ejecución, reclamos).'],
  meta: ['Meta (zona verde)', 'Valor a partir del cual el indicador <b>cumple</b>. Mayor es mejor: verde si resultado ≥ meta. Menor es mejor: verde si resultado ≤ meta.'],
  limite: ['Límite crítico', 'Frontera entre <b>alerta</b> (amarillo) y <b>crítico</b> (rojo). Mayor es mejor: rojo si resultado &lt; límite. Menor es mejor: rojo si resultado &gt; límite. Entre la meta y el límite el semáforo es amarillo.'],
  variables: ['Variables', 'Son los datos base que el jefe digita cada período (ej. <i>solicitudes gestionadas</i> y <i>recibidas</i>). La <b>clave</b> es el nombre corto que se usa dentro de la fórmula y se genera sola. Con «Opciones» puede agregar un texto de ayuda, una unidad, un valor por defecto si queda vacía, o permitir negativos.'],
  constantes: ['Constantes', 'Valores fijos que intervienen en la fórmula y que el jefe <b>no</b> digita: horas por turno, días hábiles, tarifa, factor de conversión… Cambiarlas aquí afecta las cargas futuras; las anteriores conservan su valor.'],
  formula: ['Fórmula', 'Escriba cómo se calcula el resultado usando las claves. Admite <b>+ − × ÷</b>, <b>^</b> (potencia), <b>%</b>, paréntesis, comparaciones (&gt; &lt; &gt;= &lt;= == !=), <b>and / or / not</b> y funciones (botón «Guía de fórmulas»). Para evitar dividir entre cero use <code>si(b &gt; 0, a / b * 100, 0)</code> o <code>div(a, b, 0)</code>.'],
  fuente: ['Fuente de los datos', 'De dónde salen los datos (ERP, informe de producción, laboratorio…) para que la medición sea verificable en auditoría.'],
  notas: ['Método y observaciones', 'Aclaraciones del cálculo, exclusiones, criterios o responsables. Aparece en la ficha técnica y en el reporte Excel.'],
  activo: ['Activo', 'Un indicador archivado deja de aparecer para cargar datos, pero su historial se conserva. Puede restaurarlo cuando quiera.'],
  seguimiento: ['Seguimiento de', '<b>Desempeño de proceso</b>: indicador de un proceso del SGC. <b>Objetivo organizacional</b>: contribuye a un objetivo estratégico. <b>Desempeño de proveedor externo</b>: evalúa un bien o servicio contratado. Cambia las etiquetas de la ficha impresa.'],
  ref_nombre: ['Proceso / objetivo', 'Nombre del proceso (o del objetivo organizacional) al que pertenece el indicador. Puede elegirlo de la lista o escribirlo.'],
  ref_detalle: ['Objetivo del proceso / objetivo específico', 'Descripción que aparece bajo el proceso en la ficha: objetivo del proceso, objetivo específico o bien/servicio evaluado.'],
  sigla: ['Sigla', 'Abreviatura del indicador que se usa en la fórmula documentada. Ej.: <b>SP</b> para «Servicio prestado». Aparece en la ficha: <code>SP = SG × 100 / SR</code>.'],
  gerencia: ['Gerencia', 'Gerencia de la que depende el indicador (aparece en la ficha técnica).'],
  lider: ['Líder de proceso', 'Cargo que lidera el proceso. Ej.: Jefe de sistemas.'],
  responsables: ['Responsables', '<b>Medición</b>: quien obtiene el dato. <b>Registro</b>: quien lo carga. <b>Análisis</b>: quien interpreta los resultados. Escriba el nombre; se sugieren los usuarios del sistema.'],
  topes: ['Topes de las franjas (opcional)', 'Para acotar el otro extremo de cada franja, como las columnas «Mín./Máx.» de la ficha en papel. Ej.: mayor es mejor, meta 96 con tope 500 → verde solo entre 96 y 500. Déjelos vacíos si no aplica.'],
  carga: ['¿Cómo cargar un indicador?', '<ol class="list-decimal space-y-1 pl-5"><li>Elija el <b>indicador</b> y el <b>período</b> (los pendientes aparecen arriba).</li><li>Digite solo los <b>datos base</b>; el resultado se calcula solo.</li><li>Si el semáforo es <b>amarillo o rojo</b>, escriba el análisis y el plan de mejora (obligatorio por ISO 9001).</li><li>Pulse <b>Enviar carga</b>. El Gerente / Auditor la aprobará o la devolverá con observaciones.</li></ol>'],
  semaforo: ['Semáforo', '<b class="text-green-700">Cumple</b>: alcanza la meta. <b class="text-amber-700">Alerta</b>: entre la meta y el límite crítico. <b class="text-red-700">Crítico</b>: peor que el límite crítico. En alerta y crítico debe documentar análisis y plan de mejora.'],
};
const FUNC_DOC = [
  ['si(cond, a, b)', 'Si la condición se cumple da a; si no, b. Solo evalúa la rama elegida, por eso protege divisiones.', 'si(recibidas > 0, gestionadas / recibidas * 100, 100)'],
  ['div(a, b, d)', 'División segura: si b es 0 devuelve d (0 si se omite).', 'div(gestionadas, recibidas, 0) * 100'],
  ['pct(a, b)', 'Porcentaje a / b × 100 (0 si b es 0).', 'pct(conformes, analizados)'],
  ['min(…) / max(…)', 'Menor / mayor de varios valores.', 'min(100, ejecutado / plan * 100)'],
  ['sum(…) / avg(…)', 'Suma / promedio de varios valores.', 'avg(turno_a, turno_b, turno_c)'],
  ['abs(x)', 'Valor absoluto.', 'abs(real - plan)'],
  ['round(x, n)', 'Redondea a n decimales.', 'round(a / b, 1)'],
  ['floor(x) / ceil(x)', 'Redondea hacia abajo / arriba.', 'ceil(horas / 8)'],
  ['sqrt(x)', 'Raíz cuadrada.', 'sqrt(varianza)'],
  ['clamp(x, lo, hi)', 'Limita x entre lo y hi.', 'clamp(avance, 0, 100)'],
  ['a if cond else b', 'Forma alternativa de «si».', '100 if fallas == 0 else 0'],
];
const EJEMPLOS = [
  { t: 'Porcentaje de cumplimiento (con división segura)', d: 'Cumplidos entre totales; si no hubo solicitudes se considera 100 %.', f: 'si(recibidas > 0, gestionadas / recibidas * 100, 100)', vars: [['gestionadas', 'Solicitudes gestionadas'], ['recibidas', 'Solicitudes recibidas']], unidad: '%' },
  { t: 'Disponibilidad de equipos', d: 'Horas disponibles sobre horas calendario.', f: '(horas_calendario - horas_parada) / horas_calendario * 100', vars: [['horas_calendario', 'Horas calendario'], ['horas_parada', 'Horas de parada']], unidad: '%' },
  { t: 'Promedio ponderado', d: 'Cada línea pesa según su volumen.', f: '(linea_a * tm_a + linea_b * tm_b) / (tm_a + tm_b)', vars: [['linea_a', 'Rendimiento línea A'], ['linea_b', 'Rendimiento línea B'], ['tm_a', 'TM línea A'], ['tm_b', 'TM línea B']], unidad: '%' },
  { t: 'Índice de frecuencia de accidentes', d: 'Accidentes por millón de horas-hombre (la constante evita escribir 1.000.000 a mano).', f: 'accidentes * factor / horas_hombre', vars: [['accidentes', 'Accidentes con tiempo perdido'], ['horas_hombre', 'Horas-hombre trabajadas']], consts: [['factor', 'Factor por millón de horas', 1000000]], unidad: 'cantidad' },
  { t: 'Variación porcentual (admite negativos)', d: 'Cambio respecto al período anterior; marque «permite negativos» en las variables si aplica.', f: 'si(anterior != 0, (actual - anterior) / anterior * 100, 0)', vars: [['actual', 'Valor actual'], ['anterior', 'Valor anterior']], unidad: '%' },
  { t: 'Cumplimiento topado en 100 %', d: 'Nunca supera 100 % aunque se sobreproduzca.', f: 'min(100, producido / planificado * 100)', vars: [['producido', 'TM producidas'], ['planificado', 'TM planificadas']], unidad: '%' },
  { t: 'Puntaje por rangos (escalonado)', d: 'Convierte un porcentaje en una nota de 0 a 100.', f: 'si(avance >= 95, 100, si(avance >= 85, 70, si(avance >= 70, 40, 0)))', vars: [['avance', 'Avance (%)']], unidad: 'cantidad' },
  { t: 'Costo unitario con tarifa fija', d: 'Usa una constante que el jefe no ve ni digita.', f: '(horas * tarifa + materiales) / tm', vars: [['horas', 'Horas trabajadas'], ['materiales', 'Materiales (USD)'], ['tm', 'TM producidas']], consts: [['tarifa', 'Tarifa por hora (USD)', 4.5]], unidad: 'USD' },
];
const ROLES = { jefe: 'Jefe de Área', gerente: 'Gerente / Auditor SGC', admin: 'Administrador SGC' };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const nf = (v, d) => Number(v).toLocaleString('es-VE', { minimumFractionDigits: 0, maximumFractionDigits: d });

function sigt() {
  return {
    ready: false, user: null, view: '', busy: false, menu: false, mas: false, ACCIONES, fq: { q: '', area: '', frecuencia: '', estado: 'activo' },
    prueba: { valores: {}, res: null }, ay: '', guia: false, ejemplos: EJEMPLOS, funcDoc: FUNC_DOC,
    filtro2: { semaforo: '', periodo: '', area_id: '' }, histMas: false, reabrirNota: {},
    rep: { anio: '', area_id: '', estado: '' }, repFicha: { area_id: '', indicador_id: '' },
    params: {}, parForm: {}, catalogos: [], catTab: 'proceso', catForm: { id: null, valor: '', detalle: '' },
    fv: { id: null, ejercicio: '', data: null }, imp: { prev: null, sel: {}, cat: {}, res: null, crearAreas: true, cargando: false }, bitUsuario: '', bitMas: false, fichaAbierta: false, ayudaCarga: false,
    loginForm: { username: '', password: '' }, loginError: '',
    toast: { msg: '', error: false }, _toastT: null,
    indicadores: [], areas: [],
    // carga rápida
    f: { indicador_id: '', periodo: '', valores: {}, analisis: '', plan_mejora: '', tocado: false },
    periodosInd: [], calc: null, _seq: 0,
    // listas
    historial: [], filtro: { indicador_id: '', estado: '' }, notasHist: {},
    bandeja: [], notas: {},
    dash: null, panelArea: '', tendInd: null,
    ficha: { variables: [], constantes: [] }, modal: false, formulaMsg: { ok: true, txt: '' },
    bitacora: [], bitAccion: '',
    usuarios: [], usuario: {}, modalUsuario: false, areaForm: { id: null, nombre: '' },
    modalClave: false, clave: { actual: '', nueva: '', repetir: '' },

    // ------------------------------------------------------------ base
    async init() {
      try { this.user = await this.api('/api/me', {}, true); await this.alIngresar(); }
      catch { this.user = null; }
      this.ready = true;
    },
    async api(url, opt = {}, silencioso = false) {
      const o = { credentials: 'same-origin', ...opt };
      if (o.body && typeof o.body !== 'string') { o.body = JSON.stringify(o.body); o.headers = { 'Content-Type': 'application/json' }; }
      const r = await fetch(url, o);
      if (!r.ok) {
        let d = {}; try { d = await r.json(); } catch { }
        let msg = d.detail || 'Error inesperado.';
        if (Array.isArray(msg)) msg = msg.map(e => e.msg).join('; ');
        if (r.status === 401 && this.user) { this.user = null; this.avisar('Su sesión expiró.', true); }
        else if (!silencioso) this.avisar(msg, true);
        throw new Error(msg);
      }
      return r.json();
    },
    avisar(msg, error = false) {
      this.toast = { msg, error }; clearTimeout(this._toastT);
      this._toastT = setTimeout(() => this.toast.msg = '', 4500);
    },
    async login() {
      this.busy = true; this.loginError = '';
      try { this.user = await this.api('/api/login', { method: 'POST', body: this.loginForm }, true); this.loginForm.password = ''; await this.alIngresar(); }
      catch (e) { this.loginError = e.message; }
      this.busy = false;
    },
    iniciales(u = this.user) { return u.nombre.split(' (')[0].split(' ').filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase(); },
    icono: id => ICONOS[id],
    cap: t => t.charAt(0).toUpperCase() + t.slice(1),
    async logout() { await this.api('/api/logout', { method: 'POST' }); this.user = null; this.view = ''; this.menu = false; this.indicadores = []; this.f = { indicador_id: '', periodo: '', valores: {}, analisis: '', plan_mejora: '', tocado: false }; this.periodosInd = []; },
    rolNombre: u => ROLES[u.rol],
    async alIngresar() {
      await this.cargarIndicadores();
      this.params = await this.api('/api/parametros');
      if (this.user.rol !== 'jefe') this.areas = await this.api('/api/areas');
      if (this.user.rol === 'admin') this.catalogos = await this.api('/api/catalogos');
      if (this.user.rol === 'admin') this.usuarios = await this.api('/api/usuarios');
      if (['gerente', 'admin'].includes(this.user.rol)) this.bandeja = await this.api('/api/mediciones?estado=enviado');
      await this.go({ jefe: 'carga', gerente: 'panel', admin: 'fichas' }[this.user.rol]);
    },
    async cargarIndicadores() { this.indicadores = await this.api('/api/indicadores'); },
    nav() {
      const r = this.user.rol;
      if (r === 'jefe') return [{ id: 'carga', label: 'Carga rápida', corto: 'Cargar', badge: this.pendientesTotal() || '' }, { id: 'historial', label: 'Mis cargas', corto: 'Historial' }, { id: 'reportes', label: 'Reportes', corto: 'Reportes' }];
      if (r === 'gerente') return [{ id: 'panel', label: 'Panel de análisis', corto: 'Panel' }, { id: 'bandeja', label: 'Bandeja de aprobación', corto: 'Bandeja', badge: this.bandeja.length || '' }, { id: 'historial', label: 'Todas las cargas', corto: 'Cargas' }, { id: 'reportes', label: 'Reportes', corto: 'Reportes' }];
      return [{ id: 'fichas', label: 'Indicadores', corto: 'Fichas' }, { id: 'panel', label: 'Panel de análisis', corto: 'Panel' },
      { id: 'bandeja', label: 'Bandeja de aprobación', corto: 'Bandeja', badge: this.bandeja.length || '' }, { id: 'carga', label: 'Cargar datos', corto: 'Cargar', badge: this.pendientesTotal() || '' },
      { id: 'historial', label: 'Todas las cargas', corto: 'Cargas' }, { id: 'reportes', label: 'Reportes', corto: 'Reportes' }, { id: 'org', label: 'Organización', corto: 'Equipo' }, { id: 'importar', label: 'Importar', corto: 'Importar' }, { id: 'bitacora', label: 'Bitácora', corto: 'Bitácora' }];
    },
    // En móvil: 4 accesos + «Más» cuando hay más de 5 secciones
    navMovil() { const n = this.nav(); return n.length > 5 ? [...n.slice(0, 4), { id: '_mas', label: 'Más', corto: 'Más', badge: n.slice(4).reduce((a, x) => a + (x.badge || 0), 0) || '' }] : n; },
    navMas() { return this.nav().slice(4); },
    get masActivo() { return this.navMas().some(n => n.id === this.view); },
    async go(v) {
      this.view = v; this.menu = false;
      window.scrollTo({ top: 0 });
      this.mas = false;
      if (v === 'carga' && !this.f.indicador_id && this.indicadoresCarga.length) {
        const p = this.listaPendientes()[0];
        if (p) await this.elegirPendiente(p); else { this.f.indicador_id = this.indicadoresCarga[0].id; await this.cambiarIndicador(); }
      }
      if (v === 'historial') await this.cargarHistorial();
      if (v === 'bandeja') await this.cargarBandeja();
      if (v === 'panel') await this.cargarPanel();
      if (v === 'fichas') await this.cargarIndicadores();
      if (v === 'org') { this.areas = await this.api('/api/areas'); this.usuarios = await this.api('/api/usuarios'); this.catalogos = await this.api('/api/catalogos'); this.parForm = { ...this.params }; }
      if (v === 'bitacora') await this.cargarBitacora();
      if (v === 'reportes' && this.user.rol !== 'jefe' && !this.areas.length) this.areas = await this.api('/api/areas');
    },

    // ------------------------------------------------------------- ayuda
    toggleAyuda(k) { this.ay = this.ay === k ? '' : k; },
    ayudaHtml(k) { const [t, d] = AYUDA[k] || ['', '']; return `<div class="font-semibold text-sky-900">${t}</div><div class="mt-0.5">${d}</div>`; },

    // --------------------------------------------------------- formatos
    fmt(v, u, d = 2) {
      if (v === null || v === undefined) return '—';
      const n = nf(v, d ?? 2);
      return ({ '%': n + '%', 'días': n + ' d', 'USD': '$' + n, 'TM': n + ' TM', 'cantidad': n })[u] ?? `${n} ${u}`;
    },
    fecha: iso => iso ? new Date(iso).toLocaleString('es-VE', { dateStyle: 'short', timeStyle: 'short' }) : '',
    semBg: s => ({ verde: 'bg-green-600', amarillo: 'bg-amber-500', rojo: 'bg-red-600' }[s] || 'bg-slate-300'),
    semBorde: s => ({ verde: 'border-green-600 bg-green-50', amarillo: 'border-amber-500 bg-amber-50', rojo: 'border-red-600 bg-red-50' }[s] || ''),
    semTxt: s => ({ verde: 'Cumple', amarillo: 'Alerta', rojo: 'Crítico' }[s] || ''),
    estadoTxt: e => ({ enviado: 'En revisión', aprobado: 'Aprobado', observado: 'Devuelto' }[e]),
    estadoClase: e => ({ enviado: 'border-sky-300 bg-sky-50 text-sky-800', aprobado: 'border-green-300 bg-green-50 text-green-800', observado: 'border-amber-300 bg-amber-50 text-amber-800' }[e]),
    estadoSufijo(p) { return p.medicion ? ' — ' + this.estadoTxt(p.medicion.estado) : ''; },
    umbralTxt(i) {
      const [a, b] = i.sentido === 'mayor' ? ['≥', '<'] : ['≤', '>'];
      return `${a} ${this.fmt(i.meta, i.unidad, i.decimales)} · crítico ${b} ${this.fmt(i.limite, i.unidad, i.decimales)}`;
    },
    formulaLegible(i) {
      let t = i.formula;
      [...i.variables, ...(i.constantes || [])].sort((a, b) => b.clave.length - a.clave.length).forEach(v => t = t.replace(new RegExp('\\b' + v.clave + '\\b', 'g'), v.etiqueta));
      return t;
    },

    // ---------------------------------------------------- carga rápida
    get ind() { return this.indicadores.find(i => i.id === this.f.indicador_id); },
    get medActual() { return this.periodosInd.find(p => p.periodo === this.f.periodo)?.medicion || null; },
    get bloqueado() { return !!this.medActual && this.medActual.estado !== 'observado'; },
    get indicadoresCarga() { return this.indicadores.filter(i => i.activo); },
    pendientesTotal() { return this.indicadoresCarga.reduce((n, i) => n + (i.pendientes?.length || 0), 0); },
    listaPendientes() { return this.indicadoresCarga.flatMap(i => (i.pendientes || []).map(p => ({ ind: i, ...p }))); },
    async elegirPendiente(p) { this.f.indicador_id = p.ind.id; await this.cambiarIndicador(p.periodo); },
    async cambiarIndicador(periodo) {
      this.calc = null; this.periodosInd = [];
      if (!this.f.indicador_id) return;
      await this.refrescarPeriodos();
      this.f.periodo = periodo || this._sugerido || this.periodosInd[0].periodo;
      this.cambiarPeriodo();
    },
    async refrescarPeriodos() {
      const r = await this.api(`/api/indicadores/${this.f.indicador_id}/periodos`);
      this.periodosInd = r.periodos; this._sugerido = r.sugerido;
    },
    cambiarPeriodo() {
      const m = this.medActual;
      this.f.valores = m ? { ...m.valores } : {};
      this.f.analisis = m?.analisis || ''; this.f.plan_mejora = m?.plan_mejora || ''; this.f.tocado = false;
      this.calc = m && m.estado !== 'observado' ? { ok: true, resultado: m.resultado, semaforo: m.semaforo, requiere_analisis: m.semaforo !== 'verde' } : null;
      if (m?.estado === 'observado') this.calcular();
    },
    async calcular() {
      this.f.tocado = true;
      const vals = {}; let completo = true;
      for (const v of this.ind.variables) {
        const x = this.f.valores[v.clave];
        if (x === '' || x === undefined || x === null) { vals[v.clave] = null; if (!v.opcional) completo = false; } else vals[v.clave] = Number(x);
      }
      if (!completo) { this.calc = null; return; }
      const n = ++this._seq;
      try { const r = await this.api('/api/calcular', { method: 'POST', body: { indicador_id: this.ind.id, valores: vals } }, true); if (n === this._seq) this.calc = r; }
      catch { }
    },
    analisisOk() { return this.f.analisis.trim().length >= 10 && this.f.plan_mejora.trim().length >= 10; },
    puedeEnviar() { return !this.bloqueado && this.calc?.ok && (!this.calc.requiere_analisis || this.analisisOk()); },
    async enviar() {
      this.busy = true;
      try {
        const vals = Object.fromEntries(this.ind.variables.map(v => { const x = this.f.valores[v.clave]; return [v.clave, x === '' || x === undefined || x === null ? null : Number(x)]; }));
        await this.api('/api/mediciones', { method: 'POST', body: { indicador_id: this.ind.id, periodo: this.f.periodo, valores: vals, analisis: this.f.analisis, plan_mejora: this.f.plan_mejora } });
        this.avisar('Carga enviada correctamente.');
        const per = this.f.periodo;
        await this.cargarIndicadores(); await this.refrescarPeriodos(); this.f.periodo = per; this.cambiarPeriodo();
      } catch { }
      this.busy = false;
    },

    // ------------------------------------------------------- historial
    async cargarHistorial(reset = true) {
      const q = new URLSearchParams({ limite: 50, desde: reset ? 0 : this.historial.length });
      for (const [k, v] of Object.entries({ ...this.filtro, ...this.filtro2 })) if (v) q.set(k, v);
      const r = await this.api('/api/mediciones?' + q);
      this.historial = reset ? r : [...this.historial, ...r]; this.histMas = r.length === 50;
    },
    async reabrir(m) {
      const nota = (this.reabrirNota[m.id] || '').trim();
      if (nota.length < 5) { this.avisar('Indique el motivo de la reapertura.', true); return; }
      this.busy = true;
      try { await this.api(`/api/mediciones/${m.id}/reabrir`, { method: 'POST', body: { accion: 'observar', nota } }); this.avisar('Carga devuelta al jefe de área.'); await this.cargarHistorial(); } catch { }
      this.busy = false;
    },
    // ------------------------------------------------------------ reportes
    get ejercicios() {
      const m0 = this.params.ejercicio_inicio || 1, hoy = new Date(), y = hoy.getFullYear() + (m0 > 1 && hoy.getMonth() + 1 >= m0 ? 1 : 0);
      return Array.from({ length: 7 }, (_, k) => ({ valor: y - k, etiqueta: m0 === 1 ? String(y - k) : `${y - k - 1}-${y - k}` }));
    },
    descargarFichas() {
      const q = new URLSearchParams(); if (this.rep.anio) q.set('ejercicio', this.rep.anio);
      for (const [k, v] of Object.entries(this.repFicha)) if (v) q.set(k, v);
      if (this.user.rol !== 'jefe' && this.rep.area_id && !this.repFicha.area_id) q.set('area_id', this.rep.area_id);
      return this.descargar('/api/reportes/fichas.xlsx?' + q, 'fichas_sigt.xlsx');
    },
    async descargar(url, nombreDef) {
      this.busy = true;
      try {
        const r = await fetch(url, { credentials: 'same-origin' });
        if (!r.ok) { let d = {}; try { d = await r.json(); } catch { } throw new Error(d.detail || 'No se pudo generar el archivo.'); }
        const nombre = (r.headers.get('content-disposition') || '').match(/filename="?([^";]+)/)?.[1] || nombreDef;
        const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = nombre; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 4000); this.avisar('Reporte descargado.');
      } catch (e) { this.avisar(e.message, true); }
      this.busy = false;
    },
    // ------------------------------------------------------ ficha del indicador
    async verFicha(id, ejercicio = '') {
      this.fv = { id, ejercicio, data: null, volver: this.view };
      await this.go('ficha'); await this.cargarFicha();
    },
    async cargarFicha() {
      this.fv.data = await this.api(`/api/indicadores/${this.fv.id}/ficha` + (this.fv.ejercicio ? `?ejercicio=${this.fv.ejercicio}` : ''));
      this.fv.ejercicio = this.fv.data.ejercicio;
      this.$nextTick(() => this.dibujarFicha());
    },
    fichaDescargar() { return this.descargar(`/api/reportes/fichas.xlsx?indicador_id=${this.fv.id}&ejercicio=${this.fv.ejercicio}`, 'ficha_sigt.xlsx'); },
    valorFicha(p, clave) { const m = p.medicion; return m && m.estado !== 'observado' && m.valores[clave] !== undefined ? nf(m.valores[clave], 2) : ''; },
    semaforoFranjas(i) {
      const f = x => (x === null || x === undefined) ? '' : this.fmt(x, i.unidad, i.decimales), mayor = i.sentido === 'mayor';
      return [{ n: 'Verde', c: 'verde', min: mayor ? f(i.meta) : f(i.meta_tope), max: mayor ? f(i.meta_tope) : f(i.meta) },
      { n: 'Amarillo', c: 'amarillo', min: mayor ? f(i.limite) : f(i.limite_tope), max: mayor ? f(i.limite_tope) : f(i.limite) },
      { n: 'Rojo', c: 'rojo', min: mayor ? '< ' + f(i.limite) : (i.limite_tope !== null ? '< ' + f(i.limite_tope) : ''), max: mayor ? (i.limite_tope !== null ? '> ' + f(i.limite_tope) : '') : '> ' + f(i.limite) }];
    },
    formulaDoc(i) {
      let t = i.formula; const todos = [...i.variables, ...(i.constantes || [])];
      todos.sort((a, b) => b.clave.length - a.clave.length).forEach(v => t = t.replace(new RegExp('\\b' + v.clave + '\\b', 'g'), v.clave.toUpperCase()));
      return [`${i.sigla || 'IND'} = ${t}`, ...i.variables.map(v => `${v.clave.toUpperCase()} = ${v.etiqueta}`), ...(i.constantes || []).map(c => `${c.clave.toUpperCase()} = ${c.etiqueta} (${c.valor})`)].join('\n');
    },
    dibujarFicha() {
      const d = this.fv.data, c = document.getElementById('ch-ficha');
      if (!d || !c || typeof Chart === 'undefined') return;
      Chart.getChart(c)?.destroy();
      const i = d.indicador, ps = d.periodos.filter(p => p.medicion && p.medicion.estado !== 'observado'), mayor = i.sentido === 'mayor';
      const linea = (l, v, col) => ({ label: l, data: ps.map(() => v), borderColor: col, borderDash: [6, 4], pointRadius: 0, borderWidth: 2 });
      const ds = [{ label: 'Indicador', data: ps.map(p => p.medicion.resultado), borderColor: BRAND, backgroundColor: BRAND, pointBackgroundColor: ps.map(p => SEM[p.medicion.semaforo]), pointRadius: 6, borderWidth: 2, tension: 0 }];
      const mn = mayor ? i.meta : i.meta_tope, mx = mayor ? i.meta_tope : i.meta;
      if (mn !== null && mn !== undefined) ds.push(linea('Mín.', mn, SEM.verde)); if (mx !== null && mx !== undefined) ds.push(linea('Máx.', mx, SEM.rojo));
      new Chart(c, { type: 'line', data: { labels: ps.map(p => p.corta), datasets: ds }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } } });
    },
    // ------------------------------------------------- parámetros y catálogos
    async guardarParametros() {
      this.busy = true;
      try { this.params = await this.api('/api/parametros', { method: 'PUT', body: { empresa: this.parForm.empresa, gerencia_emisora: this.parForm.gerencia_emisora, codigo_formato: this.parForm.codigo_formato, ejercicio_inicio: Number(this.parForm.ejercicio_inicio) } }); this.parForm = { ...this.params }; this.avisar('Parámetros guardados.'); } catch { }
      this.busy = false;
    },
    get catActual() { return this.catalogos.filter(c => c.tipo === this.catTab); },
    async guardarCat() {
      this.busy = true;
      try {
        const f = this.catForm, id = f.id;
        await this.api(id ? `/api/catalogos/${id}` : '/api/catalogos', { method: id ? 'PUT' : 'POST', body: { tipo: this.catTab, valor: f.valor, detalle: f.detalle } });
        this.catForm = { id: null, valor: '', detalle: '' }; this.catalogos = await this.api('/api/catalogos'); this.avisar('Lista actualizada.');
      } catch { }
      this.busy = false;
    },
    async eliminarCat(c) {
      if (!confirm(`¿Quitar «${c.valor}» de la lista? Las fichas que ya lo usan conservan el texto.`)) return;
      try { await this.api(`/api/catalogos/${c.id}`, { method: 'DELETE' }); this.catalogos = await this.api('/api/catalogos'); } catch { }
    },
    lista(tipo) { return this.catalogos.filter(c => c.tipo === tipo); },
    elegirRef() {
      const c = this.catalogos.find(c => c.tipo === 'proceso' && c.valor === this.ficha.ref_nombre);
      if (c && c.detalle && !this.ficha.ref_detalle) this.ficha.ref_detalle = c.detalle;
    },
    get sugerenciasPersonas() { return [...new Set(this.usuarios.map(u => u.nombre.split(' (')[0]))]; },
    // ------------------------------------------------------- importar Excel
    async analizarExcel(ev) {
      const f = ev.target.files[0]; if (!f) return;
      this.imp = { prev: null, sel: {}, cat: {}, res: null, crearAreas: true, cargando: true };
      try {
        const fd = new FormData(); fd.append('archivo', f);
        const r = await fetch('/api/importar/excel', { method: 'POST', body: fd, credentials: 'same-origin' });
        const d = await r.json(); if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : 'No se pudo leer el archivo.');
        this.imp.prev = d; this.imp.sel = Object.fromEntries(d.indicadores.map((_, k) => [k, !!d.indicadores[k].formula]));
        this.imp.cat = { gerencia: true, cargo: true, objetivo: true, proceso: true, area: true };
      } catch (e) { this.avisar(e.message, true); }
      this.imp.cargando = false; ev.target.value = '';
    },
    get impInicioDistinto() { const p = this.imp.prev; return !!p && p.indicadores.some(i => i.frecuencia !== 'mensual' && i.frecuencia !== 'eventual' && i.mediciones.length) && p.inicio_ejercicio && p.inicio_ejercicio !== p.inicio_actual; },
    get impSeleccion() { return this.imp.prev ? this.imp.prev.indicadores.filter((_, k) => this.imp.sel[k]) : []; },
    async confirmarImportacion() {
      const p = this.imp.prev; this.busy = true;
      try {
        const inds = this.impSeleccion, cats = [];
        for (const t of ['gerencia', 'cargo', 'objetivo', 'proceso']) if (this.imp.cat[t]) for (const v of p.catalogos[t] || []) cats.push({ tipo: t, valor: v, detalle: t === 'proceso' ? (p.detalle_procesos[v] || '') : '' });
        const nuevas = new Set(inds.filter(i => !i.area_existe).map(i => i.area));
        if (this.imp.cat.area && this.imp.crearAreas) (p.catalogos.area || []).forEach(a => nuevas.add(a));
        const cuerpo = { archivo: p.archivo, inicio_ejercicio: p.inicio_ejercicio, indicadores: inds.map(i => ({ ...i, objetivo: i.objetivo || '' })), catalogos: cats, areas_nuevas: [...nuevas] };
        this.imp.res = await this.api('/api/importar/confirmar', { method: 'POST', body: cuerpo });
        this.imp.prev = null; await this.cargarIndicadores(); this.areas = await this.api('/api/areas'); this.catalogos = await this.api('/api/catalogos'); this.avisar('Importación completada.');
      } catch { }
      this.busy = false;
    },
    descargarReporte() {
      const q = new URLSearchParams(); for (const [k, v] of Object.entries(this.rep)) if (v) q.set(k, v);
      return this.descargar('/api/reportes/general.xlsx?' + q, 'reporte_sigt.xlsx');
    },
    detalleHtml(m) {
      const et = Object.fromEntries(m.variables.map(v => [v.clave, v.etiqueta]));
      const filas = Object.entries(m.valores).map(([k, val]) => `<tr><td class="pr-4 text-slate-500">${esc(et[k] || k)}</td><td class="font-semibold">${esc(nf(val, 2))}</td></tr>`).join('');
      const bloque = (t, x) => x ? `<div class="mt-2"><div class="text-xs font-semibold uppercase text-slate-500">${t}</div><div class="text-sm whitespace-pre-line">${esc(x)}</div></div>` : '';
      const notas = m.notas.map(n => `<div class="text-sm bg-sky-50 border border-sky-200 rounded p-2 mt-1"><b>${esc(n.usuario.split(' (')[0])}</b> · ${esc(this.fecha(n.fecha))}<br>${esc(n.texto)}</div>`).join('');
      return `<div class="text-sm"><table class="text-sm">${filas}</table>
        ${bloque('Resultados del análisis', m.analisis)}${bloque('Correcciones / plan de mejora', m.plan_mejora)}
        <div class="text-xs text-slate-500 mt-2">Cargado por ${esc(m.cargado_por)} · ${esc(this.fecha(m.cargado_en))} · versión ${m.version}
        ${m.revisado_por ? ` · Revisado por ${esc(m.revisado_por.split(' (')[0])} · ${esc(this.fecha(m.revisado_en))}` : ''}</div>
        ${m.nota_revision ? `<div class="text-sm bg-amber-50 border border-amber-200 rounded p-2 mt-2"><b>Nota de revisión:</b> ${esc(m.nota_revision)}</div>` : ''}
        ${notas ? `<div class="mt-2 text-xs font-semibold uppercase text-slate-500">Notas de auditoría</div>${notas}` : ''}</div>`;
    },
    async agregarNota(m) {
      const t = (this.notasHist[m.id] || '').trim(); if (t.length < 3) return;
      this.busy = true;
      try { await this.api(`/api/mediciones/${m.id}/notas`, { method: 'POST', body: { texto: t } }); this.notasHist[m.id] = ''; this.avisar('Nota registrada.'); await this.cargarHistorial(); } catch { }
      this.busy = false;
    },

    // ---------------------------------------------------------- bandeja
    async cargarBandeja() { this.bandeja = await this.api('/api/mediciones?estado=enviado'); },
    async revisar(m, accion) {
      const nota = (this.notas[m.id] || '').trim();
      if (accion === 'observar' && nota.length < 5) { this.avisar('Indique el motivo de la devolución.', true); return; }
      this.busy = true;
      try {
        await this.api(`/api/mediciones/${m.id}/revision`, { method: 'POST', body: { accion, nota } });
        this.avisar(accion === 'aprobar' ? 'Carga aprobada.' : 'Carga devuelta al jefe de área.');
        await this.cargarBandeja();
      } catch { }
      this.busy = false;
    },

    // ------------------------------------------------------------ panel
    kpis() {
      const r = this.dash.resumen;
      return [{ t: 'Indicadores', v: r.total, c: NAVY }, { t: 'Cumplimiento', v: r.cumplimiento + '%', c: BRAND }, { t: 'En verde', v: r.verde, c: SEM.verde },
      { t: 'En alerta', v: r.amarillo, c: SEM.amarillo }, { t: 'Críticos', v: r.rojo, c: SEM.rojo }, { t: 'Por aprobar / pendientes', v: `${r.por_aprobar} / ${r.pendientes_carga}`, c: SEM.sin_datos }];
    },
    async cargarPanel() {
      this.dash = await this.api('/api/dashboard' + (this.panelArea ? '?area_id=' + this.panelArea : ''));
      if (!this.dash.indicadores.some(i => i.id === this.tendInd)) this.tendInd = this.dash.indicadores[0]?.id;
      this.$nextTick(() => this.dibujar());
    },
    dibujar() {
      if (!this.dash || typeof Chart === 'undefined') return;
      const nuevo = (id, cfg) => { const c = document.getElementById(id); if (!c) return; Chart.getChart(c)?.destroy(); new Chart(c, cfg); };
      Chart.defaults.font.family = 'system-ui, sans-serif';
      const r = this.dash.resumen, i = this.dash.indicadores.find(x => x.id === this.tendInd);
      if (i) {
        const s = i.serie, plano = a => a.map(x => Alpine.raw(x));
        nuevo('ch-tend', {
          type: 'line',
          data: {
            labels: s.map(p => p.etiqueta), datasets: [
              { label: 'Resultado', data: s.map(p => p.resultado), borderColor: BRAND, backgroundColor: BRAND, pointBackgroundColor: s.map(p => SEM[p.semaforo]), pointRadius: 6, pointBorderColor: '#fff', borderWidth: 2, tension: 0 },
              { label: 'Meta', data: s.map(p => p.meta), borderColor: NAVY, borderDash: [6, 4], pointRadius: 0, borderWidth: 2 },
              { label: 'Límite crítico', data: s.map(p => p.limite), borderColor: SEM.rojo, borderDash: [2, 4], pointRadius: 0, borderWidth: 1.5 }]
          },
          options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${this.fmt(c.parsed.y, i.unidad, i.decimales)}` } } }, scales: { y: { title: { display: true, text: i.unidad } } } }
        });
      }
      nuevo('ch-dist', {
        type: 'doughnut',
        data: { labels: ['Cumple', 'Alerta', 'Crítico', 'Sin datos'], datasets: [{ data: [r.verde, r.amarillo, r.rojo, r.sin_datos], backgroundColor: [SEM.verde, SEM.amarillo, SEM.rojo, SEM.sin_datos], borderWidth: 2, borderColor: '#fff' }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: { legend: { position: 'bottom' } } }
      });
      const A = this.dash.por_area, pct = k => A.map(a => Math.round(1000 * a[k] / a.total) / 10);
      nuevo('ch-area', {
        type: 'bar',
        data: { labels: A.map(a => a.area), datasets: [['Cumple', 'verde'], ['Alerta', 'amarillo'], ['Crítico', 'rojo']].map(([l, k]) => ({ label: l, data: pct(k), backgroundColor: SEM[k] })) },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.parsed.y}%` } } }, scales: { x: { stacked: true }, y: { stacked: true, max: 100, ticks: { callback: v => v + '%' } } } }
      });
    },

    // ----------------------------------------------------------- fichas
    get fichasFiltradas() {
      const q = this.fq.q.trim().toLowerCase();
      return this.indicadores.filter(i =>
        (!q || (i.codigo + ' ' + i.nombre + ' ' + i.area).toLowerCase().includes(q)) &&
        (!this.fq.area || i.area_id === Number(this.fq.area)) &&
        (!this.fq.frecuencia || i.frecuencia === this.fq.frecuencia) &&
        (this.fq.estado === '' || (this.fq.estado === 'activo') === i.activo));
    },
    nuevaFicha() {
      this.ficha = { codigo: '', nombre: '', objetivo: '', area_id: this.areas[0]?.id, unidad: '%', frecuencia: 'mensual', decimales: 2, sentido: 'mayor', meta: 90, limite: 80, meta_tope: null, limite_tope: null, formula: '', seguimiento: 'proceso', ref_nombre: '', ref_detalle: '', sigla: '', gerencia: '', lider: '', resp_medicion: '', resp_registro: '', resp_analisis: '', variables: [{ clave: '', etiqueta: '' }, { clave: '', etiqueta: '' }], constantes: [], fuente: '', notas: '', activo: true, n_mediciones: 0 };
      this.abrirFicha('Escriba la fórmula con las claves de las variables. Pulse «Guía de fórmulas» para ver funciones y ejemplos.');
    },
    editarFicha(i) {
      this.ficha = JSON.parse(JSON.stringify(i)); this.ficha.constantes ||= [];
      [...this.ficha.variables, ...this.ficha.constantes].forEach(v => v._manual = true);
      this.abrirFicha(''); this.validarFormula();
    },
    duplicarFicha(i) {
      this.ficha = { ...JSON.parse(JSON.stringify(i)), id: undefined, codigo: '', nombre: i.nombre + ' (copia)', n_mediciones: 0, activo: true };
      this.ficha.constantes ||= [];
      [...this.ficha.variables, ...this.ficha.constantes].forEach(v => v._manual = true);
      this.abrirFicha('Ficha duplicada: asigne un código nuevo.'); this.validarFormula();
    },
    abrirFicha(msg) { this.formulaMsg = { ok: true, txt: msg }; this.prueba = { valores: {}, res: null }; this.ay = ''; this.guia = false; this.modal = true; },
    get fichaBloqueada() { return (this.ficha.n_mediciones || 0) > 0; },
    slug: t => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').replace(/^(\d)/, 'v$1').slice(0, 30),
    autoClave(v) { if (!this.fichaBloqueada && !v._manual) { v.clave = this.slug(v.etiqueta); this.validarFormula(); } },
    mover(idx, d) { const a = this.ficha.variables, j = idx + d; if (j < 0 || j >= a.length) return; [a[idx], a[j]] = [a[j], a[idx]]; },
    semaforoAyuda() {
      const f = this.ficha, u = f.unidad;
      return f.sentido === 'mayor' ? `Verde: ≥ ${f.meta} · Amarillo: entre ${f.limite} y ${f.meta} · Rojo: < ${f.limite} (${u})`
        : `Verde: ≤ ${f.meta} · Amarillo: entre ${f.meta} y ${f.limite} · Rojo: > ${f.limite} (${u})`;
    },
    insertar(t, atras = 0) {
      const el = this.$refs.formula, f = this.ficha.formula || '';
      const a = el ? el.selectionStart : f.length, b = el ? el.selectionEnd : f.length;
      const pre = f.slice(0, a), sep = pre && !/[\s(]$/.test(pre) && /^[a-z0-9_(]/i.test(t) ? ' ' : '';
      this.ficha.formula = pre + sep + t + f.slice(b);
      this.$nextTick(() => { if (el) { el.focus(); const p = (pre + sep + t).length - atras; el.setSelectionRange(p, p); } });
      this.validarFormula();
    },
    usarEjemplo(e) {
      if (this.fichaBloqueada) { this.avisar('Este indicador tiene cargas: no se pueden cambiar las variables.', true); return; }
      this.ficha.variables = e.vars.map(([clave, etiqueta]) => ({ clave, etiqueta, _manual: true }));
      this.ficha.constantes = (e.consts || []).map(([clave, etiqueta, valor]) => ({ clave, etiqueta, valor, _manual: true }));
      this.ficha.formula = e.f; this.ficha.unidad = e.unidad; this.guia = false; this.validarFormula(); this.avisar('Ejemplo cargado: ajuste nombres, meta y límite.');
    },
    get nombresFormula() { return [...this.ficha.variables, ...(this.ficha.constantes || [])].map(v => v.clave).filter(Boolean); },
    async validarFormula() {
      if (!this.ficha.formula) return;
      try {
        const r = await this.api('/api/formula/validar', { method: 'POST', body: { formula: this.ficha.formula, claves: this.nombresFormula, variables: this.ficha.variables.map(v => v.clave).filter(Boolean) } }, true);
        this.formulaMsg = !r.ok ? { ok: false, txt: r.error } : r.sin_usar.length ? { ok: true, aviso: true, txt: '✔ Válida, pero no usa: ' + r.sin_usar.join(', ') } : { ok: true, txt: '✔ Fórmula válida' };
        if (r.ok) this.probar();
      } catch { }
    },
    async probar() {
      const f = this.ficha, valores = {};
      for (const v of f.variables.filter(v => v.clave)) {
        const x = this.prueba.valores[v.clave];
        if (x === '' || x === undefined || x === null) { if (!v.opcional) { this.prueba.res = null; return; } valores[v.clave] = Number(v.defecto || 0); } else valores[v.clave] = Number(x);
      }
      const constantes = Object.fromEntries((f.constantes || []).filter(c => c.clave).map(c => [c.clave, Number(c.valor)]));
      try { this.prueba.res = await this.api('/api/formula/probar', { method: 'POST', body: { formula: f.formula, valores, constantes, decimales: Number(f.decimales), meta: Number(f.meta), limite: Number(f.limite), meta_tope: f.meta_tope === '' ? null : f.meta_tope, limite_tope: f.limite_tope === '' ? null : f.limite_tope, sentido: f.sentido } }, true); } catch { }
    },
    cuerpoFicha(f) {
      return {
        codigo: f.codigo, nombre: f.nombre, objetivo: f.objetivo, area_id: f.area_id, unidad: f.unidad, frecuencia: f.frecuencia, sentido: f.sentido, formula: f.formula,
        variables: f.variables.map(v => ({ clave: v.clave, etiqueta: v.etiqueta, ayuda: v.ayuda || '', unidad: v.unidad || '', opcional: !!v.opcional, defecto: Number(v.defecto || 0), negativo: !!v.negativo })),
        constantes: (f.constantes || []).map(c => ({ clave: c.clave, etiqueta: c.etiqueta, valor: Number(c.valor) })),
        decimales: Number(f.decimales ?? 2), fuente: f.fuente || '', notas: f.notas || '', meta: f.meta, limite: f.limite,
        meta_tope: f.meta_tope === '' ? null : f.meta_tope, limite_tope: f.limite_tope === '' ? null : f.limite_tope, activo: f.activo,
        seguimiento: f.seguimiento || 'proceso', ref_nombre: f.ref_nombre || '', ref_detalle: f.ref_detalle || '', sigla: f.sigla || '', gerencia: f.gerencia || '',
        lider: f.lider || '', resp_medicion: f.resp_medicion || '', resp_registro: f.resp_registro || '', resp_analisis: f.resp_analisis || ''
      };
    },
    async guardarFicha() {
      this.busy = true;
      try {
        const f = this.ficha, id = f.id;
        await this.api(id ? `/api/indicadores/${id}` : '/api/indicadores', { method: id ? 'PUT' : 'POST', body: this.cuerpoFicha(f) });
        this.modal = false; this.avisar(id ? 'Ficha actualizada.' : 'Indicador creado.'); await this.cargarIndicadores();
      } catch { }
      this.busy = false;
    },
    async alternarActivo(i) {
      const accion = i.activo ? 'archivar' : 'restaurar';
      if (i.activo && !confirm(`¿Archivar ${i.codigo}? Dejará de aparecer para cargar datos; el historial se conserva.`)) return;
      try { await this.api(`/api/indicadores/${i.id}`, { method: 'PUT', body: this.cuerpoFicha({ ...i, activo: !i.activo }) }); this.avisar(`Indicador ${i.activo ? 'archivado' : 'restaurado'}.`); await this.cargarIndicadores(); } catch { }
    },
    async eliminarFicha(i) {
      const msg = i.n_mediciones ? `${i.codigo} tiene ${i.n_mediciones} carga(s) registradas: no se borrará, se archivará para conservar la trazabilidad. ¿Continuar?` : `¿Eliminar definitivamente el indicador ${i.codigo}?`;
      if (!confirm(msg)) return;
      try { const r = await this.api(`/api/indicadores/${i.id}`, { method: 'DELETE' }); this.avisar(r.archivado ? 'Indicador archivado (tiene historial de cargas).' : 'Indicador eliminado.'); await this.cargarIndicadores(); } catch { }
    },

    // ----------------------------------------------------- administración
    setup() {
      const pasos = [
        { n: 1, t: 'Crear las áreas de la empresa', ok: this.areas.length > 0, v: 'org' },
        { n: 2, t: 'Registrar usuarios (jefes de área y gerente / auditor)', ok: this.usuarios.some(u => u.rol === 'jefe') && this.usuarios.some(u => u.rol === 'gerente'), v: 'org' },
        { n: 3, t: 'Crear las fichas de indicadores', ok: this.indicadores.length > 0, v: 'fichas' }];
      return { pasos, completo: pasos.every(p => p.ok) };
    },
    async guardarArea() {
      this.busy = true;
      try {
        const id = this.areaForm.id;
        await this.api(id ? `/api/areas/${id}` : '/api/areas', { method: id ? 'PUT' : 'POST', body: { nombre: this.areaForm.nombre } });
        this.areaForm = { id: null, nombre: '' }; this.areas = await this.api('/api/areas'); this.usuarios = await this.api('/api/usuarios'); this.avisar('Área guardada.');
      } catch { }
      this.busy = false;
    },
    async eliminarArea(a) {
      if (!confirm(`¿Eliminar el área «${a.nombre}»?`)) return;
      try { await this.api(`/api/areas/${a.id}`, { method: 'DELETE' }); this.areas = await this.api('/api/areas'); this.avisar('Área eliminada.'); } catch { }
    },
    nuevoUsuario() { this.usuario = { username: '', nombre: '', rol: 'jefe', area_id: '', password: '', activo: true }; this.modalUsuario = true; },
    editarUsuario(x) { this.usuario = { ...x, area_id: x.area_id || '', password: '' }; this.modalUsuario = true; },
    async guardarUsuario() {
      this.busy = true;
      try {
        const u = this.usuario, id = u.id;
        const body = { nombre: u.nombre, rol: u.rol, area_id: u.rol === 'jefe' ? (u.area_id || null) : null };
        if (id) { body.activo = u.activo; if (u.password) body.password = u.password; } else { body.username = u.username; body.password = u.password; }
        await this.api(id ? `/api/usuarios/${id}` : '/api/usuarios', { method: id ? 'PUT' : 'POST', body });
        this.modalUsuario = false; this.usuarios = await this.api('/api/usuarios'); this.avisar('Usuario guardado.');
      } catch { }
      this.busy = false;
    },
    abrirClave() { this.menu = false; this.clave = { actual: '', nueva: '', repetir: '' }; this.modalClave = true; },
    async cambiarClave() {
      this.busy = true;
      try { await this.api('/api/cambiar-clave', { method: 'POST', body: { actual: this.clave.actual, nueva: this.clave.nueva } }); this.modalClave = false; this.avisar('Contraseña actualizada.'); } catch { }
      this.busy = false;
    },

    // --------------------------------------------------------- bitácora
    async cargarBitacora(reset = true) {
      const q = new URLSearchParams({ limite: 100, desde: reset ? 0 : this.bitacora.length });
      if (this.bitAccion) q.set('accion', this.bitAccion); if (this.bitUsuario.trim()) q.set('usuario', this.bitUsuario.trim());
      const r = await this.api('/api/bitacora?' + q);
      this.bitacora = reset ? r : [...this.bitacora, ...r]; this.bitMas = r.length === 100;
    },
    async verificarBitacora() {
      const r = await this.api('/api/bitacora/verificar');
      this.avisar(r.ok ? `Integridad verificada: ${r.total} registros sin alteraciones.` : `¡Alteración detectada en el registro #${r.primer_error_id}!`, !r.ok);
    },
    resumenBit(b) {
      const d = b.detalle || {}, c = b.codigo ? b.codigo + ' · ' : '';
      switch (b.accion) {
        case 'CARGA': case 'REENVIO': return `${c}${d.periodo}: resultado ${d.resultado} (${d.semaforo}). Valores: ` + Object.entries(d.valores || {}).map(([k, v]) => `${k}=${v}`).join(', ') + (d.plan_mejora ? `. Plan: ${d.plan_mejora}` : '');
        case 'APROBACION': case 'OBSERVACION': return `${c}${d.periodo}` + (d.nota ? `: ${d.nota}` : '');
        case 'NOTA_AUDITORIA': return `${c}${d.periodo}: ${d.texto}`;
        case 'REAPERTURA': return `${c}${d.periodo}: ${d.nota}`;
        case 'REPORTE_EXPORTADO': return `Reporte Excel (${d.filas} filas) ${(d.filtros || []).join(' · ')}`;
        case 'INDICADOR_EDITADO': return `${d.codigo}: cambios en ` + Object.keys(d.cambios || {}).join(', ');
        case 'INICIO_SESION': return 'Inicio de sesión';
        case 'IMPORTACION': return `${d.codigo} ← ${d.archivo} (${d.hoja}): ${(d.periodos || []).length} períodos importados`;
        case 'PARAMETROS_EDITADOS': return 'Cambios: ' + Object.keys(d.cambios || {}).join(', ');
        case 'CATALOGO_CREADO': case 'CATALOGO_ELIMINADO': return d.valor || `${d.cantidad || ''} elementos (${d.origen || ''})`;
        case 'CATALOGO_EDITADO': return `${d.tipo}: ${(d.antes || [])[0]} → ${(d.despues || [])[0]}`;
        case 'CLAVE_CAMBIADA': return 'Cambio de contraseña';
        case 'USUARIO_CREADO': case 'USUARIO_EDITADO': return `${d.username || ''} ${d.rol || ''} ` + Object.keys(d.cambios || {}).join(', ');
        case 'AREA_CREADA': case 'AREA_ELIMINADA': return d.nombre;
        case 'AREA_EDITADA': return `${d.antes} → ${d.despues}`;
        default: return `${d.codigo || ''} ${d.nombre || ''}`;
      }
    },
  };
}
