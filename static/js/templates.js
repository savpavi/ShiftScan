/**
 * Vardiya Takvimi - Vardiya Şablonları
 * Yaygın vardiya düzenleri için hazır şablonlar
 */

const shiftTemplates = {
    templates: [
        {
            id: 'office-standard',
            name: {
                tr: '🏢 Ofis Standart (09-18)',
                en: '🏢 Standard Office (09-18)'
            },
            description: {
                tr: 'Pazartesi-Cuma 09:00-18:00',
                en: 'Monday-Friday 09:00-18:00'
            },
            shifts: `Pzt 09:00 - 18:00
Sal 09:00 - 18:00
Çar 09:00 - 18:00
Per 09:00 - 18:00
Cum 09:00 - 18:00
Cmt OFF
Paz OFF`
        },
        {
            id: 'office-early',
            name: {
                tr: '🌅 Ofis Erken (08-17)',
                en: '🌅 Early Office (08-17)'
            },
            description: {
                tr: 'Pazartesi-Cuma 08:00-17:00',
                en: 'Monday-Friday 08:00-17:00'
            },
            shifts: `Pzt 08:00 - 17:00
Sal 08:00 - 17:00
Çar 08:00 - 17:00
Per 08:00 - 17:00
Cum 08:00 - 17:00
Cmt OFF
Paz OFF`
        },
        {
            id: 'retail-6day',
            name: {
                tr: '🛒 Perakende 6 Gün',
                en: '🛒 Retail 6 Days'
            },
            description: {
                tr: 'Pazartesi-Cumartesi 10:00-19:00',
                en: 'Monday-Saturday 10:00-19:00'
            },
            shifts: `Pzt 10:00 - 19:00
Sal 10:00 - 19:00
Çar 10:00 - 19:00
Per 10:00 - 19:00
Cum 10:00 - 19:00
Cmt 10:00 - 19:00
Paz OFF`
        },
        {
            id: 'hospital-day',
            name: {
                tr: '🏥 Hastane Gündüz (08-20)',
                en: '🏥 Hospital Day Shift (08-20)'
            },
            description: {
                tr: '12 saatlik gündüz vardiyası',
                en: '12-hour day shift pattern'
            },
            shifts: `Pzt 08:00 - 20:00
Sal 08:00 - 20:00
Çar OFF
Per 08:00 - 20:00
Cum 08:00 - 20:00
Cmt OFF
Paz OFF`
        },
        {
            id: 'hospital-night',
            name: {
                tr: '🌙 Hastane Gece (20-08)',
                en: '🌙 Hospital Night Shift (20-08)'
            },
            description: {
                tr: '12 saatlik gece vardiyası',
                en: '12-hour night shift pattern'
            },
            shifts: `Pzt 20:00 - 08:00
Sal OFF
Çar 20:00 - 08:00
Per OFF
Cum 20:00 - 08:00
Cmt OFF
Paz OFF`
        },
        {
            id: 'factory-morning',
            name: {
                tr: '🏭 Fabrika Sabah (06-14)',
                en: '🏭 Factory Morning (06-14)'
            },
            description: {
                tr: '3 vardiyalı sistemde sabah',
                en: 'Morning shift in 3-shift system'
            },
            shifts: `Pzt 06:00 - 14:00
Sal 06:00 - 14:00
Çar 06:00 - 14:00
Per 06:00 - 14:00
Cum 06:00 - 14:00
Cmt OFF
Paz OFF`
        },
        {
            id: 'factory-afternoon',
            name: {
                tr: '🏭 Fabrika Öğleden Sonra (14-22)',
                en: '🏭 Factory Afternoon (14-22)'
            },
            description: {
                tr: '3 vardiyalı sistemde öğleden sonra',
                en: 'Afternoon shift in 3-shift system'
            },
            shifts: `Pzt 14:00 - 22:00
Sal 14:00 - 22:00
Çar 14:00 - 22:00
Per 14:00 - 22:00
Cum 14:00 - 22:00
Cmt OFF
Paz OFF`
        },
        {
            id: 'call-center',
            name: {
                tr: '📞 Çağrı Merkezi (Dönüşümlü)',
                en: '📞 Call Center (Rotating)'
            },
            description: {
                tr: 'Farklı saatlerde dönüşümlü vardiya',
                en: 'Rotating shifts with different hours'
            },
            shifts: `Pzt 09:00 - 18:00
Sal 09:00 - 18:00
Çar 12:00 - 21:00
Per 12:00 - 21:00
Cum 09:00 - 18:00
Cmt OFF
Paz OFF`
        },
        {
            id: 'weekend-worker',
            name: {
                tr: '📅 Hafta Sonu Çalışan',
                en: '📅 Weekend Worker'
            },
            description: {
                tr: 'Sadece hafta sonu çalışma',
                en: 'Weekend only work schedule'
            },
            shifts: `Pzt OFF
Sal OFF
Çar OFF
Per OFF
Cum OFF
Cmt 10:00 - 22:00
Paz 10:00 - 22:00`
        },
        {
            id: 'part-time',
            name: {
                tr: '⏰ Yarı Zamanlı (4 Saat)',
                en: '⏰ Part-Time (4 Hours)'
            },
            description: {
                tr: 'Günde 4 saat yarı zamanlı',
                en: '4 hours per day part-time'
            },
            shifts: `Pzt 09:00 - 13:00
Sal 09:00 - 13:00
Çar 09:00 - 13:00
Per 09:00 - 13:00
Cum 09:00 - 13:00
Cmt OFF
Paz OFF`
        }
    ],

    // Dile göre şablon adını al
    getName(template, lang = 'tr') {
        return template.name[lang] || template.name.tr;
    },

    // Dile göre açıklamayı al
    getDescription(template, lang = 'tr') {
        return template.description[lang] || template.description.tr;
    },

    // Tüm şablonları al
    getAll() {
        return this.templates;
    },

    // ID'ye göre şablon bul
    getById(id) {
        return this.templates.find(t => t.id === id);
    },

    // Şablonu uygula (textarea'ya yaz)
    apply(id, targetTextarea) {
        const template = this.getById(id);
        if (template && targetTextarea) {
            targetTextarea.value = template.shifts;
            // Değişiklik olayını tetikle
            targetTextarea.dispatchEvent(new Event('input', { bubbles: true }));
            return true;
        }
        return false;
    }
};

// Global erişim için
window.shiftTemplates = shiftTemplates;
