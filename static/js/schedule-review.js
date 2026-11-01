/* Görselden çıkarılan haftayı kişi bazında kontrol et; onaydan önce takvime taşıma. */
(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.ShiftScanReview = api;
})(typeof window !== 'undefined' ? window : this, function () {
    'use strict';
    const DAYS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];
    const TIME = /^(?:[01]\d|2[0-3]):[0-5]\d$/;
    let pending = false;

    function toShiftText(person) {
        if (!person || person.days.length !== 7 || new Set(person.days.map(d => d.day_index)).size !== 7) {
            throw new Error('Haftanın yedi gününü kontrol edin.');
        }
        const intervals = [], lines = [];
        [...person.days].sort((a,b)=>a.day_index-b.day_index).forEach(day => {
            const label = DAYS[day.day_index];
            if (!label || !['work', 'off'].includes(day.status)) throw new Error(`${label || 'Gün'}: çalışıyor/izin seçimini tamamlayın.`);
            if (day.status === 'off') { lines.push(`${label} OFF`); return; }
            if (!day.shifts.length || day.shifts.length > 4) throw new Error(`${label}: 1–4 vardiya girin.`);
            day.shifts.forEach(shift => {
                if (!TIME.test(shift.start) || !TIME.test(shift.end) || shift.start === shift.end) throw new Error(`${label}: geçerli ve farklı saatler girin.`);
                const minutes = time => Number(time.slice(0,2))*60 + Number(time.slice(3));
                const start = day.day_index*1440 + minutes(shift.start);
                let end = day.day_index*1440 + minutes(shift.end);
                if (end < start) end += 1440;
                intervals.push([start,end]);
                lines.push(`${label} ${shift.start} - ${shift.end}`);
            });
        });
        intervals.sort((a,b)=>a[0]-b[0]);
        for (let i=1;i<intervals.length;i++) {
            if (intervals[i][0] < intervals[i-1][1]) throw new Error('Vardiya saatleri çakışıyor; saatleri kontrol edin.');
        }
        return lines.join('\n');
    }

    function localSchedule(text, weekStart) {
        const start=new Date(`${weekStart}T12:00:00Z`);
        if(Number.isNaN(start.getTime()))throw new Error('Hafta başlangıcını seçin.');
        start.setUTCDate(start.getUTCDate()-((start.getUTCDay()+6)%7));
        return {week_start:start.toISOString().slice(0,10),warnings:[
            'Yerel OCR kişi ve sütun ilişkisini doğrulayamaz. Aşağıdaki ham metinden kendi vardiyanı günlere yerleştir.'
        ],source_text:text,people:[{name:'Kendi vardiyam',days:DAYS.map((_,i)=>{
            const day=new Date(start);day.setUTCDate(day.getUTCDate()+i);
            return {date:day.toISOString().slice(0,10),day_index:i,status:'unknown',shifts:[],source_text:'',issue:'Günü ve saatleri görselden veya ham metinden tamamlayın.'};
        })}]};
    }

    function reset() {
        pending = false;
        if (typeof document !== 'undefined') {
            const panel = document.getElementById('scheduleReview');
            if (panel) { panel.replaceChildren(); panel.hidden = true; }
        }
    }

    function show(result) {
        const panel = document.getElementById('scheduleReview');
        reset(); pending = true; panel.hidden = false;
        function node(tag, text, className) {
            const el = document.createElement(tag);
            if (text) el.textContent = text;
            if (className) el.className = className;
            return el;
        }
        panel.append(node('h3', 'Vardiyaları kontrol et'));
        if(result.source_text)panel.append(node('pre',result.source_text,'ocr-raw-text'));
        panel.append(node('p', 'Kişiyi seç, belirsiz günleri düzelt ve görselle karşılaştır. Boş hücreler izin sayılmaz.', 'form-hint'));
        (result.warnings || []).forEach(w => panel.append(node('p', w, 'review-warning')));
        const personLabel=node('label','Kişi / satır','form-label');
        const select=node('select',null,'input'); select.id='reviewPerson'; personLabel.htmlFor=select.id;
        result.people.forEach((p,i) => { const opt=node('option',p.name || `Satır ${i+1}`);opt.value=String(i);select.append(opt); });
        if (result.people.length > 1) {
            const opt=node('option','Kişiyi seçin');opt.value='';opt.selected=true;opt.disabled=true;select.prepend(opt);
        }
        panel.append(personLabel,select);
        const rows=node('div',null,'review-rows'); panel.append(rows);
        const checkLabel=node('label',null,'review-confirm');
        const check=node('input'); check.type='checkbox';check.id='reviewConfirmed';
        checkLabel.append(check,document.createTextNode(' Seçili kişinin tarih ve saatlerini görselle karşılaştırdım.'));
        const apply=node('button','Kontrol ettiğim vardiyaları kullan','btn btn-primary');apply.type='button';apply.id='applySchedule';
        const discard=node('button','Vazgeç, metni kendim gireceğim','btn btn-secondary');discard.type='button';
        const error=node('p',null,'review-warning'); error.setAttribute('role','alert');
        panel.append(checkLabel,apply,discard,error);
        let editors=[];
        function render() {
            rows.replaceChildren(); editors=[]; check.checked=false;error.textContent='';
            if (select.value==='') return;
            const person=result.people[Number(select.value)];
            person.days.forEach(day => {
                const row=node('div',null,day.issue ? 'review-row needs-review' : 'review-row');
                row.append(node('strong',`${DAYS[day.day_index]} · ${day.date}`));
                const status=node('select',null,'input');status.setAttribute('aria-label',`${DAYS[day.day_index]} durum`);
                [['unknown','Kontrol gerekiyor'],['work','Çalışıyor'],['off','İzin / tatil']].forEach(([value,label])=>{
                    const opt=node('option',label);opt.value=value;opt.selected=day.status===value;status.append(opt);
                });
                const times=node('input');times.className='input';times.type='text';times.placeholder='örn. 09:00-18:00';
                times.setAttribute('aria-label',`${DAYS[day.day_index]} saatler`);
                times.value=day.shifts.map(s=>`${s.start}-${s.end}`).join(', ');times.disabled=status.value!=='work';
                const changed=()=>{ check.checked=false;times.disabled=status.value!=='work'; };
                status.addEventListener('change',changed);times.addEventListener('input',()=>{check.checked=false;});
                row.append(status,times);
                if (day.source_text) row.append(node('small',`Görselde: ${day.source_text}`,'source-cell'));
                if (day.issue) row.append(node('small',day.issue,'review-warning'));
                rows.append(row);editors.push({day,status,times});
            });
        }
        select.addEventListener('change',render);render();
        discard.addEventListener('click',()=>reset());
        apply.addEventListener('click',()=>{
            try {
                if (select.value==='') throw new Error('Önce kişiyi seçin.');
                if (!check.checked) throw new Error('Görselle karşılaştırdıktan sonra onay kutusunu işaretleyin.');
                const person={days:editors.map(({day,status,times})=>({
                    day_index:day.day_index,status:status.value,shifts:status.value==='work' ? times.value.split(',').map(part=>{
                        const match=part.trim().match(/^(\d{2}:\d{2})\s*[-–]\s*(\d{2}:\d{2})$/);
                        if (!match) throw new Error('Saatleri 09:00-18:00 biçiminde, birden çok vardiyayı virgülle ayırarak girin.');
                        return {start:match[1],end:match[2]};
                    }) : [],
                }))};
                const text=toShiftText(person);
                document.getElementById('startDate').value=result.week_start;
                const textarea=document.getElementById('shiftText');textarea.value=text;
                textarea.dispatchEvent(new Event('input',{bubbles:true}));
                reset(); textarea.focus();
            } catch(e) {error.textContent=e.message;}
        });
        panel.scrollIntoView({behavior:'smooth',block:'start'});
    }
    return {toShiftText,localSchedule,show,reset,hasPending:()=>pending};
});
