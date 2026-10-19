/* All returned source/model text is rendered as text, never interpreted as HTML. */
const $ = (s) => document.querySelector(s);
const csrf = () => $('meta[name="csrf-token"]').content;
async function api(url, body) {
  const response = await fetch(url, {method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf()},body:JSON.stringify(body ?? {})});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your preferences and try again.');
  return data;
}
const pause = (ms) => new Promise(resolve => setTimeout(resolve, ms));
async function follow(job, progress) {
  progress.classList.remove('hidden');
  while (job.status === 'RUNNING') {
    progress.textContent = job.phase + '…';
    await pause(700);
    const response = await fetch('/api/jobs/' + encodeURIComponent(job.id));
    if (!response.ok) throw new Error('The live session ended. Reopen history to inspect saved results.');
    job = await response.json();
  }
  progress.textContent = job.phase + (job.error ? ': ' + job.error : '');
  return job;
}
function element(tag, text, className) {const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
document.querySelectorAll('[data-monitor]').forEach(button => button.addEventListener('click',async()=>{
  button.disabled=true;const status=$('#global-progress');
  try {const job=await follow(await api('/api/monitor'),status);if(job.status==='FAILED')throw new Error(job.error || 'Market check failed. Review source health.');window.location.href='/monitor';}
  catch(error){status.classList.remove('hidden');status.textContent=error.message;button.disabled=false;}
}));
let conversationId=localStorage.getItem('mini-conversation')||null;
let lastAgentRun=null;
function activateChat(){if($('#chat-surface')){$('#chat-surface').classList.add('has-messages');$('#chat-welcome').classList.add('hidden');}}
function scrollChat(){const stage=$('#chat-stage');if(stage)stage.scrollTop=stage.scrollHeight;}
function renderAnswer(result) {
  activateChat();
  const entry=element('article',undefined,'chat-entry');
  entry.append(element('span',result.status === 'SUCCESS' ? 'AI research · evidence checked' : 'AI unavailable · saved source search','badge '+(result.status==='SUCCESS'?'':'warning')));
  entry.append(element('p',result.message || result.summary));
  if(result.model)entry.append(element('small',(result.provider||'')+' · '+result.model+' · thinking: '+(result.thinking||'auto')));
  if(result.attachments?.length)entry.append(element('p','Attached context: '+result.attachments.map(x=>x.name).join(', ')+' · unverified user material','upload-provenance'));
  (result.attachment_quotes||[]).forEach(item=>{entry.append(element('h3','From your file · '+item.name));entry.append(element('blockquote',item.quote));entry.append(element('p','Exact uploaded text · unverified user material, excluded from approved market conclusions.','meta'));});
  if(result.status==='SUCCESS') entry.append(element('small',(result.tool_calls||0)+' actual skill calls. AI interpretations require review.'));
  (result.claims||[]).forEach(claim=>{entry.append(element('h3',claim.kind.replaceAll('_',' ')));entry.append(element('p',claim.text));entry.append(element('blockquote',claim.quote));const a=element('a',claim.title||'Review source');a.href='/sources/'+encodeURIComponent(claim.document_id);entry.append(a);});
  if(result.stored_evidence){entry.append(element('h3','Stored evidence matches'));entry.append(element('p','Deterministic search only. No AI synthesis or live skill call has been verified.','meta'));(result.stored_evidence.evidence||[]).forEach(doc=>{const line=element('div',undefined,'source-line');const a=element('a',doc.title);a.href='/sources/'+encodeURIComponent(doc.id);line.append(a,element('small',doc.publisher+' | Published '+(doc.published_at||'not verified')+' | '+doc.source_health));entry.append(line);});}
  (result.limitations||[]).forEach(text=>entry.append(element('p',text,'meta')));
  $('#chat-history').append(entry);
  scrollChat();
  if(result.agent_run_id){lastAgentRun=result.agent_run_id;$('#save-answer-report').classList.remove('hidden');}
}
async function loadConversation(id){
  const response=await fetch('/api/conversations/'+encodeURIComponent(id));
  if(!response.ok){localStorage.removeItem('mini-conversation');conversationId=null;return;}
  const data=await response.json();conversationId=id;localStorage.setItem('mini-conversation',id);$('#chat-history').replaceChildren();
  data.runs.forEach(run=>{const user=element('div',undefined,'chat-entry user');user.append(element('p',run.question));$('#chat-history').append(user);if(run.output)renderAnswer(JSON.parse(run.output));});
}
if($('#ask-form')){
  if(conversationId)loadConversation(conversationId).catch(()=>{});
  document.querySelectorAll('[data-example]').forEach(btn=>btn.addEventListener('click',()=>{$('#question').value=btn.dataset.example;$('#question').focus();}));
  document.querySelectorAll('[data-conversation]').forEach(btn=>btn.addEventListener('click',()=>loadConversation(btn.dataset.conversation)));
  $('#new-conversation').addEventListener('click',()=>{conversationId=null;lastAgentRun=null;localStorage.removeItem('mini-conversation');$('#chat-history').replaceChildren();$('#save-answer-report').classList.add('hidden');$('#saved-report-link').replaceChildren();$('#chat-surface').classList.remove('has-messages');$('#chat-welcome').classList.remove('hidden');$('#research-progress').classList.add('hidden');$('#question').value='';$('#question').focus();});
  $('#ask-form').addEventListener('submit',async(event)=>{
    event.preventDefault();const question=$('#question').value.trim();if(!question)return;let controls;try{controls=window.miniChat?.getPayload()||{};}catch(error){$('#attachment-status').textContent=error.message;return;}const button=event.submitter||$('#ask-form button[type="submit"]');button.disabled=true;activateChat();
    const user=element('div',undefined,'chat-entry user');user.append(element('p',question));$('#chat-history').append(user);$('#question').value='';scrollChat();
    try{const submitted=await api('/api/ask',{question,conversation_id:conversationId,...controls,...(window.miniMarketContext?{market_context:window.miniMarketContext}:{})});window.miniChat?.clearFiles();const job=await follow(submitted,$('#research-progress'));if(job.result){conversationId=job.result.conversation_id;localStorage.setItem('mini-conversation',conversationId);renderAnswer(job.result);}else throw new Error(job.error||'Research could not finish.');}
    catch(error){$('#research-progress').classList.remove('hidden');$('#research-progress').textContent=error.message;}finally{button.disabled=false;}
  });
  $('#save-answer-report').addEventListener('click',async()=>{try{const result=await api('/api/reports',{agent_run_id:lastAgentRun});const a=element('a','Open saved evidence briefing');a.href=result.url;$('#saved-report-link').replaceChildren(a);}catch(error){$('#saved-report-link').textContent=error.message;}});
  $('#question').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();$('#ask-form').requestSubmit($('#ask-form button[type="submit"]'));}});
  const topic=new URLSearchParams(location.search).get('topic');if(topic){const suggested=document.querySelector('[data-topic="'+CSS.escape(topic)+'"]');if(suggested){$('#question').value=suggested.dataset.example;$('#question').focus();}}
  const drillParams=new URLSearchParams(location.search);const contextQuestion=drillParams.get('question');if(contextQuestion){$('#question').value=contextQuestion.slice(0,4000);$('#question').focus();window.miniMarketContext={geography:drillParams.get('geography'),metric:drillParams.get('metric'),period:drillParams.get('period'),evidence_ids:(drillParams.get('evidence_ids')||'').split(',').filter(Boolean)};}
  $('#new-conversation').addEventListener('click',()=>{window.miniMarketContext=null;});
}
if($('#generate-report'))$('#generate-report').addEventListener('click',async(event)=>{event.target.disabled=true;try{const result=await api('/api/reports',{});window.location.href=result.url;}catch(error){$('#global-progress').classList.remove('hidden');$('#global-progress').textContent=error.message;event.target.disabled=false;}});
if($('#settings-form')){
  $('#settings-form').addEventListener('submit',async(event)=>{event.preventDefault();const form=new FormData(event.target);const body={focus:form.getAll('focus'),scheduled_ai_analysis:form.has('scheduled_ai_analysis'),morning_time:form.get('morning_time'),evening_time:form.get('evening_time'),email_recipient:form.get('email_recipient'),notification_mode:form.get('notification_mode'),telegram_enabled:form.has('telegram_enabled'),apprise_enabled:form.has('apprise_enabled'),vacancy_threshold_pp:Number(form.get('vacancy_threshold_pp'))};try{const result=await api('/api/settings',body);$('#settings-result').textContent=result.message;}catch(error){$('#settings-result').textContent=error.message;}});
  $('#test-notification').addEventListener('click',async()=>{try{const result=await api('/api/notifications/test');$('#notification-result').textContent=result.deliveries.map(d=>d.channel+': '+d.status).join(', ');}catch(error){$('#notification-result').textContent=error.message;}});
}
if($('#geography-filter'))$('#geography-filter').addEventListener('change',event=>{document.querySelectorAll('[data-geography]').forEach(card=>card.classList.toggle('hidden',event.target.value!=='all'&&card.dataset.geography!==event.target.value));});
document.querySelectorAll('.approved-chart,.reported-chart').forEach(chart=>{const rows=JSON.parse(chart.dataset.series),canvas=chart.querySelector('canvas');canvas.width=650;canvas.height=240;const ctx=canvas.getContext('2d');const values=rows.map(r=>r.value),min=Math.min(...values),max=Math.max(...values);const times=rows.map(r=>{const m=r.period.match(/^(\d{4})([MQ])(\d+)$/);return m?Date.UTC(Number(m[1]),m[2]==='M'?Number(m[3])-1:(Number(m[3])-1)*3,1):Date.parse(r.period);});const validTimes=times.every(Number.isFinite);ctx.strokeStyle='#dce3e9';ctx.beginPath();ctx.moveTo(45,15);ctx.lineTo(45,205);ctx.lineTo(630,205);ctx.stroke();ctx.strokeStyle=chart.classList.contains('reported-chart')?'#4b7890':'#168780';ctx.lineWidth=2;ctx.beginPath();values.forEach((v,i)=>{const fraction=validTimes?(times[i]-times[0])/(times.at(-1)-times[0]||1):i/Math.max(1,values.length-1);const x=55+fraction*555,y=185-(v-min)*150/(max-min||1);if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y);ctx.fillStyle='#607083';ctx.font='11px Segoe UI';if(i===0||i===values.length-1||i%Math.ceil(values.length/4)===0){ctx.fillText(rows[i].period,x-18,227);ctx.fillText(String(v),x-8,y-10);}});ctx.stroke();ctx.fillText('percent',8,14);});
