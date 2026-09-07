// filename: gofile-abdm.user.js
// ==UserScript==
// @name         GoFile ABDM Helper
// @namespace    https://github.com/Hoyomaru/gofile-abdm-helper
// @version      1.0.2
// @description  Select GoFile files/folders on gofile.io and send them to AB Download Manager through a localhost helper.
// @homepageURL  https://github.com/Hoyomaru/gofile-abdm-helper
// @supportURL   https://github.com/Hoyomaru/gofile-abdm-helper/issues
// @match        https://gofile.io/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==

(() => {
  'use strict';

  const HELPER = 'http://127.0.0.1:8765';
  const TOOLBAR_ID = 'gofile-abdm-toolbar';
  const MODAL_ID = 'gofile-abdm-modal';
  const STYLE_ID = 'gofile-abdm-style';
  const CHECKBOX_CLASS = 'gofile-abdm-checkbox';
  const STORAGE = {
    lastSaveFolder: 'gofile_abdm_last_save_folder',
    presets: 'gofile_abdm_presets',
    queueId: 'gofile_abdm_queue_id',
  };

  const state = {
    sourceUrl: window.location.href,
    resolveId: null,
    root: null,
    topLevel: [],
    currentLevel: [],
    nodeByKey: new Map(),
    selectedKeys: new Set(),
    provisionalSelectedIds: new Set(),
    failedFileKeys: [],
    lastSendPreserveStructure: true,
    lastSendQueueId: null,
    password: null,
    resolving: false,
    sending: false,
    connected: false,
    unmatched: 0,
    lastUrl: window.location.href,
    refreshTimer: null,
    domTimer: null,
  };

  let nativeToast = null;

  function loadNativeUi() {
    import('/js/ui/toast.js')
      .then((module) => {
        if (typeof module.toast === 'function') nativeToast = module.toast;
      })
      .catch(() => {});
  }

  function gmRequest(method, path, data = null, timeout = 60000) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method,
        url: `${HELPER}${path}`,
        headers: {
          'X-GoFile-ABDM': '1',
          ...(data !== null ? { 'Content-Type': 'application/json' } : {}),
        },
        data: data !== null ? JSON.stringify(data) : undefined,
        responseType: 'json',
        ...(timeout > 0 ? { timeout } : {}),
        onload: (response) => {
          let payload = response.response;
          if (!payload && response.responseText) {
            try { payload = JSON.parse(response.responseText); } catch (_) { payload = null; }
          }
          if (response.status >= 200 && response.status < 300) {
            resolve(payload || {});
            return;
          }
          const error = new Error(payload?.error?.message || `Helper returned HTTP ${response.status}`);
          error.code = payload?.error?.code || 'http_error';
          error.status = response.status;
          reject(error);
        },
        onerror: () => reject(Object.assign(new Error('Python Helper is offline.'), { code: 'helper_offline' })),
        ontimeout: () => reject(Object.assign(new Error('Python Helper request timed out.'), { code: 'helper_timeout' })),
        onabort: () => reject(Object.assign(new Error('Python Helper request was aborted.'), { code: 'helper_aborted' })),
      });
    });
  }

  function toast(message, type = 'info') {
    if (nativeToast) {
      try {
        nativeToast(message, { type: type === 'warning' ? 'warning' : type });
        return;
      } catch (_) {}
    }
    const el = document.createElement('div');
    el.className = `gab-toast gab-toast-${type}`;
    el.textContent = message;
    document.body.appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));
    setTimeout(() => {
      el.classList.remove('show');
      setTimeout(() => el.remove(), 250);
    }, 3200);
  }

  function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (!Number.isFinite(value) || value <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
    const scaled = value / Math.pow(1024, index);
    return `${scaled >= 10 || index === 0 ? scaled.toFixed(0) : scaled.toFixed(1)} ${units[index]}`;
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      #${TOOLBAR_ID} { margin-bottom:.75rem; padding:.55rem .65rem; }
      #${TOOLBAR_ID} .gab-row { display:flex; flex-wrap:wrap; align-items:center; gap:.45rem; }
      #${TOOLBAR_ID} .gab-url { flex:1 1 260px; min-width:180px; max-width:520px; }
      #${TOOLBAR_ID} .gab-url input { width:100%; }
      #${TOOLBAR_ID} .gab-spacer { flex:1 1 auto; }
      #${TOOLBAR_ID} .gab-status { white-space:nowrap; font-size:.84rem; opacity:.9; }
      #${TOOLBAR_ID} .gab-status-dot { display:inline-block; width:.55rem; height:.55rem; border-radius:999px; margin-right:.3rem; background:#ef4444; }
      #${TOOLBAR_ID} .gab-status-dot.connected { background:#22c55e; }
      #${TOOLBAR_ID} .gab-summary { font-size:.85rem; white-space:nowrap; }
      #${TOOLBAR_ID} .gab-progress { width:100%; font-size:.82rem; opacity:.9; display:none; }
      #${TOOLBAR_ID} .gab-progress.visible { display:block; }
      #${TOOLBAR_ID} .gab-progress-bar { height:5px; border-radius:999px; overflow:hidden; background:color-mix(in srgb,currentColor 12%,transparent); margin-top:4px; }
      #${TOOLBAR_ID} .gab-progress-bar > span { display:block; height:100%; width:0%; background:currentColor; transition:width .15s ease; }
      .${CHECKBOX_CLASS} { margin-right:.5rem; flex:0 0 auto; width:1rem; height:1rem; accent-color:#3b82f6; }
      .gab-check-wrap { display:inline-flex; align-items:center; margin-right:.35rem; z-index:2; }
      .gab-btn { border:1px solid color-mix(in srgb,currentColor 18%,transparent); border-radius:.5rem; padding:.42rem .68rem; background:color-mix(in srgb,currentColor 4%,transparent); cursor:pointer; font:inherit; color:inherit; }
      .gab-btn:hover { background:color-mix(in srgb,currentColor 9%,transparent); }
      .gab-btn:disabled { opacity:.45; cursor:not-allowed; }
      .gab-btn-primary { background:color-mix(in srgb,#3b82f6 20%,transparent); border-color:color-mix(in srgb,#3b82f6 45%,transparent); }
      .gab-input, .gab-select { width:100%; box-sizing:border-box; border:1px solid color-mix(in srgb,currentColor 18%,transparent); border-radius:.5rem; padding:.5rem .6rem; background:color-mix(in srgb,currentColor 4%,transparent); color:inherit; font:inherit; }
      .gab-modal-backdrop { position:fixed; inset:0; z-index:2147483640; background:rgba(0,0,0,.55); display:flex; align-items:center; justify-content:center; padding:1rem; }
      .gab-modal-card { width:min(620px,96vw); max-height:88vh; overflow:auto; border-radius:.8rem; padding:1rem; background:var(--color-slate-900,#111827); color:var(--color-slate-100,#f3f4f6); box-shadow:0 18px 60px rgba(0,0,0,.45); border:1px solid rgba(148,163,184,.25); }
      .gab-modal-card.gab-dark { background:#111827; color:#f3f4f6; }
      .gab-modal-card.gab-light { background:#fff; color:#111827; }
      .gab-modal-card h3 { margin:0 0 .8rem; font-size:1rem; }
      .gab-grid { display:grid; grid-template-columns:1fr 1fr; gap:.65rem; }
      .gab-field { margin-bottom:.7rem; }
      .gab-field label { display:block; font-size:.78rem; opacity:.76; margin-bottom:.25rem; }
      .gab-actions { display:flex; justify-content:flex-end; gap:.45rem; margin-top:.85rem; }
      .gab-preset-actions { display:flex; gap:.4rem; flex-wrap:wrap; margin-top:.45rem; }
      .gab-tree { max-height:54vh; overflow:auto; border:1px solid rgba(148,163,184,.22); border-radius:.6rem; padding:.5rem; }
      .gab-tree-row { display:flex; align-items:center; gap:.45rem; min-height:1.85rem; font-size:.86rem; }
      .gab-tree-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .gab-tree-size { margin-left:auto; opacity:.65; font-variant-numeric:tabular-nums; }
      .gab-toast { position:fixed; right:1rem; bottom:1rem; z-index:2147483647; max-width:min(460px,90vw); padding:.7rem .85rem; border-radius:.6rem; background:#111827; color:white; border:1px solid rgba(255,255,255,.15); box-shadow:0 10px 35px rgba(0,0,0,.35); opacity:0; transform:translateY(8px); transition:.2s ease; }
      .gab-toast.show { opacity:1; transform:none; }
      .gab-toast-success { border-color:rgba(34,197,94,.55); }
      .gab-toast-error { border-color:rgba(239,68,68,.65); }
      .gab-toast-warning { border-color:rgba(245,158,11,.65); }
      .gab-muted { opacity:.68; font-size:.8rem; }
      .gab-hidden { display:none !important; }
    `;
    document.head.appendChild(style);
  }

  function button(text, id, primary = false) {
    return `<button type="button" id="${id}" class="gab-btn ${primary ? 'gab-btn-primary' : ''}">${escapeHtml(text)}</button>`;
  }

  function findToolbarAnchor() {
    return document.querySelector('#fm-toolbar') || document.querySelector('#fm-root') || document.querySelector('main') || document.body;
  }

  function ensureToolbar() {
    injectStyle();
    let toolbar = document.getElementById(TOOLBAR_ID);
    if (toolbar) return toolbar;

    toolbar = document.createElement('div');
    toolbar.id = TOOLBAR_ID;
    toolbar.className = 'panel';
    toolbar.innerHTML = `
      <div class="gab-row">
        ${button('Select All', 'gab-select-all')}
        ${button('Clear', 'gab-clear')}
        <span id="gab-summary" class="gab-summary">Selected: 0 files / 0 B</span>
        <span class="gab-spacer"></span>
        <span id="gab-status" class="gab-status"><span class="gab-status-dot"></span>ABDM Offline</span>
        ${button('Items', 'gab-items')}
        ${button('⚙', 'gab-settings')}
        ${button('Send Flat', 'gab-send-flat')}
        ${button('Send to ABDM', 'gab-send', true)}
      </div>
      <div class="gab-row" style="margin-top:.45rem">
        <div class="gab-url"><input id="gab-url" class="gab-input" type="text" spellcheck="false" aria-label="GoFile URL"></div>
        ${button('Load', 'gab-load')}
      </div>
      <div id="gab-progress" class="gab-progress">
        <div id="gab-progress-text">Ready</div>
        <div class="gab-progress-bar"><span id="gab-progress-fill"></span></div>
      </div>
    `;

    const anchor = findToolbarAnchor();
    if (anchor.id === 'fm-toolbar') anchor.insertAdjacentElement('beforebegin', toolbar);
    else if (anchor.id === 'fm-root') anchor.prepend(toolbar);
    else anchor.prepend(toolbar);

    document.getElementById('gab-url').value = state.sourceUrl;
    document.getElementById('gab-select-all').addEventListener('click', selectAll);
    document.getElementById('gab-clear').addEventListener('click', clearSelection);
    document.getElementById('gab-settings').addEventListener('click', () => openSettings());
    document.getElementById('gab-items').addEventListener('click', openSelectionTree);
    document.getElementById('gab-send-flat').addEventListener('click', () => sendSelected(false, false));
    document.getElementById('gab-send').addEventListener('click', () => sendSelected(false, true));
    document.getElementById('gab-load').addEventListener('click', () => {
      const value = document.getElementById('gab-url').value.trim();
      state.sourceUrl = value || window.location.href;
      state.password = null;
      resolveContent(true);
    });
    updateToolbar();
    return toolbar;
  }

  function flattenTree(node) {
    if (!node) return;
    state.nodeByKey.set(node.key, node);
    for (const child of node.children || []) flattenTree(child);
  }

  function currentTopLevel() {
    return Array.isArray(state.currentLevel) && state.currentLevel.length
      ? state.currentLevel
      : (Array.isArray(state.topLevel) ? state.topLevel : []);
  }

  function folderNodes() {
    const folders = [];
    for (const node of state.nodeByKey.values()) {
      if (node?.type === 'folder' && Array.isArray(node.children) && node.children.length) folders.push(node);
    }
    return folders;
  }

  function visibleContentIds(fmRoot) {
    const ids = new Set();
    const attrs = ['data-content-id', 'data-id', 'data-item-id', 'data-uuid'];
    const validId = /^[A-Za-z0-9][A-Za-z0-9-]{5,127}$/;
    for (const el of fmRoot.querySelectorAll(attrs.map((attr) => `[${attr}]`).join(','))) {
      if (el.closest(`#${TOOLBAR_ID}`) || el.closest('.gab-check-wrap')) continue;
      if (!el.getClientRects().length) continue;
      for (const attr of attrs) {
        const value = (el.getAttribute(attr) || '').trim();
        if (validId.test(value)) ids.add(value);
      }
    }
    return ids;
  }

  function detectCurrentLevelNodes() {
    const fmRoot = document.querySelector('#fm-root');
    if (!fmRoot || !state.root) return Array.isArray(state.topLevel) ? state.topLevel : [];

    // Prefer stable GoFile content IDs when the current DOM exposes them. Older
    // and newer GoFile layouts have used different data-* names, so support the
    // known variants before falling back to filename text matching.
    const visibleIds = visibleContentIds(fmRoot);
    if (visibleIds.size) {
      let bestById = null;
      let bestIdScore = 0;
      for (const folder of folderNodes()) {
        const children = folder.children || [];
        if (!children.length) continue;
        const score = children.reduce((count, child) => count + (visibleIds.has(child.id) ? 1 : 0), 0);
        if (score > bestIdScore) {
          bestById = folder;
          bestIdScore = score;
        }
      }
      if (bestById && bestIdScore > 0) return bestById.children || [];
    }

    const visibleTexts = new Set();
    for (const el of fmRoot.querySelectorAll('a,button,span,div')) {
      if (el.closest(`#${TOOLBAR_ID}`) || el.closest('.gab-check-wrap')) continue;
      if (!el.getClientRects().length) continue;
      const text = (el.textContent || '').trim();
      if (text && text.length <= 300) visibleTexts.add(text);
    }

    let best = state.root;
    let bestScore = -1;
    let bestRatio = -1;
    for (const folder of folderNodes()) {
      const children = folder.children || [];
      if (!children.length) continue;
      let score = 0;
      for (const child of children) {
        if (visibleTexts.has(child.name)) score += 1;
      }
      const ratio = score / children.length;
      if (score > bestScore || (score === bestScore && ratio > bestRatio)) {
        best = folder;
        bestScore = score;
        bestRatio = ratio;
      }
    }

    if (bestScore <= 0) return Array.isArray(state.topLevel) ? state.topLevel : [];
    return best.children || [];
  }

  function selectedFileKeys() {
    const keys = new Set();
    for (const key of state.selectedKeys) {
      const node = state.nodeByKey.get(key);
      if (!node) continue;
      if (node.type === 'file') keys.add(node.key);
      else for (const fileKey of node.file_keys || []) keys.add(fileKey);
    }
    return [...keys];
  }

  function selectedStats() {
    const files = selectedFileKeys();
    let total = 0;
    for (const key of files) total += Number(state.nodeByKey.get(key)?.size || 0);
    if (!state.root && state.provisionalSelectedIds.size) {
      return { count: state.provisionalSelectedIds.size, total: 0, provisional: true };
    }
    return { count: files.length, total, provisional: false };
  }

  function updateToolbar() {
    const toolbar = ensureToolbar();
    const stats = selectedStats();
    const summary = toolbar.querySelector('#gab-summary');
    if (summary) summary.textContent = stats.provisional
      ? `Selected: ${stats.count} visible item(s) — pending resolve`
      : `Selected: ${stats.count} files / ${formatBytes(stats.total)}`;

    const status = toolbar.querySelector('#gab-status');
    if (status) {
      status.innerHTML = `<span class="gab-status-dot ${state.connected ? 'connected' : ''}"></span>ABDM ${state.connected ? 'Connected' : 'Offline'}`;
    }

    const send = toolbar.querySelector('#gab-send');
    const sendFlat = toolbar.querySelector('#gab-send-flat');
    if (send) {
      send.disabled = state.sending || state.resolving || stats.count === 0;
      send.textContent = 'Send to ABDM';
    }
    if (sendFlat) {
      sendFlat.disabled = state.sending || state.resolving || stats.count === 0;
    }
    const items = toolbar.querySelector('#gab-items');
    if (items) items.classList.remove('gab-hidden');
    syncInjectedCheckboxes();
  }

  function setProgress(current, total, label, visible = true) {
    const progress = document.getElementById('gab-progress');
    if (!progress) return;
    progress.classList.toggle('visible', visible);
    const text = document.getElementById('gab-progress-text');
    const fill = document.getElementById('gab-progress-fill');
    if (text) text.textContent = total ? `Sending to ABDM ${current} / ${total}${label ? ` — ${label}` : ''}` : label;
    if (fill) fill.style.width = total ? `${Math.max(0, Math.min(100, current / total * 100))}%` : '0%';
  }

  async function checkABDM() {
    try {
      const data = await gmRequest('GET', '/api/abdm/status', null, 10000);
      state.connected = Boolean(data.connected);
    } catch (_) {
      state.connected = false;
    }
    updateToolbar();
    return state.connected;
  }

  function resetResolution(preserveProvisional = false) {
    state.resolveId = null;
    state.root = null;
    state.topLevel = [];
    state.currentLevel = [];
    state.nodeByKey.clear();
    state.selectedKeys.clear();
    if (!preserveProvisional) state.provisionalSelectedIds.clear();
    state.failedFileKeys = [];
    document.querySelectorAll(`.${CHECKBOX_CLASS}`).forEach((el) => el.closest('.gab-check-wrap')?.remove());
    updateToolbar();
  }

  async function resolveContent(preserveProvisional = false) {
    if (state.resolving) return;
    state.resolving = true;
    resetResolution(preserveProvisional);
    ensureToolbar();
    setProgress(0, 0, 'Resolving GoFile content…', true);
    try {
      const data = await gmRequest('POST', '/api/gofile/resolve', {
        url: state.sourceUrl,
        ...(state.password ? { password: state.password } : {}),
      }, 0);
      state.resolveId = data.resolve_id;
      state.root = data.root;
      state.topLevel = data.top_level || [];
      state.currentLevel = [...state.topLevel];
      state.nodeByKey.clear();
      flattenTree(state.root);
      state.selectedKeys.clear();
      if (state.provisionalSelectedIds.size) {
        for (const node of state.nodeByKey.values()) {
          if (state.provisionalSelectedIds.has(node.id)) state.selectedKeys.add(node.key);
        }
        state.provisionalSelectedIds.clear();
      }
      injectCheckboxes();
      setProgress(0, 0, `Ready — ${data.file_count} files / ${formatBytes(data.total_size)}`, false);
    } catch (error) {
      if (error.code === 'password_required' || error.code === 'wrong_password') {
        state.password = null;
        const password = await promptPassword(error.code === 'wrong_password');
        state.resolving = false;
        if (password !== null) {
          state.password = password;
          await resolveContent(true);
        }
        return;
      }
      setProgress(0, 0, error.message, true);
      toast(error.message, 'error');
    } finally {
      state.resolving = false;
      if (!state.root) injectCheckboxes();
      updateToolbar();
    }
  }

  function discoverVisibleDomItems() {
    const root = document.querySelector('#fm-root') || document.querySelector('#filemanager_itemslist');
    if (!root) return [];
    const attrs = ['data-content-id', 'data-item-id', 'data-uuid', 'data-id'];
    const validId = /^[A-Za-z0-9][A-Za-z0-9-]{5,127}$/;
    const items = [];
    const usedRows = new Set();
    for (const el of root.querySelectorAll(attrs.map((attr) => `[${attr}]`).join(','))) {
      if (el.closest(`#${TOOLBAR_ID}`) || el.closest('.gab-check-wrap')) continue;
      if (!el.getClientRects().length) continue;
      let id = '';
      for (const attr of attrs) {
        const value = (el.getAttribute(attr) || '').trim();
        if (validId.test(value)) { id = value; break; }
      }
      if (!id) continue;
      const row = el.closest('tr,[role="row"],li,.item,.file-row,[class*="item"],[class*="row"]') || el.parentElement || el;
      if (usedRows.has(row)) continue;
      usedRows.add(row);
      items.push({ id, row });
    }
    return items;
  }

  function injectProvisionalCheckboxes() {
    document.querySelectorAll('.gab-check-wrap').forEach((el) => el.remove());
    const items = discoverVisibleDomItems();
    for (const item of items) {
      const wrap = document.createElement('label');
      wrap.className = 'gab-check-wrap';
      wrap.title = 'Select visible GoFile item (will be matched after resolve)';
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = CHECKBOX_CLASS;
      checkbox.dataset.gabContentId = item.id;
      checkbox.checked = state.provisionalSelectedIds.has(item.id);
      checkbox.addEventListener('click', (event) => event.stopPropagation());
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) state.provisionalSelectedIds.add(item.id);
        else state.provisionalSelectedIds.delete(item.id);
        updateToolbar();
      });
      wrap.appendChild(checkbox);
      if (item.row.tagName === 'TR') {
        const cell = item.row.querySelector('td,th');
        if (cell) cell.prepend(wrap);
      } else {
        item.row.prepend(wrap);
      }
    }
    state.unmatched = items.length ? 0 : 1;
    updateToolbar();
  }

  function rowForNode(node) {
    const root = document.querySelector('#fm-root') || document.querySelector('main') || document.body;
    const escapedId = CSS.escape(node.id);
    const exact = root.querySelector([
      `[data-content-id="${escapedId}"]`,
      `[data-id="${escapedId}"]`,
      `[data-item-id="${escapedId}"]`,
      `[data-uuid="${escapedId}"]`,
    ].join(','));
    const linked = exact || [...root.querySelectorAll('a[href]')].find((el) => (el.getAttribute('href') || '').includes(node.id));
    const candidates = linked ? [linked] : [...root.querySelectorAll('a,button,span,div')].filter((el) => {
      if (el.closest(`#${TOOLBAR_ID}`)) return false;
      const text = (el.textContent || '').trim();
      return text === node.name && el.getClientRects().length > 0;
    }).sort((a, b) => (a.textContent || '').length - (b.textContent || '').length);

    const target = candidates[0];
    if (!target) return null;
    const row = target.closest('tr,[role="row"],li,[data-content-id],[data-id],.item,.file-row,[class*="item"],[class*="row"]');
    if (row && !row.closest(`#${TOOLBAR_ID}`)) return row;
    return target.parentElement;
  }

  function injectCheckboxes() {
    ensureToolbar();
    if (!state.root) {
      injectProvisionalCheckboxes();
      return;
    }
    document.querySelectorAll('.gab-check-wrap').forEach((el) => el.remove());
    let unmatched = 0;
    const used = new Set();
    const levelNodes = detectCurrentLevelNodes();
    state.currentLevel = [...levelNodes];

    for (const node of levelNodes) {
      const row = rowForNode(node);
      if (!row || used.has(row)) {
        unmatched += 1;
        continue;
      }
      used.add(row);
      const wrap = document.createElement('label');
      wrap.className = 'gab-check-wrap';
      wrap.title = node.type === 'folder' ? `Select folder recursively: ${node.name}` : `Select file: ${node.name}`;
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = CHECKBOX_CLASS;
      checkbox.dataset.gabKey = node.key;
      checkbox.checked = state.selectedKeys.has(node.key);
      checkbox.addEventListener('click', (event) => event.stopPropagation());
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) state.selectedKeys.add(node.key);
        else state.selectedKeys.delete(node.key);
        updateToolbar();
      });
      wrap.appendChild(checkbox);
      if (row.tagName === 'TR') {
        const cell = row.querySelector('td,th');
        if (cell) cell.prepend(wrap);
        else { unmatched += 1; continue; }
      } else {
        row.prepend(wrap);
      }
    }
    state.unmatched = unmatched;
    updateToolbar();
  }

  function syncInjectedCheckboxes() {
    document.querySelectorAll(`.${CHECKBOX_CLASS}`).forEach((checkbox) => {
      const contentId = checkbox.dataset.gabContentId;
      if (contentId) {
        checkbox.checked = state.provisionalSelectedIds.has(contentId);
        checkbox.indeterminate = false;
        return;
      }
      const key = checkbox.dataset.gabKey;
      checkbox.checked = state.selectedKeys.has(key);
      const node = state.nodeByKey.get(key);
      if (node?.type === 'folder') {
        const fileKeys = node.file_keys || [];
        const selectedFiles = new Set(selectedFileKeys());
        const count = fileKeys.filter((fileKey) => selectedFiles.has(fileKey)).length;
        checkbox.indeterminate = count > 0 && count < fileKeys.length && !state.selectedKeys.has(key);
      }
    });
  }

  function selectAll() {
    let nodes = currentTopLevel();
    if (!nodes.length && state.root) nodes = state.root.children || [];
    if (!nodes.length) {
      const visible = discoverVisibleDomItems();
      if (!visible.length) {
        toast('No selectable GoFile rows are visible yet.', 'warning');
        return;
      }
      for (const item of visible) state.provisionalSelectedIds.add(item.id);
      updateToolbar();
      return;
    }
    for (const node of nodes) state.selectedKeys.add(node.key);
    updateToolbar();
  }

  function clearSelection() {
    state.selectedKeys.clear();
    state.provisionalSelectedIds.clear();
    state.failedFileKeys = [];
    updateToolbar();
  }

  function pageLooksDark() {
    const explicit = document.documentElement.classList.contains('dark') ||
      document.body?.classList.contains('dark') ||
      document.documentElement.dataset.theme === 'dark' ||
      document.body?.dataset.theme === 'dark';
    if (explicit) return true;
    const color = getComputedStyle(document.body).backgroundColor.match(/[\d.]+/g);
    if (!color || color.length < 3) return matchMedia('(prefers-color-scheme: dark)').matches;
    const [r, g, b] = color.map(Number);
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) < 128;
  }

  function openModal(title, contentHtml, onReady) {
    document.getElementById(MODAL_ID)?.remove();
    const backdrop = document.createElement('div');
    backdrop.id = MODAL_ID;
    backdrop.className = 'gab-modal-backdrop';
    backdrop.innerHTML = `<div class="gab-modal-card ${pageLooksDark() ? 'gab-dark' : 'gab-light'}" role="dialog" aria-modal="true"><h3>${escapeHtml(title)}</h3>${contentHtml}</div>`;
    backdrop.addEventListener('mousedown', (event) => {
      if (event.target === backdrop) backdrop.remove();
    });
    document.body.appendChild(backdrop);
    onReady?.(backdrop.querySelector('.gab-modal-card'), backdrop);
    return backdrop;
  }

  function closeModal() {
    document.getElementById(MODAL_ID)?.remove();
  }

  function promptPassword(wrong) {
    return new Promise((resolve) => {
      const modal = openModal('GoFile Password', `
        <div class="gab-field">
          <div class="gab-muted" style="margin-bottom:.55rem">${wrong ? 'The previous password was rejected.' : 'This content is password protected.'}</div>
          <label for="gab-password">Password</label>
          <input id="gab-password" class="gab-input" type="password" autocomplete="off">
        </div>
        <div class="gab-actions">
          ${button('Cancel', 'gab-password-cancel')}
          ${button('Unlock', 'gab-password-ok', true)}
        </div>
      `, (card, backdrop) => {
        const input = card.querySelector('#gab-password');
        const finish = (value) => { backdrop.remove(); resolve(value); };
        card.querySelector('#gab-password-cancel').addEventListener('click', () => finish(null));
        card.querySelector('#gab-password-ok').addEventListener('click', () => finish(input.value));
        input.addEventListener('keydown', (event) => { if (event.key === 'Enter') finish(input.value); });
        input.focus();
      });
      return modal;
    });
  }

  function getPresets() {
    const value = GM_getValue(STORAGE.presets, []);
    return Array.isArray(value) ? value.filter((item) => item && typeof item.name === 'string' && typeof item.path === 'string') : [];
  }

  function savePresets(presets) {
    GM_setValue(STORAGE.presets, presets);
  }

  function getSelectedQueueId() {
    const value = GM_getValue(STORAGE.queueId, '');
    if (value === '' || value === null || value === undefined) return null;
    const parsed = Number(value);
    return Number.isInteger(parsed) ? parsed : null;
  }

  async function openSettings() {
    await checkABDM();
    const presets = getPresets();
    const lastFolder = GM_getValue(STORAGE.lastSaveFolder, '');
    const selectedQueueId = getSelectedQueueId();
    let queues = [];
    let queueLoadError = false;
    if (state.connected) {
      try {
        const queueData = await gmRequest('GET', '/api/abdm/queues', null, 10000);
        queues = Array.isArray(queueData.queues) ? queueData.queues : [];
      } catch (_) {
        queueLoadError = true;
      }
    }

    const presetOptions = [`<option value="">(None)</option>`, ...presets.map((p, i) => `<option value="${i}">${escapeHtml(p.name)}</option>`)].join('');
    const queueOptions = [
      '<option value="">Default (ABDM)</option>',
      ...queues.map((queue) => `<option value="${escapeHtml(queue.id)}">${escapeHtml(queue.name)} (#${escapeHtml(queue.id)})</option>`),
    ];
    const selectedQueueExists = selectedQueueId === null || queues.some((queue) => Number(queue.id) === selectedQueueId);
    if (selectedQueueId !== null && !selectedQueueExists) {
      queueOptions.push(`<option value="${escapeHtml(selectedQueueId)}">Unavailable queue (#${escapeHtml(selectedQueueId)})</option>`);
    }

    openModal('AB Download Manager Settings', `
      <div class="gab-field"><div id="gab-settings-status" class="gab-status"><span class="gab-status-dot ${state.connected ? 'connected' : ''}"></span>ABDM ${state.connected ? 'Connected' : 'Offline'}</div></div>
      <div class="gab-field">
        <label for="gab-queue-select">Download queue</label>
        <select id="gab-queue-select" class="gab-select">${queueOptions.join('')}</select>
        <div class="gab-muted" style="margin-top:.3rem">Default omits ABDM's optional <code>queueId</code>. The queue list refreshes whenever this Settings popup opens.${queueLoadError ? ' Queue list could not be refreshed.' : ''}</div>
      </div>
      <div class="gab-field">
        <label for="gab-preset-select">Save preset</label>
        <select id="gab-preset-select" class="gab-select">${presetOptions}</select>
      </div>
      <div class="gab-field">
        <label for="gab-save-folder">Save folder</label>
        <input id="gab-save-folder" class="gab-input" type="text" value="${escapeHtml(lastFolder)}" placeholder="Empty = ABDM default folder">
      </div>
      <div class="gab-field">
        <label for="gab-preset-name">Preset name</label>
        <input id="gab-preset-name" class="gab-input" type="text" placeholder="Videos">
        <div class="gab-preset-actions">
          ${button('Add', 'gab-preset-add')}
          ${button('Edit', 'gab-preset-edit')}
          ${button('Delete', 'gab-preset-delete')}
        </div>
      </div>
      <div class="gab-muted">When Save folder is empty, the helper omits ABDM's optional <code>folder</code> field so ABDM uses its configured default.</div>
      <div class="gab-actions">
        ${button('Close', 'gab-settings-close')}
        ${button('Save', 'gab-settings-save', true)}
      </div>
    `, (card, backdrop) => {
      const select = card.querySelector('#gab-preset-select');
      const queueSelect = card.querySelector('#gab-queue-select');
      const folder = card.querySelector('#gab-save-folder');
      const name = card.querySelector('#gab-preset-name');
      let localPresets = getPresets();
      queueSelect.value = selectedQueueId === null ? '' : String(selectedQueueId);

      const rebuild = (selectedIndex = '') => {
        select.innerHTML = `<option value="">(None)</option>` + localPresets.map((p, i) => `<option value="${i}">${escapeHtml(p.name)}</option>`).join('');
        select.value = selectedIndex;
      };
      select.addEventListener('change', () => {
        if (select.value === '') return;
        const preset = localPresets[Number(select.value)];
        if (!preset) return;
        name.value = preset.name;
        folder.value = preset.path;
      });
      card.querySelector('#gab-preset-add').addEventListener('click', () => {
        const presetName = name.value.trim();
        if (!presetName) return toast('Preset name is required.', 'warning');
        localPresets.push({ name: presetName, path: folder.value.trim() });
        rebuild(String(localPresets.length - 1));
      });
      card.querySelector('#gab-preset-edit').addEventListener('click', () => {
        const index = Number(select.value);
        if (select.value === '' || !localPresets[index]) return toast('Select a preset to edit.', 'warning');
        const presetName = name.value.trim();
        if (!presetName) return toast('Preset name is required.', 'warning');
        localPresets[index] = { name: presetName, path: folder.value.trim() };
        rebuild(String(index));
      });
      card.querySelector('#gab-preset-delete').addEventListener('click', () => {
        const index = Number(select.value);
        if (select.value === '' || !localPresets[index]) return toast('Select a preset to delete.', 'warning');
        localPresets.splice(index, 1);
        name.value = '';
        rebuild('');
      });
      card.querySelector('#gab-settings-close').addEventListener('click', () => backdrop.remove());
      card.querySelector('#gab-settings-save').addEventListener('click', () => {
        GM_setValue(STORAGE.lastSaveFolder, folder.value.trim());
        const queueValue = queueSelect.value;
        GM_setValue(STORAGE.queueId, queueValue === '' ? '' : Number(queueValue));
        savePresets(localPresets);
        backdrop.remove();
        toast('ABDM settings saved.', 'success');
      });
    });
  }

  function renderTreeNode(node, depth = 0) {
    const checked = state.selectedKeys.has(node.key) ? 'checked' : '';
    const size = node.type === 'file' ? formatBytes(node.size) : `${node.file_count} files / ${formatBytes(node.total_size)}`;
    return `
      <div class="gab-tree-row" style="padding-left:${Math.min(depth, 8) * 16}px">
        <input type="checkbox" data-gab-tree-key="${escapeHtml(node.key)}" ${checked}>
        <span>${node.type === 'folder' ? '📁' : '📄'}</span>
        <span class="gab-tree-name" title="${escapeHtml(node.relative_path)}">${escapeHtml(node.name)}</span>
        <span class="gab-tree-size">${escapeHtml(size)}</span>
      </div>
      ${(node.children || []).map((child) => renderTreeNode(child, depth + 1)).join('')}
    `;
  }

  function openSelectionTree() {
    if (!state.root) return toast('Load GoFile content first.', 'warning');
    openModal('GoFile Selection', `
      <div class="gab-muted" style="margin-bottom:.55rem">Fallback selector for rows that could not be matched to the current GoFile DOM. Folder selection is recursive.</div>
      <div class="gab-tree">${(state.root.children || []).map((node) => renderTreeNode(node)).join('')}</div>
      <div class="gab-actions">
        ${button('Clear', 'gab-tree-clear')}
        ${button('Apply', 'gab-tree-apply', true)}
      </div>
    `, (card, backdrop) => {
      const boxes = [...card.querySelectorAll('[data-gab-tree-key]')];
      const syncIndeterminate = () => {
        for (const box of boxes) {
          const node = state.nodeByKey.get(box.dataset.gabTreeKey);
          if (!node || node.type !== 'folder') continue;
          const descendants = new Set(node.file_keys || []);
          const checkedFiles = boxes.filter((b) => b.checked && descendants.has(b.dataset.gabTreeKey)).length;
          box.indeterminate = !box.checked && checkedFiles > 0 && checkedFiles < descendants.size;
        }
      };
      boxes.forEach((box) => box.addEventListener('change', () => {
        const node = state.nodeByKey.get(box.dataset.gabTreeKey);
        if (node?.type === 'folder') {
          const descendants = new Set(node.file_keys || []);
          boxes.forEach((childBox) => {
            if (descendants.has(childBox.dataset.gabTreeKey)) childBox.checked = box.checked;
          });
        }
        syncIndeterminate();
      }));
      card.querySelector('#gab-tree-clear').addEventListener('click', () => {
        boxes.forEach((box) => { box.checked = false; box.indeterminate = false; });
      });
      card.querySelector('#gab-tree-apply').addEventListener('click', () => {
        state.selectedKeys.clear();
        boxes.filter((box) => box.checked).forEach((box) => state.selectedKeys.add(box.dataset.gabTreeKey));
        backdrop.remove();
        updateToolbar();
      });
      syncIndeterminate();
    });
  }

  async function sendSelected(retryOnly, preserveStructure = true) {
    if (state.sending) return;
    let queueId;
    if (retryOnly) {
      preserveStructure = state.lastSendPreserveStructure;
      queueId = state.lastSendQueueId;
    } else {
      state.lastSendPreserveStructure = preserveStructure;
      queueId = getSelectedQueueId();
      state.lastSendQueueId = queueId;
    }
    if (!retryOnly && !state.resolveId && state.provisionalSelectedIds.size) {
      await resolveContent(true);
      if (!state.resolveId && state.provisionalSelectedIds.size) {
        return toast('Selection kept. GoFile resolve is still unavailable; try Send again later.', 'warning');
      }
    }
    let keys = retryOnly ? [...state.failedFileKeys] : selectedFileKeys();
    if (!keys.length) return toast(retryOnly ? 'No failed items to retry.' : 'No files selected.', 'warning');
    if (!state.resolveId) return toast('GoFile content could not be resolved yet.', 'warning');

    const connected = await checkABDM();
    if (!connected) return toast('AB Download Manager is offline.', 'error');

    state.sending = true;
    state.failedFileKeys = [];
    updateToolbar();
    const saveRoot = GM_getValue(STORAGE.lastSaveFolder, '');
    let success = 0;
    const failed = [];

    for (let index = 0; index < keys.length; index += 1) {
      const key = keys[index];
      const node = state.nodeByKey.get(key);
      setProgress(index, keys.length, node?.name || '');
      try {
        const data = await gmRequest('POST', '/api/abdm/send', {
          resolve_id: state.resolveId,
          file_keys: [key],
          save_root: saveRoot,
          preserve_structure: preserveStructure,
          queue_id: queueId,
        }, 30000);
        const result = data.results?.[0];
        if (result?.ok) success += 1;
        else failed.push(key);
      } catch (error) {
        if (error.code === 'resolve_expired') {
          toast('Resolved GoFile session expired. Reloading content…', 'warning');
          state.sending = false;
          await resolveContent();
          return;
        }
        failed.push(key);
      }
      setProgress(index + 1, keys.length, node?.name || '');
    }

    state.failedFileKeys = failed;
    state.sending = false;
    updateToolbar();
    showSendResult(success, failed.length);
  }

  function showSendResult(success, failed) {
    openModal('Sent to ABDM', `
      <div class="gab-field">Success <strong>${success}</strong><br>Failed <strong>${failed}</strong></div>
      <div class="gab-actions">
        ${failed ? button('Retry Failed', 'gab-retry-failed', true) : ''}
        ${button('Close', 'gab-result-close')}
      </div>
    `, (card, backdrop) => {
      card.querySelector('#gab-result-close').addEventListener('click', () => backdrop.remove());
      const retry = card.querySelector('#gab-retry-failed');
      if (retry) retry.addEventListener('click', () => { backdrop.remove(); sendSelected(true); });
    });
    toast(failed ? `Sent ${success}; ${failed} failed.` : `Sent ${success} file(s) to ABDM.`, failed ? 'warning' : 'success');
  }

  function scheduleDomRefresh() {
    clearTimeout(state.domTimer);
    state.domTimer = setTimeout(() => {
      ensureToolbar();
      injectCheckboxes();
    }, 250);
  }

  function scheduleNavigationRefresh() {
    clearTimeout(state.refreshTimer);
    state.refreshTimer = setTimeout(() => {
      const current = window.location.href;
      if (current === state.lastUrl) return;
      state.lastUrl = current;
      state.sourceUrl = current;
      state.password = null;
      const input = document.getElementById('gab-url');
      if (input) input.value = current;
      state.provisionalSelectedIds.clear();
      if (/^https:\/\/gofile\.io\/d\//i.test(current)) resolveContent(false);
      else resetResolution(false);
    }, 180);
  }

  function hookHistory() {
    for (const method of ['pushState', 'replaceState']) {
      const original = history[method];
      history[method] = function (...args) {
        const result = original.apply(this, args);
        scheduleNavigationRefresh();
        return result;
      };
    }
    window.addEventListener('popstate', scheduleNavigationRefresh);
  }

  function observeFileManager() {
    const target = document.querySelector('#fm-root')?.parentElement || document.querySelector('main') || document.body;
    const observer = new MutationObserver((mutations) => {
      const relevant = mutations.some((mutation) => {
        const changedNodes = [...mutation.addedNodes, ...mutation.removedNodes];
        const ownOnly = changedNodes.length > 0 && changedNodes.every((node) =>
          node instanceof Element && (node.matches('.gab-check-wrap') || node.closest?.('.gab-check-wrap') || node.id === TOOLBAR_ID || node.closest?.(`#${TOOLBAR_ID}`))
        );
        if (ownOnly) return false;
        const mutationTarget = mutation.target instanceof Element ? mutation.target : mutation.target.parentElement;
        if (mutationTarget?.id === 'fm-root' || mutationTarget?.closest?.('#fm-root')) return true;
        return changedNodes.some((node) => {
          if (!(node instanceof Element)) return false;
          return node.id === 'fm-root' || node.id === 'fm-toolbar' || Boolean(node.querySelector?.('#fm-root,#fm-toolbar'));
        });
      });
      if (relevant || !document.getElementById(TOOLBAR_ID)) scheduleDomRefresh();
    });
    observer.observe(target, { childList: true, subtree: true });
  }

  async function init() {
    loadNativeUi();
    ensureToolbar();
    hookHistory();
    observeFileManager();
    await checkABDM();
    injectCheckboxes();
    if (/^https:\/\/gofile\.io\/d\//i.test(window.location.href)) await resolveContent(false);
  }

  init();
})();
