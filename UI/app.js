/* Presentation and HTTP event bindings only. All placement and policies run in Python. */
const $ = id => document.getElementById(id);
let live, replay = null, tab = 'tools', selected = '', playback = null;
let actionPending = false;
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, data) {
  const response = await fetch('/api/' + path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed');
  return result;
}
function feedback(message, error=false) { $('feedback').textContent=message; $('feedback').classList.toggle('error',error); }
function showError(error) { feedback(error.message,true); }
function currentView() {
  if(tab !== 'previews' || !replay) return live;
  const step = Number($('timeline').value), history = replay.history.slice(0,step);
  const items = step ? history[step-1].after : replay.initial_items;
  const slots = items.filter(i=>i.kind==='slot');
  return {layout:replay.layout,items,history,grid:{resolution:replay.resolution},max_actions:replay.max_actions,
    metrics:{total_slots:slots.length,slot_area:slots.reduce((n,i)=>n+i.length*i.width,0),
      utilization:100*slots.reduce((n,i)=>n+i.length*i.width,0)/(replay.layout.width*replay.layout.height),
      rejected:history.filter(e=>!e.accepted).length,actions:step}};
}
function render() {
  const view = currentView(); if(!view) return;
  const {layout, metrics, history} = view;
  $('slots').textContent=metrics.total_slots;
  $('utilization').innerHTML=Number(metrics.utilization).toFixed(1)+'<span>%</span>';
  $('slot-area').textContent=Number(metrics.slot_area).toFixed(2)+' m² / '+(layout.width*layout.height).toLocaleString()+' m²';
  $('layout-id').textContent=layout.id;
  $('grid-status').textContent=view.grid.resolution+' m';
  $('actions').textContent=metrics.actions+' / '+view.max_actions;
  $('rejected').textContent=metrics.rejected;
  $('progress').style.width=Math.min(100,metrics.actions/view.max_actions*100)+'%';
  $('source-badge').textContent=tab==='previews' && replay ? 'SAVED REPLAY' : 'LIVE SESSION';
  $('canvas-title').innerHTML='Rectangular site <span>'+esc(layout.width)+' × '+esc(layout.height)+' m</span>';
  $('log-count').textContent=history.length+' events';
  $('log').innerHTML=[...history].reverse().map(e=>`<div class="event"><span class="step">${String(e.step).padStart(3,'0')}</span><div><time>${esc(new Date(e.timestamp).toLocaleTimeString('th-TH',{hour12:false}))}</time><strong>${esc(e.command.type)} · ${esc(e.command.kind || e.command.id || 'layout')}</strong><small>${e.command.x!==undefined ? 'X '+Number((e.proposal || e.command).x).toFixed(2)+' / Y '+Number((e.proposal || e.command).y).toFixed(2)+' m' : esc(e.command.template || '')}</small><span class="${e.accepted?'ok':'bad'}">${e.accepted?'✓ Accepted':'× '+esc(e.reason)}</span></div></div>`).join('') || '<div class="empty">ยังไม่มี action ในเฟรมนี้</div>';
  const oldSelected=selected;
  $('selected').innerHTML='<option value="">เลือกจากผังหรือรายการ</option>'+live.items.map(i=>`<option value="${esc(i.id)}">${esc(i.id)} · ${esc(i.template || i.kind)}</option>`).join('');
  selected=live.items.some(i=>i.id===oldSelected)?oldSelected:''; $('selected').value=selected;
  $('move').disabled=$('remove').disabled=!selected;
  $('save').disabled=tab==='previews' && !!replay;
  const atLimit=live.history.length>=live.max_actions;
  for(const id of ['place','move','remove','reset']) $(id).disabled=atLimit || (['move','remove'].includes(id) && !selected);
  draw(view);
  document.dispatchEvent(new Event('workspace-rendered'));
}
function draw(view) {
  const {layout,items}=view, grid=view.grid.resolution;
  const svg=$('canvas');
  svg.setAttribute('viewBox',`-2 -3 ${layout.width+4} ${layout.height+6}`);
  let html=`<defs><pattern id="grid" width="${grid}" height="${grid}" patternUnits="userSpaceOnUse"><path d="M ${grid} 0 L 0 0 0 ${grid}" fill="none" stroke="#d4e0df" stroke-width=".018"/></pattern><pattern id="hatch" width=".6" height=".6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2=".6" stroke="#415b65" stroke-width=".12"/></pattern></defs><rect x="0" y="0" width="${layout.width}" height="${layout.height}" fill="#fbfdfc" stroke="#9bb1b6" stroke-width=".09"/>`;
  if($('show-grid').checked) html+=`<rect width="${layout.width}" height="${layout.height}" fill="url(#grid)"/>`;
  for(let x=0;x<=layout.width;x+=6) html+=`<text class="coordinate" x="${x}" y="-1" text-anchor="middle">${x}</text>`;
  for(let y=0;y<=layout.height;y+=6) html+=`<text class="coordinate" x="-1" y="${y+.2}" text-anchor="middle">${y}</text>`;
  for(const i of [...items.filter(i=>i.kind==='road'),...layout.obstacles,...items.filter(i=>i.kind==='slot')]) {
    const road=i.kind==='road', slot=i.kind==='slot';
    const points=i.polygon ? i.polygon.map(p=>p.join(',')).join(' ') : null;
    const attrs=`fill="${road?'#d2dce0':slot?'#c6e5d8':'#637b85'}" stroke="${road?'#a8bbc3':slot?'#338a70':'#425e6a'}" stroke-width=".065"`;
    html+=`<g data-object="${esc(i.id)}" style="cursor:pointer"><title>${esc(i.id)} · ${esc(i.template || i.kind)} · ${i.length} × ${i.width} m</title>`;
    if(points) html+=`<polygon points="${points}" ${attrs} class="${selected===i.id && tab==='tools'?'selected-shape':''}"/>`;
    else html+=`<rect x="${i.x-i.length/2}" y="${i.y-i.width/2}" width="${i.length}" height="${i.width}" ${attrs}/>`;
    if(road) html+=`<g transform="translate(${i.x} ${i.y}) rotate(${i.angle})"><path d="M ${-i.length/2+.5} 0 H ${i.length/2-.5}" stroke="#fff" stroke-width=".07" stroke-dasharray=".9 .7"/><text text-anchor="middle" y="-.7" font-size=".6" fill="#69808c">↔ ${i.width.toFixed(1)} m</text></g>`;
    if(slot) html+=`<g transform="translate(${i.x} ${i.y}) rotate(${i.angle})"><rect x="-1.65" y="-.82" width="3.3" height="1.64" rx=".35" fill="#5da88b" opacity=".28"/><text text-anchor="middle" y=".2" font-size=".58" fill="#2d705a" transform="rotate(${-i.angle})">P</text></g>`;
    if(!slot&&!road) html+=`<text x="${i.x}" y="${i.y+.2}" text-anchor="middle" font-size=".55" fill="white">${i.kind==='core'?'CORE':'C'}</text>`;
    html+='</g>';
  }
  for(const gate of layout.gates) {
    const [x,y]=gate.point;
    html+=`<line x1="${x}" y1="${y-gate.width/2}" x2="${x}" y2="${y+gate.width/2}" stroke="${gate.role==='entry'?'#05846c':'#c39042'}" stroke-width=".24"/><text x="${x===0?1:layout.width-1}" y="${y+.22}" text-anchor="${x===0?'start':'end'}" font-size=".65" fill="#385d5a">${gate.role==='entry'?'IN →':'OUT →'}</text>`;
  }
  if(tab==='tools') html+=`<g pointer-events="none" stroke="#cf922d" stroke-width=".06"><path d="M ${Number($('x').value)-.7} ${Number($('y').value)} h 1.4 M ${Number($('x').value)} ${Number($('y').value)-.7} v 1.4"/></g>`;
  svg.innerHTML=html;
}
function command(type) {
  if(type==='remove') return {type,id:selected};
  if(type==='reset') return {type};
  if(type==='move') return {type,id:selected,x:Number($('x').value),y:Number($('y').value),rotation:Number($('rotation').value)};
  return {type,kind:$('kind').value,template:$('template').value,x:Number($('x').value),y:Number($('y').value),rotation:Number($('rotation').value),width:Number($('road-width').value),length:Number($('road-length').value)};
}
async function submit(type, payload=command(type)) {
  if(actionPending) return;
  actionPending=true;
  document.dispatchEvent(new Event('workspace-rendered'));
  try { const result=await api('action',payload); live=result.state; render(); feedback(result.event.accepted ? `Action ${result.event.step} · ${type} สำเร็จ` : `Action ${result.event.step} · ถูกปฏิเสธ: ${result.event.reason}`,!result.event.accepted); } catch(error){showError(error);}
  finally { actionPending=false; document.dispatchEvent(new Event('workspace-rendered')); }
}
for(const type of ['place','move','remove','reset']) $(type).onclick=()=>submit(type);
$('new-session').onclick=async()=>{try{live=await api('session',{seed:Number($('seed').value),resolution:Number($('resolution').value),max_actions:Number($('limit').value)});selected='';render();feedback('เริ่ม session ใหม่แล้ว · ถนนเริ่มต้นถูกบันทึกเป็น Action 1');}catch(error){showError(error);}};
$('kind').onchange=()=>{$('road-fields').classList.toggle('hidden',$('kind').value!=='road');$('template-label').classList.toggle('hidden',$('kind').value==='road');};
function selectObject(id) { const item=live.items.find(i=>i.id===id); if(!item)return; selected=id;$('x').value=item.x;$('y').value=item.y;$('rotation').value=item.rotation;render(); }
$('selected').onchange=()=>{selected=$('selected').value;selected?selectObject(selected):render();};
for(const id of ['x','y','show-grid']) $(id).addEventListener('input',()=>draw(currentView()));
$('save').onclick=async()=>{try{const result=await api('save',{});feedback('บันทึกแล้ว: Outputs/'+result.name);await refreshOutputs();}catch(error){showError(error);}};
async function refreshOutputs(){const result=await api('outputs');$('outputs').innerHTML='<option value="">เลือกผลที่บันทึกไว้</option>'+result.files.map(name=>`<option value="${esc(name)}">${esc(name)}</option>`).join('');}
$('refresh').onclick=()=>refreshOutputs().catch(showError);
function stopPlayback(){clearInterval(playback);playback=null;$('play').textContent='▶ Play';}
function frame(step){$('timeline').value=Math.max(0,Math.min(Number($('timeline').max),step));$('frame-label').textContent=$('timeline').value+' / '+$('timeline').max;render();}
$('load-output').onclick=async()=>{try{stopPlayback();replay=await api('preview',{name:$('outputs').value});$('timeline').max=replay.history.length;frame(replay.history.length);feedback('กำลังดูผลบันทึก · '+(replay.source || replay.model || 'saved output'));}catch(error){showError(error);}};
$('timeline').oninput=()=>{stopPlayback();frame(Number($('timeline').value));};
$('previous').onclick=()=>{stopPlayback();frame(Number($('timeline').value)-1);};
$('next').onclick=()=>{stopPlayback();frame(Number($('timeline').value)+1);};
$('play').onclick=()=>{if(playback)return stopPlayback();if(!replay)return;if(Number($('timeline').value)>=replay.history.length)frame(0);$('play').textContent='Ⅱ Pause';playback=setInterval(()=>{frame(Number($('timeline').value)+1);if(Number($('timeline').value)>=replay.history.length)stopPlayback();},650);};
document.querySelectorAll('[data-tab]').forEach(button=>button.onclick=()=>{stopPlayback();tab=button.dataset.tab;document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b===button));for(const name of ['tools','runs','previews']) $(name+'-panel').classList.toggle('hidden',name!==tab);render();if(tab==='previews')refreshOutputs().catch(showError);feedback(tab==='previews'?'เลือก JSON เพื่อเปิดประวัติการจัดวาง':tab==='runs'?'Phase 02 · ยังไม่มีโมเดลสำหรับรัน':'พร้อมทดสอบเครื่องมือ');});
async function initialize(){try{live=await api('state');$('template').innerHTML=Object.entries(live.templates).map(([key,t])=>`<option value="${esc(key)}">${esc(t.label)}</option>`).join('');render();await refreshOutputs();}catch(error){showError(error);}}
initialize();
