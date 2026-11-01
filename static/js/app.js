/**
 * Vardiya Takvimi - Ana JavaScript
 * Modern, sade ve kullanıcı dostu vardiya planlayıcı
 */

document.addEventListener('DOMContentLoaded', () => {
    // ============================================
    // KONFİGÜRASYON
    // ============================================
    
    // Ceviri kisayolu: i18n yoksa Ingilizce yedek metin
    function tr(key, fallback, params) {
        return window.i18n ? window.i18n.t(key, params) : fallback;
    }

    const ADVANCED_MODE_KEY = 'shiftscan-advanced-mode';

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
    let scanController = null;
    let localWorker = null;
    let planController = null;

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
        
        // Vardiya sonu hatırlatması
        shiftReminder: document.getElementById('shiftReminder')
    };

    window.addEventListener('shiftscan:logout',()=>{
        scanController?.abort();planController?.abort();elements.shiftText.value='';parsedEvents=[];elements.previewSection.classList.add('hidden');
    });
    [elements.shiftText, elements.startDateInput].forEach(input=>input.addEventListener('input',()=>{
        parsedEvents=[];elements.previewSection.classList.add('hidden');
    }));

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
                <span class="toast-message"></span>
                <button class="toast-close" aria-label="${window.i18n ? window.i18n.t('close') : 'Close'}">&times;</button>
            `;
            
            toastEl.querySelector('.toast-message').textContent = String(message);

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
    window.toast = toast; // inceleme panelinin (schedule-review.js) bildirimleri için

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
        elements.languageSelect.value = window.i18n ? window.i18n.currentLang : 'en';
        
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
                window.i18n.setLanguage(window.i18n.currentLang);
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
    
    function applyAdvancedMode(on) {
        isAdvancedMode = on;
        elements.advancedModeToggle.checked = on;
        elements.advancedSection.classList.toggle('hidden', !on);
        elements.generatePlanBtn.classList.toggle('hidden', !on);
        document.getElementById('planConnectionSettings').classList.toggle('hidden', !on);
    }

    if (elements.advancedModeToggle) {
        // Varsayilan kapali; bir kez acan kullanici icin tercih hatirlanir.
        let remembered = false;
        try { remembered = localStorage.getItem(ADVANCED_MODE_KEY) === '1'; } catch (e) { /* yok say */ }
        applyAdvancedMode(remembered);

        elements.advancedModeToggle.addEventListener('change', () => {
            applyAdvancedMode(elements.advancedModeToggle.checked);
            try { localStorage.setItem(ADVANCED_MODE_KEY, isAdvancedMode ? '1' : '0'); } catch (e) { /* yok say */ }
        });
    }

    // Vardiya sonu hatırlatması checkbox - gün seçicileri göster/gizle
    if (elements.shiftReminder) {
        const reminderDaysContainer = document.getElementById('reminderDaysContainer');
        elements.shiftReminder.addEventListener('change', () => {
            if (reminderDaysContainer) {
                if (elements.shiftReminder.checked) {
                    reminderDaysContainer.classList.remove('hidden');
                } else {
                    reminderDaysContainer.classList.add('hidden');
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
        if (window.i18n) window.i18n.updateUI(activityListEl);

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
            if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 8000000) {
                showAlert('En fazla 8 MB PNG, JPEG veya WebP görseli yükleyin.', 'warning');
                e.target.value = ''; return;
            }
            if (scanController) scanController.abort();
            window.ShiftScanReview.reset();
            elements.shiftText.value = '';
            parsedEvents = [];
            elements.previewSection.classList.add('hidden');

            const reader = new FileReader();
            reader.onload = (event) => {
                elements.imageToCrop.src = event.target.result;
                elements.cropperContainer.classList.remove('hidden');
                
                // Önceki cropper'ı yok et
                if (cropper) {
                    cropper.destroy();
                }

                // Yeni Cropper başlat
                if (typeof Cropper === 'undefined') return;
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

    const ocrSelect = document.getElementById('ocrConnection');
    const fullButton = document.getElementById('scanFullBtn');
    const cancelButton = document.getElementById('cancelScanBtn');
    ocrSelect.addEventListener('change', () => {
        const connection = window.ShiftScanAccounts.getConnection(ocrSelect.value);
        document.getElementById('ocrPrivacy').textContent = connection
            ? `Görsel ${connection.label} (${connection.provider}) bağlantısına gönderilecek. Seçili model görsel desteklemeli; sağlayıcının API ücretleri geçerlidir.`
            : 'Görsel cihazında işlenir. Çok kişili tabloda kendi satırını kırpman daha iyi sonuç verir.';
    });
    function scanCanvas(cropped) {
        if (cropped && cropper) return cropper.getCroppedCanvas({maxWidth:4096,maxHeight:4096,fillColor:'#fff'});
        const img = elements.imageToCrop;
        if (!img.naturalWidth) throw new Error('Önce görsel yükleyin ve açılmasını bekleyin.');
        const scale = Math.min(1,4096/Math.max(img.naturalWidth,img.naturalHeight));
        const canvas = document.createElement('canvas');
        canvas.width=Math.round(img.naturalWidth*scale);canvas.height=Math.round(img.naturalHeight*scale);
        const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
        return canvas;
    }
    cancelButton.addEventListener('click',()=>{if(scanController)scanController.abort();});
    async function scan(cropped) {
        if(scanController)return;
        const controller=new AbortController();scanController=controller;
        const connectionId=ocrSelect.value;
        const owner=window.ShiftScanAccounts.getUser()?.id;
        let timer;
        try {
            if (!elements.startDateInput.value) throw new Error('Önce hafta başlangıcını seçin.');
            const canvas=scanCanvas(cropped);
            if(!canvas)throw new Error('Görsel hazırlanamadı.');
            fullButton.disabled=true;elements.scanCropBtn.disabled=true;cancelButton.hidden=false;
            elements.ocrProgressContainer.classList.remove('hidden');
            elements.ocrProgressBar.style.width='0%';elements.ocrPercent.textContent='';
            elements.ocrStatusText.textContent=connectionId?'Tablo okunuyor…':'Cihazda OCR hazırlanıyor…';
            parsedEvents=[];elements.previewSection.classList.add('hidden');
            window.ShiftScanReview.reset();
            timer=setTimeout(()=>controller.abort(),connectionId?60000:120000);
            if(connectionId){
                const result=await window.ShiftScanAccounts.api('/api/ocr/extract',{
                    method:'POST',signal:controller.signal,
                    body:JSON.stringify({connection_id:connectionId,start_date:elements.startDateInput.value,image_base64:canvas.toDataURL('image/jpeg',0.94)})
                });
                if(controller.signal.aborted)return;
                if(owner!==window.ShiftScanAccounts.getUser()?.id)throw new Error('Oturum değişti; tarama sonucu kullanılmadı.');
                window.ShiftScanReview.show(result);
            }else{
                if(typeof Tesseract==='undefined')throw new Error('Yerel OCR yüklenemedi. İnternet bağlantısını kontrol edin veya metni elle girin.');
                localWorker=await Tesseract.createWorker('tur+eng',1,{
                    logger:m=>{if(m.status==='recognizing text'&&!controller.signal.aborted){
                        const p=Math.round(m.progress*100);elements.ocrProgressBar.style.width=`${p}%`;elements.ocrPercent.textContent=`%${p}`;
                    }}
                });
                if(controller.signal.aborted)throw new DOMException('Aborted','AbortError');
                controller.signal.addEventListener('abort',()=>{localWorker?.terminate();},{once:true});
                const result=await localWorker.recognize(canvas);
                if(controller.signal.aborted)return;
                window.ShiftScanReview.show(window.ShiftScanReview.localSchedule(result.data.text,elements.startDateInput.value));
            }
            elements.ocrStatusText.textContent='Okuma tamamlandı; vardiyaları kontrol edin.';
            elements.ocrProgressBar.style.width='100%';elements.ocrPercent.textContent='';
        }catch(error){
            showAlert(controller.signal.aborted
                ? 'Tarama beklemesi sonlandırıldı. Başlamış bir bulut isteği sağlayıcıda ücretlenmiş olabilir.'
                : error.message,'warning');
        }finally{
            clearTimeout(timer);
            if(localWorker){await localWorker.terminate().catch(()=>{});localWorker=null;}
            scanController=null;fullButton.disabled=false;elements.scanCropBtn.disabled=false;cancelButton.hidden=true;
            elements.ocrProgressContainer.classList.add('hidden');
        }
    }
    fullButton.addEventListener('click',()=>scan(false));
    elements.scanCropBtn.addEventListener('click',()=>scan(true));

    // ============================================
    // METİN PARSE FONKSİYONLARI
    // ============================================

    // Backend'in yerlestiremedigi hedefleri tek satirlik uyariya cevirir;
    // bos liste veya eksik alan -> null (uyari yok).
    function formatUnplaced(unplaced) {
        if (!Array.isArray(unplaced) || unplaced.length === 0) {
            return null;
        }
        const t = (key, fallback) => (window.i18n ? window.i18n.t(key) : fallback);
        const list = unplaced.map((item) => {
            const unit = item.unit === 'days' ? t('unitDaysShort', 'd') : t('unitHoursShort', 'h');
            return `${item.name} (${item.amount} ${unit})`;
        }).join(', ');
        const template = t('planUnplaced', 'Not enough free time; could not place: {list}');
        return template.replace('{list}', list);
    }

    function parseText(text, baseDate) {
        if (text.includes('?')) throw new Error('Belirsiz günleri tamamlayın; izin günlerini OFF olarak belirtin.');
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

                        if (startH > 23 || endH > 23 || startM > 59 || endM > 59 || (startH === endH && startM === endM)) throw new Error('Vardiya saatlerini kontrol edin.');
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
        
        const ordered = [...events].sort((a,b)=>a.start-b.start);
        for(let i=1;i<ordered.length;i++){
            if(ordered[i].start<ordered[i-1].end)throw new Error('Vardiya saatleri çakışıyor.');
        }
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
                
                const dateStr = ev.start.toLocaleDateString(window.i18n ? window.i18n.locale() : 'en-US', { 
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
                if(window.ShiftScanReview.hasPending() || scanController) throw new Error('Önce görseldeki vardiyaların incelemesini tamamlayın.');
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
                showAlert(err.message || 'Vardiya bilgilerini kontrol edin.', 'error');
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
            
            // Vardiya sonu hatırlatması etkinlikleri ekle (checkbox işaretliyse)
            if (elements.advancedModeToggle?.checked && elements.shiftReminder?.checked) {
                // Seçili günleri al (0=Pzt, 1=Sal, ... 6=Paz)
                const selectedDays = [];
                document.querySelectorAll('.reminder-day:checked').forEach(cb => {
                    selectedDays.push(parseInt(cb.dataset.day));
                });
                
                const reminderTitle = document.getElementById('shiftReminderTitle').value.trim();
                if (!reminderTitle) {
                    showAlert('Hatırlatma için bir başlık yazın.', 'warning');
                    return;
                }
                
                // En az bir gün seçilmediyse uyar
                if (selectedDays.length === 0) {
                    showAlert('Vardiya sonu hatırlatması için en az bir gün seçin!', 'warning');
                    return;
                }
                
                const reminderEvents = [];
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
                    const reminderStart = new Date(Math.max(ev.start.getTime(), ev.end.getTime() - (1 * 60 * 60 * 1000))); // 1 saat önce
                    const reminderEnd = new Date(ev.end.getTime()); // Vardiya bitimiyle aynı
                    
                    reminderEvents.push({
                        title: reminderTitle,
                        start: reminderStart,
                        end: reminderEnd,
                        originalLine: ''
                    });
                });

                // Hatırlatma etkinliklerini ekle
                allEvents = allEvents.concat(reminderEvents);
            }
            
            downloadICS(allEvents);
            
            // Bildirim
            const reminderMsg = elements.advancedModeToggle?.checked && elements.shiftReminder?.checked ? ' + hatırlatma' : '';
            if (repeatWeeks > 1) {
                toast.success(tr('icsDownloadedWeeks', `ICS file downloaded with ${repeatWeeks} weeks${reminderMsg}!`, { weeks: repeatWeeks, extra: reminderMsg }));
            } else {
                toast.success(tr('icsDownloaded', `ICS file downloaded${reminderMsg}!`, { extra: reminderMsg }));
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
                
                showLoading(tr('pdfCreating', 'Creating PDF...'));
                await window.exportModule.exportToPDF(allEvents);
                hideLoading();
                toast.success(tr('pdfDownloaded', 'PDF downloaded!'));
            } catch (error) {
                hideLoading();
                console.error('PDF export error:', error);
                toast.error(tr('pdfFailed', 'PDF export failed'));
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
                
                showLoading(tr('excelCreating', 'Creating Excel...'));
                await window.exportModule.exportToExcel(allEvents);
                hideLoading();
                toast.success(tr('excelDownloaded', 'Excel downloaded!'));
            } catch (error) {
                hideLoading();
                console.error('Excel export error:', error);
                toast.error(tr('excelFailed', 'Excel export failed'));
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
                toast.error(tr('qrFailed', 'QR code generation failed'));
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
                    toast.success(tr('linkCopied', 'Link copied!'));
                } catch (error) {
                    // Fallback for older browsers
                    const textArea = document.createElement('textarea');
                    textArea.value = currentShareUrl;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    toast.success(tr('linkCopied', 'Link copied!'));
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
                    
                    toast.info(tr('sharedLoaded', 'Shared schedule loaded!'));
                    
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
            if(elements.generatePlanBtn.disabled)return;
            elements.generatePlanBtn.disabled=true;
            const planOwner=window.ShiftScanAccounts.getUser()?.id;
            planController=new AbortController();
            const planTimer=setTimeout(()=>planController?.abort(),60000);
            try {
                if(window.ShiftScanReview.hasPending() || scanController) throw new Error('Önce görseldeki vardiyaların incelemesini tamamlayın.');
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
                    connection_id: document.getElementById('planConnection').value || null,
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


                // Loading göster
                showLoading(window.i18n?.t('aiPlanCreating') || 'AI plan oluşturuyor...');

                // Backend'e POST isteği
                const result = await window.ShiftScanAccounts.api('/generate-plan', {
                    method: 'POST',
                    body: JSON.stringify(planData),
                    signal: planController.signal
                });
                if(planOwner!==window.ShiftScanAccounts.getUser()?.id)throw new Error('Oturum değişti; plan kullanılmadı.');
                if(result.fallback_reason)showAlert('Seçili sağlayıcı plan üretemedi. Ücretsiz kural tabanlı plan kullanıldı.','warning');

                hideLoading();
                
                if (result.status === 'success' && result.ics_content) {
                    downloadICSFromContent(result.ics_content, 'akilli_haftalik_plan.ics');
                    showAlert(window.i18n?.t('planCreated') || 'Akıllı haftalık plan başarıyla oluşturuldu!', 'success');
                    const unplacedMessage = formatUnplaced(result.unplaced);
                    if (unplacedMessage) {
                        showAlert(unplacedMessage, 'warning');
                    }
                } else {
                    showAlert(window.i18n?.t('planDownloadError') || 'Plan oluşturuldu ancak indirilemedi.', 'warning');
                }

            } catch (error) {
                console.error('Plan oluşturma hatası:', error);
                hideLoading();
                showAlert('Plan oluşturulurken bir hata oluştu: ' + error.message, 'error');
            } finally {
                clearTimeout(planTimer);planController=null;
                elements.generatePlanBtn.disabled=false;
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
            
            toast.info(tr(newTheme === 'dark' ? 'darkModeOn' : 'lightModeOn', newTheme === 'dark' ? 'Dark mode enabled' : 'Light mode enabled'));
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
