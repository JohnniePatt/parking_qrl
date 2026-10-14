// Regression: pointer preview must be visible before any policy response.
// No browser/package dependency; exercises actual event bindings in interactions.js.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const nodes = new Map(), listeners = new Map(), timers = new Map();
let timerId = 0, requests = [];
class Element {
  constructor(id='') { this.id=id; this.children=[]; this.attrs={}; this.handlers={}; this.dataset={}; this.value='0'; this.textContent=''; this.style={}; this.classes=new Set();
    this.classList={toggle:(c,on)=>on?this.classes.add(c):this.classes.delete(c),add:c=>this.classes.add(c),remove:c=>this.classes.delete(c)}; }
  append(node) {this.children.push(node); if(node.id) nodes.set(node.id,node);}
  setAttribute(k,v) {this.attrs[k]=String(v);}
  addEventListener(k,fn) {this.handlers[k]=fn;}
  remove() {nodes.delete(this.id);}
  setPointerCapture() {}
  getBoundingClientRect() {return {left:0,top:0,right:48,bottom:30};}
  getScreenCTM() {return {inverse:()=>({})};}
  querySelectorAll() {return [];}
  closest(selector) {return selector==='#canvas' && this.id==='canvas'?this:null;}
}
for(const id of ['canvas','palette','game-tools','rotation','kind','template','road-width','road-length',
  'selected','active-tool','quick-remove','quick-rotate','quick-length','pointer-position']) nodes.set(id,new Element(id));
nodes.get('quick-length').value='12';nodes.get('road-length').value='12';nodes.get('kind').onchange=()=>{};
const document={body:new Element(),createElement:()=>new Element(),createElementNS:()=>new Element(),
  querySelectorAll:()=>[],addEventListener:(name,fn)=>listeners.set(name,fn)};
const context=vm.createContext({document,window:{addEventListener(){}},console,
  $:id=>nodes.get(id),live:{history:[],max_actions:200,items:[],layout:{width:48,height:30},templates:{perpendicular:{label:'90',angle:90,length:5.5,width:2.5}}},
  tab:'tools',selected:'',actionPending:false,esc:String,
  DOMPoint:class {constructor(x,y){this.x=x;this.y=y;} matrixTransform(){return this;}},
  setTimeout:fn=>{timers.set(++timerId,fn);return timerId;},clearTimeout:id=>timers.delete(id),
  api:(_route,command)=>new Promise((resolve,reject)=>requests.push({command,resolve,reject})),
  render:()=>listeners.get('workspace-rendered')?.(),selectObject(){},submit(){throw Error('Preview must not commit');}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../UI/interactions.js'),'utf8'),context);
listeners.get('workspace-rendered')();
const card=nodes.get('palette').children[1];
const pointer=(x,y)=>({clientX:x,clientY:y,pointerId:1,button:0,target:nodes.get('canvas'),currentTarget:card,preventDefault(){}});
function move(x,y){listeners.get('pointermove')(pointer(x,y));}
function shape(){return nodes.get('placement-ghost')?.children[0];}
function flushTimer(){const [id,fn]=timers.entries().next().value;timers.delete(id);return fn();}

(async()=>{
  card.handlers.pointerdown(pointer(-10,-10));
  assert.ok(nodes.get('drag-token'),'A cursor token appears while leaving the menu');
  move(8.03,14.78);
  assert.ok(shape(),'A footprint appears immediately, before the preview timer fires');
  assert.equal(shape().attrs.fill,'#e8b652','Pending preview has a neutral colour');
  assert.equal(requests.length,0,'Rendering does not wait on network');
  const first=flushTimer();
  move(10.03,14.78);
  requests[0].resolve({accepted:true,proposal:{x:8,y:14.75,angle:90,length:5.5,width:2.5}});
  await first;
  assert.match(nodes.get('placement-ghost').attrs.transform,/10.03/,'Stale responses cannot pull the ghost backwards');
  const second=flushTimer();
  requests[1].reject(new Error('Server unavailable'));
  await second;
  assert.ok(shape(),'Network failure leaves the visible pointer preview in place');
  move(12.03,14.78);
  const third=flushTimer();
  requests[2].resolve({accepted:true,proposal:{x:12,y:14.75,angle:90,length:5.5,width:2.5}});
  await third;
  assert.equal(shape().attrs.fill,'#58b58f','Current policy response turns preview green');
  assert.match(nodes.get('placement-ghost').attrs.transform,/12 14.75/,'Confirmed geometry uses server snapping');
  move(24.03,26.48);
  const fourth=flushTimer();
  requests[3].resolve({accepted:false,reason:'collision:core_1',proposal:{x:24,y:26.5,angle:90,length:5.5,width:2.5}});
  await fourth;
  assert.equal(shape().attrs.fill,'#d86b57','Rejected geometry is visible in red');
  listeners.get('pointercancel')();
  assert.equal(nodes.get('placement-ghost'),undefined,'Cancellation removes the footprint');
  assert.equal(nodes.get('drag-token'),undefined,'Cancellation removes the cursor token');
  console.log('Preview regressions passed: immediate display, latency, stale responses, errors, policy feedback and cancellation');
})().catch(error=>{console.error(error);process.exitCode=1;});
