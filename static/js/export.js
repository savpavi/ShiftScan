/**
 * Vardiya Takvimi - Export Modülü
 * PDF ve Excel export desteği
 */

const exportModule = {
    // jsPDF ve SheetJS CDN'den yüklenecek (lazy loading)
    jsPDFLoaded: false,
    xlsxLoaded: false,

    // PDF export için jsPDF'i lazy load et
    async loadJsPDF() {
        if (this.jsPDFLoaded) return true;
        
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
            script.onload = () => {
                this.jsPDFLoaded = true;
                resolve(true);
            };
            script.onerror = () => reject(new Error('jsPDF yüklenemedi'));
            document.head.appendChild(script);
        });
    },

    // Excel export için SheetJS'i lazy load et
    async loadXLSX() {
        if (this.xlsxLoaded) return true;
        
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js';
            script.onload = () => {
                this.xlsxLoaded = true;
                resolve(true);
            };
            script.onerror = () => reject(new Error('SheetJS yüklenemedi'));
            document.head.appendChild(script);
        });
    },

    // PDF olarak export et
    async exportToPDF(events, options = {}) {
        try {
            await this.loadJsPDF();
            
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            
            const lang = window.i18n?.currentLang || 'tr';
            const title = lang === 'tr' ? 'Vardiya Programı' : 
                         lang === 'de' ? 'Schichtplan' :
                         lang === 'fr' ? 'Planning des Équipes' : 'Shift Schedule';
            
            // Başlık
            doc.setFontSize(20);
            doc.setTextColor(59, 130, 246); // Primary color
            doc.text(title, 105, 20, { align: 'center' });
            
            // Tarih aralığı
            if (events.length > 0) {
                const startDate = events[0].start;
                const endDate = events[events.length - 1].end;
                
                const dateRange = `${this.formatDate(startDate, lang)} - ${this.formatDate(endDate, lang)}`;
                doc.setFontSize(12);
                doc.setTextColor(100, 116, 139);
                doc.text(dateRange, 105, 30, { align: 'center' });
            }
            
            // Çizgi
            doc.setDrawColor(226, 232, 240);
            doc.line(20, 35, 190, 35);
            
            // Tablo başlıkları
            const headers = this.getHeaders(lang);
            let y = 45;
            
            doc.setFontSize(10);
            doc.setTextColor(30, 41, 59);
            doc.setFont(undefined, 'bold');
            
            doc.text(headers.day, 25, y);
            doc.text(headers.date, 60, y);
            doc.text(headers.time, 100, y);
            doc.text(headers.duration, 150, y);
            
            doc.setFont(undefined, 'normal');
            y += 8;
            
            // Çizgi
            doc.line(20, y - 3, 190, y - 3);
            
            // Etkinlikler
            events.forEach((event, index) => {
                if (y > 270) {
                    doc.addPage();
                    y = 20;
                }
                
                const dayName = this.getDayName(event.start, lang);
                const dateStr = this.formatDateShort(event.start, lang);
                const timeStr = `${this.formatTime(event.start)} - ${this.formatTime(event.end)}`;
                const duration = this.calculateDuration(event.start, event.end, lang);
                
                // Zebra striping
                if (index % 2 === 1) {
                    doc.setFillColor(248, 250, 252);
                    doc.rect(20, y - 5, 170, 8, 'F');
                }
                
                doc.setTextColor(30, 41, 59);
                doc.text(dayName, 25, y);
                doc.text(dateStr, 60, y);
                doc.text(timeStr, 100, y);
                doc.text(duration, 150, y);
                
                y += 8;
            });
            
            // Footer
            doc.setFontSize(8);
            doc.setTextColor(148, 163, 184);
            const footerText = lang === 'tr' ? 'Vardiya Takvimi ile oluşturuldu' :
                              lang === 'de' ? 'Erstellt mit Schichtkalender' :
                              lang === 'fr' ? 'Créé avec Calendrier des Équipes' : 'Created with Shift Calendar';
            doc.text(footerText, 105, 290, { align: 'center' });
            
            // İndir
            const filename = options.filename || 'vardiya_programi.pdf';
            doc.save(filename);
            
            return true;
        } catch (error) {
            console.error('PDF export error:', error);
            throw error;
        }
    },

    // Excel olarak export et
    async exportToExcel(events, options = {}) {
        try {
            await this.loadXLSX();
            
            const lang = window.i18n?.currentLang || 'tr';
            const headers = this.getHeaders(lang);
            
            // Veri hazırla
            const data = [
                [headers.day, headers.date, headers.time, headers.duration, headers.notes]
            ];
            
            events.forEach(event => {
                data.push([
                    this.getDayName(event.start, lang),
                    this.formatDateShort(event.start, lang),
                    `${this.formatTime(event.start)} - ${this.formatTime(event.end)}`,
                    this.calculateDuration(event.start, event.end, lang),
                    event.originalLine || ''
                ]);
            });
            
            // Worksheet oluştur
            const ws = XLSX.utils.aoa_to_sheet(data);
            
            // Sütun genişlikleri
            ws['!cols'] = [
                { wch: 15 },  // Gün
                { wch: 12 },  // Tarih
                { wch: 15 },  // Saat
                { wch: 12 },  // Süre
                { wch: 30 }   // Notlar
            ];
            
            // Workbook oluştur
            const wb = XLSX.utils.book_new();
            const sheetName = lang === 'tr' ? 'Vardiya Programı' :
                             lang === 'de' ? 'Schichtplan' :
                             lang === 'fr' ? 'Planning' : 'Shift Schedule';
            XLSX.utils.book_append_sheet(wb, ws, sheetName);
            
            // İndir
            const filename = options.filename || 'vardiya_programi.xlsx';
            XLSX.writeFile(wb, filename);
            
            return true;
        } catch (error) {
            console.error('Excel export error:', error);
            throw error;
        }
    },

    // Yardımcı fonksiyonlar
    getHeaders(lang) {
        const headers = {
            tr: { day: 'Gün', date: 'Tarih', time: 'Saat', duration: 'Süre', notes: 'Notlar' },
            en: { day: 'Day', date: 'Date', time: 'Time', duration: 'Duration', notes: 'Notes' },
            de: { day: 'Tag', date: 'Datum', time: 'Zeit', duration: 'Dauer', notes: 'Notizen' },
            fr: { day: 'Jour', date: 'Date', time: 'Heure', duration: 'Durée', notes: 'Notes' }
        };
        return headers[lang] || headers.en;
    },

    getDayName(date, lang) {
        const options = { weekday: 'long' };
        const locale = lang === 'tr' ? 'tr-TR' : 
                      lang === 'de' ? 'de-DE' :
                      lang === 'fr' ? 'fr-FR' : 'en-US';
        return date.toLocaleDateString(locale, options);
    },

    formatDate(date, lang) {
        const locale = lang === 'tr' ? 'tr-TR' : 
                      lang === 'de' ? 'de-DE' :
                      lang === 'fr' ? 'fr-FR' : 'en-US';
        return date.toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
    },

    formatDateShort(date, lang) {
        const locale = lang === 'tr' ? 'tr-TR' : 
                      lang === 'de' ? 'de-DE' :
                      lang === 'fr' ? 'fr-FR' : 'en-US';
        return date.toLocaleDateString(locale, { day: '2-digit', month: '2-digit' });
    },

    formatTime(date) {
        return date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    },

    calculateDuration(start, end, lang) {
        const diff = (end - start) / (1000 * 60 * 60);
        const hours = Math.floor(diff);
        const minutes = Math.round((diff - hours) * 60);
        
        if (minutes === 0) {
            const hourLabel = lang === 'tr' ? 'saat' : 
                             lang === 'de' ? 'Std' :
                             lang === 'fr' ? 'h' : 'h';
            return `${hours} ${hourLabel}`;
        }
        
        return `${hours}:${minutes.toString().padStart(2, '0')}`;
    }
};

// Global erişim için
window.exportModule = exportModule;
