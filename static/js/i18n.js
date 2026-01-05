/**
 * Vardiya Takvimi - Çoklu Dil Desteği (i18n)
 * Türkçe, İngilizce, Almanca ve Fransızca dil desteği
 */

const i18n = {
    // Mevcut dil
    currentLang: 'tr',

    // Desteklenen diller
    languages: {
        tr: '🇹🇷 Türkçe',
        en: '🇬🇧 English',
        de: '🇩🇪 Deutsch',
        fr: '🇫🇷 Français'
    },

    // Çeviriler
    translations: {
        tr: {
            // Genel
            appTitle: 'Vardiya OCR',
            appSubtitle: 'Vardiya görselinizi AI ile tarayıp ICS takvim dosyasına dönüştürün',
            loading: 'Yükleniyor...',
            planCreating: 'Plan oluşturuluyor...',
            aiPlanCreating: 'AI plan oluşturuyor...',
            
            // Form Alanları
            weekStart: 'Hafta Başlangıcı',
            weekStartHint: 'Programın başladığı Pazartesi gününü seçin',
            shiftProgram: 'Vardiya Programı',
            uploadHint: 'Görsel yükleyin veya metin olarak girin',
            textareaPlaceholder: `Örnek format:
Pzt 08:00 - 17:00
Salı OFF
Çarşamba 14:00 - 22:00
Perşembe 08:00 - 17:00
Cuma OFF
Cumartesi 10:00 - 18:00
Pazar 10:00 - 18:00`,
            textareaHint: 'Her satıra bir gün yazın. İzinli günler için OFF, İZİN veya BOŞ kullanabilirsiniz.',
            
            // Gelişmiş Mod
            advancedMode: 'Gelişmiş Mod:',
            advancedModeDesc: 'Aktivite planlama ve AI desteği',
            weeklyActivities: 'Haftalık Aktiviteler',
            activitiesHint: 'Boş zamanlarınıza yerleştirilecek aktiviteleri seçin',
            
            // Aktiviteler
            contentProduction: 'İçerik Üretimi',
            sports: 'Spor',
            reading: 'Kitap Okuma',
            social: 'Sosyal Aktivite',
            gaming: 'Oyun / Dinlenme',
            weeklyHours: 'Haftalık saat',
            weeklyDays: 'Haftalık gün',
            
            // Butonlar
            preview: 'Önizle',
            createAIPlan: 'AI ile Plan Oluştur',
            downloadICS: 'ICS Dosyasını İndir',
            scanSelectedArea: 'Seçili Alanı Tara',
            
            // OCR
            scanning: 'Taranıyor...',
            starting: 'Başlatılıyor...',
            completed: 'Tamamlandı!',
            
            // Önizleme
            detectedShifts: 'Algılanan Vardiyalar',
            shiftsWillBeAdded: 'Aşağıdaki vardiyalar takvime eklenecek',
            noShiftDetected: 'Hiçbir vardiya algılanamadı. Formatı kontrol edin.',
            
            // Uyarılar
            selectStartDate: 'Lütfen bir başlangıç tarihi seçin!',
            enterShiftText: 'Lütfen vardiya metnini girin veya görsel yükleyin!',
            selectActivity: 'Lütfen en az bir aktivite seçin ve süre/gün belirtin!',
            previewFirst: 'Önce vardiyaları önizleyin!',
            scanError: 'Tarama sırasında bir hata oluştu.',
            convertError: 'Dönüştürme sırasında bir hata oluştu. Lütfen formatı kontrol edin.',
            planCreated: 'Akıllı haftalık plan başarıyla oluşturuldu!',
            planDownloadError: 'Plan oluşturuldu ancak indirilemedi.',
            
            // Footer
            footer: 'Vardiya OCR © 2024 | Ücretsiz ve açık kaynak',
            
            // Şablonlar
            templates: 'Hazır Şablonlar',
            templatesHint: 'Yaygın vardiya düzenlerini hızlıca seçin',
            useTemplate: 'Şablonu Kullan',
            
            // Gün isimleri
            days: {
                mon: 'Pzt',
                tue: 'Sal',
                wed: 'Çar',
                thu: 'Per',
                fri: 'Cum',
                sat: 'Cmt',
                sun: 'Paz'
            },
            
            // Haftalık Tekrar
            repeatWeeks: 'Tekrar Sayısı',
            repeatHint: 'Aynı vardiya programını kaç hafta tekrarlasın?',
            oneWeek: '1 Hafta',
            twoWeeks: '2 Hafta',
            threeWeeks: '3 Hafta',
            fourWeeks: '4 Hafta (1 Ay)',
            eightWeeks: '8 Hafta (2 Ay)',
            twelveWeeks: '12 Hafta (3 Ay)',
            repeatApplied: 'Vardiyalar {weeks} hafta için tekrarlandı',
            
            // QR Kod Paylaşım
            share: 'Paylaş',
            shareWithQR: 'QR Kod ile Paylaş',
            scanToShare: 'Bu QR kodu tarayarak vardiya programını paylaşabilirsiniz',
            copyLink: 'Linki Kopyala'
        },
        
        en: {
            // General
            appTitle: 'Shift OCR',
            appSubtitle: 'Scan your shift image with AI and convert to ICS calendar file',
            loading: 'Loading...',
            planCreating: 'Creating plan...',
            aiPlanCreating: 'AI is creating plan...',
            
            // Form Fields
            weekStart: 'Week Start',
            weekStartHint: 'Select the Monday when the schedule starts',
            shiftProgram: 'Shift Schedule',
            uploadHint: 'Upload image or enter as text',
            textareaPlaceholder: `Example format:
Mon 08:00 - 17:00
Tue OFF
Wed 14:00 - 22:00
Thu 08:00 - 17:00
Fri OFF
Sat 10:00 - 18:00
Sun 10:00 - 18:00`,
            textareaHint: 'Write one day per line. Use OFF, LEAVE, or HOLIDAY for days off.',
            
            // Advanced Mode
            advancedMode: 'Advanced Mode:',
            advancedModeDesc: 'Activity planning and AI support',
            weeklyActivities: 'Weekly Activities',
            activitiesHint: 'Select activities to schedule in your free time',
            
            // Activities
            contentProduction: 'Content Creation',
            sports: 'Sports',
            reading: 'Reading',
            social: 'Social Activity',
            gaming: 'Gaming / Rest',
            weeklyHours: 'Weekly hours',
            weeklyDays: 'Weekly days',
            
            // Buttons
            preview: 'Preview',
            createAIPlan: 'Create Plan with AI',
            downloadICS: 'Download ICS File',
            scanSelectedArea: 'Scan Selected Area',
            
            // OCR
            scanning: 'Scanning...',
            starting: 'Starting...',
            completed: 'Completed!',
            
            // Preview
            detectedShifts: 'Detected Shifts',
            shiftsWillBeAdded: 'The following shifts will be added to calendar',
            noShiftDetected: 'No shifts detected. Please check the format.',
            
            // Alerts
            selectStartDate: 'Please select a start date!',
            enterShiftText: 'Please enter shift text or upload an image!',
            selectActivity: 'Please select at least one activity and specify duration/days!',
            previewFirst: 'Preview shifts first!',
            scanError: 'An error occurred during scanning.',
            convertError: 'An error occurred during conversion. Please check the format.',
            planCreated: 'Smart weekly plan created successfully!',
            planDownloadError: 'Plan created but could not be downloaded.',
            
            // Footer
            footer: 'Shift OCR © 2024 | Free and open source',
            
            // Templates
            templates: 'Quick Templates',
            templatesHint: 'Quickly select common shift patterns',
            useTemplate: 'Use Template',
            
            // Day names
            days: {
                mon: 'Mon',
                tue: 'Tue',
                wed: 'Wed',
                thu: 'Thu',
                fri: 'Fri',
                sat: 'Sat',
                sun: 'Sun'
            },
            
            // Weekly Repeat
            repeatWeeks: 'Repeat Count',
            repeatHint: 'How many weeks should this schedule repeat?',
            oneWeek: '1 Week',
            twoWeeks: '2 Weeks',
            threeWeeks: '3 Weeks',
            fourWeeks: '4 Weeks (1 Month)',
            eightWeeks: '8 Weeks (2 Months)',
            twelveWeeks: '12 Weeks (3 Months)',
            repeatApplied: 'Shifts repeated for {weeks} weeks',
            
            // QR Code Sharing
            share: 'Share',
            shareWithQR: 'Share with QR Code',
            scanToShare: 'Scan this QR code to share the shift schedule',
            copyLink: 'Copy Link'
        },

        // Almanca (German)
        de: {
            // Allgemein
            appTitle: 'Schicht OCR',
            appSubtitle: 'Scannen Sie Ihr Schichtbild mit KI und konvertieren Sie es in eine ICS-Kalenderdatei',
            loading: 'Laden...',
            planCreating: 'Plan wird erstellt...',
            aiPlanCreating: 'KI erstellt Plan...',
            
            // Formularfelder
            weekStart: 'Wochenanfang',
            weekStartHint: 'Wählen Sie den Montag, an dem der Plan beginnt',
            shiftProgram: 'Schichtplan',
            uploadHint: 'Bild hochladen oder als Text eingeben',
            textareaPlaceholder: `Beispielformat:
Mo 08:00 - 17:00
Di FREI
Mi 14:00 - 22:00
Do 08:00 - 17:00
Fr FREI
Sa 10:00 - 18:00
So 10:00 - 18:00`,
            textareaHint: 'Schreiben Sie einen Tag pro Zeile. Verwenden Sie FREI, URLAUB oder FEIERTAG für freie Tage.',
            
            // Erweiterter Modus
            advancedMode: 'Erweiterter Modus:',
            advancedModeDesc: 'Aktivitätsplanung und KI-Unterstützung',
            weeklyActivities: 'Wöchentliche Aktivitäten',
            activitiesHint: 'Wählen Sie Aktivitäten für Ihre Freizeit',
            
            // Aktivitäten
            contentProduction: 'Content-Erstellung',
            sports: 'Sport',
            reading: 'Lesen',
            social: 'Soziale Aktivität',
            gaming: 'Spielen / Ausruhen',
            weeklyHours: 'Wochenstunden',
            weeklyDays: 'Wochentage',
            
            // Buttons
            preview: 'Vorschau',
            createAIPlan: 'Plan mit KI erstellen',
            downloadICS: 'ICS-Datei herunterladen',
            scanSelectedArea: 'Ausgewählten Bereich scannen',
            
            // OCR
            scanning: 'Scannen...',
            starting: 'Starten...',
            completed: 'Abgeschlossen!',
            
            // Vorschau
            detectedShifts: 'Erkannte Schichten',
            shiftsWillBeAdded: 'Folgende Schichten werden zum Kalender hinzugefügt',
            noShiftDetected: 'Keine Schichten erkannt. Bitte überprüfen Sie das Format.',
            
            // Warnungen
            selectStartDate: 'Bitte wählen Sie ein Startdatum!',
            enterShiftText: 'Bitte geben Sie einen Schichttext ein oder laden Sie ein Bild hoch!',
            selectActivity: 'Bitte wählen Sie mindestens eine Aktivität und geben Sie Dauer/Tage an!',
            previewFirst: 'Zuerst Vorschau der Schichten!',
            scanError: 'Beim Scannen ist ein Fehler aufgetreten.',
            convertError: 'Bei der Konvertierung ist ein Fehler aufgetreten. Bitte überprüfen Sie das Format.',
            planCreated: 'Intelligenter Wochenplan erfolgreich erstellt!',
            planDownloadError: 'Plan erstellt, konnte aber nicht heruntergeladen werden.',
            
            // Footer
            footer: 'Schicht OCR © 2024 | Kostenlos und Open Source',
            
            // Vorlagen
            templates: 'Schnellvorlagen',
            templatesHint: 'Wählen Sie häufige Schichtmuster schnell aus',
            useTemplate: 'Vorlage verwenden',
            
            // Tagesnamen
            days: {
                mon: 'Mo',
                tue: 'Di',
                wed: 'Mi',
                thu: 'Do',
                fri: 'Fr',
                sat: 'Sa',
                sun: 'So'
            },
            
            // Wöchentliche Wiederholung
            repeatWeeks: 'Wiederholungsanzahl',
            repeatHint: 'Wie viele Wochen soll dieser Plan wiederholt werden?',
            oneWeek: '1 Woche',
            twoWeeks: '2 Wochen',
            threeWeeks: '3 Wochen',
            fourWeeks: '4 Wochen (1 Monat)',
            eightWeeks: '8 Wochen (2 Monate)',
            twelveWeeks: '12 Wochen (3 Monate)',
            repeatApplied: 'Schichten für {weeks} Wochen wiederholt'
        },

        // Fransızca (French)
        fr: {
            // Général
            appTitle: 'OCR Planning',
            appSubtitle: 'Scannez votre image de planning avec IA et convertissez en fichier calendrier ICS',
            loading: 'Chargement...',
            planCreating: 'Création du plan...',
            aiPlanCreating: "L'IA crée le plan...",
            
            // Champs du formulaire
            weekStart: 'Début de semaine',
            weekStartHint: 'Sélectionnez le lundi où commence le planning',
            shiftProgram: 'Planning des équipes',
            uploadHint: 'Télécharger une image ou saisir comme texte',
            textareaPlaceholder: `Format exemple:
Lun 08:00 - 17:00
Mar CONGÉ
Mer 14:00 - 22:00
Jeu 08:00 - 17:00
Ven CONGÉ
Sam 10:00 - 18:00
Dim 10:00 - 18:00`,
            textareaHint: 'Écrivez un jour par ligne. Utilisez CONGÉ, REPOS ou FÉRIÉ pour les jours de repos.',
            
            // Mode avancé
            advancedMode: 'Mode avancé:',
            advancedModeDesc: 'Planification des activités et support IA',
            weeklyActivities: 'Activités hebdomadaires',
            activitiesHint: 'Sélectionnez les activités pour votre temps libre',
            
            // Activités
            contentProduction: 'Création de contenu',
            sports: 'Sport',
            reading: 'Lecture',
            social: 'Activité sociale',
            gaming: 'Jeux / Repos',
            weeklyHours: 'Heures par semaine',
            weeklyDays: 'Jours par semaine',
            
            // Boutons
            preview: 'Aperçu',
            createAIPlan: 'Créer un plan avec IA',
            downloadICS: 'Télécharger le fichier ICS',
            scanSelectedArea: 'Scanner la zone sélectionnée',
            
            // OCR
            scanning: 'Numérisation...',
            starting: 'Démarrage...',
            completed: 'Terminé!',
            
            // Aperçu
            detectedShifts: 'Équipes détectées',
            shiftsWillBeAdded: 'Les équipes suivantes seront ajoutées au calendrier',
            noShiftDetected: 'Aucune équipe détectée. Veuillez vérifier le format.',
            
            // Alertes
            selectStartDate: 'Veuillez sélectionner une date de début!',
            enterShiftText: 'Veuillez saisir le texte des équipes ou télécharger une image!',
            selectActivity: 'Veuillez sélectionner au moins une activité et spécifier la durée/jours!',
            previewFirst: "Prévisualisez d'abord les équipes!",
            scanError: 'Une erreur est survenue lors de la numérisation.',
            convertError: 'Une erreur est survenue lors de la conversion. Veuillez vérifier le format.',
            planCreated: 'Plan hebdomadaire intelligent créé avec succès!',
            planDownloadError: 'Plan créé mais impossible à télécharger.',
            
            // Pied de page
            footer: 'OCR Planning © 2024 | Gratuit et open source',
            
            // Modèles
            templates: 'Modèles rapides',
            templatesHint: 'Sélectionnez rapidement des modèles courants',
            useTemplate: 'Utiliser le modèle',
            
            // Noms des jours
            days: {
                mon: 'Lun',
                tue: 'Mar',
                wed: 'Mer',
                thu: 'Jeu',
                fri: 'Ven',
                sat: 'Sam',
                sun: 'Dim'
            },
            
            // Répétition hebdomadaire
            repeatWeeks: 'Nombre de répétitions',
            repeatHint: 'Combien de semaines ce planning doit-il se répéter?',
            oneWeek: '1 Semaine',
            twoWeeks: '2 Semaines',
            threeWeeks: '3 Semaines',
            fourWeeks: '4 Semaines (1 Mois)',
            eightWeeks: '8 Semaines (2 Mois)',
            twelveWeeks: '12 Semaines (3 Mois)',
            repeatApplied: 'Équipes répétées pour {weeks} semaines'
        }
    },

    // Dili ayarla
    setLanguage(lang) {
        if (this.translations[lang]) {
            this.currentLang = lang;
            localStorage.setItem('vardiya-lang', lang);
            this.updateUI();
        }
    },

    // Çeviri al
    t(key) {
        const keys = key.split('.');
        let value = this.translations[this.currentLang];
        for (const k of keys) {
            value = value?.[k];
        }
        return value || key;
    },

    // Kaydedilmiş dili yükle
    loadSavedLanguage() {
        const saved = localStorage.getItem('vardiya-lang');
        if (saved && this.translations[saved]) {
            this.currentLang = saved;
        }
    },

    // UI'ı güncelle
    updateUI() {
        // data-i18n attribute'u olan tüm elemanları güncelle
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);
            if (translation) {
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                    if (el.placeholder !== undefined) {
                        el.placeholder = translation;
                    }
                } else {
                    el.textContent = translation;
                }
            }
        });

        // data-i18n-placeholder için
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });

        // Title güncelle
        document.title = this.t('appTitle') + ' | ' + (this.currentLang === 'tr' ? 'Görselinden Takvime' : 'Image to Calendar');
    }
};

// Sayfa yüklendiğinde kaydedilmiş dili yükle
document.addEventListener('DOMContentLoaded', () => {
    i18n.loadSavedLanguage();
});

// Global erişim için
window.i18n = i18n;
