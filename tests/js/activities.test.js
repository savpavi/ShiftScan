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

test('a deliberately empty list is preserved, not replaced with defaults', () => {
    const storage = fakeStorage({});
    const list = [];

    A.save(storage, list);

    assert.deepStrictEqual(A.load(storage, NAMES), []);
});

test('storage that throws is handled gracefully: load returns defaults', () => {
    const badStorage = {
        getItem: () => { throw new Error('storage unavailable'); },
        setItem: () => { throw new Error('storage unavailable'); }
    };

    const list = A.load(badStorage, NAMES);
    assert.strictEqual(list.length, Object.keys(NAMES).length);
});

test('storage that throws is handled gracefully: save does not propagate', () => {
    const badStorage = {
        getItem: () => null,
        setItem: () => { throw new Error('storage unavailable'); }
    };

    const list = [{ id: 'x1', name: 'Test', amount: 1, unit: 'hours', preferred: 'any' }];

    // Should not throw
    A.save(badStorage, list);
    assert.ok(true);
});

test('valid JSON that is not an array falls back to defaults', () => {
    const storage = fakeStorage({ [A.STORAGE_KEY]: '{}' });
    assert.strictEqual(A.load(storage, NAMES).length, Object.keys(NAMES).length);
});

test('payload activity with missing preferred defaults to any', () => {
    const list = [{ id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', enabled: true }];

    const payload = A.toPayload(list);
    assert.strictEqual(payload[0].preferred, 'any');
});

test('malformed entries are dropped instead of poisoning the rendered list', () => {
    // A corrupt element used to reach renderActivities and throw there, which
    // the user could only recover from by clearing localStorage by hand.
    const stored = [
        null,
        'not an object',
        { id: 'x1', name: 'Guitar', amount: 2, unit: 'hours', preferred: 'evening' },
        { name: 'no id', amount: 1, unit: 'hours' },
        { id: 'x2', amount: 1, unit: 'hours' }
    ];
    const storage = fakeStorage({ [A.STORAGE_KEY]: JSON.stringify(stored) });

    assert.deepStrictEqual(A.load(storage, NAMES), [stored[2]]);
});

test('an emptied or non-positive amount is rejected instead of being stored as 0', () => {
    // Number('') is 0, and ActivityGoal.amount is gt=0 on the server: storing
    // it would survive a reload and 422 the next plan request.
    assert.strictEqual(A.parseAmount(''), null);
    assert.strictEqual(A.parseAmount('   '), null);
    assert.strictEqual(A.parseAmount('0'), null);
    assert.strictEqual(A.parseAmount('-3'), null);
    assert.strictEqual(A.parseAmount('abc'), null);
    assert.strictEqual(A.parseAmount(Infinity), null);
});

test('a valid amount is parsed to a number', () => {
    assert.strictEqual(A.parseAmount('2'), 2);
    assert.strictEqual(A.parseAmount('1.5'), 1.5);
    assert.strictEqual(A.parseAmount(4), 4);
});
