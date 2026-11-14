// Results explorer (2026-11-13): small-multiple grouped bars + pivot + long table over console.results.summary().
// No external requests. Labels come from data files, so they are inserted with textContent only.
(function () {
  const el = document.getElementById('rx-data'); if (!el) return;
  const D = JSON.parse(el.textContent);
  const $ = id => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const POL = Object.keys(D.policies);                       // fixed order = fixed color slot
  const SCF = D.scaffolds;
  const RELS = D.relationships.filter(r => r.measured).map(r => r.label);
  const pct = v => v == null ? '–' : Math.round(100 * v) + '%';
  const ci = c => c ? `${Math.round(100 * c.lo)}–${Math.round(100 * c.hi)}` : '';
  const polColor = p => `var(--m${(POL.indexOf(p) % 8) + 1})`;
  const scfColor = s => `var(--s${SCF.indexOf(s) + 1})`;
  const relOrder = l => D.relationships.findIndex(r => r.label === l);
  const rows = D.rows.map(r => ({ ...r, rel: r.relationship }));

  // ---- state (kept in the URL hash so a view can be linked) ----
  const DS = Object.keys(D.datasets || {});
  const S = { ds: DS.includes('pilot2') ? 'pilot2' : DS[0], metric: 'correct', compare: 'policy', pol: new Set(POL.filter(p => rows.some(r => r.policy === p))),
              scf: new Set(SCF), rel: new Set(RELS), ci: true, earlier: false };
  try {
    const h = new URLSearchParams(location.hash.slice(1));
    if (h.get('m') && D.metrics[h.get('m')]) S.metric = h.get('m');
    if (h.get('d') && DS.includes(h.get('d'))) S.ds = h.get('d');
    if (h.get('c')) S.compare = h.get('c') === 'scaffold' ? 'scaffold' : 'policy';
    ['pol', 'scf', 'rel'].forEach(k => { if (h.has(k)) S[k] = new Set(h.get(k).split('|').filter(Boolean)); });
    if (h.has('ci')) S.ci = h.get('ci') === '1';
    if (h.has('e')) S.earlier = h.get('e') === '1';
  } catch (e) { /* bad hash: defaults */ }
  const saveHash = () => {
    const h = new URLSearchParams({ d: S.ds, m: S.metric, c: S.compare, pol: [...S.pol].join('|'), scf: [...S.scf].join('|'),
                                    rel: [...S.rel].join('|'), ci: S.ci ? '1' : '0', e: S.earlier ? '1' : '0' });
    history.replaceState(null, '', '#' + h.toString());
  };

  // ---- controls ----
  const msel = $('rx-metric');
  Object.entries(D.metrics).forEach(([k, v]) => { const o = document.createElement('option'); o.value = k; o.textContent = v.label; msel.appendChild(o); });
  const dsel = $('rx-dataset');
  DS.forEach(k => { const o = document.createElement('option'); o.value = k; o.textContent = D.datasets[k]; dsel.appendChild(o); });
  dsel.value = S.ds; dsel.addEventListener('change', () => { S.ds = dsel.value; draw(); });
  msel.value = S.metric; $('rx-compare').value = S.compare; $('rx-ci').checked = S.ci; $('rx-earlier').checked = S.earlier;
  function boxes(host, items, set, label) {
    items.forEach(it => {
      const l = document.createElement('label'); const i = document.createElement('input');
      i.type = 'checkbox'; i.checked = set.has(it); i.addEventListener('change', () => { i.checked ? set.add(it) : set.delete(it); draw(); });
      l.appendChild(i); l.appendChild(document.createTextNode(' ' + label(it))); host.appendChild(l);
    });
  }
  boxes($('rx-policies'), POL.filter(p => rows.some(r => r.policy === p)), S.pol, p => D.policies[p]);
  boxes($('rx-scaffolds'), SCF, S.scf, s => s);
  boxes($('rx-arms'), RELS, S.rel, s => s);
  msel.addEventListener('change', () => { S.metric = msel.value; draw(); });
  $('rx-compare').addEventListener('change', e => { S.compare = e.target.value; draw(); });
  $('rx-ci').addEventListener('change', e => { S.ci = e.target.checked; draw(); });
  $('rx-earlier').addEventListener('change', e => { S.earlier = e.target.checked; draw(); });

  // ---- helpers ----
  const filtered = () => rows.filter(r => r.cells === S.ds && S.pol.has(r.policy) && S.scf.has(r.scaffold) && S.rel.has(r.rel) &&
                                         (S.earlier || r.variant !== 'earlier'));
  const variantTag = r => r.variant === 'earlier' ? ` (${r.thinking === 'in_structure' ? 'YAML in thinking' : 'mode ' + r.mode_line})` : '';
  const seriesOf = r => S.compare === 'policy'
    ? { id: r.policy + (r.variant === 'earlier' ? '|' + r.run : ''), name: r.model + variantTag(r), color: polColor(r.policy), earlier: r.variant === 'earlier', ord: POL.indexOf(r.policy) * 10 + (r.variant === 'earlier' ? 1 : 0) }
    : { id: r.scaffold + (r.variant === 'earlier' ? '|' + r.run : ''), name: r.scaffold + variantTag(r), color: scfColor(r.scaffold), earlier: r.variant === 'earlier', ord: SCF.indexOf(r.scaffold) * 10 + (r.variant === 'earlier' ? 1 : 0) };
  const facetOf = r => S.compare === 'policy' ? r.scaffold : r.policy;
  const facetName = f => S.compare === 'policy' ? `Scaffold: ${f}` : D.policies[f] || f;
  const facetOrd = f => S.compare === 'policy' ? SCF.indexOf(f) : POL.indexOf(f);
  function svg(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
  function txt(tag, attrs, s, parent) { const e = svg(tag, attrs, parent); e.textContent = s; return e; }
  function barPath(x, y, w, h) {                         // 4px rounded data end, square at the baseline
    const r = Math.min(4, w / 2, h);
    return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
  }

  // ---- tooltip ----
  const tip = $('rx-tip');
  function showTip(ev, r, s, c) {
    tip.replaceChildren();
    const v = document.createElement('div'); v.className = 'v'; v.textContent = pct(c.m) + (c ? `  [${ci(c)}]` : ''); tip.appendChild(v);
    const a = document.createElement('div'); const k = document.createElement('span'); k.className = 'key'; k.style.background = s.color;
    a.appendChild(k); a.appendChild(document.createTextNode(`${r.model}${variantTag(r)} · ${r.scaffold}`)); tip.appendChild(a);
    const b = document.createElement('div'); b.textContent = `${r.rel} (arm ${r.arm})`; tip.appendChild(b);
    const d = document.createElement('div'); d.className = 's'; d.textContent = `${D.metrics[S.metric].label} · ${c.n} replies · ${c.nx} X1 · k=${r.k}`; tip.appendChild(d);
    const e = document.createElement('div'); e.className = 's'; e.textContent = 'click: open the run'; tip.appendChild(e);
    tip.hidden = false;
    const bx = ev.clientX != null ? ev.clientX : ev.target.getBoundingClientRect().right;
    const by = ev.clientY != null ? ev.clientY : ev.target.getBoundingClientRect().top;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(window.innerWidth - w - 8, bx + 14) + 'px';
    tip.style.top = Math.max(8, by - h - 10) + 'px';
  }
  const hideTip = () => { tip.hidden = true; };

  // ---- chart ----
  function draw() {
    saveHash();
    $('rx-help').textContent = D.metrics[S.metric].help;
    const F = filtered();
    const series = new Map(); F.forEach(r => { const s = seriesOf(r); if (!series.has(s.id)) series.set(s.id, s); });
    const sers = [...series.values()].sort((a, b) => a.ord - b.ord);
    // legend
    const lg = $('rx-legend'); lg.replaceChildren();
    sers.forEach(s => { const sp = document.createElement('span'); const sw = document.createElement('span'); sw.className = 'sw';
      sw.style.background = s.color; if (s.earlier) sw.style.opacity = .45; sp.appendChild(sw); sp.appendChild(document.createTextNode(s.name)); lg.appendChild(sp); });
    const facets = [...new Set(F.map(facetOf))].sort((a, b) => facetOrd(a) - facetOrd(b));
    const host = $('rx-panels'); host.replaceChildren();
    if (!F.length) { const p = document.createElement('p'); p.className = 'muted'; p.textContent = 'Nothing matches the filters.'; host.appendChild(p); }
    facets.forEach(f => {
      const R = F.filter(r => facetOf(r) === f);
      const rels = [...new Set(R.map(r => r.rel))].sort((a, b) => relOrder(a) - relOrder(b));
      const ps = sers.filter(s => R.some(r => seriesOf(r).id === s.id));
      const div = document.createElement('div'); div.className = 'rx-panel';
      const h = document.createElement('h3'); h.textContent = facetName(f); div.appendChild(h);
      const W = 560, H = 250, ml = 34, mr = 6, mt = 10, mb = 40, pw = W - ml - mr, ph = H - mt - mb;
      const s = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img',
        'aria-label': `${D.metrics[S.metric].label} by relationship, ${facetName(f)}; bars: ${ps.map(x => x.name).join(', ')}` }, div);
      [0, .25, .5, .75, 1].forEach(t => { const y = mt + ph * (1 - t);
        svg('line', { x1: ml, x2: W - mr, y1: y, y2: y, class: t === 0 ? 'ax' : 'gl' }, s);
        txt('text', { x: ml - 5, y: y + 3.5, 'text-anchor': 'end' }, Math.round(t * 100) + '%', s); });
      const gw = pw / Math.max(1, rels.length), inner = gw * 0.82, bw = Math.max(4, Math.min(30, inner / Math.max(1, ps.length) - 2));
      rels.forEach((rel, gi) => {
        const gx = ml + gi * gw + (gw - (bw + 2) * ps.length + 2) / 2;
        const words = rel.split(' '); const mid = Math.ceil(words.length / 2);
        const lines = rel.length > 16 ? [words.slice(0, mid).join(' '), words.slice(mid).join(' ')] : [rel];
        lines.forEach((ln, li) => txt('text', { x: ml + gi * gw + gw / 2, y: H - mb + 15 + li * 13, 'text-anchor': 'middle' }, ln, s));
        let any = false;
        ps.forEach((se, si) => {
          const r = R.find(r => r.rel === rel && seriesOf(r).id === se.id); if (!r) return;
          const c = r.metrics[S.metric]; if (!c) return; any = true;
          const x = gx + si * (bw + 2), y = mt + ph * (1 - c.m), bh = Math.max(0.5, ph * c.m);
          const g = svg('g', { class: 'bar', tabindex: 0, role: 'link', 'aria-label': `${se.name}, ${rel}: ${pct(c.m)}` }, s);
          svg('rect', { x: x - 1, y: mt, width: bw + 2, height: ph, fill: 'transparent' }, g);     // hit area = full column
          svg('path', { d: barPath(x, y, bw, bh), class: 'f', style: `fill:${se.color};fill-opacity:${se.earlier ? .45 : 1}` }, g);
          if (S.ci && c.hi > c.lo) { const cx = x + bw / 2, y1 = mt + ph * (1 - c.hi), y2 = mt + ph * (1 - c.lo), cap = Math.min(4, bw / 2);
            svg('line', { x1: cx, x2: cx, y1, y2, class: 'ci' }, g);
            svg('line', { x1: cx - cap, x2: cx + cap, y1, y2: y1, class: 'ci' }, g);
            svg('line', { x1: cx - cap, x2: cx + cap, y1: y2, y2, class: 'ci' }, g); }
          g.addEventListener('pointermove', ev => showTip(ev, r, se, c)); g.addEventListener('pointerleave', hideTip);
          g.addEventListener('focus', ev => showTip(ev, r, se, c)); g.addEventListener('blur', hideTip);
          const go = () => { location.href = '/run?run=' + encodeURIComponent(r.run); };
          g.addEventListener('click', go); g.addEventListener('keydown', ev => { if (ev.key === 'Enter') go(); });
        });
        if (!any) txt('text', { x: ml + gi * gw + gw / 2, y: mt + ph - 6, 'text-anchor': 'middle', class: 'na' }, 'n/a', s);
      });
      host.appendChild(div);
    });
    pivot(F); long(F);
  }

  // ---- pivot table: rows = model x scaffold (x variant), columns = relationships, current metric ----
  function pivot(F) {
    $('rx-pivot-title').textContent = D.metrics[S.metric].label;
    const t = $('rx-pivot'); t.replaceChildren();
    const rels = [...new Set(F.map(r => r.rel))].sort((a, b) => relOrder(a) - relOrder(b));
    const hr = t.insertRow(); ['Model', 'Scaffold'].concat(rels).forEach(h => { const th = document.createElement('th'); th.textContent = h; hr.appendChild(th); });
    const keys = [...new Set(F.map(r => r.run))];
    const meta = k => F.find(r => r.run === k);
    keys.sort((a, b) => { const x = meta(a), y = meta(b); return (POL.indexOf(x.policy) - POL.indexOf(y.policy)) || (SCF.indexOf(x.scaffold) - SCF.indexOf(y.scaffold)) || (x.variant > y.variant ? 1 : -1); });
    keys.forEach(k => {
      const m = meta(k); const tr = t.insertRow(); if (m.variant === 'earlier') tr.className = 'earlier';
      const a = tr.insertCell();
      a.textContent = m.model + variantTag(m);
      const b = tr.insertCell(); const ln = document.createElement('a'); ln.href = '/run?run=' + encodeURIComponent(k); ln.textContent = m.scaffold; b.appendChild(ln);
      rels.forEach(rel => {
        const td = tr.insertCell(); td.className = 'num cell';
        const r = F.find(r => r.run === k && r.rel === rel); const c = r && r.metrics[S.metric];
        if (!c) { td.textContent = '–'; return; }
        td.title = `${c.nx} X1 · arm ${r.arm}`;
        const v = document.createElement('b'); v.textContent = pct(c.m); td.appendChild(v);
        const s = document.createElement('div'); s.className = 'ci'; s.textContent = `${ci(c)} · n=${c.n}`; td.appendChild(s);
        const fill = document.createElement('div'); fill.className = 'fill'; fill.style.width = (100 * c.m).toFixed(1) + '%'; td.appendChild(fill);
      });
    });
  }

  // ---- long table: every metric ----
  const LCOLS = [['Model', r => r.model + variantTag(r)], ['Scaffold', r => r.scaffold], ['Relationship', r => r.rel], ['Arm', r => r.arm], ['k', r => r.k]];
  let sortCol = null, sortDir = 1, lastF = [];
  function long(F) {
    lastF = F;
    const t = $('rx-long'); t.replaceChildren();
    const hr = t.insertRow();
    const heads = LCOLS.map(c => c[0]).concat(Object.values(D.metrics).map(m => m.label), ['Replies', 'X1', 'Run']);
    heads.forEach((h, i) => { const th = document.createElement('th'); th.textContent = h + (sortCol === i ? (sortDir > 0 ? ' ▲' : ' ▼') : '');
      th.addEventListener('click', () => { sortDir = sortCol === i ? -sortDir : 1; sortCol = i; long(lastF); }); hr.appendChild(th); });
    const mk = Object.keys(D.metrics);
    const val = (r, i) => i < LCOLS.length ? LCOLS[i][1](r)
      : i < LCOLS.length + mk.length ? (r.metrics[mk[i - LCOLS.length]] || { m: -1 }).m
      : i === LCOLS.length + mk.length ? (r.metrics.correct || {}).n : i === LCOLS.length + mk.length + 1 ? (r.metrics.correct || {}).nx : r.run;
    const R = F.slice().sort((a, b) => {
      if (sortCol == null) return (POL.indexOf(a.policy) - POL.indexOf(b.policy)) || (SCF.indexOf(a.scaffold) - SCF.indexOf(b.scaffold)) || (relOrder(a.rel) - relOrder(b.rel));
      const x = val(a, sortCol), y = val(b, sortCol); return (x > y ? 1 : x < y ? -1 : 0) * sortDir; });
    R.forEach(r => {
      const tr = t.insertRow(); if (r.variant === 'earlier') tr.className = 'earlier';
      LCOLS.forEach(c => { tr.insertCell().textContent = c[1](r); });
      mk.forEach(k => { const td = tr.insertCell(); td.className = 'num'; const c = r.metrics[k];
        if (!c) { td.textContent = '–'; return; }
        const v = document.createElement('span'); v.textContent = pct(c.m); td.appendChild(v);
        const s = document.createElement('span'); s.className = 'ci'; s.textContent = ' ' + ci(c); td.appendChild(s); });
      const c0 = r.metrics.correct || {};
      const n = tr.insertCell(); n.className = 'num'; n.textContent = c0.n ?? '–';
      const nx = tr.insertCell(); nx.className = 'num'; nx.textContent = c0.nx ?? '–';
      const rl = tr.insertCell(); const a = document.createElement('a'); a.href = '/run?run=' + encodeURIComponent(r.run); a.textContent = r.run.split('/').pop(); a.className = 'mono small'; rl.appendChild(a);
    });
  }

  // ---- CSV of the filtered rows (every metric with its interval) ----
  $('rx-csv').addEventListener('click', () => {
    const mk = Object.keys(D.metrics);
    const head = ['model', 'policy', 'scaffold', 'variant', 'relationship', 'arm', 'k', 'run'].concat(...mk.map(k => [k, k + '_lo', k + '_hi', k + '_n', k + '_nx']));
    const esc = v => { const s = v == null ? '' : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
    const lines = [head.join(',')].concat(lastF.map(r => [r.model, r.policy, r.scaffold, r.variant, r.rel, r.arm, r.k, r.run]
      .concat(...mk.map(k => { const c = r.metrics[k]; return c ? [c.m, c.lo, c.hi, c.n, c.nx] : ['', '', '', '', '']; })).map(esc).join(',')));
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' }));
    a.download = 'benchbook-results.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });

  draw();
})();
