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
            sports: 'Spor',
            reading: 'Kitap Okuma',
            social: 'Sosyal Yaşam',
            gaming: 'Oyun / Dinlenme',
            addActivity: '+ Aktivite Ekle',
            newActivityName: 'Yeni aktivite',
            unitHours: 'saat',
            unitDays: 'gün',
            preferAny: 'Fark etmez',
            preferMorning: 'Sabah',
            preferAfternoon: 'Öğlen',
            preferEvening: 'Akşam',
            removeActivity: 'Sil',
            ariaActivityEnabled: 'Aktiviteyi plana dahil et',
            ariaActivityName: 'Aktivite adı',
            ariaActivityAmount: 'Haftalık miktar',
            ariaActivityUnit: 'Birim',
            ariaActivityPreferred: 'Tercih edilen zaman',
            activityLimitReached: 'En fazla 20 aktivite ekleyebilirsiniz.',

            // ICS etiketleri
            icsShift: 'Vardiya',
            icsSleep: 'Uyku',

            // Varsayılan aktivite adları
            'content-production': 'İçerik Üretimi',

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
            planUnplaced: 'Boş zaman yetmedi, yerleşemeyen: {list}',
            unitHoursShort: 'sa',
            unitDaysShort: 'gün',
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
            share: 'Paylaş',
            shareWithQR: 'QR Kod ile Paylaş',
            scanToShare: 'Bu QR kodu tarayarak vardiya programını paylaşabilirsiniz',
            copyLink: 'Linki Kopyala',
            appTagline: 'Görselinden Takvime',
            close: 'Kapat',
            ocrNanonetsDone: 'Nanonets AI ile OCR tamamlandı!',
            ocrLowConfidence: 'Düşük güven - lütfen kontrol edip düzenleyin',
            ocrTesseractDone: 'Tesseract ile OCR tamamlandı (yedek)',
            icsDownloaded: 'ICS dosyası indirildi{extra}!',
            icsDownloadedWeeks: '{weeks} haftalık ICS dosyası indirildi{extra}!',
            pdfCreating: 'PDF oluşturuluyor...',
            pdfDownloaded: 'PDF indirildi!',
            pdfFailed: 'PDF oluşturulamadı',
            excelCreating: 'Excel oluşturuluyor...',
            excelDownloaded: 'Excel indirildi!',
            excelFailed: 'Excel oluşturulamadı',
            qrFailed: 'QR kod oluşturulamadı',
            linkCopied: 'Link kopyalandı!',
            sharedLoaded: 'Paylaşılan program yüklendi!',
            darkModeOn: 'Karanlık mod aktif',
            lightModeOn: 'Aydınlık mod aktif',
            
            // QR Kod Paylaşım
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
            sports: 'Sports',
            reading: 'Reading',
            social: 'Social Life',
            gaming: 'Gaming / Rest',
            addActivity: '+ Add Activity',
            newActivityName: 'New activity',
            unitHours: 'hours',
            unitDays: 'days',
            preferAny: 'Any time',
            preferMorning: 'Morning',
            preferAfternoon: 'Afternoon',
            preferEvening: 'Evening',
            removeActivity: 'Remove',
            ariaActivityEnabled: 'Include this activity in the plan',
            ariaActivityName: 'Activity name',
            ariaActivityAmount: 'Weekly amount',
            ariaActivityUnit: 'Unit',
            ariaActivityPreferred: 'Preferred time of day',
            activityLimitReached: 'You can add up to 20 activities.',

            // ICS labels
            icsShift: 'Shift',
            icsSleep: 'Sleep',

            // Default activity names
            'content-production': 'Content Creation',

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
            planUnplaced: 'Not enough free time; could not place: {list}',
            unitHoursShort: 'h',
            unitDaysShort: 'd',
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
            share: 'Share',
            shareWithQR: 'Share with QR Code',
            scanToShare: 'Scan this QR code to share the shift schedule',
            copyLink: 'Copy Link',
            appTagline: 'Image to Calendar',
            close: 'Close',
            ocrNanonetsDone: 'OCR completed with Nanonets AI!',
            ocrLowConfidence: 'Low confidence - please check and edit',
            ocrTesseractDone: 'OCR completed with Tesseract (fallback)',
            icsDownloaded: 'ICS file downloaded{extra}!',
            icsDownloadedWeeks: 'ICS file downloaded with {weeks} weeks{extra}!',
            pdfCreating: 'Creating PDF...',
            pdfDownloaded: 'PDF downloaded!',
            pdfFailed: 'PDF export failed',
            excelCreating: 'Creating Excel...',
            excelDownloaded: 'Excel downloaded!',
            excelFailed: 'Excel export failed',
            qrFailed: 'QR code generation failed',
            linkCopied: 'Link copied!',
            sharedLoaded: 'Shared schedule loaded!',
            darkModeOn: 'Dark mode enabled',
            lightModeOn: 'Light mode enabled',
            
            // QR Code Sharing
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
            sports: 'Sport',
            reading: 'Lesen',
            social: 'Soziales Leben',
            gaming: 'Spielen / Ausruhen',
            addActivity: '+ Aktivität hinzufügen',
            newActivityName: 'Neue Aktivität',
            unitHours: 'Stunden',
            unitDays: 'Tage',
            preferAny: 'Egal',
            preferMorning: 'Morgens',
            preferAfternoon: 'Nachmittags',
            preferEvening: 'Abends',
            removeActivity: 'Entfernen',
            ariaActivityEnabled: 'Diese Aktivität in den Plan aufnehmen',
            ariaActivityName: 'Name der Aktivität',
            ariaActivityAmount: 'Wöchentliche Menge',
            ariaActivityUnit: 'Einheit',
            ariaActivityPreferred: 'Bevorzugte Tageszeit',
            activityLimitReached: 'Sie können maximal 20 Aktivitäten hinzufügen.',

            // ICS-Beschriftungen
            icsShift: 'Schicht',
            icsSleep: 'Schlaf',

            // Standard-Aktivitätsnamen
            'content-production': 'Content-Erstellung',

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
            planUnplaced: 'Nicht genug freie Zeit; nicht eingeplant: {list}',
            unitHoursShort: 'Std',
            unitDaysShort: 'Tg',
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
            repeatApplied: 'Schichten für {weeks} Wochen wiederholt',
            share: 'Teilen',
            shareWithQR: 'Per QR-Code teilen',
            scanToShare: 'Diesen QR-Code scannen, um den Schichtplan zu teilen',
            copyLink: 'Link kopieren',
            appTagline: 'Vom Bild zum Kalender',
            close: 'Schließen',
            ocrNanonetsDone: 'OCR mit Nanonets AI abgeschlossen!',
            ocrLowConfidence: 'Geringe Sicherheit - bitte prüfen und korrigieren',
            ocrTesseractDone: 'OCR mit Tesseract abgeschlossen (Ersatz)',
            icsDownloaded: 'ICS-Datei heruntergeladen{extra}!',
            icsDownloadedWeeks: 'ICS-Datei mit {weeks} Wochen heruntergeladen{extra}!',
            pdfCreating: 'PDF wird erstellt...',
            pdfDownloaded: 'PDF heruntergeladen!',
            pdfFailed: 'PDF-Export fehlgeschlagen',
            excelCreating: 'Excel wird erstellt...',
            excelDownloaded: 'Excel heruntergeladen!',
            excelFailed: 'Excel-Export fehlgeschlagen',
            qrFailed: 'QR-Code konnte nicht erstellt werden',
            linkCopied: 'Link kopiert!',
            sharedLoaded: 'Geteilter Plan geladen!',
            darkModeOn: 'Dunkler Modus aktiv',
            lightModeOn: 'Heller Modus aktiv'
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
            sports: 'Sport',
            reading: 'Lecture',
            social: 'Vie sociale',
            gaming: 'Jeux / Repos',
            addActivity: '+ Ajouter une activité',
            newActivityName: 'Nouvelle activité',
            unitHours: 'heures',
            unitDays: 'jours',
            preferAny: 'Peu importe',
            preferMorning: 'Matin',
            preferAfternoon: 'Après-midi',
            preferEvening: 'Soir',
            removeActivity: 'Supprimer',
            ariaActivityEnabled: 'Inclure cette activité dans le plan',
            ariaActivityName: "Nom de l'activité",
            ariaActivityAmount: 'Quantité hebdomadaire',
            ariaActivityUnit: 'Unité',
            ariaActivityPreferred: 'Moment de la journée préféré',
            activityLimitReached: "Vous pouvez ajouter jusqu'à 20 activités.",

            // Libellés ICS
            icsShift: 'Équipe',
            icsSleep: 'Sommeil',

            // Noms d'activités par défaut
            'content-production': 'Création de contenu',

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
            planUnplaced: 'Pas assez de temps libre ; non placé : {list}',
            unitHoursShort: 'h',
            unitDaysShort: 'j',
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
            repeatApplied: 'Équipes répétées pour {weeks} semaines',
            share: 'Partager',
            shareWithQR: 'Partager par QR code',
            scanToShare: 'Scannez ce QR code pour partager le planning',
            copyLink: 'Copier le lien',
            appTagline: "De l'image au calendrier",
            close: 'Fermer',
            ocrNanonetsDone: 'OCR terminée avec Nanonets AI !',
            ocrLowConfidence: 'Faible confiance - veuillez vérifier et corriger',
            ocrTesseractDone: 'OCR terminée avec Tesseract (secours)',
            icsDownloaded: 'Fichier ICS téléchargé{extra} !',
            icsDownloadedWeeks: 'Fichier ICS téléchargé avec {weeks} semaines{extra} !',
            pdfCreating: 'Création du PDF...',
            pdfDownloaded: 'PDF téléchargé !',
            pdfFailed: "Échec de l'export PDF",
            excelCreating: 'Création du fichier Excel...',
            excelDownloaded: 'Excel téléchargé !',
            excelFailed: "Échec de l'export Excel",
            qrFailed: 'Échec de la génération du QR code',
            linkCopied: 'Lien copié !',
            sharedLoaded: 'Planning partagé chargé !',
            darkModeOn: 'Mode sombre activé',
            lightModeOn: 'Mode clair activé'
        }
    },

    // Tarih bicimleme icin BCP 47 etiketi
    locales: { tr: 'tr-TR', en: 'en-US', de: 'de-DE', fr: 'fr-FR' },

    // Dili ayarla
    setLanguage(lang) {
        if (this.translations[lang]) {
            this.currentLang = lang;
            try { localStorage.setItem('vardiya-lang', lang); } catch (e) { /* gizli sekme vb. */ }
            this.updateUI();
        }
    },

    // Çeviri al; {ad} yer tutuculari params ile doldurulur
    t(key, params) {
        const keys = key.split('.');
        let value = this.translations[this.currentLang];
        for (const k of keys) {
            value = value?.[k];
        }
        if (typeof value !== 'string') {
            return key;
        }
        if (params) {
            Object.keys(params).forEach((name) => {
                value = value.split('{' + name + '}').join(String(params[name]));
            });
        }
        return value;
    },

    locale() {
        return this.locales[this.currentLang] || 'en-US';
    },

    // Ilk ziyarette tarayici dili; desteklenen yoksa Ingilizce
    detectLanguage() {
        const candidates = (typeof navigator !== 'undefined' && (navigator.languages || [navigator.language])) || [];
        for (const tag of candidates) {
            const code = String(tag || '').toLowerCase().split('-')[0];
            if (this.translations[code]) {
                return code;
            }
        }
        return 'en';
    },

    // Kaydedilmiş dili yükle; yoksa tarayici dilinden sec
    loadSavedLanguage() {
        let saved = null;
        try { saved = localStorage.getItem('vardiya-lang'); } catch (e) { /* yok say */ }
        this.currentLang = (saved && this.translations[saved]) ? saved : this.detectLanguage();
        this.applyLangAttribute();
    },

    applyLangAttribute() {
        if (typeof document !== 'undefined' && document.documentElement) {
            document.documentElement.lang = this.currentLang;
        }
    },

    // UI'ı güncelle
    // root verilirse yalnizca o alt agac guncellenir (ornegin yeni klonlanan
    // aktivite satirlari); tum sayfayi yeniden yazmak OCR durum metni gibi
    // calisma zamaninda degisen alanlari sifirliyordu.
    updateUI(root) {
        const scope = root || document;
        if (!root) {
            this.applyLangAttribute();
            const select = document.getElementById && document.getElementById('languageSelect');
            if (select && select.value !== this.currentLang) {
                select.value = this.currentLang;
            }
        }

        // data-i18n attribute'u olan tüm elemanları güncelle
        scope.querySelectorAll('[data-i18n]').forEach(el => {
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
        scope.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });

        // data-i18n-aria-label için
        scope.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
            const key = el.getAttribute('data-i18n-aria-label');
            el.setAttribute('aria-label', this.t(key));
        });

        // Title güncelle
        if (!root) {
            document.title = this.t('appTitle') + ' | ' + this.t('appTagline');
        }
    }
};

// Sayfa yüklendiğinde kaydedilmiş dili yükle
document.addEventListener('DOMContentLoaded', () => {
    i18n.loadSavedLanguage();
});

// Global erişim için
window.i18n = i18n;
