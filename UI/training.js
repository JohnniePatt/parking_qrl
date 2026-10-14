/* Job controls and presentation only; model/environment operations are server-side. */
let trainingState=null, trainingTimer=null;
function trainingChart(id,rows,key,color) {
  const svg=$(id),values=rows.map(r=>r[key]);
  if(!values.length){svg.innerHTML='<text x="15" y="65" font-size="14" fill="#69808c">ยังไม่มีผล</text>';return;}
  const low=Math.min(0,...values),high=Math.max(1,...values),range=high-low;
  const points=values.map((v,i)=>`${20+i*360/Math.max(1,values.length-1)},${100-(v-low)*80/range}`).join(' ');
  svg.innerHTML=`<path d="M20 15 V100 H390" fill="none" stroke="#cad7db"/><polyline points="${points}" fill="none" stroke="${color}" stroke-width="2.5"/><text x="20" y="13" font-size="10">${high.toFixed(1)}</text><text x="20" y="117" font-size="10">${low.toFixed(1)} · episodes 1–${values.length}</text>`;
}
function renderTraining(state) {
  trainingState=state;
  const busy=['running','stopping'].includes(state.status);
  $('train-start').disabled=busy || !runtimeSupports('dqn_training');
  $('train-stop').disabled=!busy || state.status==='stopping';
  $('test-start').disabled=busy || !$('trained-runs').value || !runtimeSupports('dqn_training');
  $('train-preview').disabled=!state.latest_output;
  $('train-history').disabled=busy || !$('trained-runs').value;
  const labels={idle:'พร้อมเริ่มฝึก',interrupted:'การรันก่อนหน้าหยุดเมื่อเซิร์ฟเวอร์ปิด',running:'กำลังทำงาน',stopping:'กำลังหยุดหลัง action ปัจจุบัน',completed:'เสร็จแล้ว',cancelled:'หยุดและบันทึกผลแล้ว',failed:'ทำงานไม่สำเร็จ'};
  $('train-status').textContent=`${state.mode==='test'?'Test':'Train'} · ${labels[state.status]||state.status}${state.error?' · '+state.error:''}`;
  $('train-progress').max=state.episodes_total||100;$('train-progress').value=state.episodes_completed||0;
  $('train-details').textContent=`${busy?(state.phase==='test'?'กำลังทดสอบ':'กำลังฝึก'):'ผลการรัน'} · จบแล้ว ${state.episodes_completed||0}/${state.episodes_total||'—'} episodes · Action ${state.action||0}/${state.max_actions||50} · เรียนรู้สะสม ${state.updates||0} ครั้ง${state.mode==='test'?' · Test ไม่เรียนรู้เพิ่ม':''} · ε ${(state.epsilon||0).toFixed(3)} · เวลา ${Math.round(state.elapsed_seconds||0)} s`;
  const rows=state.metrics||[];
  trainingChart('reward-chart',rows,'reward','#338a70');trainingChart('slots-chart',rows,'verified_slots','#3978a1');
  $('train-results').innerHTML='<table><thead><tr><th>ชุด</th><th>Episode</th><th>Seed</th><th>Actions</th><th>Reward</th><th>ช่องผ่าน</th><th>เวลา (s)</th></tr></thead><tbody>'+[...rows,...(state.evaluations||[])].map(r=>`<tr><td>${esc(r.split)}</td><td>${r.episode}</td><td>${r.seed}</td><td>${r.actions}</td><td>${r.reward.toFixed(2)}</td><td>${r.verified_slots}</td><td>${r.elapsed_seconds.toFixed(1)}</td></tr>`).join('')+'</tbody></table>';
}
async function trainingRuns() {
  const result=await api('training/runs'),selected=$('trained-runs').value;
  $('trained-runs').innerHTML='<option value="">เลือกโมเดล</option>'+result.runs.filter(r=>r.mode==='train').map(r=>`<option value="${esc(r.id)}">${esc(r.id)} · updates ${r.updates} · ${esc(r.status)}</option>`).join('');
  if([...$('trained-runs').options].some(o=>o.value===selected))$('trained-runs').value=selected;
  else if($('trained-runs').options.length>1)$('trained-runs').selectedIndex=1;
}
async function pollTraining() {
  try {
    const state=await api('training/status');renderTraining(state);
    if(['running','stopping'].includes(state.status))trainingTimer=setTimeout(pollTraining,1500);
    else {await trainingRuns();renderTraining(state);}
  } catch(error){showError(error);}
}
$('train-start').onclick=async()=>{
  try {
    const state=await api('run',{mode:'train',model:'Model_RL',episodes:Number($('train-episodes').value),max_actions:Number($('train-limit').value),seed:Number($('train-seed').value)});
    clearTimeout(trainingTimer);renderTraining(state);pollTraining();
  } catch(error){showError(error);}
};
$('train-stop').onclick=async()=>{try{renderTraining(await api('training/stop',{}));}catch(error){showError(error);}};
$('test-start').onclick=async()=>{
  try {const state=await api('run',{mode:'test',model:'Model_RL',run_id:$('trained-runs').value});clearTimeout(trainingTimer);renderTraining(state);pollTraining();}catch(error){showError(error);}
};
$('trained-runs').onchange=()=>trainingState && renderTraining(trainingState);
$('train-preview').onclick=async()=>{
  try {const name=trainingState.latest_output;document.querySelector('[data-tab="previews"]').click();await refreshOutputs();$('outputs').value=name;await $('load-output').onclick();}catch(error){showError(error);}
};
(async()=>{try {await trainingRuns();await pollTraining();}catch(error){showError(error);}})();

$('train-history').onclick=async()=>{try{renderTraining(await api('training/results',{run_id:$('trained-runs').value}));}catch(error){showError(error);}};
