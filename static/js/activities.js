/**
 * ShiftScan - kullanici tanimli aktivite listesi
 * Hem tarayicida (window.ShiftScanActivities) hem Node'da (require) calisir.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.ShiftScanActivities = api;
    }
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const STORAGE_KEY = 'shiftscan-activities-v1';

    // Varsayilan sablon: eskiden sabit kodlanmis bes aktivite, artik
    // duzenlenebilir siradan satirlar.
    const DEFAULT_TEMPLATE = [
        { key: 'content-production', amount: 4, unit: 'hours', preferred: 'afternoon' },
        { key: 'sports', amount: 3, unit: 'days', preferred: 'morning' },
        { key: 'reading', amount: 5, unit: 'hours', preferred: 'evening' },
        { key: 'social', amount: 4, unit: 'hours', preferred: 'evening' },
        { key: 'gaming', amount: 2, unit: 'hours', preferred: 'any' }
    ];

    function defaultActivities(names) {
        return DEFAULT_TEMPLATE.map(function (entry, index) {
            return {
                id: 'd' + (index + 1),
                name: (names && names[entry.key]) || entry.key,
                amount: entry.amount,
                unit: entry.unit,
                preferred: entry.preferred,
                enabled: true
            };
        });
    }

    function load(storage, names) {
        try {
            const raw = storage.getItem(STORAGE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                // Sadece dizi olmasi yetmez: bozuk bir eleman (null, string,
                // id'siz kayit) render sirasinda patlar ve kullanici ancak
                // localStorage'i elle temizleyerek kurtulur.
                if (Array.isArray(parsed)) {
                    return parsed.filter(function (e) {
                        return e && typeof e.id === 'string' && typeof e.name === 'string';
                    });
                }
            }
        } catch (err) {
            // Bozuk veya erisilemeyen depolama varsayilanlari engellememeli
        }
        return defaultActivities(names);
    }

    function save(storage, list) {
        try {
            storage.setItem(STORAGE_KEY, JSON.stringify(list));
        } catch (err) {
            // Depolama dolu veya kapali olabilir; plan uretimi yine calisir
        }
    }

    // Bos alan Number('') === 0 verir; 0 kaydedilirse hem localStorage'da
    // kalir hem de sunucudaki amount > 0 kuralina takilip 422 dondurur.
    // Gecersiz girdi icin null doner: cagiran taraf kaydetmez ama kullaniciyi
    // yazarken engellemez.
    function parseAmount(value) {
        const parsed = Number(value);
        if (typeof value === 'string' && value.trim() === '') return null;
        if (!Number.isFinite(parsed) || parsed <= 0) return null;
        return parsed;
    }

    function nextId(list) {
        let candidate = 1;
        const taken = new Set(list.map(function (a) { return a.id; }));
        while (taken.has('u' + candidate)) candidate += 1;
        return 'u' + candidate;
    }

    function addActivity(list, entry) {
        return list.concat([{
            id: nextId(list),
            name: entry.name,
            amount: entry.amount,
            unit: entry.unit,
            preferred: entry.preferred || 'any',
            enabled: true
        }]);
    }

    function removeActivity(list, id) {
        return list.filter(function (a) { return a.id !== id; });
    }

    function toPayload(list) {
        return list
            .filter(function (a) { return a.enabled !== false; })
            .map(function (a) {
                return {
                    id: a.id,
                    name: a.name,
                    amount: a.amount,
                    unit: a.unit,
                    preferred: a.preferred || 'any'
                };
            });
    }

    return {
        STORAGE_KEY: STORAGE_KEY,
        defaultActivities: defaultActivities,
        parseAmount: parseAmount,
        load: load,
        save: save,
        addActivity: addActivity,
        removeActivity: removeActivity,
        toPayload: toPayload
    };
});
