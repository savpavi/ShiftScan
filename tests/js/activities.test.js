// tests/js/activities.test.js
const test = require('node:test');
const assert = require('node:assert');
const A = require('../../static/js/activities.js');

const NAMES = {
    'content-production': 'Content',
    sports: 'Sports',
    reading: 'Reading',
    social: 'Social',
    gaming: 'Gaming'
};

function fakeStorage(initial) {
    const data = { ...initial };
    return {
        getItem: (k) => (k in data ? data[k] : null),
        setItem: (k, v) => { data[k] = String(v); },
        _data: data
    };
}

test('defaults are named from the supplied translations', () => {
    const list = A.defaultActivities(NAMES);
    assert.deepStrictEqual(list.map((a) => a.name), Object.values(NAMES));
});

test('defaults have unique ids', () => {
    const ids = A.defaultActivities(NAMES).map((a) => a.id);
    assert.strictEqual(new Set(ids).size, ids.length);
});

test('load returns defaults when storage is empty', () => {
    const list = A.load(fakeStorage({}), NAMES);
    assert.strictEqual(list.length, Object.keys(NAMES).length);
});

test('a stored list wins over the defaults', () => {
    const stored = [{ id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'evening' }];
    const storage = fakeStorage({ [A.STORAGE_KEY]: JSON.stringify(stored) });

    assert.deepStrictEqual(A.load(storage, NAMES), stored);
});

test('corrupt stored data falls back to defaults instead of throwing', () => {
    const storage = fakeStorage({ [A.STORAGE_KEY]: 'not json' });
    assert.strictEqual(A.load(storage, NAMES).length, Object.keys(NAMES).length);
});

test('save round-trips through storage', () => {
    const storage = fakeStorage({});
    const list = [{ id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'any' }];

    A.save(storage, list);

    assert.deepStrictEqual(A.load(storage, NAMES), list);
});

test('added activities get an id that does not collide', () => {
    const list = A.defaultActivities(NAMES);
    const grown = A.addActivity(list, { name: 'Guitar', amount: 2, unit: 'hours' });

    const ids = grown.map((a) => a.id);
    assert.strictEqual(new Set(ids).size, ids.length);
    assert.strictEqual(grown.length, list.length + 1);
});

test('a new activity defaults to no time preference', () => {
    const grown = A.addActivity([], { name: 'Guitar', amount: 2, unit: 'hours' });
    assert.strictEqual(grown[0].preferred, 'any');
});

test('removing an activity leaves the others untouched', () => {
    const list = A.defaultActivities(NAMES);
    const shrunk = A.removeActivity(list, list[1].id);

    assert.strictEqual(shrunk.length, list.length - 1);
    assert.ok(!shrunk.some((a) => a.id === list[1].id));
});

test('payload carries only the fields the API accepts', () => {
    const list = [{ id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'evening', enabled: true }];

    assert.deepStrictEqual(A.toPayload(list), [
        { id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'evening' }
    ]);
});

test('disabled activities are left out of the payload', () => {
    const list = [
        { id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'any', enabled: false },
        { id: 'x2', name: 'Sport', amount: 1, unit: 'days', preferred: 'any', enabled: true }
    ];

    assert.deepStrictEqual(A.toPayload(list).map((a) => a.id), ['x2']);
});
