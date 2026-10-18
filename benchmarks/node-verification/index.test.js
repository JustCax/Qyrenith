const { test } = require('node:test');
const assert = require('node:assert');
const { add } = require('./index.js');

test('one plus one is two', () => {
  assert.strictEqual(add(1, 1), 2);
});
