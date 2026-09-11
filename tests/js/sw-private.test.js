const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
test('private GET requests never read or populate offline caches',async()=>{
 const handlers={},seen=[];
 const context={
  self:{addEventListener:(name,handler)=>{handlers[name]=handler;},location:{origin:'https://example.test'}},
  URL,Response,console,
  caches:{match:()=>{throw new Error('Private cache read');},open:()=>{throw new Error('Private cache write');}},
  fetch:async(request,options)=>{seen.push(options);return new Response('{}');}
 };
 vm.runInNewContext(fs.readFileSync('templates/sw.js','utf8'),context);
 for(const path of ['/api/session','/api/connections','/health','/ocr/status']){
  let promise;handlers.fetch({request:{method:'GET',url:'https://example.test'+path},respondWith:p=>{promise=p;}});
  assert.equal((await promise).status,200);
 }
 assert.equal(seen.length,4);
 assert.ok(seen.every(options=>options.cache==='no-store'));
});
