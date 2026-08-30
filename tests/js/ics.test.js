const test = require('node:test');
const assert = require('node:assert');
const { escapeICSText, foldICSLine, buildICS } = require('../../static/js/ics.js');

const EVENT = {
    start: new Date(2026, 7, 24, 9, 0, 0),
    end: new Date(2026, 7, 24, 18, 0, 0),
    title: 'Vardiya',
    originalLine: 'Pzt 09:00-18:00'
};

test('escapes comma, semicolon and backslash', () => {
    assert.strictEqual(escapeICSText('Spor, Kitap; C:\\Plan'), 'Spor\\, Kitap\\; C:\\\\Plan');
});

test('escapes newline so it cannot inject a property', () => {
    assert.strictEqual(escapeICSText('Spor\nDESCRIPTION:enjekte'), 'Spor\\nDESCRIPTION:enjekte');
});

test('folds lines longer than 75 octets', () => {
    const folded = foldICSLine('SUMMARY:' + 'A'.repeat(200));
    for (const line of folded.split('\r\n')) {
        assert.ok(Buffer.byteLength(line, 'utf8') <= 75, line);
    }
    assert.ok(folded.split('\r\n')[1].startsWith(' '));
});

test('does not split a multi-byte character across a fold', () => {
    const folded = foldICSLine('SUMMARY:' + 'ç'.repeat(100));
    const rejoined = folded.split('\r\n').map((l, i) => (i ? l.slice(1) : l)).join('');
    assert.strictEqual(rejoined, 'SUMMARY:' + 'ç'.repeat(100));
});

test('injected text stays inside the SUMMARY property', () => {
    const ics = buildICS([{ ...EVENT, title: 'Spor\nDESCRIPTION:enjekte' }]);
    assert.strictEqual((ics.match(/BEGIN:VEVENT/g) || []).length, 1);
    assert.ok(!ics.includes('\r\nDESCRIPTION:enjekte'));
});

test('every event carries UID, DTSTAMP, DTSTART and DTEND', () => {
    const ics = buildICS([EVENT]);
    for (const prop of ['UID:', 'DTSTAMP:', 'DTSTART:', 'DTEND:']) {
        assert.ok(ics.includes(prop), prop);
    }
});

test('events starting in the same minute get distinct UIDs', () => {
    const ics = buildICS([EVENT, { ...EVENT, title: 'Ikinci' }]);
    const uids = ics.split('\r\n').filter((l) => l.startsWith('UID:'));
    assert.strictEqual(new Set(uids).size, 2);
});

test('uses the same PRODID as the backend', () => {
    assert.ok(buildICS([EVENT]).includes('PRODID:-//ShiftScan//ShiftScan//EN'));
});

test('emits DTSTART as floating local time', () => {
    const ics = buildICS([EVENT]);
    assert.ok(ics.includes('DTSTART:20260824T090000'));
});
