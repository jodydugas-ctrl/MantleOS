/* Append-only live module loading. No iframe replacement or fabricated readiness. */
(() => {
  'use strict';
  const root = document.getElementById('mantle-root');
  const status = document.getElementById('mantle-status');
  const ready = new Set(), installed = new Map(), failed = new Map();
  const locks = new WeakMap();
  let app = null, revision = 0, shell = null, snapshot = null, pollTimer = null;
  const required = el => (el.getAttribute('data-mantle-requires') || '').split(/\s+/).filter(Boolean);
  function controls() {
    for (const el of root.querySelectorAll('[data-mantle-requires]')) {
      const pending = required(el).some(id => !ready.has(id));
      if (pending) {
        if (!locks.has(el)) locks.set(el, {disabled: el.disabled, aria: el.getAttribute('aria-disabled')});
        if ('disabled' in el) el.disabled = true;
        el.setAttribute('aria-disabled', 'true');
        el.setAttribute('data-mantle-pending', '');
      } else if (locks.has(el)) {
        const old = locks.get(el);
        if ('disabled' in el) el.disabled = old.disabled;
        if (old.aria === null) el.removeAttribute('aria-disabled'); else el.setAttribute('aria-disabled', old.aria);
        el.removeAttribute('data-mantle-pending');
        locks.delete(el);
      }
    }
  }
  // Block non-button gated controls too. Authors must declare all prerequisites.
  for (const type of ['click', 'submit', 'keydown']) root.addEventListener(type, event => {
    const gate = event.target.closest('[data-mantle-requires]');
    if (gate && required(gate).some(id => !ready.has(id))) {
      event.preventDefault(); event.stopImmediatePropagation();
    }
  }, true);
  function report() {
    controls();
    const total = snapshot ? snapshot.modules.length : 0;
    const pendingControls = [...root.querySelectorAll('[data-mantle-requires]')].some(
      el => required(el).some(id => !ready.has(id)));
    const complete = snapshot && snapshot.phase === 'COMPLETE' && ready.size === total && !failed.size && !pendingControls;
    status.textContent = (complete ? 'Ready' : 'Building') + ` · ${ready.size}/${total} modules ready` +
      (failed.size ? ' · Failed: ' + [...failed.keys()].join(', ') : '');
    status.dataset.phase = complete ? 'READY' : failed.size ? 'FAILED' : 'BUILDING';
    window.dispatchEvent(new CustomEvent('mantle:status', {detail: window.MantleCanvas.inspect()}));
  }
  function drain() {
    if (!snapshot) return;
    let progress;
    do {
    progress = false;
    for (const module of snapshot.modules) {
      if (installed.has(module.id) || module.depends.some(dep => !ready.has(dep))) continue;
      installed.set(module.id, module.content_sha256);
      progress = true;
      try {
        if (module.kind === 'html') {
          const section = document.createElement('section');
          section.dataset.mantleModule = module.id; section.innerHTML = module.content;
          // HTML is markup; executable behavior belongs in javascript modules.
          for (const script of section.querySelectorAll('script')) script.remove();
          root.append(section); ready.add(module.id);
        } else if (module.kind === 'css') {
          const style = document.createElement('style'); style.textContent = module.content;
          document.head.append(style); ready.add(module.id);
        } else {
          let acknowledged = false, settled = false;
          const api = Object.freeze({root,
            ready: () => { if (!settled) acknowledged = true; },
            has: id => ready.has(id)});
          controls();
          const result = new Function('api', 'root', '"use strict";\n' + module.content)(api, root);
          // Enable dependents only after completion AND explicit acknowledgement.
          Promise.resolve(result).then(() => {
            settled = true;
            if (!acknowledged) throw new Error('Module did not call api.ready()');
            ready.add(module.id); drain(); report();
          }).catch(error => { settled = true; failed.set(module.id, String(error)); report(); });
        }
      } catch (error) { failed.set(module.id, String(error)); }
    }
    } while (progress);
    report();
  }
  function apply(next) {
    if (!next || next.schema !== 'mantle.progressive-app/1' || !Array.isArray(next.modules))
      throw new Error('Invalid snapshot');
    if (app !== null && next.app_id !== app) throw new Error('Wrong app');
    if (next.revision < revision) throw new Error('Stale snapshot');
    if (app !== null && next.shell !== shell) throw new Error('Shell replacement requires new mount');
    const byId = new Map(next.modules.map(m => [m.id, m]));
    for (const [id, hash] of installed) {
      if (!byId.has(id) || byId.get(id).content_sha256 !== hash) throw new Error('Published modules are immutable');
    }
    if (snapshot && next.revision === revision) {
      if (next.sha256 !== snapshot.sha256) throw new Error('Conflicting snapshot revision');
      return;
    }
    if (app === null) {
      app = next.app_id; shell = next.shell; root.innerHTML = shell;
      for (const script of root.querySelectorAll('script')) script.remove();
    }
    snapshot = next; revision = next.revision; controls(); drain();
  }
  function inspect() {
    return {app_id: app, revision, ready: [...ready], failed: Object.fromEntries(failed),
      waiting: snapshot ? snapshot.modules.filter(m => !installed.has(m.id)).map(m => m.id) : []};
  }
  async function poll(url) {
    if (!url) return;
    clearTimeout(pollTimer);
    try {
      const response = await fetch(url, {cache: 'no-store'});
      if (!response.ok) throw new Error('Snapshot HTTP ' + response.status);
      apply(await response.json());
    } catch (error) { status.textContent = 'Update unavailable; loaded features remain usable. ' + String(error); }
    pollTimer = setTimeout(() => poll(url), 250);
  }
  window.MantleCanvas = Object.freeze({apply, inspect, poll});
})();
