// tests/js/ocrparse.test.js
const test = require('node:test');
const assert = require('node:assert');
const O = require('../../static/js/ocrparse.js');

test('without day names, shifts are assigned in order (old behaviour)', () => {
    const out = O.parseShiftText('09:00-18:00 OFF 14:00-22:00');
    assert.match(out, /^Pzt 09:00 - 18:00\nSal OFF\nÇar 14:00 - 22:00\nPer \?/);
    assert.match(out, /4 gün eksik/);
});

test('a missed day no longer shifts the rest of the week', () => {
    // OCR Carsamba'yi kacirdi: eski kod Per'i Car'a yazardi.
    const out = O.parseShiftText('Pzt 09:00-18:00 Sal OFF Per 14:00-22:00 Cum 09:00-18:00');
    const lines = out.split('\n');
    assert.strictEqual(lines[0], 'Pzt 09:00 - 18:00');
    assert.strictEqual(lines[1], 'Sal OFF');
    assert.strictEqual(lines[2], 'Çar ?');
    assert.strictEqual(lines[3], 'Per 14:00 - 22:00');
    assert.strictEqual(lines[4], 'Cum 09:00 - 18:00');
    assert.match(out, /3 gün eksik/);
});

test('day names with punctuation and English/German/French are recognised', () => {
    assert.strictEqual(O.dayIndexOf('Mon:'), 0);
    assert.strictEqual(O.dayIndexOf('Cumartesi'), 5);
    assert.strictEqual(O.dayIndexOf('cum'), 4);
    assert.strictEqual(O.dayIndexOf('Mittwoch'), 2);
    assert.strictEqual(O.dayIndexOf('dimanche'), 6);
    assert.strictEqual(O.dayIndexOf('09:00'), -1);
});

test('unanchored shifts fill the days the anchored ones left free', () => {
    const out = O.parseShiftText('Sal 10:00-19:00 09:00-18:00 OFF');
    const lines = out.split('\n');
    assert.strictEqual(lines[0], 'Pzt 09:00 - 18:00');
    assert.strictEqual(lines[1], 'Sal 10:00 - 19:00');
    assert.strictEqual(lines[2], 'Çar OFF');
});

test('every token format still parses', () => {
    const found = O.scan('09.00-18.00 11:0020:00 09001800 0900 1800 rapor YI');
    assert.deepStrictEqual(found.map((f) => f.value), [
        '09:00 - 18:00', '11:00 - 20:00', '09:00 - 18:00', '09:00 - 18:00', 'OFF', 'OFF'
    ]);
});

test('a full week prints no missing-days footer', () => {
    const out = O.parseShiftText('Pzt 09:00-18:00 Sal 09:00-18:00 Çar OFF Per 09:00-18:00 Cum 09:00-18:00 Cmt OFF Paz OFF');
    assert.doesNotMatch(out, /eksik/);
    assert.strictEqual(out.split('\n').length, 7);
});

test('text without any shift returns null so the caller can show the raw text', () => {
    assert.strictEqual(O.parseShiftText('lorem ipsum'), null);
});
