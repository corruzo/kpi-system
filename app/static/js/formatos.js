/* Formatos de presentación: números, fechas, semáforos, estados y textos de metas y fórmulas. */
SIGT.modulos.formatos = () => ({


    fmt(v, u, d = 2) {
      if (v === null || v === undefined) return '—';
      const n = nf(v, d ?? 2);
      return ({ '%': n + '%', 'días': n + ' d', 'USD': '$' + n, 'TM': n + ' TM', 'cantidad': n })[u] ?? `${n} ${u}`;
    },
    fecha: iso => iso ? new Date(iso).toLocaleString('es-VE', { dateStyle: 'short', timeStyle: 'short' }) : '',
    fechaCorta: d => d ? new Date(d + 'T12:00:00').toLocaleDateString('es-VE', { day: '2-digit', month: 'short', year: 'numeric' }) : '',
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
    icono: id => ICONOS[id],
    cap: t => t.charAt(0).toUpperCase() + t.slice(1),
});
