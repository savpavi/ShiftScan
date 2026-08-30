/**
 * ShiftScan - OCR metninden haftalik vardiya satirlari
 * Hem tarayicida (window.ShiftScanOcr) hem Node'da (require) calisir.
 *
 * Eski davranis bulunan her vardiyayi sirayla Pzt->Paz'a atiyordu; OCR bir
 * gunu kacirinca haftanin kalani bir gun kayiyordu (backlog 10). Simdi
 * metinde gun adi varsa vardiyalar o gune capalanir; gun adi yoksa eski
 * sirali atama aynen calisir.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.ShiftScanOcr = api;
    }
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // Cikti etiketleri: app.js'teki parseText bunlari (ve Ingilizce
    // kisaltmalari) taniyor.
    const DAY_LABELS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];

    const DAY_NAMES = {
        pzt: 0, pazartesi: 0, mon: 0, monday: 0, mo: 0, montag: 0, lun: 0, lundi: 0,
        sal: 1, sali: 1, salı: 1, tue: 1, tues: 1, tuesday: 1, di: 1, dienstag: 1, mar: 1, mardi: 1,
        car: 2, çar: 2, carsamba: 2, çarşamba: 2, wed: 2, wednesday: 2, mi: 2, mittwoch: 2, mer: 2, mercredi: 2,
        per: 3, persembe: 3, perşembe: 3, thu: 3, thur: 3, thurs: 3, thursday: 3, do: 3, donnerstag: 3, jeu: 3, jeudi: 3,
        cum: 4, cuma: 4, fri: 4, friday: 4, fr: 4, freitag: 4, ven: 4, vendredi: 4,
        cmt: 5, cumartesi: 5, sat: 5, saturday: 5, sa: 5, samstag: 5, sam: 5, samedi: 5,
        paz: 6, pazar: 6, sun: 6, sunday: 6, so: 6, sonntag: 6, dim: 6, dimanche: 6
    };

    const TIME_RANGE = /^(\d{1,2})[:.]?(\d{2})[-–—](\d{1,2})[:.]?(\d{2})$/;
    const NO_HYPHEN = /^(\d{1,2}):(\d{2})(\d{1,2}):(\d{2})$/;
    const COMBINED_8 = /^(\d{4})(\d{4})$/;
    const SINGLE_4 = /^(\d{4})$/;
    // YI=Yillik Izin, HT=Hafta Tatili, RT=Resmi Tatil, UI=Ucretsiz Izin
    const OFF = /^(OFF|0FF|OEF|İZİN|IZIN|IZİN|İZIN|BOŞ|BOS|B0Ş|TATIL|TATİL|RAPOR|RAP0R|RAPORLU|LEAVE|FREE|HOLIDAY|FREI|CONGÉ|CONGE|YI|Yİ|Yl|YL|YILLIK|HT|RT|Üİ|ÜI|UI|ÜCRETSİZ)$/i;

    function range(h1, m1, h2, m2) {
        return `${h1.padStart(2, '0')}:${m1} - ${h2.padStart(2, '0')}:${m2}`;
    }

    function dayIndexOf(token) {
        const key = token.toLowerCase().replace(/[^\p{L}]/gu, '');
        return Object.prototype.hasOwnProperty.call(DAY_NAMES, key) ? DAY_NAMES[key] : -1;
    }

    /**
     * Metni tarar; {day: 0-6|null, value: 'HH:MM - HH:MM'|'OFF'} listesi
     * dondurur. day, vardiyadan hemen once gorulen gun adidir.
     */
    function scan(text) {
        const tokens = String(text || '')
            .replace(/\r\n|\r|\n/g, ' ')
            .split(/\s+/)
            .filter((t) => t.length > 0);

        const found = [];
        let pendingDay = null;

        const push = (value) => {
            found.push({ day: pendingDay, value: value });
            pendingDay = null;
        };

        for (let i = 0; i < tokens.length; i++) {
            const token = tokens[i];

            const day = dayIndexOf(token);
            if (day !== -1) {
                pendingDay = day;
                continue;
            }

            let m = token.match(TIME_RANGE);
            if (m) { push(range(m[1], m[2], m[3], m[4])); continue; }

            m = token.match(NO_HYPHEN);
            if (m) { push(range(m[1], m[2], m[3], m[4])); continue; }

            if (OFF.test(token)) { push('OFF'); continue; }

            m = token.match(COMBINED_8);
            if (m) { push(range(m[1].slice(0, 2), m[1].slice(2), m[2].slice(0, 2), m[2].slice(2))); continue; }

            m = token.match(SINGLE_4);
            if (m && i + 1 < tokens.length) {
                const next = tokens[i + 1].match(SINGLE_4);
                if (next) {
                    push(range(m[1].slice(0, 2), m[1].slice(2), next[1].slice(0, 2), next[1].slice(2)));
                    i++;
                }
            }
        }

        return found;
    }

    /**
     * Bulunanlari 7 gune dagitir. Gun adina capali olanlar kendi gunune
     * gider; capasizlar bos kalan ilk gunlere sirayla girer. Geriye
     * {entries: [7 x string|null], anchored: bool} doner.
     */
    function assignToWeek(found) {
        const entries = new Array(7).fill(null);
        const anchored = found.some((f) => f.day !== null);

        found.forEach((f) => {
            if (f.day !== null && entries[f.day] === null) {
                entries[f.day] = f.value;
            }
        });

        let cursor = 0;
        found.forEach((f) => {
            if (f.day !== null && entries[f.day] === f.value) { return; }
            while (cursor < 7 && entries[cursor] !== null) { cursor++; }
            if (cursor < 7) { entries[cursor] = f.value; cursor++; }
        });

        return { entries: entries, anchored: anchored, found: found.length };
    }

    /**
     * Kullanicinin duzenleyecegi metin. Eksik gunler gun adi + '?' ile
     * yerinde birakilir; parseText bu satirlari (saat yok) atlar.
     */
    function formatWeek(week) {
        const lines = week.entries.map((value, i) => `${DAY_LABELS[i]} ${value === null ? '?' : value}`);
        const missing = week.entries.filter((v) => v === null).length;
        let out = lines.join('\n');
        if (missing > 0) {
            out += `\n\n--- ${missing} gün eksik, lütfen tamamlayın ---`;
        }
        return out;
    }

    function parseShiftText(text) {
        const found = scan(text);
        if (found.length === 0) {
            return null;
        }
        return formatWeek(assignToWeek(found));
    }

    return {
        DAY_LABELS: DAY_LABELS,
        dayIndexOf: dayIndexOf,
        scan: scan,
        assignToWeek: assignToWeek,
        formatWeek: formatWeek,
        parseShiftText: parseShiftText
    };
});
