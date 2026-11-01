const test = require('node:test');
const assert = require('node:assert/strict');
const R = require('../../static/js/schedule-review.js');
const person = () => ({name:'A',days:Array.from({length:7},(_,i)=>({day_index:i,status:'off',shifts:[]}))});
test('unknown cell cannot silently become OFF',()=>{
 const p=person();p.days[2].status='unknown';
 assert.throws(()=>R.toShiftText(p),/Çar/);
});
test('two shifts and overnight shift retain selected day',()=>{
 const p=person();p.days[0]={day_index:0,status:'work',shifts:[{start:'09:00',end:'12:00'},{start:'13:00',end:'18:00'}]};
 p.days[4]={day_index:4,status:'work',shifts:[{start:'22:00',end:'06:00'}]};
 const result=R.toShiftText(p);
 assert.match(result,/Pzt 09:00 - 12:00\nPzt 13:00 - 18:00/);
 assert.match(result,/Cum 22:00 - 06:00/);
});
test('invalid hour and overlapping shifts are rejected',()=>{
 const p=person();p.days[0]={day_index:0,status:'work',shifts:[{start:'29:00',end:'18:00'}]};
 assert.throws(()=>R.toShiftText(p));
 p.days[0].shifts=[{start:'09:00',end:'14:00'},{start:'13:00',end:'18:00'}];
 assert.throws(()=>R.toShiftText(p),/çakış/);
});
test('overnight overlap with next day is rejected',()=>{
 const p=person();p.days[0]={day_index:0,status:'work',shifts:[{start:'22:00',end:'08:00'}]};
 p.days[1]={day_index:1,status:'work',shifts:[{start:'07:00',end:'12:00'}]};
 assert.throws(()=>R.toShiftText(p),/çakış/);
});
test('partial or duplicate week is rejected',()=>{
 const p=person();p.days.pop();assert.throws(()=>R.toShiftText(p));
 const q=person();q.days[6].day_index=0;assert.throws(()=>R.toShiftText(q));
});
test('local OCR never guesses people or weekdays from unstructured text',()=>{
 const result=R.localSchedule('Alice 09:00-18:00 OFF OFF OFF OFF OFF OFF\nBob 22:00-06:00','2026-09-07');
 assert.equal(result.people.length,1);
 assert.ok(result.people[0].days.every(d=>d.status==='unknown'&&d.shifts.length===0));
 assert.throws(()=>R.toShiftText(result.people[0]));
});

test('relabelWeek moves dates but keeps day indexes',()=>{
 const r={week_start:'2026-10-26',suggested_week_start:'2026-11-02',people:[person()]};
 R.relabelWeek(r,'2026-11-02');
 assert.equal(r.week_start,'2026-11-02');
 assert.deepEqual(r.people[0].days.map(d=>d.date),['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06','2026-11-07','2026-11-08']);
 assert.equal(r.suggested_week_start,undefined);
});
test('dutyDays keeps only duty days the person actually works',()=>{
 const p=person();
 p.days[0]={day_index:0,status:'work',duties:['DİJİTAL ACENTELİK']};
 p.days[2]={day_index:2,status:'off',duties:['DİJİTAL ACENTELİK']};
 p.days[3]={day_index:3,status:'work',duties:['DİJİTAL ACENTELİK']};
 assert.deepEqual(R.dutyDays(p),{'DİJİTAL ACENTELİK':[0,3]});
 const edited=p.days.map(d=>d.status);edited[3]='off';
 assert.deepEqual(R.dutyDays(p,edited),{'DİJİTAL ACENTELİK':[0]});
});
test('titleCase is Turkish aware',()=>{
 assert.equal(R.titleCase('DİJİTAL ACENTELİK'),'Dijital Acentelik');
});
