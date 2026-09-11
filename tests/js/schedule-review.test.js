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
