const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(path.join(__dirname, '..', 'gofile-abdm.user.js'), 'utf8');

function runtime() {
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
    GM_xmlhttpRequest: () => {},
    requestAnimationFrame: (callback) => callback(),
    matchMedia: () => ({matches: false}),
    getComputedStyle: () => ({backgroundColor: 'rgb(255, 255, 255)'}),
  };
  vm.runInNewContext(SOURCE, context, {filename: 'gofile-abdm.user.js'});
  return window.__GAB_TEST_API__;
}

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
