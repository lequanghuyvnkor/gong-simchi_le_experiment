'use strict';
var currentView='home',presentationContent=null,talkMinutes=60;
var pageTitles={home:'Từ mô phỏng đến bằng chứng',lab:'Một ngày trong hệ thống tồn kho',stress:'Thiết kế và quan sát stress test',films:'Quy trình bốn mô hình qua diagram động',present:'Chuẩn bị bài trình bày thực nghiệm',learn:'Đọc đúng nguồn và phạm vi kết quả'};
function downloadFile(filename,content,type){var url=URL.createObjectURL(new Blob([content],{type:type}));var link=document.createElement('a');link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();setTimeout(function(){URL.revokeObjectURL(url);},1000);}
function navigate(view,writeHash){
  if(!pageTitles[view])view='home';stopAuto();stopStress();currentView=view;
  Object.keys(pageTitles).forEach(function(k){$(k+'-view').hidden=k!==view;});
  document.querySelectorAll('.nav').forEach(function(b){b.classList.toggle('active',b.dataset.view===view);b.setAttribute('aria-current',b.dataset.view===view?'page':'false');});
  $('page-title').textContent=pageTitles[view];document.title=pageTitles[view]+' · Inventory Research Hub';
  $('research-notes').hidden=view!=='learn';
  if(writeHash!==false&&location.hash!=='#'+view)history.replaceState(null,'','#'+view);
  document.querySelectorAll('video').forEach(function(v){if(!v.closest('#'+view+'-view')&&v.pause)v.pause();});
  if((view==='lab'||view==='stress')&&!worker)boot();
  if(view==='present'||view==='learn')loadPresentation();updateButtons();
}
function showModelVideo(model){$('video-dialog-title').textContent=labels[model]+' · sơ đồ quy trình';$('model-film').poster='./media/'+model+'.png';$('model-film-source').src='./media/'+model+'.mp4';$('model-film').load();$('video-dialog').showModal();}
document.querySelectorAll('.nav').forEach(function(button){button.onclick=function(){navigate(button.dataset.view);};});
document.addEventListener('click',function(e){var go=e.target.closest('[data-go]'),demo=e.target.closest('[data-demo]');if(go)navigate(go.dataset.go);if(demo){navigate('lab');selectModel(demo.dataset.demo);}});
$('model-video').onclick=function(){showModelVideo(kind);};
$('video-close').onclick=function(){$('video-dialog').close();};
$('video-dialog').addEventListener('close',function(){$('model-film').pause();});
window.addEventListener('hashchange',function(){navigate(location.hash.slice(1),false);});
function renderOutline(){if(!presentationContent)return;var outline=presentationContent.outlines.find(function(o){return o.minutes===talkMinutes;});$('talk-timeline').innerHTML=outline.segments.map(function(s){return '<div class="talk-segment"><div class="time">'+esc(s.time)+'</div><div><h3>Slide '+esc(s.slides)+'</h3><p>'+esc(s.task)+'</p><p class="closing">'+esc(s.closing)+'</p></div></div>';}).join('');document.querySelectorAll('[data-duration]').forEach(function(b){b.classList.toggle('active',Number(b.dataset.duration)===talkMinutes);b.setAttribute('aria-pressed',String(Number(b.dataset.duration)===talkMinutes));});}
async function loadPresentation(){
  if(presentationContent){renderOutline();return;}
  try{var response=await fetch('./resources/presentation.json');if(!response.ok)throw new Error('Không tải được nội dung báo cáo.');presentationContent=await response.json();renderOutline();
    $('present-checks').innerHTML=presentationContent.checklist.map(function(item,i){return '<label><input type="checkbox" data-present-check="'+i+'"><span>'+esc(typeof item==='string'?item:item.title)+((item.detail)?'<small class="report-caption" style="display:block">'+esc(item.detail)+'</small>':'')+'</span></label>';}).join('');
    $('present-qa').innerHTML=presentationContent.qa.map(function(q){var source=q.sources&&q.sources[0];return '<details><summary>'+esc(q.question)+'</summary><p>'+esc(q.answer)+'</p>'+(source?'<p class="footnote"><a target="_blank" rel="noreferrer" href="https://github.com/lequanghuyvnkor/gong-simchi_le_experiment/blob/main/'+esc(source.path)+'">Tra nguồn trong repo</a></p>':'')+'</details>';}).join('');
    $('evidence-messages').innerHTML=presentationContent.key_messages.map(function(m){var tag=presentationContent.evidence_labels.find(function(t){return t.id===m.evidence_type;});return '<article class="panel"><span class="pill">'+esc(tag?tag.label:m.evidence_type)+'</span><h3 style="margin-top:14px">'+esc(m.title)+'</h3><p>'+esc(m.body)+'</p><p class="footnote">'+m.sources.map(function(s){return '<a target="_blank" rel="noreferrer" href="https://github.com/lequanghuyvnkor/gong-simchi_le_experiment/blob/main/'+esc(s.path)+'">'+esc(s.path.split('/').pop()+(s.pointer?' · '+s.pointer:''))+'</a>';}).join(' · ')+'</p></article>';}).join('');
    $('research-direction').innerHTML=presentationContent.research_questions.map(function(q){return '<article class="module-card"><span class="module-tag">CÂU HỎI NGHIÊN CỨU</span><h3>'+esc(q.title)+'</h3><p>'+esc(q.question)+'</p><p class="footnote">'+esc(q.current_evidence)+'</p><p class="footnote"><b>Bước tiếp:</b> '+esc(q.next_step)+'</p></article>';}).join('');
  }catch(e){$('talk-timeline').textContent='Chưa tải được lộ trình. Bạn vẫn có thể đọc báo cáo và tải PDF/DOCX bên dưới.';}
}
document.querySelectorAll('[data-duration]').forEach(function(b){b.onclick=function(){talkMinutes=Number(b.dataset.duration);renderOutline();};});
document.querySelectorAll('[data-document]').forEach(function(b){b.onclick=function(){document.querySelectorAll('[data-document]').forEach(function(x){x.classList.toggle('active',x===b);});$('report-reader').src='./resources/'+b.dataset.document+'.html';$('report-reader').title=b.dataset.document==='presenter_playbook'?'Báo cáo hướng dẫn trình bày':'Kế hoạch stress test';};});
navigate(location.hash.slice(1)||'home',false);
