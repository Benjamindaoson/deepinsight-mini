/* Secrets are write-only inputs: never persisted in browser storage or returned. */
(() => {
  const q = selector => document.querySelector(selector);
  const all = selector => [...document.querySelectorAll(selector)];
  const el = (tag, text, cls) => {const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;};
  let state={profiles:[],selection:{}}, options=[], pending=[], uploading=false, selecting=false;
  const labels={auto:'Auto · provider default',off:'Instant · thinking off',low:'Light thinking',medium:'Standard thinking',high:'Extended thinking',max:'Maximum thinking'};
  const message = (selector,text,error=false) => {const node=q(selector);if(node){node.textContent=text;node.classList.toggle('error',error);}};
  async function post(url, body={}) {const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':q('meta[name="csrf-token"]').content},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Check the input and try again.');return data;}
  function current(){const select=q('.model-select');return options.find(x=>x.value===select?.value);}
  function renderThinking(preferred='auto'){
    const chosen=current(), levels=chosen?.model.thinking||['auto'];
    all('.thinking-select').forEach(select=>{select.replaceChildren(...levels.map(level=>{const option=el('option',labels[level]||level);option.value=level;return option;}));select.value=levels.includes(preferred)?preferred:'auto';});
    message('#thinking-help',levels.length===1?'This model uses its provider-defined thinking mode. Manual effort controls are unavailable.':'This setting is sent with each model request.');
  }
  async function saveSelection(){
    const chosen=current();if(!chosen)return;
    selecting=true;
    try{
      state.selection={profile_id:chosen.profile.id,model:chosen.model.id,thinking:q('.thinking-select')?.value||'auto'};
      await post('/api/providers/select',state.selection);
      message('#model-selection-status','Selection saved.');
      message('#current-model-label',chosen.model.id+' ⌄');
      message('#thinking-label',state.selection.thinking==='auto'?'Auto':(state.selection.thinking==='off'?'Instant':state.selection.thinking[0].toUpperCase()+state.selection.thinking.slice(1)));
      message('#chat-connection',chosen.profile.label+' · '+chosen.model.id+' · '+(labels[state.selection.thinking]||state.selection.thinking));
    }catch(error){message('#model-selection-status',error.message,true);}finally{selecting=false;}
  }
  function populate(){
    options=[];
    state.profiles.forEach(profile=>(profile.models||[]).forEach(model=>options.push({profile,model,value:profile.id+'|'+model.id})));
    options.sort((a,b)=>a.profile.scope.localeCompare(b.profile.scope)||a.model.id.localeCompare(b.model.id));
    const preferred=state.selection.profile_id+'|'+state.selection.model;
    const initial=options.find(x=>x.value===preferred)||options.find(x=>x.model.id==='gpt-5.6-terra')||options.find(x=>x.model.id==='deepseek-flash')||options[0];
    all('.model-select').forEach(select=>{select.replaceChildren();if(!options.length){select.append(el('option','Add a key and refresh models in Settings'));return;}const groups=new Map();options.forEach(option=>{if(!groups.has(option.profile.id)){const group=el('optgroup');group.label=option.profile.label+' · '+option.profile.scope;groups.set(option.profile.id,group);select.append(group);}const node=el('option',option.model.id);node.value=option.value;groups.get(option.profile.id).append(node);});select.value=initial.value;});
    renderThinking(state.selection.thinking||'auto');
    if(initial){message('#current-model-label',initial.model.id+' ⌄');saveSelection();}
    renderProfiles();
  }
  async function load(){const response=await fetch('/api/providers');if(!response.ok)throw new Error('Sign in or reload to configure your connection.');state=await response.json();populate();}
  async function runJob(job,status){while(job.status==='RUNNING'){status.textContent=job.phase+'…';await new Promise(resolve=>setTimeout(resolve,700));const response=await fetch('/api/jobs/'+encodeURIComponent(job.id));if(!response.ok)throw new Error('The check session ended. Retry explicitly.');job=await response.json();}if(job.result)return job.result;throw new Error(job.error||'Connection check failed.');}
  function renderProfiles(){
    const list=q('#provider-list');if(!list)return;list.replaceChildren();
    state.profiles.forEach(profile=>{
      const card=el('article',undefined,'provider-card');card.append(el('h3',profile.label));card.append(el('span',profile.scope==='personal'?'Personal · encrypted key':'Workspace connection · key hidden','badge'));
      card.append(el('p',profile.base_url,'provider-url'));
      card.append(el('p',(profile.models||[]).length+' discovered chat models. '+(profile.check?profile.check.status+' · '+profile.check.model:'No saved connection check for this profile.'),'connection-check'));
      const actions=el('div',undefined,'actions'),status=el('p','','meta');
      const refresh=el('button','Refresh models','secondary');refresh.type='button';refresh.addEventListener('click',async()=>{refresh.disabled=true;try{status.textContent='Reading provider model catalog…';const result=await post('/api/providers/'+profile.id+'/models');status.textContent=result.models.length+' models returned by provider.';await load();}catch(error){status.textContent=error.message;}finally{refresh.disabled=false;}});
      const check=el('button','Test connection','secondary');check.type='button';check.addEventListener('click',async()=>{check.disabled=true;try{const chosen=current();const model=chosen?.profile.id===profile.id?chosen.model.id:profile.models?.[0]?.id;if(!model)throw new Error('Refresh models first.');const thinking=chosen?.profile.id===profile.id?(q('.thinking-select')?.value||'auto'):'auto';const result=await runJob(await post('/api/providers/'+profile.id+'/check',{model,thinking}),status);status.textContent=result.status+' · '+result.message;status.classList.toggle('error',result.status!=='SUCCESS');}catch(error){status.textContent=error.message;status.classList.add('error');}finally{check.disabled=false;}});
      actions.append(refresh,check);
      if(profile.scope==='personal'){
        const edit=el('button','Replace key','secondary');edit.type='button';edit.addEventListener('click',()=>{q('#profile-id').value=profile.id;q('#provider-kind').value=profile.provider;q('#provider-label').value=profile.label;updateUrl();q('#provider-key').value='';q('#provider-key').focus();message('#provider-result','Paste the replacement key. Existing key stays active until you save.');});
        const remove=el('button','Remove','secondary');remove.type='button';remove.addEventListener('click',async()=>{if(!window.confirm('Remove this personal API connection? Saved research will remain.'))return;try{await post('/api/providers/'+profile.id+'/remove');await load();}catch(error){status.textContent=error.message;}});actions.append(edit,remove);
      }
      card.append(actions,status);list.append(card);
    });
  }
  function updateUrl(){if(q('#provider-url'))q('#provider-url').value=q('#provider-kind').value==='deepseek'?'https://api.deepseek.com':'https://toapis.cn/v1';}
  all('.model-select').forEach(select=>select.addEventListener('change',()=>{renderThinking('auto');saveSelection();}));
  all('.thinking-select').forEach(select=>select.addEventListener('change',saveSelection));
  if(q('#provider-form')){
    q('#provider-kind').addEventListener('change',updateUrl);
    q('#cancel-provider-edit').addEventListener('click',()=>{q('#provider-form').reset();q('#profile-id').value='';updateUrl();message('#provider-result','');});
    q('#provider-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;try{const body={provider:q('#provider-kind').value,label:q('#provider-label').value,api_key:q('#provider-key').value.trim()};if(q('#profile-id').value)body.id=q('#profile-id').value;const result=await post('/api/providers',body);q('#provider-key').value='';q('#profile-id').value='';message('#provider-result','Key saved encrypted. Refreshing its model catalog…');try{await post('/api/providers/'+result.id+'/models');message('#provider-result','Encrypted key saved and model catalog loaded. Choose a model and test the connection.');}catch(error){message('#provider-result','Key saved. '+error.message,true);}await load();}catch(error){q('#provider-key').value='';message('#provider-result',error.message,true);}finally{button.disabled=false;}});
  }
  function renderUploads(){
    const region=q('#queued-attachments');if(!region)return;region.replaceChildren();pending.forEach(item=>{const chip=el('div',undefined,'attachment-chip');chip.append(el('span','📎 '+item.name+(item.truncated?' · text truncated':'')));const remove=el('button','×');remove.type='button';remove.setAttribute('aria-label','Remove '+item.name);remove.addEventListener('click',()=>{pending=pending.filter(x=>x.id!==item.id);renderUploads();});chip.append(remove);region.append(chip);});
  }
  if(q('#attachment-input')){
    q('#attach-button').addEventListener('click',()=>q('#attachment-input').click());
    q('#attachment-input').addEventListener('change',async event=>{const files=[...event.target.files];if(files.length+pending.length>5){message('#attachment-status','Attach at most five files per message.',true);event.target.value='';return;}uploading=true;q('#attach-button').disabled=true;try{for(const file of files){if(file.size>8*1024*1024)throw new Error('Each file must be at most 8 MiB.');message('#attachment-status','Uploading '+file.name+'…');const body=new FormData();body.append('file',file);const response=await fetch('/api/attachments',{method:'POST',headers:{'X-CSRF-Token':q('meta[name="csrf-token"]').content},body});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Upload failed.');pending.push(data);renderUploads();}message('#attachment-status','Files ready. Sending will share their content with your selected provider.');}catch(error){message('#attachment-status',error.message,true);}finally{uploading=false;q('#attach-button').disabled=false;event.target.value='';}});
  }
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&q('#model-menu'))q('#model-menu').open=false;});
  document.addEventListener('click',event=>{const menu=q('#model-menu');if(menu&&!menu.contains(event.target))menu.open=false;});
  window.miniChat={getPayload(){if(uploading)throw new Error('Wait until the files finish uploading.');if(selecting)throw new Error('Wait until the model selection is saved.');if(!current())throw new Error('Configure an API key and refresh models in Settings first.');const params=new URLSearchParams(location.search);const scope={};['geography','metric','period'].forEach(k=>{if(params.get(k))scope[k]=params.get(k);});if(params.get('evidence_ids'))scope.evidence_ids=params.get('evidence_ids').split(',').filter(Boolean).slice(0,20);return {selection:{...state.selection},attachment_ids:pending.map(x=>x.id),...(Object.keys(scope).length?{market_context:scope}:{})};},clearFiles(){pending=[];renderUploads();message('#attachment-status','');}};
  if(q('.model-select'))load().catch(error=>{message('#chat-connection',error.message,true);message('#provider-result',error.message,true);});
})();
