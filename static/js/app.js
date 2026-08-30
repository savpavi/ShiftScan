/**
 * Vardiya Takvimi - Ana JavaScript
 * Modern, sade ve kullanıcı dostu vardiya planlayıcı
 */

document.addEventListener('DOMContentLoaded', () => {
    // ============================================
    // KONFİGÜRASYON
    // ============================================
    
    const dayMap = {
        'pzt': 0, 'pazartesi': 0, 'mon': 0, 'monday': 0,
        'sal': 1, 'salı': 1, 'sali': 1, 'tue': 1, 'tuesday': 1,
        'çar': 2, 'çarşamba': 2, 'carsamba': 2, 'wed': 2, 'wednesday': 2,
        'per': 3, 'perşembe': 3, 'persembe': 3, 'thu': 3, 'thursday': 3,
        'cum': 4, 'cuma': 4, 'fri': 4, 'friday': 4,
        'cmt': 5, 'cumartesi': 5, 'sat': 5, 'saturday': 5,
        'paz': 6, 'pazar': 6, 'sun': 6, 'sunday': 6
    };

    const ignoreKeywords = ['off', 'izin', 'İzin', 'boş', 'bos', 'tatil', 'yıllık', 'rapor', 'leave', 'holiday'];
    
    let parsedEvents = [];
    let cropper = null;
    let isAdvancedMode = false;

    // ============================================
    // DOM ELEMANLARI
    // ============================================
    
    const elements = {
        // Temel
        startDateInput: document.getElementById('startDate'),
        shiftText: document.getElementById('shiftText'),
        convertBtn: document.getElementById('convertBtn'),
        downloadBtn: document.getElementById('downloadBtn'),
        previewSection: document.getElementById('previewSection'),
        previewList: document.getElementById('previewList'),
        
        // OCR
        ocrInput: document.getElementById('ocrInput'),
        cropperContainer: document.getElementById('cropperContainer'),
        imageToCrop: document.getElementById('imageToCrop'),
        scanCropBtn: document.getElementById('scanCropBtn'),
        ocrProgressContainer: document.getElementById('ocrProgressContainer'),
        ocrProgressBar: document.getElementById('ocrProgressBar'),
        ocrStatusText: document.getElementById('ocrStatusText'),
        ocrPercent: document.getElementById('ocrPercent'),
        
        // Gelişmiş Mod
        advancedModeToggle: document.getElementById('advancedModeToggle'),
        advancedSection: document.getElementById('advancedSection'),
        generatePlanBtn: document.getElementById('generatePlanBtn'),
        
        // Loading
        loadingOverlay: document.getElementById('loadingOverlay'),
        
        // Dil ve Şablon
        languageSelect: document.getElementById('languageSelect'),
        templateGrid: document.getElementById('templateGrid'),
        
        // Tema
        themeToggle: document.getElementById('themeToggle'),
        
        // Tekrar
        repeatWeeks: document.getElementById('repeatWeeks'),
        
        // Export Butonları
        downloadPDFBtn: document.getElementById('downloadPDFBtn'),
        downloadExcelBtn: document.getElementById('downloadExcelBtn'),
        
        // QR Kod Paylaşım
        shareQRBtn: document.getElementById('shareQRBtn'),
        qrModal: document.getElementById('qrModal'),
        qrCodeContainer: document.getElementById('qrCodeContainer'),
        closeQRModal: document.getElementById('closeQRModal'),
        copyLinkBtn: document.getElementById('copyLinkBtn'),
        
        // Dijital Acentelik
        dijitalAcentelik: document.getElementById('dijitalAcentelik')
    };

    // ============================================
    // TOAST BİLDİRİM SİSTEMİ
    // ============================================
    
    const toast = {
        container: null,
        
        init() {
            // Toast container oluştur
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        },
        
        show(message, type = 'info', duration = 4000) {
            if (!this.container) this.init();
            
            const toastEl = document.createElement('div');
            toastEl.className = `toast ${type}`;
            
            const icons = {
                success: '✅',
                error: '❌',
                warning: '⚠️',
                info: 'ℹ️'
            };
            
            toastEl.innerHTML = `
                <span class="toast-icon">${icons[type] || icons.info}</span>
                <span class="toast-message">${message}</span>
                <button class="toast-close" aria-label="Kapat">&times;</button>
            `;
            
            // Kapatma butonu
            toastEl.querySelector('.toast-close').addEventListener('click', () => {
                this.hide(toastEl);
            });
            
            this.container.appendChild(toastEl);
            
            // Otomatik kapat
            if (duration > 0) {
                setTimeout(() => this.hide(toastEl), duration);
            }
            
            return toastEl;
        },
        
        hide(toastEl) {
            toastEl.style.animation = 'slideOutRight 0.3s ease-out forwards';
            setTimeout(() => toastEl.remove(), 300);
        },
        
        success(message) { return this.show(message, 'success'); },
        error(message) { return this.show(message, 'error'); },
        warning(message) { return this.show(message, 'warning'); },
        info(message) { return this.show(message, 'info'); }
    };

    // ============================================
    // YARDIMCI FONKSİYONLAR
    // ============================================
    
    function showLoading(message = 'Yükleniyor...') {
        const loadingText = elements.loadingOverlay.querySelector('.loading-text');
        if (loadingText) loadingText.textContent = message;
        elements.loadingOverlay.classList.remove('hidden');
    }

    function hideLoading() {
        elements.loadingOverlay.classList.add('hidden');
    }

    function showAlert(message, type = 'info') {
        toast.show(message, type);
    }

    function formatTime(date) {
        return date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    }

    // ============================================
    // DİL SEÇİCİ
    // ============================================
    
    if (elements.languageSelect) {
        // Kaydedilmiş dili yükle
        const savedLang = localStorage.getItem('vardiya-lang') || 'tr';
        elements.languageSelect.value = savedLang;
        
        // Dil değişikliği
        elements.languageSelect.addEventListener('change', () => {
            const lang = elements.languageSelect.value;
            if (window.i18n) {
                window.i18n.setLanguage(lang);
                renderTemplates(); // Şablonları yeni dilde göster
            }
        });
        
        // Sayfa yüklendiğinde i18n varsa UI'ı güncelle
        setTimeout(() => {
            if (window.i18n) {
                window.i18n.setLanguage(savedLang);
                renderTemplates();
            }
        }, 100);
    }

    // ============================================
    // ŞABLON YÖNETİMİ
    // ============================================
    
    function renderTemplates() {
        if (!elements.templateGrid || !window.shiftTemplates) return;
        
        const lang = window.i18n?.currentLang || 'tr';
        const templates = window.shiftTemplates.getAll();
        
        elements.templateGrid.innerHTML = '';
        
        // İlk 5 şablonu göster (daha fazlası için dropdown kullanılabilir)
        templates.slice(0, 6).forEach(template => {
            const btn = document.createElement('button');
            btn.className = 'template-btn';
            btn.textContent = window.shiftTemplates.getName(template, lang);
            btn.title = window.shiftTemplates.getDescription(template, lang);
            btn.dataset.templateId = template.id;
            
            btn.addEventListener('click', () => {
                // Tüm butonların active class'ını kaldır
                elements.templateGrid.querySelectorAll('.template-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Şablonu uygula
                window.shiftTemplates.apply(template.id, elements.shiftText);
                
                const successMsg = lang === 'tr' ? 'Şablon uygulandı' : 'Template applied';
                toast.success(successMsg);
            });
            
            elements.templateGrid.appendChild(btn);
        });
    }

    // ============================================
    // GELİŞMİŞ MOD TOGGLE
    // ============================================
    
    if (elements.advancedModeToggle) {
        elements.advancedModeToggle.addEventListener('change', () => {
            isAdvancedMode = elements.advancedModeToggle.checked;
            
            if (isAdvancedMode) {
                elements.advancedSection.classList.remove('hidden');
                elements.generatePlanBtn.classList.remove('hidden');
            } else {
                elements.advancedSection.classList.add('hidden');
                elements.generatePlanBtn.classList.add('hidden');
            }
        });
    }

    // Dijital Acentelik checkbox - gün seçicileri göster/gizle
    if (elements.dijitalAcentelik) {
        const dijitalDaysContainer = document.getElementById('dijitalDaysContainer');
        elements.dijitalAcentelik.addEventListener('change', () => {
            if (dijitalDaysContainer) {
                if (elements.dijitalAcentelik.checked) {
                    dijitalDaysContainer.classList.remove('hidden');
                } else {
                    dijitalDaysContainer.classList.add('hidden');
                }
            }
        });
    }

    // ============================================
    // AKTİVİTE LİSTESİ
    // ============================================

    // Backend'deki services/models.py::MAX_ACTIVITIES ile aynı sınır;
    // sunucu zaten reddediyor ama kullanıcı 21. satırı eklerken
    // sebepsiz bir 422 ile karşılaşmasın diye burada da uygulanır.
    const MAX_ACTIVITIES = 20;

    const activityListEl = document.getElementById('activity-list');
    const activityTemplate = document.getElementById('activity-row-template');
    const addActivityBtn = document.getElementById('add-activity');

    // Aktivite listesi opsiyonel bir eklenti: modül yüklenmezse veya
    // şablon/liste elemanları eksikse tarama → ICS akışı etkilenmemeli.
    // Burada atılacak bir hata DOMContentLoaded'i keser ve altındaki
    // cropper/OCR/convert bağlamalarını hiç kurulmadan bırakır.
    const activitiesAvailable = Boolean(
        window.ShiftScanActivities && activityListEl && activityTemplate && addActivityBtn
    );
    let activityList = [];

    function activityNames() {
        const keys = ['content-production', 'sports', 'reading', 'social', 'gaming'];
        const names = {};
        keys.forEach((key) => { names[key] = window.i18n ? window.i18n.t(key) : key; });
        return names;
    }

    function persistActivities() {
        ShiftScanActivities.save(localStorage, activityList);
    }

    function renderActivities() {
        activityListEl.innerHTML = '';

        activityList.forEach((activity) => {
            const row = activityTemplate.content.cloneNode(true);
            const li = row.querySelector('.activity-row');

            const enabled = li.querySelector('.activity-enabled');
            const name = li.querySelector('.activity-name');
            const amount = li.querySelector('.activity-amount');
            const unit = li.querySelector('.activity-unit');
            const preferred = li.querySelector('.activity-preferred');

            enabled.checked = activity.enabled !== false;
            name.value = activity.name;
            amount.value = activity.amount;
            unit.value = activity.unit;
            preferred.value = activity.preferred || 'any';

            enabled.addEventListener('change', () => {
                activity.enabled = enabled.checked;
                persistActivities();
            });
            name.addEventListener('input', () => { activity.name = name.value; persistActivities(); });
            amount.addEventListener('input', () => {
                // Alan silinip yeniden yazılırken Number('') === 0 kaydedilir,
                // reload'dan sonra da kalır ve sunucu 422 döner. Geçersiz
                // değeri kaydetmiyoruz ama satırı da kilitlemiyoruz.
                const parsed = ShiftScanActivities.parseAmount(amount.value);
                if (parsed === null) return;
                activity.amount = parsed;
                persistActivities();
            });
            unit.addEventListener('change', () => { activity.unit = unit.value; persistActivities(); });
            preferred.addEventListener('change', () => {
                activity.preferred = preferred.value;
                persistActivities();
            });
            li.querySelector('.activity-remove').addEventListener('click', () => {
                activityList = ShiftScanActivities.removeActivity(activityList, activity.id);
                persistActivities();
                renderActivities();
            });

            activityListEl.appendChild(row);
        });

        // Yeni klonlanan satırlar (aria-label, seçenek metinleri) mevcut dile
        // hemen senkronlansın; bir sonraki dil değişimini beklemesin.
        if (window.i18n) window.i18n.updateUI();

        if (addActivityBtn) {
            addActivityBtn.disabled = activityList.length >= MAX_ACTIVITIES;
        }
    }

    if (activitiesAvailable) {
        activityList = ShiftScanActivities.load(localStorage, activityNames());

        addActivityBtn.addEventListener('click', () => {
            if (activityList.length >= MAX_ACTIVITIES) {
                showAlert(window.i18n ? window.i18n.t('activityLimitReached') : 'You can add up to 20 activities.', 'warning');
                return;
            }
            activityList = ShiftScanActivities.addActivity(activityList, {
                // 'addActivity' butonun kendi etiketi ve başında '+' taşıyor;
                // ICS'e 'SUMMARY:+ Add Activity' düşmesin diye ayrı anahtar.
                name: window.i18n ? window.i18n.t('newActivityName') : 'New activity',
                amount: 1,
                unit: 'hours'
            });
            persistActivities();
            renderActivities();
        });

        renderActivities();
    } else {
        console.warn('ShiftScan: aktivite listesi yüklenemedi, gelişmiş mod devre dışı.');
    }

    // ============================================
    // GÖRSEL YÜKLEME & CROPPER
    // ============================================
    
    if (elements.ocrInput) {
        elements.ocrInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = (event) => {
                elements.imageToCrop.src = event.target.result;
                elements.cropperContainer.classList.remove('hidden');
                
                // Önceki cropper'ı yok et
                if (cropper) {
                    cropper.destroy();
                }

                // Yeni Cropper başlat
                cropper = new Cropper(elements.imageToCrop, {
                    viewMode: 1,
                    dragMode: 'move',
                    autoCropArea: 1,
                    restore: false,
                    guides: true,
                    center: true,
                    highlight: false,
                    cropBoxMovable: true,
                    cropBoxResizable: true,
                    toggleDragModeOnDblclick: false,
                });
            };
            reader.readAsDataURL(file);
        });
    }

    // ============================================
    // OCR TARAMA (Nanonets-OCR2-3B + Tesseract Fallback)
    // ============================================

    // Nanonets OCR API call
    async function performNanonetsOCR(imageBase64) {
        try {
            const response = await fetch('/ocr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_base64: imageBase64 })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const result = await response.json();
            return {
                success: true,
                text: result.text,
                model: result.model || 'Nanonets-OCR2-3B'
            };
        } catch (error) {
            console.error('Nanonets OCR error:', error);
            return {
                success: false,
                text: '',
                error: error.message
            };
        }
    }

    // Tesseract.js fallback OCR
    async function performTesseractOCR(blob) {
        return new Promise(async (resolve, reject) => {
            try {
                const worker = await Tesseract.createWorker('eng', 1, {
                    logger: m => {
                        if (m.status === 'recognizing text') {
                            const p = Math.round(m.progress * 100);
                            elements.ocrProgressBar.style.width = `${p}%`;
                            elements.ocrPercent.innerText = `${p}%`;
                            elements.ocrStatusText.innerText = `Tesseract: %${p}`;
                        }
                    }
                });

                const ret = await worker.recognize(blob);
                await worker.terminate();

                resolve({
                    success: true,
                    text: ret.data.text,
                    confidence: ret.data.confidence,
                    model: 'Tesseract.js'
                });
            } catch (error) {
                reject(error);
            }
        });
    }

    if (elements.scanCropBtn) {
        elements.scanCropBtn.addEventListener('click', async () => {
            if (!cropper) {
                showAlert('Önce bir görsel yükleyin!', 'warning');
                return;
            }

            try {
                const canvas = cropper.getCroppedCanvas({
                    maxWidth: 2000,
                    maxHeight: 2000,
                    fillColor: '#fff'
                });

                if (!canvas) {
                    showAlert('Görsel işlenemedi!', 'error');
                    return;
                }

                // Progress göster
                elements.ocrProgressContainer.classList.remove('hidden');
                elements.ocrProgressBar.style.width = '0%';
                elements.ocrPercent.innerText = '0%';
                elements.ocrStatusText.innerText = 'Nanonets AI OCR...';
                elements.shiftText.value = '';

                // Canvas'ı base64'e çevir
                const imageBase64 = canvas.toDataURL('image/png');

                // Önce Nanonets OCR dene
                console.log('Trying Nanonets-OCR2-3B...');
                elements.ocrProgressBar.style.width = '20%';
                elements.ocrPercent.innerText = '20%';

                const nanonetsResult = await performNanonetsOCR(imageBase64);

                if (nanonetsResult.success && nanonetsResult.text.trim().length > 0) {
                    // Nanonets başarılı
                    console.log('Nanonets OCR Success:', nanonetsResult.text);
                    elements.ocrProgressBar.style.width = '100%';
                    elements.ocrPercent.innerText = '100%';
                    elements.ocrStatusText.innerText = 'Nanonets AI OCR tamamlandı!';

                    const parsedShift = parseLineToShifts(nanonetsResult.text);
                    elements.shiftText.value = parsedShift;

                    toast.success(window.i18n?.currentLang === 'en'
                        ? 'OCR completed with Nanonets AI!'
                        : 'Nanonets AI ile OCR tamamlandı!');

                    elements.shiftText.scrollIntoView({ behavior: 'smooth' });
                    return;
                }

                // Nanonets başarısız, Tesseract.js fallback
                console.log('Nanonets failed, falling back to Tesseract.js...');
                console.log('Nanonets error:', nanonetsResult.error);
                elements.ocrStatusText.innerText = 'Tesseract.js ile devam ediliyor...';
                elements.ocrProgressBar.style.width = '30%';

                // Canvas'ı blob'a çevir
                canvas.toBlob(async (blob) => {
                    if (!blob) {
                        showAlert('Görsel dönüştürülemedi!', 'error');
                        elements.ocrProgressContainer.classList.add('hidden');
                        return;
                    }

                    try {
                        const tesseractResult = await performTesseractOCR(blob);

                        if (!tesseractResult.text || tesseractResult.text.trim().length === 0) {
                            elements.shiftText.value = 'OCR hiçbir metin algılayamadı. Lütfen:\n- Görselin daha net olduğundan emin olun\n- Sadece vardiya saatlerini içeren alanı seçin\n- Manuel olarak girin';
                            showAlert('Metin algılanamadı!', 'warning');
                        } else {
                            const parsedShift = parseLineToShifts(tesseractResult.text);
                            elements.shiftText.value = parsedShift;

                            if (tesseractResult.confidence < 60) {
                                toast.warning(window.i18n?.currentLang === 'en'
                                    ? 'Low confidence - please check and edit'
                                    : 'Düşük güven - lütfen kontrol edip düzenleyin');
                            } else {
                                toast.info(window.i18n?.currentLang === 'en'
                                    ? 'OCR completed with Tesseract (fallback)'
                                    : 'Tesseract ile OCR tamamlandı (yedek)');
                            }
                        }

                        elements.ocrStatusText.innerText = window.i18n?.t('completed') || 'Tamamlandı!';
                        elements.ocrProgressBar.style.width = '100%';
                        elements.ocrPercent.innerText = '100%';

                        elements.shiftText.scrollIntoView({ behavior: 'smooth' });

                    } catch (tesseractError) {
                        console.error('Tesseract error:', tesseractError);
                        showAlert('OCR işlemi başarısız oldu. Manuel giriş yapın.', 'error');
                        elements.ocrProgressContainer.classList.add('hidden');
                    }
                }, 'image/png');

            } catch (err) {
                console.error("OCR Hatası:", err);
                showAlert(window.i18n?.t('scanError') || "Tarama sırasında bir hata oluştu.", 'error');
                elements.ocrProgressContainer.classList.add('hidden');
            }
        });
    }

    // ============================================
    // METİN PARSE FONKSİYONLARI
    // ============================================

    // HTML tablo formatını parse et (Nanonets bazen tablo döndürüyor)
    function parseHTMLTable(htmlText) {
        const days = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];
        const results = [];

        // Tüm <td> ve <th> içeriklerini çıkar
        const cellRegex = /<t[dh][^>]*>([^<]*)<\/t[dh]>/gi;
        let match;
        const cellContents = [];

        while ((match = cellRegex.exec(htmlText)) !== null) {
            const content = match[1].trim();
            if (content) {
                cellContents.push(content);
            }
        }

        console.log('Tablo hücre içerikleri:', cellContents);

        // Saat aralığı ve OFF pattern'lerini bul
        const timeRangeRegex = /^(\d{1,2})[:\.]?(\d{2})[-–—](\d{1,2})[:\.]?(\d{2})$/;
        // YI=Yıllık İzin, HT=Hafta Tatili, RT=Resmi Tatil, Üİ/UI=Ücretsiz İzin
        const offRegex = /^(OFF|0FF|OEF|İZİN|IZIN|BOŞ|BOS|TATİL|TATIL|RAPOR|RAPORLU|LEAVE|FREE|HOLIDAY|FREI|CONGÉ|YI|Yİ|YL|YILLIK|HT|HAFTA\s*TATİLİ?|RT|RESMİ?\s*TATİL|Üİ|ÜI|UI|ÜCRETSİZ)$/i;

        for (const content of cellContents) {
            // Saat aralığı mı?
            const timeMatch = content.match(timeRangeRegex);
            if (timeMatch) {
                const h1 = timeMatch[1].padStart(2, '0');
                const m1 = timeMatch[2];
                const h2 = timeMatch[3].padStart(2, '0');
                const m2 = timeMatch[4];
                results.push(`${h1}:${m1} - ${h2}:${m2}`);
                continue;
            }

            // OFF/İZİN mi?
            if (offRegex.test(content)) {
                results.push('OFF');
                continue;
            }
        }

        console.log('Tablo parse sonucu:', results);

        if (results.length === 0) {
            return `Vardiya formatı algılanamadı. Ham veri:\n\n${htmlText}`;
        }

        // Günleri oluştur
        let result = '';
        const count = Math.min(results.length, 7);
        for (let i = 0; i < count; i++) {
            result += `${days[i]} ${results[i]}\n`;
        }

        if (count < 7) {
            result += `\n--- ${7 - count} gün eksik, lütfen tamamlayın ---`;
        }

        return result.trim();
    }

    function parseLineToShifts(ocrText) {
        console.log('OCR Ham Metin:', ocrText);

        // HTML tablo formatını kontrol et ve parse et
        if (ocrText.includes('<table') || ocrText.includes('<td>') || ocrText.includes('<th>')) {
            console.log('HTML tablo formatı algılandı, parse ediliyor...');
            return parseHTMLTable(ocrText);
        }

        // Metni temizle ve normalleştir
        let text = ocrText
            .replace(/\r\n/g, ' ')
            .replace(/\r/g, ' ')
            .replace(/\n/g, ' ')
            .trim();
        
        // OCR metin tokenlarını oluştur (boşlukla ayır)
        const tokens = text.split(/\s+/).filter(t => t.length > 0);
        console.log('Tokenlar:', tokens);
        
        // Her token'ı analiz et ve saat aralığı mı OFF mi bul
        const results = [];
        
        // Saat aralığı regex (09:00-18:00, 09.00-18.00, vb.)
        const timeRangeRegex = /^(\d{1,2})[:\.]?(\d{2})[-–—](\d{1,2})[:\.]?(\d{2})$/;
        
        // YI=Yıllık İzin, HT=Hafta Tatili, RT=Resmi Tatil, Üİ/UI=Ücretsiz İzin
        const offRegex = /^(OFF|0FF|OEF|İZİN|IZIN|IZİN|İZIN|BOŞ|BOS|B0Ş|TATIL|TATİL|RAPOR|RAP0R|RAPORLU|LEAVE|FREE|HOLIDAY|FREI|CONGÉ|CONGE|YI|Yİ|Yl|YL|YILLIK|HT|RT|Üİ|ÜI|UI|ÜCRETSİZ)$/i;
        
        for (let i = 0; i < tokens.length; i++) {
            const token = tokens[i];
            
            // Saat aralığı mı? (09:00-18:00, 09.00-18.00, vb.)
            const timeMatch = token.match(timeRangeRegex);
            if (timeMatch) {
                const h1 = timeMatch[1].padStart(2, '0');
                const m1 = timeMatch[2];
                const h2 = timeMatch[3].padStart(2, '0');
                const m2 = timeMatch[4];
                results.push(`${h1}:${m1} - ${h2}:${m2}`);
                continue;
            }
            
            // Tire eksik format: HH:MMHH:MM veya H:MMHH:MM (örn: 11:0020:00, 0:0018:00)
            const noHyphenMatch = token.match(/^(\d{1,2}):(\d{2})(\d{1,2}):(\d{2})$/);
            if (noHyphenMatch) {
                const h1 = noHyphenMatch[1].padStart(2, '0');
                const m1 = noHyphenMatch[2];
                const h2 = noHyphenMatch[3].padStart(2, '0');
                const m2 = noHyphenMatch[4];
                results.push(`${h1}:${m1} - ${h2}:${m2}`);
                continue;
            }
            
            // OFF/İZİN mi?
            if (offRegex.test(token)) {
                results.push('OFF');
                continue;
            }
            
            // Birleşik 4+4 haneli sayı mı? (örn: 09001800)
            const combined8 = token.match(/^(\d{4})(\d{4})$/);
            if (combined8) {
                const start = combined8[1];
                const end = combined8[2];
                results.push(`${start.slice(0,2)}:${start.slice(2)} - ${end.slice(0,2)}:${end.slice(2)}`);
                continue;
            }
            
            // 4 haneli tek başına mı ve sonraki de 4 haneli mi? (örn: 0900 1800)
            const single4 = token.match(/^(\d{4})$/);
            if (single4 && i + 1 < tokens.length) {
                const next4 = tokens[i + 1].match(/^(\d{4})$/);
                if (next4) {
                    const start = single4[1];
                    const end = next4[1];
                    results.push(`${start.slice(0,2)}:${start.slice(2)} - ${end.slice(0,2)}:${end.slice(2)}`);
                    i++; // Sonraki token'ı da tükettik
                    continue;
                }
            }
        }
        
        console.log('Bulunan vardiyalar (sıralı):', results);
        
        if (results.length === 0) {
            // Hiçbir şey bulunamadı, ham metni döndür
            return `Vardiya formatı algılanamadı. Lütfen manuel düzenleyin:\n\n${ocrText}`;
        }
        
        // Günleri oluştur
        const days = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];
        let result = '';
        
        // İlk 7 sonucu günlere ata
        const count = Math.min(results.length, 7);
        for (let i = 0; i < count; i++) {
            result += `${days[i]} ${results[i]}\n`;
        }
        
        // Eğer 7 günden az varsa, uyar
        if (count < 7) {
            result += `\n--- ${7 - count} gün eksik, lütfen tamamlayın ---`;
        }
        
        return result.trim();
    }

    function parseText(text, baseDate) {
        const lines = text.split('\n');
        const events = [];
        
        const dayRegex = /(Pzt|Pazartesi|Sal|Salı|Sali|Çar|Çarşamba|Carsamba|Per|Perşembe|Persembe|Cum|Cuma|Cmt|Cumartesi|Paz|Pazar|Mon|Tue|Wed|Thu|Fri|Sat|Sun)/i;
        const timeRegex = /(\d{1,2})[:.]?(\d{2})?\s*-\s*(\d{1,2})[:.]?(\d{2})?/;

        lines.forEach(line => {
            const lowerLine = line.toLowerCase();
            const dayMatch = line.match(dayRegex);
            const timeMatch = line.match(timeRegex);

            if (dayMatch) {
                const dayName = dayMatch[0].toLowerCase();
                let dayIndex = -1;
                
                for (const [key, val] of Object.entries(dayMap)) {
                    if (dayName.startsWith(key)) {
                        dayIndex = val;
                        break;
                    }
                }

                if (dayIndex !== -1) {
                    const eventDate = new Date(baseDate);
                    eventDate.setDate(baseDate.getDate() + dayIndex);
                    
                    const isOff = ignoreKeywords.some(kw => lowerLine.includes(kw.toLowerCase()));

                    if (!isOff && timeMatch) {
                        let startH = parseInt(timeMatch[1]);
                        let startM = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
                        let endH = parseInt(timeMatch[3]);
                        let endM = timeMatch[4] ? parseInt(timeMatch[4]) : 0;

                        let endDate = new Date(eventDate);
                        if (endH < startH || (endH === startH && endM < startM)) {
                            endDate.setDate(endDate.getDate() + 1);
                        }

                        const startDateTime = new Date(eventDate);
                        startDateTime.setHours(startH, startM, 0, 0);
                        
                        const endDateTime = new Date(endDate);
                        endDateTime.setHours(endH, endM, 0, 0);

                        events.push({
                            title: 'Vardiya',
                            start: startDateTime,
                            end: endDateTime,
                            originalLine: line.trim()
                        });
                    }
                }
            }
        });
        
        return events;
    }

    // ============================================
    // ÖNİZLEME
    // ============================================
    
    function renderPreview(events) {
        elements.previewList.innerHTML = '';

        if (events.length === 0) {
            const noShiftMsg = window.i18n?.t('noShiftDetected') || 'Hiçbir vardiya algılanamadı. Formatı kontrol edin.';
            elements.previewList.innerHTML = `<li class="preview-item" style="color: var(--error);">${noShiftMsg}</li>`;
        } else {
            events.forEach(ev => {
                const li = document.createElement('li');
                li.className = 'preview-item';
                
                const dateStr = ev.start.toLocaleDateString(window.i18n?.currentLang === 'en' ? 'en-US' : 'tr-TR', { 
                    weekday: 'short', 
                    day: 'numeric', 
                    month: 'short' 
                });
                const timeStr = `${formatTime(ev.start)} - ${formatTime(ev.end)}`;
                
                li.innerHTML = `
                    <span class="preview-day">${dateStr}</span>
                    <span class="preview-time">${timeStr}</span>
                `;
                elements.previewList.appendChild(li);
            });
        }
        
        elements.previewSection.classList.remove('hidden');
        elements.previewSection.scrollIntoView({ behavior: 'smooth' });
    }

    // ============================================
    // ICS OLUŞTURMA & İNDİRME
    // ============================================
    
    function generateICS(events) {
        return window.ShiftScanICS.buildICS(events);
    }

    function downloadICS(events, filename = 'vardiya_programi.ics') {
        const icsContent = generateICS(events);
        const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    function downloadICSFromContent(icsContent, filename) {
        const cleanContent = icsContent.replace(/```ics\n?/g, '').replace(/```\n?/g, '').trim();
        const blob = new Blob([cleanContent], { type: 'text/calendar;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    // ============================================
    // ANA BUTON OLAYLARI
    // ============================================
    
    // Önizle Butonu
    if (elements.convertBtn) {
        elements.convertBtn.addEventListener('click', () => {
            try {
                const startDateVal = elements.startDateInput.value;
                const text = elements.shiftText.value;
                
                if (!startDateVal) {
                    showAlert(window.i18n?.t('selectStartDate') || 'Lütfen bir başlangıç tarihi seçin!', 'warning');
                    return;
                }
                if (!text.trim()) {
                    showAlert(window.i18n?.t('enterShiftText') || 'Lütfen vardiya metnini girin veya görsel yükleyin!', 'warning');
                    return;
                }

                const [y, m, d] = startDateVal.split('-').map(Number);
                const baseDate = new Date(y, m - 1, d); 

                parsedEvents = parseText(text, baseDate);
                renderPreview(parsedEvents);
            } catch (err) {
                console.error("Dönüştürme hatası:", err);
                showAlert(window.i18n?.t('convertError') || "Dönüştürme sırasında bir hata oluştu. Lütfen formatı kontrol edin.", 'error');
            }
        });
    }

    // İndir Butonu
    if (elements.downloadBtn) {
        elements.downloadBtn.addEventListener('click', () => {
            if (parsedEvents.length === 0) {
                showAlert(window.i18n?.t('previewFirst') || 'Önce vardiyaları önizleyin!', 'warning');
                return;
            }
            
            // Haftalık tekrar sayısını al
            const repeatWeeks = elements.repeatWeeks ? parseInt(elements.repeatWeeks.value) || 1 : 1;
            
            // Tekrar uygula
            let allEvents = [];
            for (let week = 0; week < repeatWeeks; week++) {
                parsedEvents.forEach(ev => {
                    const newEvent = {
                        title: ev.title,
                        start: new Date(ev.start.getTime() + (week * 7 * 24 * 60 * 60 * 1000)),
                        end: new Date(ev.end.getTime() + (week * 7 * 24 * 60 * 60 * 1000)),
                        originalLine: ev.originalLine
                    };
                    allEvents.push(newEvent);
                });
            }
            
            // Dijital Acentelik etkinlikleri ekle (checkbox işaretliyse)
            if (elements.dijitalAcentelik && elements.dijitalAcentelik.checked) {
                // Seçili günleri al (0=Pzt, 1=Sal, ... 6=Paz)
                const selectedDays = [];
                document.querySelectorAll('.dijital-day:checked').forEach(cb => {
                    selectedDays.push(parseInt(cb.dataset.day));
                });
                
                console.log('Dijital Acentelik seçili günler:', selectedDays);
                
                // En az bir gün seçilmediyse uyar
                if (selectedDays.length === 0) {
                    showAlert('Dijital Acentelik için en az bir gün seçin!', 'warning');
                    return;
                }
                
                const acentelikEvents = [];
                allEvents.forEach(ev => {
                    // OFF günlerini atla (title içinde OFF var mı kontrolü)
                    if (ev.title && ev.title.toUpperCase().includes('OFF')) return;
                    
                    // Haftanın günü (0=Pazar, 1=Pazartesi... JavaScript'te)
                    // Bizim sistemimiz: 0=Pzt, 1=Sal... 6=Paz
                    // JavaScript getDay(): 0=Paz, 1=Pzt, 2=Sal... 6=Cmt
                    // Dönüşüm: (getDay() + 6) % 7 = bizim sistemimiz
                    const jsDay = ev.start.getDay();
                    const ourDay = (jsDay + 6) % 7; // 0=Pzt, 1=Sal... 6=Paz
                    
                    // Bu gün seçili değilse atla
                    if (!selectedDays.includes(ourDay)) return;
                    
                    // Bitiş saatinden 1 saat önce başla
                    const acentelikStart = new Date(ev.end.getTime() - (1 * 60 * 60 * 1000)); // 1 saat önce
                    const acentelikEnd = new Date(ev.end.getTime()); // Vardiya bitimiyle aynı
                    
                    acentelikEvents.push({
                        title: '📞 Dijital Acentelik',
                        start: acentelikStart,
                        end: acentelikEnd,
                        originalLine: 'Dijital Acentelik görevi'
                    });
                });
                
                console.log('Oluşturulan Dijital Acentelik etkinlikleri:', acentelikEvents.length);
                
                // Acentelik etkinliklerini ekle
                allEvents = allEvents.concat(acentelikEvents);
            }
            
            downloadICS(allEvents);
            
            // Bildirim
            const dijitalMsg = elements.dijitalAcentelik?.checked ? ' + Dijital Acentelik' : '';
            if (repeatWeeks > 1) {
                const msg = window.i18n?.currentLang === 'en' 
                    ? `ICS file downloaded with ${repeatWeeks} weeks${dijitalMsg}!`
                    : `${repeatWeeks} haftalık ICS dosyası indirildi${dijitalMsg}!`;
                toast.success(msg);
            } else {
                const msg = window.i18n?.currentLang === 'en' 
                    ? `ICS file downloaded${dijitalMsg}!` 
                    : `ICS dosyası indirildi${dijitalMsg}!`;
                toast.success(msg);
            }
        });
    }

    // PDF İndir Butonu
    if (elements.downloadPDFBtn) {
        elements.downloadPDFBtn.addEventListener('click', async () => {
            if (parsedEvents.length === 0) {
                showAlert(window.i18n?.t('previewFirst') || 'Önce vardiyaları önizleyin!', 'warning');
                return;
            }
            
            try {
                // Haftalık tekrar uygula
                const repeatWeeks = elements.repeatWeeks ? parseInt(elements.repeatWeeks.value) || 1 : 1;
                let allEvents = [];
                for (let week = 0; week < repeatWeeks; week++) {
                    parsedEvents.forEach(ev => {
                        allEvents.push({
                            title: ev.title,
                            start: new Date(ev.start.getTime() + (week * 7 * 24 * 60 * 60 * 1000)),
                            end: new Date(ev.end.getTime() + (week * 7 * 24 * 60 * 60 * 1000)),
                            originalLine: ev.originalLine
                        });
                    });
                }
                
                showLoading(window.i18n?.currentLang === 'en' ? 'Creating PDF...' : 'PDF oluşturuluyor...');
                await window.exportModule.exportToPDF(allEvents);
                hideLoading();
                toast.success(window.i18n?.currentLang === 'en' ? 'PDF downloaded!' : 'PDF indirildi!');
            } catch (error) {
                hideLoading();
                console.error('PDF export error:', error);
                toast.error(window.i18n?.currentLang === 'en' ? 'PDF export failed' : 'PDF oluşturulamadı');
            }
        });
    }

    // Excel İndir Butonu
    if (elements.downloadExcelBtn) {
        elements.downloadExcelBtn.addEventListener('click', async () => {
            if (parsedEvents.length === 0) {
                showAlert(window.i18n?.t('previewFirst') || 'Önce vardiyaları önizleyin!', 'warning');
                return;
            }
            
            try {
                // Haftalık tekrar uygula
                const repeatWeeks = elements.repeatWeeks ? parseInt(elements.repeatWeeks.value) || 1 : 1;
                let allEvents = [];
                for (let week = 0; week < repeatWeeks; week++) {
                    parsedEvents.forEach(ev => {
                        allEvents.push({
                            title: ev.title,
                            start: new Date(ev.start.getTime() + (week * 7 * 24 * 60 * 60 * 1000)),
                            end: new Date(ev.end.getTime() + (week * 7 * 24 * 60 * 60 * 1000)),
                            originalLine: ev.originalLine
                        });
                    });
                }
                
                showLoading(window.i18n?.currentLang === 'en' ? 'Creating Excel...' : 'Excel oluşturuluyor...');
                await window.exportModule.exportToExcel(allEvents);
                hideLoading();
                toast.success(window.i18n?.currentLang === 'en' ? 'Excel downloaded!' : 'Excel indirildi!');
            } catch (error) {
                hideLoading();
                console.error('Excel export error:', error);
                toast.error(window.i18n?.currentLang === 'en' ? 'Excel export failed' : 'Excel oluşturulamadı');
            }
        });
    }

    // QR Kod Paylaşım
    let qrCodeLib = null;
    let currentShareUrl = '';

    async function loadQRCodeLib() {
        if (qrCodeLib) return true;
        
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js';
            script.onload = () => {
                qrCodeLib = window.QRCode;
                resolve(true);
            };
            script.onerror = () => reject(new Error('QRCode library yüklenemedi'));
            document.head.appendChild(script);
        });
    }

    function encodeShiftData(startDate, shiftText) {
        // Vardiya verisini URL-safe encode et
        const data = {
            s: startDate, // start date
            t: shiftText  // shift text
        };
        return btoa(encodeURIComponent(JSON.stringify(data)));
    }

    function generateShareUrl(startDate, shiftText) {
        const encoded = encodeShiftData(startDate, shiftText);
        const baseUrl = window.location.origin + window.location.pathname;
        return `${baseUrl}?share=${encoded}`;
    }

    if (elements.shareQRBtn) {
        elements.shareQRBtn.addEventListener('click', async () => {
            const startDateVal = elements.startDateInput.value;
            const shiftTextVal = elements.shiftText.value;
            
            if (!startDateVal || !shiftTextVal.trim()) {
                showAlert(window.i18n?.t('enterShiftText') || 'Lütfen vardiya verisi girin!', 'warning');
                return;
            }
            
            try {
                await loadQRCodeLib();
                
                // Paylaşım URL'i oluştur
                currentShareUrl = generateShareUrl(startDateVal, shiftTextVal);
                
                // QR konteynerini temizle
                elements.qrCodeContainer.innerHTML = '';
                
                // QR kod oluştur (canvas olarak)
                const canvas = document.createElement('canvas');
                await QRCode.toCanvas(canvas, currentShareUrl, {
                    width: 200,
                    margin: 2,
                    color: {
                        dark: '#1e293b',
                        light: '#ffffff'
                    }
                });
                
                elements.qrCodeContainer.appendChild(canvas);
                
                // Modal'ı göster
                elements.qrModal.classList.remove('hidden');
                
            } catch (error) {
                console.error('QR kod oluşturma hatası:', error);
                toast.error(window.i18n?.currentLang === 'en' ? 'QR code generation failed' : 'QR kod oluşturulamadı');
            }
        });
    }

    // Modal kapatma
    if (elements.closeQRModal) {
        elements.closeQRModal.addEventListener('click', () => {
            elements.qrModal.classList.add('hidden');
        });
    }

    // Modal dışına tıklayınca kapat
    if (elements.qrModal) {
        elements.qrModal.addEventListener('click', (e) => {
            if (e.target === elements.qrModal) {
                elements.qrModal.classList.add('hidden');
            }
        });
    }

    // Link kopyalama
    if (elements.copyLinkBtn) {
        elements.copyLinkBtn.addEventListener('click', async () => {
            if (currentShareUrl) {
                try {
                    await navigator.clipboard.writeText(currentShareUrl);
                    toast.success(window.i18n?.currentLang === 'en' ? 'Link copied!' : 'Link kopyalandı!');
                } catch (error) {
                    // Fallback for older browsers
                    const textArea = document.createElement('textarea');
                    textArea.value = currentShareUrl;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    toast.success(window.i18n?.currentLang === 'en' ? 'Link copied!' : 'Link kopyalandı!');
                }
            }
        });
    }

    // URL'den paylaşılan veriyi yükle
    function loadSharedData() {
        const urlParams = new URLSearchParams(window.location.search);
        const shareData = urlParams.get('share');
        
        if (shareData) {
            try {
                const decoded = JSON.parse(decodeURIComponent(atob(shareData)));
                
                if (decoded.s && decoded.t) {
                    elements.startDateInput.value = decoded.s;
                    elements.shiftText.value = decoded.t;
                    
                    toast.info(window.i18n?.currentLang === 'en' ? 'Shared schedule loaded!' : 'Paylaşılan program yüklendi!');
                    
                    // URL'i temizle
                    window.history.replaceState({}, document.title, window.location.pathname);
                }
            } catch (error) {
                console.error('Paylaşım verisi çözümlenemedi:', error);
            }
        }
    }

    // AI ile Plan Oluştur (Gelişmiş Mod)
    if (elements.generatePlanBtn) {
        elements.generatePlanBtn.addEventListener('click', async () => {
            try {
                const startDateVal = elements.startDateInput.value;
                const shiftTextVal = elements.shiftText.value;
                
                if (!startDateVal) {
                    showAlert(window.i18n?.t('selectStartDate') || 'Lütfen bir başlangıç tarihi seçin!', 'warning');
                    return;
                }
                if (!shiftTextVal.trim()) {
                    showAlert(window.i18n?.t('enterShiftText') || 'Lütfen vardiya metnini girin!', 'warning');
                    return;
                }

                // Aktivite listesini payload'a çevir (kapatılmış/silinmiş satırlar hariç)
                const activityPayload = activitiesAvailable
                    ? ShiftScanActivities.toPayload(activityList)
                    : [];

                if (activityPayload.length === 0) {
                    showAlert(window.i18n?.t('selectActivity') || 'Lütfen en az bir aktivite seçin ve süre/gün belirtin!', 'warning');
                    return;
                }

                // Vardiya verilerini parse et
                const [y, m, d] = startDateVal.split('-').map(Number);
                const baseDate = new Date(y, m - 1, d);
                const shiftEvents = parseText(shiftTextVal, baseDate);

                // Backend'e gönderilecek veri
                const planData = {
                    start_date: startDateVal,
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    shift_events: shiftEvents.map((ev) => ({
                        start: ev.start.toISOString(),
                        end: ev.end.toISOString()
                    })),
                    activities: activityPayload,
                    labels: {
                        shift: window.i18n ? window.i18n.t('icsShift') : 'Shift',
                        sleep: window.i18n ? window.i18n.t('icsSleep') : 'Sleep'
                    }
                };

                console.log('Plan verileri:', planData);

                // Loading göster
                showLoading(window.i18n?.t('aiPlanCreating') || 'AI plan oluşturuyor...');

                // Backend'e POST isteği
                const response = await fetch('/generate-plan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(planData)
                });

                if (!response.ok) {
                    // Ham durum kodu tek başına çıkmaz yol: 422 hangi alanın
                    // reddedildiğini, 400 hangi saat diliminin tanınmadığını
                    // yalnızca gövdedeki `detail` söylüyor (bkz. /ocr).
                    // FastAPI doğrulama hatalarında `detail` bir liste gelir;
                    // düz string'e zorlanırsa "[object Object]" görünür.
                    const errorData = await response.json().catch(() => ({}));
                    const detail = errorData.detail;
                    const message = Array.isArray(detail)
                        ? detail.map((d) => d && d.msg).filter(Boolean).join('; ')
                        : detail;
                    throw new Error(message || `HTTP ${response.status}`);
                }

                const result = await response.json();
                console.log('Backend yanıtı:', result);
                
                hideLoading();
                
                if (result.status === 'success' && result.ics_content) {
                    downloadICSFromContent(result.ics_content, 'akilli_haftalik_plan.ics');
                    showAlert(window.i18n?.t('planCreated') || 'Akıllı haftalık plan başarıyla oluşturuldu!', 'success');
                } else {
                    showAlert(window.i18n?.t('planDownloadError') || 'Plan oluşturuldu ancak indirilemedi.', 'warning');
                }

            } catch (error) {
                console.error('Plan oluşturma hatası:', error);
                hideLoading();
                showAlert('Plan oluşturulurken bir hata oluştu: ' + error.message, 'error');
            }
        });
    }

    // ============================================
    // VARSAYİLAN TARİH AYARI
    // ============================================
    
    // Bugünün Pazartesi'sini bul ve varsayılan olarak ayarla
    const today = new Date();
    const dayOfWeek = today.getDay();
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek; // Pazar ise önceki pazartesi, değilse bu haftanın pazartesisi
    const monday = new Date(today);
    monday.setDate(today.getDate() + diff);
    
    if (elements.startDateInput) {
        elements.startDateInput.valueAsDate = monday;
    }

    // ============================================
    // TEMA YÖNETİMİ (DARK MODE)
    // ============================================
    
    const themeManager = {
        init() {
            // Kaydedilmiş temayı yükle veya sistem tercihini kullan
            const savedTheme = localStorage.getItem('vardiya-theme');
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            if (savedTheme) {
                this.setTheme(savedTheme);
            } else if (systemPrefersDark) {
                this.setTheme('dark');
            } else {
                this.setTheme('light');
            }
            
            // Sistem tema değişikliğini dinle
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem('vardiya-theme')) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
            
            // Toggle butonuna event listener ekle
            if (elements.themeToggle) {
                elements.themeToggle.addEventListener('click', () => this.toggle());
            }
        },
        
        setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('vardiya-theme', theme);
            
            // PWA manifest renk güncelleme
            const metaThemeColor = document.querySelector('meta[name="theme-color"]');
            if (metaThemeColor) {
                metaThemeColor.setAttribute('content', theme === 'dark' ? '#0f172a' : '#3b82f6');
            }
        },
        
        toggle() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            this.setTheme(newTheme);
            
            const message = window.i18n?.currentLang === 'en' 
                ? (newTheme === 'dark' ? 'Dark mode enabled' : 'Light mode enabled')
                : (newTheme === 'dark' ? 'Karanlık mod aktif' : 'Aydınlık mod aktif');
            toast.info(message);
        },
        
        getCurrentTheme() {
            return document.documentElement.getAttribute('data-theme') || 'light';
        }
    };

    // ============================================
    // BAŞLATMA
    // ============================================
    
    // Toast sistemini başlat
    toast.init();
    
    // Tema sistemini başlat
    themeManager.init();
    
    // Şablonları render et
    renderTemplates();
    
    // URL'den paylaşılan veriyi kontrol et
    loadSharedData();

    console.log('Vardiya Takvimi yüklendi.');
});
