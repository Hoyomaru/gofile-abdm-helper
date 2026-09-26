const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(path.join(__dirname, '..', 'gofile-abdm.user.js'), 'utf8');

function replaceFunctionBlock(source, startNeedle, endNeedle, replacement) {
  const start = source.indexOf(startNeedle);
  const end = source.indexOf(endNeedle, start);
  assert.ok(start >= 0 && end > start, `Could not replace ${startNeedle}`);
  return source.slice(0, start) + replacement + source.slice(end);
}

function headlessSendSource() {
  let source = SOURCE;
  source = replaceFunctionBlock(source, '  function toast(', '\n  function formatBytes(', '  function toast() {}\n');
  source = replaceFunctionBlock(source, '  function updateToolbar()', '\n  function setProgress(', '  function updateToolbar() {}\n');
  source = replaceFunctionBlock(source, '  function setProgress(', '\n  async function checkABDM()', '  function setProgress() {}\n');
  return source;
}

function runtime({gmXmlhttpRequest = () => {}, neutralizeUi = false} = {}) {
  const window = {
    __GAB_TEST_MODE__: true,
    location: {href: 'https://gofile.io/d/root123'},
    sessionStorage: {getItem: () => null},
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
    GM_xmlhttpRequest: gmXmlhttpRequest,
    requestAnimationFrame: (callback) => callback(),
    matchMedia: () => ({matches: false}),
    getComputedStyle: () => ({backgroundColor: 'rgb(255, 255, 255)'}),
  };
  vm.runInNewContext(neutralizeUi ? headlessSendSource() : SOURCE, context, {filename: 'gofile-abdm.user.js'});
  return window.__GAB_TEST_API__;
}

test('toolbar uses one primary send action with a structure mode checkbox', () => {
  assert.ok(SOURCE.includes('id="gab-preserve-structure"'));
  assert.ok(SOURCE.includes("button('ABDMへ送信', 'gab-send', true)"));
  assert.ok(SOURCE.includes("sendSelected(false, preserveStructure)"));
  assert.ok(!SOURCE.includes("id='gab-send-flat'"));
  assert.ok(!SOURCE.includes('id="gab-send-flat"'));
  assert.ok(!SOURCE.includes("button('Send Flat', 'gab-send-flat')"));
});

test('toolbar explains disabled send and keeps cancel beside progress', () => {
  const hintAt = SOURCE.indexOf('id="gab-send-hint"');
  const progressAt = SOURCE.indexOf('id="gab-progress"');
  const cancelAt = SOURCE.indexOf("button('送信を中止', 'gab-cancel-send')", progressAt);

  assert.ok(hintAt > 0);
  assert.ok(progressAt > hintAt);
  assert.ok(cancelAt > progressAt);
  assert.ok(SOURCE.includes('ファイルを選択してください'));
  assert.ok(SOURCE.includes('role="status" aria-live="polite"'));
  assert.ok(SOURCE.includes("send.title = stats.count === 0 ? '送信するファイルを選択してください。' : ''"));
});

test('resolved row checkbox accessible names stay in Japanese', () => {
  assert.ok(SOURCE.includes('フォルダを再帰的に選択:'));
  assert.ok(SOURCE.includes('ファイルを選択:'));
  assert.ok(SOURCE.includes("checkbox.setAttribute('aria-label'"));
});

test('settings expose a self-diagnosis flow for Helper and ABDM', () => {
  assert.ok(SOURCE.includes("button('自己診断', 'gab-diagnostics')"));
  assert.ok(SOURCE.includes("gmRequest('GET', '/api/diagnostics', null, 10000)"));
  assert.ok(SOURCE.includes('Python Helperに接続できません'));
  assert.ok(SOURCE.includes('ABDMを起動してからもう一度「自己診断」を実行してください。'));
  assert.ok(SOURCE.includes('role="status" aria-live="polite"'));
});

test('fallback selection button is only shown when row matching needs help', () => {
  const start = SOURCE.indexOf('  function updateToolbar()');
  const end = SOURCE.indexOf('  function setProgress(', start);
  const block = SOURCE.slice(start, end);
  assert.ok(block.includes('const fallbackNeeded = Boolean(state.root) && state.unmatched > 0'));
  assert.ok(block.includes("items.classList.toggle('gab-hidden', !fallbackNeeded)"));
});

test('send operation becomes stale when source, generation, or cancellation changes', () => {
  const api = runtime();
  const op = {
    generation: 4,
    sourceUrl: 'https://gofile.io/d/root123',
    cancelled: false,
  };
  api.state.sourceUrl = op.sourceUrl;
  api.state.sendGeneration = op.generation;
  api.state.activeSend = op;
  assert.equal(api.isCurrentSend(op), true);

  api.state.sourceUrl = 'https://gofile.io/d/other456';
  assert.equal(api.isCurrentSend(op), false);
  api.state.sourceUrl = op.sourceUrl;

  api.state.sendGeneration += 1;
  assert.equal(api.isCurrentSend(op), false);
  api.state.sendGeneration = op.generation;

  op.cancelled = true;
  assert.equal(api.isCurrentSend(op), false);
});

test('remaining files remap by stable GoFile content id after re-resolve', () => {
  const api = runtime();
  api.state.nodeByKey.set('old-key-a', {key: 'old-key-a', id: 'file001', type: 'file'});
  api.state.nodeByKey.set('old-key-b', {key: 'old-key-b', id: 'file002', type: 'file'});
  assert.equal(JSON.stringify(api.fileIdsForKeys(['old-key-a', 'old-key-b'])), JSON.stringify(['file001', 'file002']));

  api.state.nodeByKey.clear();
  api.state.nodeByKey.set('new-key-a', {key: 'new-key-a', id: 'file001', type: 'file'});
  api.state.nodeByKey.set('new-key-b', {key: 'new-key-b', id: 'file002', type: 'file'});

  assert.equal(api.fileKeyForContentId('file001'), 'new-key-a');
  const remapped = JSON.parse(JSON.stringify(api.remapFileIdsToKeys(['file001', 'file002'])));
  assert.deepEqual(remapped, [
    {contentId: 'file001', key: 'new-key-a'},
    {contentId: 'file002', key: 'new-key-b'},
  ]);
});

test('navigation invalidates send before starting a new page resolve', () => {
  const start = SOURCE.indexOf('  function scheduleNavigationRefresh()');
  const end = SOURCE.indexOf('  function hookHistory()', start);
  const block = SOURCE.slice(start, end);
  const sendIndex = block.indexOf("invalidateSend('navigation', false)");
  const resolveIndex = block.indexOf('invalidateResolve()');
  assert.notEqual(sendIndex, -1);
  assert.notEqual(resolveIndex, -1);
  assert.ok(sendIndex < resolveIndex);
});

test('resolve expiry resumes by content id and uncertain results are excluded from normal retry', () => {
  const start = SOURCE.indexOf('  async function sendSelected(');
  const end = SOURCE.indexOf('  function showSendResult(', start);
  const block = SOURCE.slice(start, end);

  assert.ok(block.includes("if (error.code === 'resolve_expired')"));
  assert.ok(block.includes('const remainingIds = pendingIds.slice(index)'));
  assert.ok(block.includes('await resolveContent(true)'));
  assert.ok(block.includes('operation.resolveId = state.resolveId'));
  assert.ok(block.includes('pendingIds = remainingIds'));
  assert.ok(block.includes('if (result?.uncertain)'));
  assert.ok(block.includes('operation.uncertain.push'));
  assert.ok(block.includes('state.failedResults.map((item) => item.id)'));
  assert.ok(!block.includes('state.uncertainResults.map((item) => item.id)'));
});

test('send is reserved before ABDM preflight so rapid double-click issues one request', async () => {
  const requests = [];
  const api = runtime({
    neutralizeUi: true,
    gmXmlhttpRequest: (request) => requests.push(request),
  });
  api.state.resolveId = 'resolve-1';
  api.state.nodeByKey.set('key-1', {
    key: 'key-1',
    id: 'file001',
    type: 'file',
    name: 'Episode01.mkv',
    size: 100,
    file_keys: ['key-1'],
  });
  api.state.selectedKeys.add('key-1');

  const first = api.sendSelected(false, true);
  const second = api.sendSelected(false, true);

  assert.equal(requests.length, 1);
  assert.equal(requests[0].method, 'GET');
  assert.match(requests[0].url, /\/api\/abdm\/status$/);
  assert.equal(api.state.sending, true);
  assert.ok(api.state.activeSend);
  await second;

  requests[0].onload({status: 200, response: {connected: false}, responseText: ''});
  await first;

  assert.equal(api.state.sending, false);
  assert.equal(api.state.activeSend, null);

  const third = api.sendSelected(false, true);
  assert.equal(requests.length, 2);
  requests[1].onload({status: 200, response: {connected: false}, responseText: ''});
  await third;
  assert.equal(api.state.sending, false);
});

