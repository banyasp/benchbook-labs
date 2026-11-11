// Benchbook console: tiny helpers (no external requests).
document.addEventListener('keydown', e => {
  const t = e.target.tagName;
  if (e.key === '/' && t !== 'INPUT' && t !== 'TEXTAREA' && t !== 'SELECT') { e.preventDefault(); const s = document.getElementById('gsearch'); if (s) s.focus(); }
});
// sign-off forms come back to the page they were sent from
document.querySelectorAll('.backfield').forEach(i => i.value = location.pathname + location.search);
// client-side row filter: <input class="tfilter" data-table="tableid">
document.querySelectorAll('.tfilter').forEach(inp => inp.addEventListener('input', () => {
  const q = inp.value.toLowerCase(); const tb = document.getElementById(inp.dataset.table);
  tb.querySelectorAll('tr').forEach((tr, i) => { if (tr.querySelector('th')) return; tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none'; });
}));
// sortable tables: click a header
document.querySelectorAll('table.sortable').forEach(tbl => {
  tbl.querySelectorAll('th').forEach((th, col) => th.addEventListener('click', () => {
    const body = tbl.tBodies[0] || tbl; const rows = Array.from(body.querySelectorAll('tr')).filter(r => !r.querySelector('th'));
    const dir = th.dataset.dir === 'asc' ? -1 : 1; th.dataset.dir = dir === 1 ? 'asc' : 'desc';
    const val = r => { const c = r.children[col]; const s = c ? c.textContent.trim() : ''; const n = parseFloat(s.replace('%', '')); return isNaN(n) ? s.toLowerCase() : n; };
    rows.sort((a, b) => { const x = val(a), y = val(b); return (x > y ? 1 : x < y ? -1 : 0) * dir; });
    rows.forEach(r => body.appendChild(r));
  }));
});
// labelling shortcuts on task pages
function taskKeys() {
  const form = document.getElementById('ansform'); if (!form) return;
  const submitWith = v => { const b = Array.from(form.querySelectorAll('button[name=answer]')).find(b => b.value === v); if (b) b.click(); };
  document.addEventListener('keydown', e => {
    const t = e.target.tagName;
    if (t === 'TEXTAREA' || t === 'INPUT') {
      if (e.key === 'Enter' && !e.shiftKey && e.target.id === 'gt') { e.preventDefault(); submitWith('edit'); }
      if (e.key === 'Escape') e.target.blur();
      return;
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const key = e.key.toLowerCase();
    const btn = Array.from(form.querySelectorAll('button[data-key]')).find(b => b.dataset.key === key);
    if (btn) { e.preventDefault(); btn.click(); return; }
    if (key === 'e') { const g = document.getElementById('gt'); if (g) { e.preventDefault(); g.focus(); } }
    if (key === 'c') { const n = document.getElementById('note'); if (n) { e.preventDefault(); n.focus(); } }
    if (e.key === 'ArrowRight') { const n = document.getElementById('nextlink'); if (n) location = n.href; }
  });
}
