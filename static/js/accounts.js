/* Oturum token'ı cookie'de, CSRF yalnız bellekte; anahtarlar localStorage'a girmez. */
(function () {
    'use strict';
    let session = {user:null,csrf_token:null,configured:false}, connections = [];
    let refreshing;
    async function api(path, options = {}) {
        const headers = {'Content-Type':'application/json', ...(options.headers || {})};
        if (session.csrf_token) headers['X-CSRF-Token'] = session.csrf_token;
        const response = await fetch(path, {...options, headers, credentials:'same-origin', cache:'no-store'});
        const body = await response.json().catch(()=>({}));
        if (!response.ok) {
            const detail=body.detail;
            const message=Array.isArray(detail) ? detail.map(x=>x.msg).join('; ') : typeof detail==='object' && detail ? detail.message : detail;
            const error = new Error(message || `İstek tamamlanamadı (${response.status}).`);
            error.status=response.status;throw error;
        }
        return body;
    }
    function fillSelections() {
        ['ocrConnection','planConnection'].forEach(id=>{
            const select=document.getElementById(id);if(!select)return;
            const old=select.value;select.replaceChildren();
            const local=document.createElement('option');local.value='';
            local.textContent=id==='ocrConnection'?'Cihazda OCR · ücretsiz':'Kural tabanlı · ücretsiz';select.append(local);
            connections.forEach(c=>{
                const opt=document.createElement('option');opt.value=c.id;opt.textContent=`${c.label} · ${c.provider} / ${c.model}`;select.append(opt);
            });
            if(connections.some(c=>c.id===old)) select.value=old;
            select.dispatchEvent(new Event('change'));
        });
    }
    function render() {
        document.getElementById('accountBadge').textContent=session.user?session.user.username:'Misafir';
        document.getElementById('authForm').hidden=!!session.user || !session.configured;
        document.getElementById('signedIn').hidden=!session.user;
        const list=document.getElementById('connectionList');list.replaceChildren();
        connections.forEach(c=>{
            const li=document.createElement('li');
            const text=document.createElement('span');text.textContent=`${c.label} — ${c.provider} / ${c.model}`;
            const remove=document.createElement('button');remove.type='button';remove.className='btn btn-secondary';remove.textContent='Kaldır';
            remove.setAttribute('aria-label',`${c.label} bağlantısını kaldır`);
            remove.addEventListener('click',()=>run(remove,async()=>{
                await api(`/api/connections/${encodeURIComponent(c.id)}`,{method:'DELETE'});await refresh();setMessage('Bağlantı kaldırıldı.');
            }));
            const edit=document.createElement('button');edit.type='button';edit.className='btn btn-secondary';edit.textContent='Model değiştir';
            edit.addEventListener('click',()=>{edit.disabled=true;modelEditor(c,li);});
            const actions=document.createElement('span');actions.className='account-actions';actions.append(edit,remove);
            li.append(text,actions);list.append(li);
        });
        if(!connections.length && session.user){const li=document.createElement('li');li.textContent='Henüz bağlantı yok. Aşağıdan ilk anahtarını ekle.';list.append(li);}
        fillSelections();
    }
    function fillModelSelect(select, models, current) {
        select.replaceChildren();
        if(!models.length){const o=document.createElement('option');o.value='';o.textContent='Uygun model bulunamadı';select.append(o);select.disabled=true;return;}
        models.forEach(m=>{
            const o=document.createElement('option');o.value=m.id;
            o.textContent=m.label && m.label!==m.id ? `${m.label} (${m.id})` : m.id;
            if(m.vision===false)o.textContent+=' · görsel yok';
            select.append(o);
        });
        if(current && models.some(m=>m.id===current)) select.value=current;
        select.disabled=false;
    }
    async function fetchModels(payload) {
        return (await api('/api/providers/models',{method:'POST',body:JSON.stringify(payload)})).models;
    }
    function modelEditor(c, li) {
        const box=document.createElement('div');box.className='account-actions';
        const select=document.createElement('select');select.className='input';select.disabled=true;
        select.setAttribute('aria-label',`${c.label} için model`);
        const save=document.createElement('button');save.type='button';save.className='btn btn-primary';save.textContent='Kaydet';save.disabled=true;
        box.append(select,save);li.append(box);
        run(null,async()=>{
            setMessage('Modeller getiriliyor…');
            fillModelSelect(select, await fetchModels({connection_id:c.id}), c.model);save.disabled=select.disabled;setMessage('');
        }).catch(()=>{});
        save.addEventListener('click',()=>run(save,async()=>{
            await api(`/api/connections/${encodeURIComponent(c.id)}`,{method:'PATCH',body:JSON.stringify({model:select.value})});
            await refresh();setMessage('Model güncellendi.');
        }));
    }
    function setMessage(text) {document.getElementById('accountMessage').textContent=text;}
    async function run(button, action) {
        if(button)button.disabled=true;
        try{await action();}catch(e){setMessage(e.message);}finally{if(button)button.disabled=false;}
    }
    async function refresh() {
        if(refreshing)return refreshing;
        refreshing=(async()=>{
            session=await api('/api/session');
            connections=session.user?(await api('/api/connections')).connections:[];
            render();
            if(!session.configured)setMessage('Bu kurulumda hesap bağlantıları henüz açılmamış. Manuel giriş ve cihazda OCR kullanılabilir.');
        })().finally(()=>{refreshing=null;});
        return refreshing;
    }
    window.ShiftScanAccounts={api,refresh,getConnection:id=>connections.find(c=>c.id===id),getUser:()=>session.user};
    document.addEventListener('DOMContentLoaded',async()=>{
        document.getElementById('authForm').addEventListener('submit',event=>{
            event.preventDefault();const form=event.currentTarget;const button=event.submitter;
            run(button,async()=>{
                const fields=new FormData(form);
                session=await api(`/api/auth/${button?.value==='register'?'register':'login'}`,{method:'POST',body:JSON.stringify({username:fields.get('username'),password:fields.get('password')})});
                form.reset();await refresh();setMessage('Giriş yapıldı. Bağlantılarını ekleyebilir veya seçebilirsin.');
            });
        });
        document.getElementById('logoutBtn').addEventListener('click',event=>run(event.currentTarget,async()=>{
            await api('/api/auth/logout',{method:'POST'});session={user:null,csrf_token:null,configured:true};connections=[];
            document.getElementById('connectionForm').reset();window.ShiftScanReview?.reset();window.dispatchEvent(new Event('shiftscan:logout'));await refresh();setMessage('Çıkış yapıldı.');
        }));
        document.getElementById('connectionForm').addEventListener('submit',event=>{
            event.preventDefault();const form=event.currentTarget;
            run(event.submitter,async()=>{
                const data=Object.fromEntries(new FormData(form));
                await api('/api/connections',{method:'POST',body:JSON.stringify(data)});
                form.reset();resetModelSelect();await refresh();setMessage('Bağlantı eklendi. OCR veya planlama bölümünden seçebilirsin.');
            });
        });
        const modelSelect=document.getElementById('connectionModel');
        function resetModelSelect(){modelSelect.replaceChildren(new Option('Önce anahtarı gir, sonra modelleri getir',''));modelSelect.disabled=true;}
        document.getElementById('connectionProvider').addEventListener('change',resetModelSelect);
        document.getElementById('connectionApiKey').addEventListener('change',resetModelSelect);
        document.getElementById('fetchModelsBtn').addEventListener('click',event=>run(event.currentTarget,async()=>{
            const provider=document.getElementById('connectionProvider').value;
            const api_key=document.getElementById('connectionApiKey').value.trim();
            if(!api_key){setMessage('Önce API anahtarını gir.');return;}
            setMessage('Modeller getiriliyor…');
            const models=await fetchModels({provider,api_key});
            fillModelSelect(modelSelect, models);
            setMessage(models.length?`${models.length} model bulundu. Listeden seç ve bağlantıyı ekle.`:'Bu anahtarla uygun model bulunamadı.');
        }));
        try{
            const metadata=await api('/api/providers');
            const select=document.getElementById('connectionProvider');
            metadata.providers.forEach(p=>{const o=document.createElement('option');o.value=p.id;o.textContent=p.label;select.append(o);});
            await refresh();
        }catch(e){setMessage('Hesap bilgileri alınamadı. Sayfayı yenileyerek tekrar deneyebilirsin.');}
    });
})();
