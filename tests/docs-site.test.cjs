const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync(require('node:path').join(__dirname, '..', 'docs', 'site.js'), 'utf8');

function setup(clipboard) {
  const state = { handler: null, selected: false, focused: false, children: [] };
  const button = {
    dataset: { copyUrl: 'https://example.invalid/private' },
    addEventListener(event, fn) {
      assert.equal(event, 'click');
      state.handler = fn;
    }
  };
  const status = {
    textContent: '',
    replaceChildren() { this.textContent = ''; state.children = []; },
    append(node) { state.children.push(node); }
  };
  const year = { textContent: '' };
  const document = {
    querySelector(selector) {
      return selector === '[data-copy-url]' ? button :
        selector === '.copy-status' ? status : null;
    },
    getElementById(id) { return id === 'year' ? year : null; },
    createElement(tag) {
      return {
        tag, children: [],
        append(node) { this.children.push(node); },
        focus() { state.focused = true; },
        select() { state.selected = true; }
      };
    }
  };
  vm.runInNewContext(script, { document, navigator: { clipboard }, Date });
  return { state, status, year };
}

test('copies URL and announces success', async () => {
  let copied = null;
  const { state, status, year } = setup({ writeText: async value => { copied = value; } });
  await state.handler();
  assert.equal(copied, 'https://example.invalid/private');
  assert.match(status.textContent, /copiado/);
  assert.equal(year.textContent, new Date().getFullYear());
});

test('provides a labelled, selected fallback input without clipboard API', async () => {
  const { state, status } = setup(undefined);
  await state.handler();
  assert.equal(status.textContent, '');
  assert.equal(state.children[0].tag, 'label');
  const field = state.children[0].children[0];
  assert.equal(field.value, 'https://example.invalid/private');
  assert.equal(field.readOnly, true);
  assert.equal(state.focused, true);
  assert.equal(state.selected, true);
});

test('falls back when clipboard permission is denied', async () => {
  const { state } = setup({ writeText: async () => { throw new Error('denied'); } });
  await state.handler();
  assert.equal(state.children[0].children[0].className, 'copy-fallback');
});
