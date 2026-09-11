/* Device-code ceremony. Tokens never enter the browser. */
(function(){
    'use strict';
    let pending=null, timer=null;
    const el=id=>document.getElementById(id);
    const api=(...args)=>window.ShiftScanAccounts.api(...args);
    function reset(){clearTimeout(timer);pending=null;el('chatgptLoginPanel').hidden=true;el('chatgptCode').textContent='';el('chatgptVerification').removeAttribute('href');el('chatgptModel').replaceChildren();el('chatgptModel').disabled=true;el('chatgptFinishBtn').disabled=true;el('chatgptLoginBtn').disabled=false;}
    async function cancel(){
        const p=pending;reset();
        if(p)await api(`/api/chatgpt/login/${encodeURIComponent(p.id)}`,{method:'DELETE'}).catch(()=>{});
    }
    async function poll(){
        const p=pending;if(!p)return;
        if(window.ShiftScanAccounts.getUser()?.id!==p.owner){await cancel();return;}
        try{
            const result=await api(`/api/chatgpt/login/${encodeURIComponent(p.id)}/status`,{method:'POST'});
            if(pending!==p)return;
            if(result.status==='ready'){
                el('chatgptStatus').textContent='Giriş tamamlandı. Model seçip bağlantıyı kaydet.';
                el('chatgptCode').textContent='Onaylandı';el('chatgptVerification').removeAttribute('href');
                el('chatgptModel').replaceChildren();
                result.models.forEach(m=>{const option=document.createElement('option');option.value=m.id;option.textContent=m.label;option.selected=m.default;el('chatgptModel').append(option);});
                el('chatgptModel').disabled=false;el('chatgptFinishBtn').disabled=false;return;
            }
            timer=setTimeout(poll,2500);
        }catch(e){if(pending===p){reset();el('accountMessage').textContent=e.message;}}
    }
    window.ShiftScanChatGPT={cancel};
    document.addEventListener('DOMContentLoaded',()=>{
        el('chatgptLoginBtn').addEventListener('click',async()=>{
            el('chatgptLoginBtn').disabled=true;
            const owner=window.ShiftScanAccounts.getUser()?.id;
            try{
                const result=await api('/api/chatgpt/login',{method:'POST',body:JSON.stringify({label:el('chatgptLabel').value})});
                pending={id:result.id,owner};
                if(window.ShiftScanAccounts.getUser()?.id!==owner){await cancel();return;}
                el('chatgptVerification').href=result.verification_url;
                el('chatgptCode').textContent=result.user_code;
                el('chatgptStatus').textContent='OpenAI onayın bekleniyor. Giriş 10 dakika içinde tamamlanmalı.';
                el('chatgptLoginPanel').hidden=false;timer=setTimeout(poll,2000);
            }catch(e){reset();el('accountMessage').textContent=e.message;}
        });
        el('chatgptCancelBtn').addEventListener('click',cancel);
        el('chatgptFinishBtn').addEventListener('click',async()=>{
            if(!pending)return;
            el('chatgptFinishBtn').disabled=true;
            try{
                await api(`/api/chatgpt/login/${encodeURIComponent(pending.id)}/finish`,{method:'POST',body:JSON.stringify({model:el('chatgptModel').value})});
                reset();await window.ShiftScanAccounts.refresh();el('accountMessage').textContent='ChatGPT bağlantısı eklendi. Gelişmiş modda planlama bağlantısından seçebilirsin.';
            }catch(e){el('accountMessage').textContent=e.message;el('chatgptFinishBtn').disabled=false;}
        });
    });
})();
