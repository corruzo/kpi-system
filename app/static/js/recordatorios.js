/* Recordatorios de carga (administrador y gerente): quién tiene períodos pendientes y aviso por correo con un mensaje ya redactado.
   El correo se abre en el programa de correo de la computadora (Outlook, si es el predeterminado) mediante un enlace mailto:
   con destinatario, asunto y texto listos; la persona solo pulsa «Enviar». */
const ENLACE_APP = 'https://sgctpv.vercel.app';   // dirección que reciben los encargados en el mensaje

SIGT.modulos.recordatorios = () => ({
    rec: { data: null, cargando: false, plantilla: 'amable', abierto: null, soloConDeuda: true },

    ganchos: {
      entrar: { recordatorios() { return this.cargarRecordatorios(); } },
      salida() { this.rec = { data: null, cargando: false, plantilla: 'amable', abierto: null, soloConDeuda: true }; },
    },

    // Mensajes prescritos. {nombre}, {lista}, {enlace} y {remitente} se sustituyen por los datos de cada encargado.
    PLANTILLAS: {
      amable: {
        titulo: 'Recordatorio amable',
        asunto: 'Recordatorio: carga de indicadores en SPE TPV',
        cuerpo: 'Estimado(a) {nombre}:\n\nLe recordamos cargar su información en la aplicación SPE TPV. Tiene pendiente:\n\n{lista}\n\nPuede ingresar aquí: {enlace}\n\nMuchas gracias por su colaboración.\n\nSaludos cordiales,\n{remitente}',
      },
      urgente: {
        titulo: 'Urgente (carga vencida)',
        asunto: 'URGENTE: carga de indicadores vencida en SPE TPV',
        cuerpo: 'Estimado(a) {nombre}:\n\nSu carga de información en la aplicación SPE TPV se encuentra vencida y es necesario completarla a la brevedad. Pendiente:\n\n{lista}\n\nIngrese aquí para cargarla: {enlace}\n\nSi tiene algún inconveniente para hacerlo, avíseme para apoyarle.\n\nSaludos cordiales,\n{remitente}',
      },
      devuelta: {
        titulo: 'Carga devuelta para corregir',
        asunto: 'Corrección pendiente de su carga en SPE TPV',
        cuerpo: 'Estimado(a) {nombre}:\n\nTiene cargas devueltas o pendientes en la aplicación SPE TPV que requieren su atención. Le recordamos revisarlas y completarlas:\n\n{lista}\n\nIngrese aquí: {enlace}\n\nGracias por su pronta gestión.\n\nSaludos cordiales,\n{remitente}',
      },
    },

    // Pide una página de encargados (el filtro «solo con pendientes» y los totales los calcula el servidor)
    async cargarRecordatorios(pagina = 1) {
      this.rec.cargando = true;
      try {
        const p = this.pg('recordatorios'), n = Math.max(1, pagina);
        const d = await this.api(`/api/recordatorios?solo_pendientes=${this.rec.soloConDeuda}&limite=${p.por}&desde=${(n - 1) * p.por}`);
        p.total = d.total; p.pagina = n; this.rec.data = d;
      } catch { }
      this.rec.cargando = false;
    },
    get recLista() { return this.rec.data?.encargados || []; },
    get recDeben() { return this.rec.data?.deben || 0; },
    get recSinCorreo() { return this.rec.data?.sin_correo || 0; },

    // Texto con los pendientes de un encargado: un renglón por indicador (máx. 8, y los períodos de cada uno acotados)
    textoPendientesDe(e) {
      const filas = e.indicadores.slice(0, 8).map(i => {
        const nombres = i.periodos.slice(0, 6).map(p => p.etiqueta + (p.devuelto ? ' (devuelta)' : ''));
        const resto = i.total - nombres.length;
        return `- ${i.codigo} · ${i.nombre}: ${nombres.join(', ')}${resto > 0 ? ` y ${resto} más` : ''}`;
      });
      if (e.indicadores.length > 8) filas.push(`- … y ${e.indicadores.length - 8} indicador(es) más`);
      return filas.join('\n');
    },
    mensaje(e) {
      const p = this.PLANTILLAS[this.rec.plantilla];
      const datos = { nombre: e.nombre, lista: this.textoPendientesDe(e) || '- (sin períodos pendientes)', enlace: ENLACE_APP, remitente: this.user.nombre };
      const llenar = t => t.replace(/\{(\w+)\}/g, (_, k) => datos[k] ?? '');
      return { asunto: llenar(p.asunto), cuerpo: llenar(p.cuerpo) };
    },
    enlaceCorreo(e) {
      const m = this.mensaje(e);
      return `mailto:${encodeURIComponent(e.email).replace('%40', '@')}?subject=${encodeURIComponent(m.asunto)}&body=${encodeURIComponent(m.cuerpo.replace(/\n/g, '\r\n'))}`;
    },
    // Abre el correo ya redactado en el programa de correo (Outlook) y deja constancia en la bitácora.
    async enviarRecordatorio(e) {
      const a = document.createElement('a'); a.href = this.enlaceCorreo(e); document.body.appendChild(a); a.click(); a.remove();
      try { await this.api(`/api/recordatorios/${e.id}`, { method: 'POST', body: { mensaje: this.rec.plantilla } }, true); await this.cargarRecordatorios(this.pg('recordatorios').pagina); } catch { }
      this.avisar('Se abrió el correo en Outlook. Revíselo y pulse «Enviar».');
    },
    async copiarMensaje(e) {
      const m = this.mensaje(e);
      try { await navigator.clipboard.writeText(`Para: ${e.email}\nAsunto: ${m.asunto}\n\n${m.cuerpo}`); this.avisar('Mensaje copiado. Péguelo en un correo nuevo.'); }
      catch { this.avisar('No se pudo copiar. Seleccione el texto de la vista previa y cópielo.', true); }
    },
    ultimoAviso(e) { return e.ultimo_recordatorio ? 'Último aviso: ' + this.fecha(e.ultimo_recordatorio) : 'Aún no se le ha enviado aviso'; },
});
