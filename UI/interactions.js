/* Pointer/keyboard input and transient SVG ghosts only.
   Persisted geometry, snapping, validation and mutations remain in Arrange_tools. */
(() => {
  let brush = null, gesture = null, hover = null;
  let previewTimer = null, previewSequence = 0, queuedPreview = null, previewInFlight = false;
  let previewEpoch = 0, lastRenderedPreview = 0;
  const svg = $('canvas');
  const ns = 'http://www.w3.org/2000/svg';
  const editable = () => live && live.session_mode!=='environment_test' && tab === 'tools' && !actionPending && live.history.length < live.max_actions;
  const scenePoint = event => new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());
  const inSite = point => point && point.x >= 0 && point.y >= 0 && point.x <= live.layout.width && point.y <= live.layout.height;
  function inCanvas(event) {
    const box=svg.getBoundingClientRect();
    return event.clientX>=box.left && event.clientX<=box.right && event.clientY>=box.top && event.clientY<=box.bottom;
  }
  function palette() {
    if(!live || $('palette').children.length) return;
    const tools=[{key:'select',label:'เลือก / ย้าย',icon:'↖',note:'ลากอุปกรณ์เดิม'},
      ...Object.entries(live.templates).map(([key,t])=>({key,label:t.label,icon:t.angle===90?'▥':t.angle===45?'▨':'▤',note:`${t.length} × ${t.width} m`,kind:'slot',template:key})),
      ...[3.5,6].map(width=>({key:'road-'+width,label:'ถนน '+width.toFixed(1)+' m',icon:width===3.5?'→':'↔',note:width===3.5?'ทางเดียว · R หมุนทิศ':'สองทาง · ปรับความยาวได้',kind:'road',width})),
      ...['perpendicular','angled'].map(template=>({key:'row-'+template,label:'แถว '+live.templates[template].label,icon:'▥▥',note:'ทั้งแถว = 1 action',kind:'row',template}))];
    for(const tool of tools) {
      const button=document.createElement('button');
      button.className='palette-card';button.type='button';button.dataset.tool=tool.key;
      button.setAttribute('aria-label',tool.label);button.setAttribute('aria-pressed','false');
      button.innerHTML=`<span class="tool-icon ${tool.kind==='road'?'road-icon':''}">${tool.icon}</span><strong>${esc(tool.label)}</strong><small>${esc(tool.note)}</small>`;
      button.addEventListener('pointerdown',event=>{
        if(event.button!==0 || !editable()) return;
        choose(tool);
        if(tool.kind) start(event,{source:'palette',tool:{...tool},offset:{x:0,y:0}});
      });
      button.addEventListener('click',()=>choose(tool)); // Keyboard and click-to-place.
      $('palette').append(button);
    }
  }
  function choose(tool) {
    if(!editable()) return;
    cancel();
    brush=tool.kind?{...tool}:null;
    if(brush) {
      selected='';$('selected').value='';
      $('kind').value=brush.kind;
      if(brush.kind==='slot' || brush.kind==='row') $('template').value=brush.template;
      else $('road-width').value=brush.width;
      $('kind').onchange();
    }
    hover=null;
    render();
  }
  function sync() {
    if(!live) return;
    palette();
    $('game-tools').classList.toggle('hidden',tab!=='tools');
    for(const button of $('palette').children) {
      const active=brush ? button.dataset.tool===brush.key : button.dataset.tool==='select';
      button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));
      button.disabled=!editable() || (button.dataset.tool.startsWith('row-') && !runtimeSupports('place_row'));
    }
    $('active-tool').textContent=(brush ? brush.label+' · คลิกหรือลากวาง' : selected ? 'เลือก: '+selected+' · ลากเพื่อย้าย' : 'เลือก / ลากย้ายอุปกรณ์')+' · '+$('rotation').value+'°';
    $('quick-remove').disabled=!editable() || !selected;
    $('quick-rotate').disabled=!editable();
    $('quick-length').disabled=!editable();
    svg.classList.toggle('paint-mode',!!brush && tab==='tools');
    if(gesture && !editable()) cancel();
  }
  function drawGhost(point, item, accepted, reason, append=false) {
    if(!append) clearGhost();
    if(!point || !item) return;
    const group=document.createElementNS(ns,'g');
    group.id=append?'placement-ghost-'+item.id:'placement-ghost';group.setAttribute('pointer-events','none');
    if(append) group.setAttribute('data-preview-extra','true');
    group.setAttribute('transform',`translate(${point.x} ${point.y}) rotate(${item.angle})`);
    const shape=document.createElementNS(ns,'rect');
    for(const [key,value] of Object.entries({x:-item.length/2,y:-item.width/2,width:item.length,height:item.width,rx:.08,
      fill:accepted===null?'#e8b652':accepted?'#58b58f':'#d86b57','fill-opacity':.48,stroke:accepted===null?'#a87513':accepted?'#087c68':'#bc4433','stroke-width':.14,'stroke-dasharray':'.3 .18'})) shape.setAttribute(key,value);
    group.append(shape);svg.append(group);
    $('pointer-position').textContent=accepted===null ? `X ${point.x.toFixed(2)} · Y ${point.y.toFixed(2)} m · ${reason || 'กำลังตรวจ policy…'}`
      : `Snap X ${point.x.toFixed(2)} · Y ${point.y.toFixed(2)} m · ${accepted?'ผ่าน policy':reason}`;
  }
  function ghost(point, item) {
    if(!point || !item || !inSite(point)) {
      previewEpoch++;queuedPreview=null;clearGhost();return;
    }
    // Immediate display only: policy checks and snapping still belong to Python.
    drawGhost(point,item,null);
    const rotation=Number($('rotation').value);
    const moving=gesture?.source==='move';
    const tool=gesture?.tool || brush;
    const command=moving ? {type:'move',id:gesture.item.id,x:point.x,y:point.y,rotation}
      : tool.kind==='row' ? {type:'place_row',template:tool.template,row_length:Number($('quick-length').value),x:point.x,y:point.y,rotation}
      : {type:'place',kind:tool.kind,template:tool.template,width:tool.width,
         length:Number($('quick-length').value),x:point.x,y:point.y,rotation};
    queuedPreview={command,sequence:++previewSequence,epoch:previewEpoch};
    if(!previewTimer && !previewInFlight) previewTimer=setTimeout(fetchPreview,75);
  }
  async function fetchPreview() {
    previewTimer=null;
    const request=queuedPreview;queuedPreview=null;
    if(!request || !editable()) return;
    previewInFlight=true;
    try {
      const result=await api('propose',request.command);
      if(request.epoch===previewEpoch && request.sequence===previewSequence && request.sequence>=lastRenderedPreview && editable() && result.proposal) {
        lastRenderedPreview=request.sequence;
        (result.proposals || [result.proposal]).forEach((item,index)=>drawGhost(item,item,result.accepted,result.reason,index>0));
      }
    } catch(error) {
      if(request.epoch===previewEpoch && request.sequence===previewSequence) {
        $('pointer-position').textContent='ตัวอย่างตำแหน่ง · ตรวจ policy ไม่สำเร็จ: '+error.message;
      }
    } finally {
      previewInFlight=false;
      if(queuedPreview && !previewTimer) previewTimer=setTimeout(fetchPreview,75);
    }
  }
  function visualItem() {
    const item=gesture?.item;
    const tool=gesture?.tool || brush;
    const rotation=Number($('rotation').value);
    if(item) return {...item,angle:item.angle-item.rotation+rotation};
    if(!tool) return null;
    if(tool.kind==='road') return {kind:'road',width:tool.width,length:Number($('quick-length').value),angle:rotation};
    const t=live.templates[tool.template];
    return {...t,kind:tool.kind,angle:t.angle+rotation};
  }
  function clearGhost() { $('placement-ghost')?.remove();svg.querySelectorAll('[data-preview-extra]').forEach(node=>node.remove()); }
  function cursorToken(event, item) {
    if(!item) return;
    let token=$('drag-token');
    if(!token) {
      token=document.createElement('div');token.id='drag-token';
      token.setAttribute('aria-hidden','true');document.body.append(token);
    }
    token.style.left=(event.clientX+16)+'px';token.style.top=(event.clientY+16)+'px';
    token.textContent=item.kind==='row' ? '▥▥ แถวจอด · '+$('quick-length').value+' m · จุดจับช่องแรก'
      : (item.kind==='road'?'⇄ ถนน':'▥ ช่องจอด')+' · '+item.length+' × '+item.width+' m';
    token.classList.toggle('hidden',inCanvas(event) && inSite(scenePoint(event)));
  }
  function finishVisuals() {
    previewEpoch++;queuedPreview=null;clearTimeout(previewTimer);previewTimer=null;
    clearGhost();
    $('drag-token')?.remove();
    svg.querySelectorAll('.drag-source').forEach(node=>node.classList.remove('drag-source'));
    $('pointer-position').textContent='หน่วย: เมตร · ลากจากเมนูเพื่อวาง';
  }
  function cancel() { gesture=null;hover=null;finishVisuals(); }
  function start(event, info) {
    gesture={...info,pointer:event.pointerId,startX:event.clientX,startY:event.clientY,moved:false,point:null};
    event.currentTarget.setPointerCapture?.(event.pointerId);
    event.preventDefault();
    cursorToken(event,visualItem());
  }
  svg.addEventListener('pointerdown',event=>{
    if(event.button!==0 || !editable()) return;
    const point=scenePoint(event);
    if(brush) {
      start(event,{source:'canvas',tool:{...brush},offset:{x:0,y:0}});
      gesture.point=point;ghost(point,visualItem());
      return;
    }
    const node=event.target.closest('[data-object]');
    const item=live.items.find(i=>i.id===node?.dataset.object);
    if(!item) {
      selected='';$('x').value=point.x.toFixed(2);$('y').value=point.y.toFixed(2);render();
      return;
    }
    selectObject(item.id);
    start(event,{source:'move',item:{...item},offset:{x:point.x-item.x,y:point.y-item.y}});
    gesture.point={x:item.x,y:item.y};ghost(gesture.point,visualItem());
    svg.querySelector(`[data-object="${item.id}"]`)?.classList.add('drag-source');
  });
  document.addEventListener('pointermove',event=>{
    if(gesture && event.pointerId===gesture.pointer) {
      gesture.moved ||= Math.hypot(event.clientX-gesture.startX,event.clientY-gesture.startY)>5;
      const point=scenePoint(event);
      gesture.point={x:point.x-gesture.offset.x,y:point.y-gesture.offset.y};
      cursorToken(event,visualItem());
      ghost(inCanvas(event)?gesture.point:null,visualItem());
      return;
    }
    if(editable() && brush && event.target.closest('#canvas')) {
      hover=scenePoint(event);ghost(hover,visualItem());
    }
  });
  svg.addEventListener('pointerleave',()=>{if(!gesture){hover=null;finishVisuals();}});
  document.addEventListener('pointerup',async event=>{
    if(!gesture || event.pointerId!==gesture.pointer) return;
    const current=gesture;
    const point=scenePoint(event);
    const destination={x:point.x-current.offset.x,y:point.y-current.offset.y};
    const drop=inCanvas(event) && inSite(destination);
    const shouldSubmit=drop && (current.moved || current.source==='canvas');
    cancel();
    if(!editable() || !shouldSubmit) return;
    $('x').value=destination.x.toFixed(4);$('y').value=destination.y.toFixed(4);
    const rotation=Number($('rotation').value);
    if(current.source==='move') {
      await submit('move',{type:'move',id:current.item.id,x:destination.x,y:destination.y,rotation});
    } else if(current.tool.kind==='row') {
      await submit('place_row',{type:'place_row',template:current.tool.template,row_length:Number($('quick-length').value),x:destination.x,y:destination.y,rotation});
    } else {
      await submit('place',{type:'place',kind:current.tool.kind,template:current.tool.template,
        width:current.tool.width,length:Number($('quick-length').value),x:destination.x,y:destination.y,rotation});
    }
  });
  document.addEventListener('pointercancel',cancel);
  window.addEventListener('blur',cancel);
  function rotateTool() {
    if(!editable()) return;
    $('rotation').value=(Number($('rotation').value)+90)%360;
    if(gesture || brush) { ghost(gesture?.point || hover,visualItem());sync(); }
    else if(selected) {
      const item=live.items.find(i=>i.id===selected);
      if(item) submit('move',{type:'move',id:item.id,x:item.x,y:item.y,rotation:Number($('rotation').value)});
    }
    else sync();
  }
  $('quick-rotate').onclick=rotateTool;
  $('quick-remove').onclick=()=>submit('remove');
  $('quick-length').oninput=()=>{$('road-length').value=$('quick-length').value;$('row-length').value=$('quick-length').value;if(hover)ghost(hover,visualItem());};
  $('road-length').addEventListener('input',()=>{$('quick-length').value=$('road-length').value;});
  $('rotation').addEventListener('change',sync);
  document.addEventListener('keydown',event=>{
    if(tab!=='tools' || event.ctrlKey || event.metaKey || event.altKey || event.target.closest('input,select,textarea,[contenteditable="true"]')) return;
    if(event.key==='Escape') {event.preventDefault();cancel();choose({key:'select'});}
    if(event.key.toLowerCase()==='r' && !event.repeat) {event.preventDefault();rotateTool();}
    if(event.key==='Delete' && selected && editable()) {event.preventDefault();submit('remove');}
  });
  document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',cancel));
  document.addEventListener('workspace-rendered',sync);
})();
