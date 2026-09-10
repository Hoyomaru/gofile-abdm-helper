const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(require('node:path').join(__dirname, '..', 'gofile-abdm.user.js'), 'utf8');

function makeSessionStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
  };
}

function makeRuntime({dom = false} = {}) {
  const sessionStorage = makeSessionStorage();
  const window = {
    __GAB_TEST_MODE__: true,
    location: {href: 'https://gofile.io/d/root123'},
    sessionStorage,
  };
  const context = {
    window,
    crypto: crypto.webcrypto,
    TextEncoder,
    console,
    setTimeout,
    clearTimeout,
    GM_getValue: () => '',
    GM_setValue: () => {},
    GM_xmlhttpRequest: () => {},
    requestAnimationFrame: (callback) => callback(),
    matchMedia: () => ({matches: false}),
    getComputedStyle: () => ({backgroundColor: 'rgb(255, 255, 255)'}),
  };
  if (dom) context.document = makeDocument();
  vm.runInNewContext(SOURCE, context, {filename: 'gofile-abdm.user.js'});
  return {api: window.__GAB_TEST_API__, window, document: context.document};
}

function operation(api, sourceUrl = 'https://gofile.io/d/root123') {
  const op = {
    generation: 1,
    sourceUrl,
    credentials: new Map(),
    preservedNodeIds: new Set(),
    triedStorage: new Set(),
    invalidated: false,
  };
  api.state.sourceUrl = sourceUrl;
  api.state.resolveGeneration = 1;
  api.state.activeResolve = op;
  api.state.resolving = true;
  return op;
}

function digest(value) {
  return crypto.createHash('sha256').update(value, 'utf8').digest('hex');
}

test('wrong password is replaced in one resolve operation without recursion', async () => {
  const {api} = makeRuntime();
  const op = operation(api);
  const requests = [];
  const prompts = [];
  const result = await api.runResolveOperation(op, async (body) => {
    requests.push(body);
    if (requests.length === 1) {
      throw Object.assign(new Error('wrong'), {code: 'wrong_password', contentId: 'folder01'});
    }
    return {resolve_id: 'resolved'};
  }, async (wrong, context) => {
    prompts.push({wrong, context});
    return 'correct 日本語';
  });

  assert.deepEqual(result, {resolve_id: 'resolved'});
  assert.equal(requests.length, 2);
  assert.equal(prompts[0].wrong, true);
  assert.equal(prompts[0].context.contentId, 'folder01');
  assert.equal(requests[1].password_hashes.folder01, digest('correct 日本語'));
});

test('a storage digest is tried once and is sent without double hashing', async () => {
  const {api, window} = makeRuntime();
  const stored = 'A'.repeat(64);
  window.sessionStorage.setItem('password|folder01', stored);
  const op = operation(api);
  const requests = [];
  let prompted = false;
  const result = await api.runResolveOperation(op, async (body) => {
    requests.push(body);
    if (requests.length === 1) {
      throw Object.assign(new Error('required'), {code: 'password_required', contentId: 'folder01'});
    }
    return {resolve_id: 'resolved'};
  }, async () => {
    prompted = true;
    return null;
  });

  assert.deepEqual(result, {resolve_id: 'resolved'});
  assert.equal(prompted, false);
  assert.equal(requests.length, 2);
  assert.equal(requests[1].password_hashes.folder01, stored.toLowerCase());
  assert.notEqual(requests[1].password_hashes.folder01, digest(stored));
  assert.equal(op.triedStorage.size, 1);
});

test('cancel ends the operation and does not issue a second resolve', async () => {
  const {api} = makeRuntime();
  const op = operation(api);
  let calls = 0;
  const result = await api.runResolveOperation(op, async () => {
    calls += 1;
    throw Object.assign(new Error('required'), {code: 'password_required', contentId: 'folder01'});
  }, async () => null);

  assert.equal(result, null);
  assert.equal(calls, 1);
  assert.equal(op.cancelled, true);
});

test('a stale response is ignored after navigation invalidates its operation', async () => {
  const {api} = makeRuntime();
  const op = operation(api, 'https://gofile.io/d/root123');
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  const running = api.runResolveOperation(op, () => pending, async () => 'unused');
  await new Promise((resolve) => setImmediate(resolve));

  api.state.sourceUrl = 'https://gofile.io/d/other456';
  api.invalidateResolve();
  release({resolve_id: 'stale'});

  assert.equal(await running, null);
  assert.equal(api.state.activeResolve, null);
  assert.equal(api.state.resolving, false);
  assert.equal(op.credentials.size, 0);
});

class FakeClassList {
  constructor() { this.values = new Set(); }
  add(...values) { values.forEach((value) => this.values.add(value)); }
  remove(...values) { values.forEach((value) => this.values.delete(value)); }
  contains(value) { return this.values.has(value); }
}

class FakeElement {
  constructor(tagName, document) {
    this.tagName = tagName.toUpperCase();
    this.ownerDocument = document;
    this.children = [];
    this.listeners = new Map();
    this.classList = new FakeClassList();
    this.dataset = {};
    this.style = {};
    this.value = '';
    this.removed = false;
  }

  set className(value) {
    this._className = value;
    this.classList = new FakeClassList();
    value.split(/\s+/).filter(Boolean).forEach((item) => this.classList.add(item));
  }

  get className() { return this._className || ''; }

  set innerHTML(value) {
    this.children = [];
    const card = new FakeElement('div', this.ownerDocument);
    card.className = 'gab-modal-card';
    this.appendChild(card);
    for (const match of value.matchAll(/id="([^"]+)"/g)) {
      const child = new FakeElement(match[1].includes('password') ? 'input' : 'button', this.ownerDocument);
      child.id = match[1];
      if (child.id === 'gab-password') child.value = '';
      card.appendChild(child);
    }
  }

  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    this.ownerDocument?.register(child);
    return child;
  }

  prepend(child) {
    child.parentElement = this;
    this.children.unshift(child);
    this.ownerDocument?.register(child);
    return child;
  }

  querySelector(selector) {
    if (selector === '.gab-modal-card') return this.find((item) => item.classList.contains('gab-modal-card'));
    if (selector.startsWith('#')) return this.find((item) => item.id === selector.slice(1));
    return null;
  }

  find(predicate) {
    for (const child of this.children) {
      if (predicate(child)) return child;
      const nested = child.find(predicate);
      if (nested) return nested;
    }
    return null;
  }

  addEventListener(type, listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(listener);
  }

  removeEventListener(type, listener) {
    const listeners = this.listeners.get(type) || [];
    this.listeners.set(type, listeners.filter((item) => item !== listener));
  }

  dispatchEvent(event) {
    if (!event.target) event.target = this;
    if (!event.preventDefault) event.preventDefault = () => {};
    for (const listener of [...(this.listeners.get(event.type) || [])]) listener(event);
  }

  getClientRects() { return [{}]; }
  focus() { this.focused = true; }

  remove() {
    this.removed = true;
    this.ownerDocument?.unregister(this);
    this.parentElement?.removeChild(this);
  }

  removeChild(child) {
    this.children = this.children.filter((item) => item !== child);
  }
}

function makeDocument() {
  const document = {
    registry: new Map(),
    documentElement: new FakeElement('html', null),
    body: null,
    head: null,
    register(element) {
      if (element.id) this.registry.set(element.id, element);
      for (const child of element.children) this.register(child);
    },
    unregister(element) {
      if (element.id) this.registry.delete(element.id);
      for (const child of element.children) this.unregister(child);
    },
    createElement(tagName) { return new FakeElement(tagName, this); },
    getElementById(id) { return this.registry.get(id) || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  };
  document.documentElement.ownerDocument = document;
  document.documentElement.classList = new FakeClassList();
  document.documentElement.dataset = {};
  document.body = new FakeElement('body', document);
  document.body.classList = new FakeClassList();
  document.body.dataset = {};
  document.head = new FakeElement('head', document);
  return document;
}

test('password modal resolves exactly once for click, Enter, Escape, background, and replacement', async () => {
  const {api, document} = makeRuntime({dom: true});

  const clickPromise = api.promptPassword(false, {relativePath: 'Root/Subs'});
  const clickModal = document.getElementById('gofile-abdm-modal');
  const clickCard = clickModal.querySelector('.gab-modal-card');
  clickCard.querySelector('#gab-password').value = 'with spaces ';
  clickCard.querySelector('#gab-password-ok').dispatchEvent({type: 'click'});
  clickCard.querySelector('#gab-password-ok').dispatchEvent({type: 'click'});
  assert.equal(await clickPromise, 'with spaces ');

  const composingPromise = api.promptPassword(false);
  const composingInput = document.getElementById('gab-password');
  composingInput.value = 'ime';
  composingInput.dispatchEvent({type: 'keydown', key: 'Enter', isComposing: true});
  assert.equal(document.getElementById('gofile-abdm-modal').removed, false);
  composingInput.dispatchEvent({type: 'keydown', key: 'Enter', isComposing: false});
  assert.equal(await composingPromise, 'ime');

  const escapePromise = api.promptPassword(false);
  const escapeModal = document.getElementById('gofile-abdm-modal');
  escapeModal.querySelector('#gab-password').dispatchEvent({type: 'keydown', key: 'Escape'});
  assert.equal(await escapePromise, null);

  const backgroundPromise = api.promptPassword(false);
  const backgroundModal = document.getElementById('gofile-abdm-modal');
  backgroundModal.dispatchEvent({type: 'click', target: backgroundModal});
  assert.equal(await backgroundPromise, null);

  const replacedPromise = api.promptPassword(false);
  const replacementPromise = api.promptPassword(false);
  assert.equal(await replacedPromise, null);
  api.closeModal();
  assert.equal(await replacementPromise, null);
});

test('empty password stays open and Cancel completes it', async () => {
  const {api, document} = makeRuntime({dom: true});
  const pending = api.promptPassword(false);
  const modal = document.getElementById('gofile-abdm-modal');
  modal.querySelector('#gab-password-ok').dispatchEvent({type: 'click'});
  assert.equal(document.getElementById('gofile-abdm-modal').removed, false);
  modal.querySelector('#gab-password-cancel').dispatchEvent({type: 'click'});
  assert.equal(await pending, null);
});
