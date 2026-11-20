'use strict';
let csrf = '', currentPlan = null, activeTab = 'overview', polling = null;
let hasConnections = false;
const expandedLogs = new Set();
let sourceResources = [];
const selectedUuids = new Set();
let selectionModel = new CloneSelection();
const $ = selector => document.querySelector(selector);
const element = (tag, text, className) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (className) e.className = className; return e; };
function notify(message, error = false) { const n = $('#notice'); n.textContent = message; n.className = error ? 'notice error' : 'notice'; n.hidden = false; n.scrollIntoView({block:'nearest', behavior:'smooth'}); }
async function api(path, options = {}) {
  const response = await fetch('/api' + path, { credentials:'same-origin', ...options, headers:{'Content-Type':'application/json', 'X-CSRF-Token':csrf, ...(options.headers || {})} });
  let data; try { data = await response.json(); } catch { throw new Error('Risposta del server non valida'); }
  if (response.status === 401 && path !== '/login') { showLogin(); throw new Error('Sessione scaduta: accedi nuovamente'); }
  if (!response.ok) throw new Error(data.detail || 'Operazione non riuscita');
  return data;
}
const post = (path, body = {}) => api(path, {method:'POST', body:JSON.stringify(body)});
function showLogin() { $('#workspace').hidden = true; $('#login-screen').hidden = false; if (polling) clearInterval(polling); }
function tab(name) { activeTab = name; for (const panel of document.querySelectorAll('.tab-panel')) panel.hidden = panel.id !== name; for (const b of document.querySelectorAll('[data-tab]')) b.classList.toggle('active', b.dataset.tab === name); $('#setup-prompt').hidden=hasConnections || name!=='overview'; $('#page-label').textContent = {overview:'Panoramica', connections:'Connessioni', history:'Operazioni', guide:'Guida e istruzioni'}[name]; if (name === 'history') refreshJobs().catch(e => notify(e.message, true)); if(name==='guide')loadGuide().catch(e=>notify(e.message,true)); }
function field(role, key, label, type='text', placeholder='', value='') {
  const l = element('label', label); const input = element('input'); input.type = type; input.name = `${role}.${key}`; input.id = `${role}-${key}`; input.placeholder = placeholder; input.value = value; input.autocomplete = type === 'password' ? 'new-password' : 'off';
  if (['url','token','ssh_host','ssh_key','ssh_user','ssh_port'].includes(key)) input.required = true;
  if (type === 'number') { input.min = 1; input.max = 65535; }
  l.append(input); return l;
}
function checkbox(role, key, label) { const l = element('label', undefined, 'check'); const input = element('input'); input.type='checkbox'; input.id=`${role}-${key}`; l.append(input, element('span',label)); return l; }
function connectionForms() {
  for (const role of ['source','target']) {
    const card = element('article',undefined,'panel connection-card'); card.append(element('span', role === 'source' ? 'SORGENTE' : 'DESTINAZIONE', role === 'source' ? 'pill' : 'pill orange'), element('h2',role === 'source' ? 'Il server da copiare' : 'Il nuovo server'));
    card.append(field(role,'url','URL Coolify','url','https://coolify.example.it'), field(role,'token','Token API','password','Token con visibilità completa'), field(role,'server_uuid','UUID server Coolify (facoltativo)','text','Automatico se è presente un solo server'), field(role,'ssh_host','IP o hostname SSH','text','203.0.113.10'));
    const row = element('div',undefined,'field-row'); row.append(field(role,'ssh_port','Porta SSH','number','22','22'),field(role,'ssh_user','Utente SSH','text','root','root')); card.append(row,field(role,'ssh_key','Nome del file chiave in ssh/','text',`${role}_ed25519`,`${role}_ed25519`),checkbox(role,'sudo','Usa sudo non interattivo per i comandi remoti'),checkbox(role,'allow_http','Consenti API HTTP su rete fidata (token non cifrato in transito)'));
    $('#connection-fields').append(card);
  }
}
async function loadConfig() { const data = await api('/config'); hasConnections=data.configured; $('#setup-prompt').hidden=hasConnections || activeTab!=='overview'; for (const role of ['source','target']) { const config=data.connections[role]; if (!config) continue; for (const [key,value] of Object.entries(config)) { const input=$(`#${role}-${key}`); if (input) { if (input.type === 'checkbox') input.checked = value; else input.value = value; } } $(`#${role}-summary-url`).textContent=config.url; $(`#${role}-state`).textContent='Configurata · da verificare'; } }
async function loadGuide() {
  const data=await api('/setup'); $('#ssh-path').textContent=`Cartella SSH del backend: ${data.ssh_directory}`; $('#setup-checks').replaceChildren(); $('#guide-sections').replaceChildren(); $('#guide-limits').replaceChildren();
  function check(label, present) { const row=element('div',undefined,'setup-check'); row.append(element('span',label),element('strong',present?'Presente':'Da preparare',present?'ok':'muted')); $('#setup-checks').append(row); }
  for(const c of data.connections){const role=c.role==='source'?'Sorgente':'Destinazione';check(`${role}: connessione salvata`,c.configured);check(`${role}: ${c.key_name}`,c.key_present);}
  check('File known_hosts',data.known_hosts_present);
  for(const section of data.sections){const card=element('article',undefined,'panel guide-section');card.append(element('h2',section.title),element('p',section.text,'muted'));if(section.commands){for(const command of section.commands){const block=element('div',undefined,'guide-command'),code=element('pre',command),copy=element('button','Copia comando','secondary');copy.type='button';copy.onclick=async()=>{try{await navigator.clipboard.writeText(command);copy.textContent='Copiato';setTimeout(()=>{copy.textContent='Copia comando';},1800);}catch{notify('Seleziona e copia il comando mostrato nella guida.');}};block.append(code,copy);card.append(block);}}if(section.items){const list=element('ul');for(const text of section.items)list.append(element('li',text));card.append(list);}$('#guide-sections').append(card);}
  for(const text of data.limits)$('#guide-limits').append(element('li',text));
}
function selectionChanged() {
  selectedUuids.clear();for(const id of selectionModel.ids())selectedUuids.add(id);
  renderPlan(null);
  renderSelection();
}
function renderSelection() {
  $('#selection-rows').replaceChildren(); $('#selection-table').hidden=sourceResources.length===0;
  $('#selection-empty').hidden=sourceResources.length>0;
  $('#select-all').disabled=!sourceResources.length; $('#select-none').disabled=!sourceResources.length;
  const byId=new Map(sourceResources.map(row=>[row.uuid,row]));
  const linkedIds=new Set(sourceResources.filter(row=>row.group!=='databases').flatMap(row=>row.database_uuids||[]));
  function choiceFor(row,id) { const input=element('input');input.type='checkbox';input.id=id;input.checked=selectedUuids.has(row.uuid);input.setAttribute('aria-label',`Clona ${row.name}`);input.onchange=()=>{selectionModel.toggle(row.uuid,input.checked);selectionChanged();};return input; }
  function resourceRow(row) { const tr=element('tr',undefined,'app-resource-row');tr.dataset.resourceUuid=row.uuid;const choice=element('td'),input=choiceFor(row,`choose-${row.uuid}`);choice.append(input);const name=element('td'),label=element('label',row.name,'selection-table-name');label.htmlFor=input.id;name.append(label,element('small',row.uuid));if(row.dependency_warning)name.append(element('p',row.dependency_warning,'dependency-warning'));const kind=element('td',row.group==='services'?'Stack Compose':row.group==='databases'?'Database':row.kind||'Applicazione');kind.append(element('small',row.supported_hint));tr.append(choice,name,kind,element('td',[row.project,row.environment].filter(Boolean).join(' / ')||'Da verificare'));$('#selection-rows').append(tr); }
  for(const row of sourceResources.filter(resource=>resource.group!=='databases')){
    resourceRow(row);
    const linked=(row.database_uuids||[]).map(id=>byId.get(id)).filter(Boolean),embedded=row.embedded_databases||[];
    if(!linked.length&&!embedded.length)continue;
    const tr=element('tr',undefined,'database-group-row');tr.dataset.parentResourceUuid=row.uuid;const cell=element('td');cell.colSpan=4;
    const section=element('section',undefined,'database-subsection');section.setAttribute('aria-label',`Database di ${row.name}`);section.append(element('h3',`Database collegati (${linked.length+embedded.length})`));
    for(const db of linked){const item=element('label',undefined,'database-item'),input=choiceFor(db,`choose-db-${row.uuid}-${db.uuid}`),required=selectionModel.requiredBy(db.uuid);input.disabled=required.length>0;const description=element('span');description.append(element('strong',db.name),element('small',db.kind==='databases'?'Database':db.kind||'Database'));const owners=(db.application_uuids||[]).length;let note=required.length?'Incluso automaticamente con le applicazioni selezionate':'Selezionabile anche singolarmente';if(owners>1)note+=` · Condiviso tra ${owners} applicazioni`;description.append(element('span',note,'database-note'));item.append(input,description);section.append(item);}
    for(const db of embedded){const item=element('div',undefined,'database-item'),input=element('input');input.type='checkbox';input.checked=selectedUuids.has(row.uuid);input.disabled=true;input.setAttribute('aria-label',`${db.name}: incluso nello stack ${row.name}`);const description=element('span');description.append(element('strong',db.name),element('small',db.kind),element('span','Database interno: incluso nella selezione dello stack','database-note'));item.append(input,description);section.append(item);}
    cell.append(section);tr.append(cell);$('#selection-rows').append(tr);
  }
  const unlinked=sourceResources.filter(row=>row.group==='databases'&&!linkedIds.has(row.uuid));
  if(unlinked.length){const tr=element('tr',undefined,'unlinked-databases-heading'),cell=element('td');cell.colSpan=4;cell.append(element('strong','Database senza collegamento verificato'),element('small','Selezione manuale: la presenza nello stesso progetto non prova un collegamento.'));tr.append(cell);$('#selection-rows').append(tr);for(const db of unlinked)resourceRow(db);}
  const applications=sourceResources.filter(row=>row.group!=='databases'&&selectedUuids.has(row.uuid)).length;
  const databases=sourceResources.filter(row=>row.group==='databases'&&selectedUuids.has(row.uuid)).length+sourceResources.filter(row=>selectedUuids.has(row.uuid)).reduce((total,row)=>total+(row.embedded_databases||[]).length,0);
  $('#selection-count').textContent=selectedUuids.size?`${applications} ${applications===1?'applicazione/stack':'applicazioni/stack'} · ${databases} ${databases===1?'database selezionato':'database selezionati'}`:'Nessuna risorsa selezionata';$('#analyze').disabled=!selectedUuids.size;
}
async function loadResources() {
  const b=$('#load-resources');b.disabled=true;b.textContent='Lettura sorgente…';
  try{const data=await post('/resources');sourceResources=data.resources;selectionModel=new CloneSelection(sourceResources,[...selectedUuids]);selectionChanged();if(!sourceResources.length)$('#selection-empty').textContent='Nessuna applicazione, database o stack visibile al token sorgente.';notify('Elenco caricato. Selezionando un’app includi anche i suoi database collegati.');}catch(e){notify(e.message,true);}finally{b.disabled=false;b.textContent='Carica elenco sorgente';}
}
function renderPlan(plan) {
  currentPlan=plan; $('#resource-rows').replaceChildren(); $('#plan-blocks').replaceChildren(); $('#plan-warnings').replaceChildren();
  $('#empty-plan').hidden=!!plan; $('#plan-content').hidden=!plan; $('#open-execute').disabled=!plan || !!plan.blocks.length;
  for (const [id,value] of [['resources',plan?.resources.length],['volumes',plan?.resources.filter(r=>r.group==='applications').reduce((a,r)=>a+r.volumes,0)],['blocks',plan?.blocks.length]]) $(`#stat-${id}`).textContent=value ?? '—';
  if (!plan) return;
  for (const row of plan.resources) { const tr=element('tr'), name=element('td'); name.append(element('strong',row.name),element('small',row.uuid)); const state=element('td',row.blocks.length ? 'Da risolvere' : 'Pronta',row.blocks.length ? 'bad':'ok'); tr.append(name,element('td',row.group === 'databases' ? row.kind : row.kind==='github'?'GitHub / Dockerfile':'Docker Image'),element('td',`${row.volumes} vol. · ${row.variables} var.`),state); $('#resource-rows').append(tr); }
  for (const message of plan.blocks) $('#plan-blocks').append(element('div',message,'block'));
  for (const message of plan.warnings) $('#plan-warnings').append(element('div',message,'warning'));
  $('#plan-expiry').textContent=`Analizzato alle ${new Date(plan.created*1000).toLocaleTimeString('it-IT')}. Il piano scade dopo 15 minuti. Coolify ${plan.source_version} / ${plan.target_version}.`;
  $('#source-state').textContent='API e identità SSH verificate'; $('#target-state').textContent=plan.blocks.length ? 'Controlli da risolvere' : 'Pronta per la copia';
}
const statuses={queued:'In coda',running:'In corso',failed:'Non completata',copied:'Copiata · verifica finale richiesta',interrupted:'Interrotta · controlla la sorgente'};
async function refreshJobs() {
  const result=await api('/jobs'); $('#job-count').textContent=result.jobs.length; $('#jobs').replaceChildren();
  if (!result.jobs.length) { const empty=element('div',undefined,'panel empty'); empty.append(element('h3','Nessuna clonazione avviata'),element('p','Le operazioni appariranno qui con il loro stato e il registro degli eventi.')); $('#jobs').append(empty); }
  for (const job of result.jobs) {
    const card=element('article',undefined,'panel job-card'), top=element('div',undefined,'job-top'), info=element('div'); info.append(element('h2',job.id.slice(0,12)),element('small',new Date(job.created*1000).toLocaleString('it-IT'))); top.append(info,element('span',statuses[job.status] || job.status,'pill')); const progress=element('progress',undefined,'job-progress'); progress.max=100; progress.value=job.data.progress||0; progress.setAttribute('aria-label','Avanzamento clonazione'); card.append(top,progress,element('p',`Fase: ${job.data.phase}`,'muted'));
    if (job.data.error) card.append(element('p',job.data.error,'error'));
    if (job.status==='copied') card.append(element('p','Il clone è una copia al momento del backup. La sorgente è stata riavviata; la destinazione è ferma. Avvio, verifica applicativa e passaggio DNS si eseguono in Coolify dopo aver controllato i dati.','warning'));
    if (job.status==='interrupted' || job.data.recovery_required) card.append(element('p','Controlla subito che le applicazioni sorgente siano avviate. Un arresto del worker può impedire il recupero automatico.','block'));
    const actions=element('div',undefined,'job-actions'); const logs=element('button',expandedLogs.has(job.id)?'Nascondi registro':'Mostra registro','secondary'); const logBox=element('pre',undefined,'job-events'); logBox.hidden=!expandedLogs.has(job.id); const loadEvents=async()=>{const events=await api(`/jobs/${job.id}/events`);logBox.textContent=events.map(e=>`${new Date(e.time*1000).toLocaleTimeString('it-IT')}  ${e.message}`).join('\n')||'Nessun evento ancora disponibile';}; logs.onclick=async()=>{try{if(expandedLogs.has(job.id)){expandedLogs.delete(job.id);logBox.hidden=true;logs.textContent='Mostra registro';}else{await loadEvents();expandedLogs.add(job.id);logBox.hidden=false;logs.textContent='Nascondi registro';}}catch(e){notify(e.message,true);}}; if(expandedLogs.has(job.id))await loadEvents(); actions.append(logs);
    if (job.data.stopped_source?.length && !result.busy) { const recovery=element('button','Recupera sorgente','secondary'); recovery.onclick=async()=>{ recovery.disabled=true;try {await post(`/jobs/${job.id}/recover`);notify('Comando di riavvio sorgente completato.');await refreshJobs();}catch(e){notify(e.message,true);}finally{recovery.disabled=false;}}; actions.append(recovery); }
    const report=element('button','Esporta report','secondary'); report.onclick=()=>{const blob=new Blob([JSON.stringify(job,null,2)],{type:'application/json'}); const url=URL.createObjectURL(blob); const a=element('a'); a.href=url;a.download=`clone-${job.id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};actions.append(report);card.append(actions,logBox);
    if (job.data.backups?.length) { const details=element('details'),summary=element('summary',`${job.data.backups.length} backup cifrati conservati`);details.append(summary);for(const artifact of job.data.backups){const p=element('p',`${artifact.file} · ${(artifact.bytes/1048576).toFixed(1)} MiB · SHA256 ${artifact.sha256}`,'muted');details.append(p);}card.append(details); }
    $('#jobs').append(card);
  }
  if(result.busy) $('#open-execute').disabled=true;
}
async function enter() { $('#login-screen').hidden=true; $('#workspace').hidden=false;await loadConfig();const plan=await api('/plan');if(plan){selectedUuids.clear();for(const row of plan.resources)selectedUuids.add(row.uuid);}renderSelection();renderPlan(plan);await refreshJobs();tab(hasConnections?'overview':'guide');if(polling)clearInterval(polling);polling=setInterval(()=>{if(activeTab==='history')refreshJobs().catch(()=>{});},5000); }
connectionForms();
for(const button of document.querySelectorAll('[data-tab]'))button.onclick=()=>tab(button.dataset.tab);
$('#open-connections').onclick=()=>tab('connections');
$('#load-resources').onclick=loadResources;
$('#select-all').onclick=()=>{selectionModel.selectAll();selectionChanged();};
$('#select-none').onclick=()=>{selectionModel.clear();selectionChanged();};
for(const button of document.querySelectorAll('[data-open-guide]'))button.onclick=()=>tab('guide');
$('#guide-connections').onclick=()=>tab('connections');
$('#refresh-setup').onclick=async()=>{const b=$('#refresh-setup');b.disabled=true;try{await loadGuide();notify('Stato locale aggiornato. Nessuna connessione ai server eseguita.');}catch(e){notify(e.message,true);}finally{b.disabled=false;}};
$('#login-form').onsubmit=async event=>{event.preventDefault();const b=event.submitter;b.disabled=true;$('#login-error').textContent='';try{const data=await post('/login',{password:$('#password').value});csrf=data.csrf;$('#password').value='';await enter();}catch(e){$('#login-error').textContent=e.message;}finally{b.disabled=false;}};
$('#logout').onclick=async()=>{try{await post('/logout');}finally{csrf='';showLogin();}};
$('#connections-form').onsubmit=async event=>{event.preventDefault();const data={};for(const role of ['source','target']){data[role]={};for(const key of ['url','token','server_uuid','ssh_host','ssh_user','ssh_key','ssh_port','sudo','allow_http']){const input=$(`#${role}-${key}`);data[role][key]=input.type==='checkbox'?input.checked:key==='ssh_port'?Number(input.value):input.value.trim();}}const b=event.submitter;b.disabled=true;try{await post('/config',data);for(const role of ['source','target'])$(`#${role}-token`).value='';sourceResources=[];selectedUuids.clear();renderSelection();renderPlan(null);await loadConfig();notify('Connessioni salvate in forma cifrata. Ora carica l’elenco e scegli cosa clonare.');tab('overview');}catch(e){notify(e.message,true);}finally{b.disabled=false;}};
$('#analyze').onclick=async()=>{const b=$('#analyze');if(!selectedUuids.size){notify('Seleziona almeno una risorsa da clonare.',true);return;}b.disabled=true;b.textContent='Analisi in corso…';notify('Verifica API, SSH e selezione in corso. I server non vengono modificati.');try{const p=await post('/plan',{preserve_domains:$('#preserve-domains').checked,resource_uuids:[...selectedUuids]});renderPlan(p);notify(p.blocks.length?`Analisi completata: ${p.blocks.length} controlli da risolvere.`:'Analisi completata: piano pronto per la revisione.',!!p.blocks.length);}catch(e){renderPlan(null);notify(e.message,true);}finally{b.disabled=!selectedUuids.size;b.textContent='Analizza selezione';}};
$('#preserve-domains').onchange=()=>{renderPlan(null);notify('Opzioni modificate: ripeti l’analisi prima della copia.');};
$('#open-execute').onclick=()=>{$('#execute-form').reset();$('#execute-dialog').showModal();};
$('#cancel-execute').onclick=()=>$('#execute-dialog').close();
$('#execute-form').onsubmit=async event=>{event.preventDefault();const b=event.submitter;b.disabled=true;try{await post('/execute',{plan_id:currentPlan?.id,confirmation:$('#confirmation').value,downtime_accepted:$('#accept-downtime').checked,external_writers_stopped:$('#accept-writers').checked});$('#execute-dialog').close();renderPlan(null);tab('history');notify('Clonazione avviata. Puoi seguire l’avanzamento nel registro.');}catch(e){$('#execute-dialog').close();notify(e.message,true);}finally{b.disabled=false;}};
$('#refresh-jobs').onclick=()=>refreshJobs().catch(e=>notify(e.message,true));
api('/session').then(async data=>{csrf=data.csrf;$('#version').textContent=`v${data.version}`;await enter();}).catch(()=>showLogin());
