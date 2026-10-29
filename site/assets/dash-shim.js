/* Runtime ringan pengganti "dash" claude.ai untuk hosting mandiri.
   Membaca dataset dari folder ./data, mengelola filter, dan menggambar ulang halaman. */
(function () {
  const DATASETS = {
    user_events: 'data/user_events.json',
    admin_events: 'data/admin_events.json',
    drive_events: 'data/drive_events.json',
    accounts: 'data/accounts.json',
    findings: 'data/findings.json',
  };
  const DEFAULTS = { q: null, start: '2026-09-01', end: '2026-10-22', issues: true, page: 'user-activity' };
  let params = { ...DEFAULTS };
  const store = {};
  const draws = new Map();
  const onDatas = [];
  let queued = false;

  function load(id) {
    if (store[id] || !DATASETS[id]) return;
    store[id] = { status: 'loading', data: [] };
    fetch(DATASETS[id], { cache: 'no-store' })
      .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then((d) => { store[id] = { status: 'ok', data: Array.isArray(d) ? d : (d.rows || d.data || []) }; schedule(); })
      .catch((e) => { store[id] = { status: 'error', data: [], message: String(e) }; console.error('Gagal memuat', id, e); schedule(); });
  }

  function render() {
    queued = false;
    onDatas.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
    draws.forEach((fn, name) => {
      document.querySelectorAll(`[data-draw="${name}"]`).forEach((el) => {
        if (el.closest('[hidden]')) return;
        try { fn(el); } catch (e) { console.error('draw', name, e); }
      });
    });
  }
  function schedule() { if (!queued) { queued = true; requestAnimationFrame(render); } }

  window.dash = {
    colors: ['#2f6fdb', '#e07a2e', '#3a9d74', '#8a5cd1', '#c94f7c', '#5b8fa8', '#b5a33a', '#7a7a7a'],
    data: (id) => { load(id); return store[id] || { status: 'missing', data: [] }; },
    params: () => ({ ...params }),
    setParams: (p) => { params = { ...params, ...p }; schedule(); },
    resetParams: () => { params = { ...DEFAULTS }; schedule(); },
    onData: (fn) => { onDatas.push(fn); schedule(); },
    draw: (name, fn) => { if (typeof fn === 'function') draws.set(name, fn); schedule(); },
    setLink: (name) => { history.replaceState(null, '', '#' + name); },
    refresh: () => schedule(),
  };

  let lastW = 0;
  new ResizeObserver(() => { const w = document.documentElement.clientWidth; if (w !== lastW) { lastW = w; schedule(); } }).observe(document.documentElement);
})();
