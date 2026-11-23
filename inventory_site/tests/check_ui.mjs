/* DOM component integration with the real Python cores. No browser automation.
 * This verifies handlers and state; it makes no visual or browser-CDN claim.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import readline from 'node:readline';
import vm from 'node:vm';
import {JSDOM,VirtualConsole} from 'jsdom';

const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const virtualConsole=new VirtualConsole();
const errors=[];virtualConsole.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(await fs.readFile(path.join(site,'dist/index.html'),'utf8'),{url:'https://inventory.example/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole});
const w=dom.window,d=w.document,workers=[],downloads=[],blobs=new Map();
let narrow=false;
w.matchMedia=q=>({matches:q.includes('max-width')?narrow:false,addEventListener(){},removeEventListener(){}});
w.HTMLElement.prototype.scrollIntoView=function(){};
w.HTMLMediaElement.prototype.pause=function(){};w.HTMLMediaElement.prototype.load=function(){};
w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'));};
w.URL.createObjectURL=blob=>{const id='blob:'+blobs.size;blobs.set(id,blob);return id;};w.URL.revokeObjectURL=()=>{};
w.HTMLAnchorElement.prototype.click=function(){downloads.push({name:this.download,blob:blobs.get(this.href)});};
w.fetch=async url=>{const p=path.join(site,'dist',String(url).replace(/^\.\//,''));return {ok:true,json:async()=>JSON.parse(await fs.readFile(p,'utf8')),text:async()=>fs.readFile(p,'utf8')};};
class NativeWorker{
  constructor(){this.terminated=false;this.drop=false;this.child=spawn(process.env.PYTHON||'python',['-u',path.join(site,'tests/bridge.py')],{stdio:['pipe','pipe','pipe']});workers.push(this);readline.createInterface({input:this.child.stdout}).on('line',line=>{if(!this.terminated&&this.onmessage)this.onmessage({data:JSON.parse(line)});});this.child.stderr.on('data',b=>errors.push(b.toString()));this.child.on('error',e=>{if(!this.terminated&&this.onerror)this.onerror(e);});}
  postMessage(message){if(!this.drop)this.child.stdin.write(JSON.stringify(message)+'\n');}
  terminate(){this.terminated=true;this.child.kill();}
  fail(){this.drop=true;this.onerror(new Error('test worker failure'));}
}
w.Worker=NativeWorker;
const el=id=>{const found=d.getElementById(id);assert.ok(found,id);return found;};
const wait=async(predicate,label)=>{const end=Date.now()+10000;while(Date.now()<end){if(predicate())return;await new Promise(r=>setTimeout(r,10));}throw new Error('Timed out: '+label+'; '+el('error').textContent);};
const click=async id=>{el(id).click();await new Promise(r=>setTimeout(r,0));};
const value=(id,v)=>{el(id).value=String(v);el(id).dispatchEvent(new w.Event('input',{bubbles:true}));};
const checks=[];
try{
  for(const name of ['app.js','stress.js','slides.js','hub.js'])new vm.Script(await fs.readFile(path.join(site,'dist',name),'utf8'),{filename:name}).runInContext(dom.getInternalVMContext());
  assert.equal(workers.length,0);assert.equal(el('home-view').hidden,false);checks.push('home is usable without loading Python');
  w.navigate('lab');await wait(()=>!el('step').disabled,'lab boot');
  for(let day=1;day<=3;day++){await click('step');await wait(()=>el('day-badge').textContent.startsWith('Ngày '+day+' /')&&!el('step').disabled,'HQL day '+day);}
  await click('q-show');await wait(()=>el('q-detail').textContent.includes('Q cũ'),'Q trace');
  value('replay',0);assert.equal(el('step').disabled,true);assert.match(el('day-badge').textContent,/Ngày 0 /);await click('live');assert.equal(el('step').disabled,false);
  value('seed',1.5);await click('reset');await wait(()=>!w.busy,'invalid config');assert.match(el('error').textContent,/Seed/);assert.equal(w.state.day,3);value('seed',42);
  await click('export');await wait(()=>downloads.length===1&&!w.busy,'CSV export');assert.equal(downloads[0].name,'inventory-hql-seed42.csv');checks.push('HQL step/Q/replay/config validation/CSV');
  for(const kind of ['meta','fql','mimic']){
    await w.selectModel(kind);assert.equal(w.state.kind,kind);
    for(let i=0;i<6;i++){await click('step');await wait(()=>!w.busy&&w.state.day===i+1,kind+' step');}
    await click('q-show');await wait(()=>!w.busy,kind+' Q');assert.equal(el('error').hidden,true);
  }
  await w.selectModel('hql');assert.equal(w.state.day,3);checks.push('all four models, Q and independent retained sessions');
  narrow=true;w.dispatchEvent(new w.Event('resize'));assert.ok(el('diagram').querySelector('.mobile-system'));assert.match(el('diagram').textContent,/Nhà cung cấp/);assert.equal(el('diagram').querySelector('svg'),null);narrow=false;w.dispatchEvent(new w.Event('resize'));assert.ok(el('diagram').querySelector('svg'));checks.push('responsive diagram branch switches without changing learner');
  w.navigate('stress');value('stress-cycles',1);value('stress-seeds',2);await click('stress-apply');await wait(()=>w.stressState&&!w.stressBusy,'stress apply');assert.equal(el('stress-step').disabled,false);
  await click('stress-auto');await wait(()=>w.stressState.finished&&!w.stressBusy,'stress completion');assert.equal(w.stressState.completed,6);assert.equal(w.stressState.failures.length,0);assert.ok(w.stressState.summary.ci95);assert.equal(el('stress-table').children.length,2);
  const old=JSON.stringify(w.stressState);value('stress-replay',0);assert.match(el('stress-replay-label').textContent,/ngày 1/);assert.equal(JSON.stringify(w.stressState),old);await click('stress-live');
  value('stress-scenario','drift');assert.equal(el('stress-dirty').hidden,false);assert.match(el('stress-scope').textContent,/Ngoài/);assert.equal(JSON.stringify(w.stressState),old);assert.equal(el('stress-step').disabled,true);checks.push('stress diagram/config/actual Python run/CI/replay/dirty-design separation');
  el('stress-config-editor').value='{"kind":"mimic","cycles":1,"seeds":1,"scenario":"zero"}';await click('stress-import');assert.equal(el('stress-kind').value,'mimic');assert.equal(el('stress-lost-options').hidden,true);await click('stress-apply');await wait(()=>w.stressState.config.kind==='mimic'&&!w.stressBusy,'Mimic config import');await click('stress-step');await wait(()=>w.stressState.completed===1&&!w.stressBusy,'Mimic stress step');assert.match(el('stress-live-flow').textContent,/FQL ảo/);
  const count=downloads.length;await click('stress-json');await wait(()=>downloads.length>count&&!w.stressBusy,'stress JSON export');assert.match(downloads.at(-1).name,/stress-mimic/);w.navigate('lab');assert.equal(w.state.day,3);checks.push('Mimic virtual diagram, result export and isolation from manual lab');
  w.navigate('present');await wait(()=>el('present-qa').children.length===10,'presentation content');assert.equal(el('present-checks').querySelectorAll('input').length,8);assert.ok(el('present-checks').textContent.includes('Gắn nhãn'));
  assert.equal(el('research-direction').children.length,3);assert.equal(el('evidence-messages').children.length,6);
  d.querySelector('[data-duration="40"]').click();assert.match(el('talk-timeline').textContent,/38:00/);d.querySelector('[data-document="stress_test_plan"]').click();assert.match(el('report-reader').src,/stress_test_plan.html/);checks.push('presentation outline, checklist, Q&A, report reader and download links');
  w.navigate('slides');await wait(()=>w.slideDeck!==null,'slide deck');assert.equal(w.slideDeck.count,38);assert.equal(el('deck-thumbnails').children.length,38);assert.equal(el('deck-counter').textContent,'1 / 38');assert.equal(el('deck-prev').disabled,true);
  await click('deck-next');assert.equal(el('deck-counter').textContent,'2 / 38');
  el('deck-stage').dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));assert.equal(w.slideIndex,2);
  el('deck-stage').dispatchEvent(new w.KeyboardEvent('keydown',{key:'End',bubbles:true}));assert.equal(w.slideIndex,37);assert.equal(el('deck-next').disabled,true);
  el('deck-select').value=19;el('deck-select').dispatchEvent(new w.Event('change'));assert.match(el('deck-title').textContent,/Online Learning/);assert.match(el('deck-image').src,/slide_20.webp/);
  el('deck-thumbnails').querySelector('[data-slide-index="0"]').click();assert.equal(w.slideIndex,0);
  await click('deck-zoom');assert.equal(el('deck-stage').classList.contains('zoomed'),true);
  await click('deck-fullscreen');assert.equal(el('deck-shell').classList.contains('presentation-mode'),true);
  el('deck-stage').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));assert.equal(el('deck-shell').classList.contains('presentation-mode'),false);
  assert.equal(w.state.day,3);checks.push('38-slide viewer, selection/thumbnails, keyboard navigation, zoom and presentation-mode escape');
  w.navigate('lab');el('step').click();workers.at(-1).fail();await wait(()=>!w.busy&&!w.ready,'worker failure');assert.equal(el('retry').hidden,false);assert.equal(el('step').disabled,true);assert.equal(w.waiting.size,0);
  await click('retry');await wait(()=>w.ready&&w.state&&w.state.day===0&&!w.busy,'worker retry');assert.equal(w.stressState,null);assert.equal(el('human-cost').textContent,'0,00');checks.push('worker crash releases pending requests; clean restart resets all sessions');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({status:'passed',scope:'DOM component integration with real native Python; not browser visual QA',checks:checks.length,details:checks},null,2));
}finally{for(const worker of workers)worker.terminate();w.close();}
