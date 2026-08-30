// tests/js/i18n.test.js - i18n.js tarayici globali olarak yazilmis; vm ile yukle.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const vm = require('node:vm');

function load({ saved = null, languages = ['en-US'] } = {}) {
    const store = {};
    if (saved) store['vardiya-lang'] = saved;
    const html = { lang: 'tr' };
    const ctx = {
        console,
        document: { addEventListener() {}, querySelectorAll: () => [], documentElement: html, title: '' },
        localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = v; } },
        navigator: { languages: languages, language: languages[0] },
        window: {}
    };
    ctx.window = ctx;
    vm.createContext(ctx);
    vm.runInContext(fs.readFileSync(__dirname + '/../../static/js/i18n.js', 'utf8'), ctx);
    return { i18n: ctx.i18n, html: html, store: store };
}

test('every language carries the same keys as Turkish', () => {
    const { i18n } = load();
    const base = Object.keys(i18n.translations.tr).sort();
    for (const lang of Object.keys(i18n.languages)) {
        assert.deepStrictEqual(Object.keys(i18n.translations[lang]).sort(), base, lang);
    }
});

test('first visit picks the browser language when it is supported, else English', () => {
    assert.strictEqual(load({ languages: ['de-CH', 'en'] }).i18n.detectLanguage(), 'de');
    assert.strictEqual(load({ languages: ['fr'] }).i18n.detectLanguage(), 'fr');
    assert.strictEqual(load({ languages: ['tr-TR'] }).i18n.detectLanguage(), 'tr');
    assert.strictEqual(load({ languages: ['ja-JP', 'zh'] }).i18n.detectLanguage(), 'en');
});

test('a saved choice beats the browser language', () => {
    const { i18n } = load({ saved: 'fr', languages: ['de'] });
    i18n.loadSavedLanguage();
    assert.strictEqual(i18n.currentLang, 'fr');
});

test('setLanguage updates <html lang> and persists', () => {
    const { i18n, html, store } = load();
    i18n.setLanguage('de');
    assert.strictEqual(html.lang, 'de');
    assert.strictEqual(store['vardiya-lang'], 'de');
});

test('t() fills {placeholders} and falls back to the key', () => {
    const { i18n } = load();
    i18n.currentLang = 'en';
    assert.strictEqual(i18n.t('icsDownloadedWeeks', { weeks: 4, extra: '' }), 'ICS file downloaded with 4 weeks!');
    assert.strictEqual(i18n.t('no.such.key'), 'no.such.key');
});

test('locale() maps the UI language to a BCP 47 tag for dates', () => {
    const { i18n } = load();
    i18n.currentLang = 'fr';
    assert.strictEqual(i18n.locale(), 'fr-FR');
});
