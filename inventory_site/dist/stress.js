'use strict';
var stressState=null,stressBusy=false,stressAuto=false,stressTimer=null,stressEpoch=0;
var stressScenarios={native:['Nhu cầu gốc','within','Phân phối theo pha của bản học; cường độ 1× giữ bộ sinh gốc.'],zero:['Không có nhu cầu','within','Đường cầu 0 để kiểm tra tồn dư và chi phí.'],steady:['Nhu cầu đều','within','Phân phối cố định qua các pha, vẫn lặp theo H=3.'],peak:['Đỉnh theo chu kỳ','within','Nhu cầu cao ở pha thứ hai, lặp đúng chu kỳ H=3.'],alternating:['Luân phiên hai ngày','outside','Chu kỳ 2 khác H=3: thử ngoài giả định lặp của mô hình.'],burst:['Bùng cầu rồi lắng','outside','Burst đầu đường chạy rồi lắng: phân phối không lặp theo pha.'],drift:['Đổi mức giữa chừng','outside','Nhu cầu đổi mức giữa chân trời: stress ngoài giả định.']};
var stressFields=['kind','scenario','seed','seeds','cycles','load','reference','capacity','holding','penalty','bounds','confidence'];
function normalizeStress(raw){
  if(!raw||typeof raw!=='object'||Array.isArray(raw))throw new Error('Cấu hình phải là một object JSON.');
  Object.keys(raw).forEach(function(k){if(!stressFields.includes(k))throw new Error('Trường chưa hỗ trợ: '+k);});
  var c=Object.assign({kind:'meta',scenario:'peak',seed:9000,seeds:3,cycles:6,load:1,reference:'phase',capacity:20,holding:1,penalty:4,bounds:'practical',confidence:1},raw);
  if(!labels[c.kind]||!stressScenarios[c.scenario]||!['fixed','phase'].includes(c.reference)||!['paper','practical'].includes(c.bounds))throw new Error('Mô hình, kịch bản hoặc baseline không hợp lệ.');
  [['seed',0,2147483643,true],['seeds',1,5,true],['cycles',1,20,true],['load',.25,2,false],['capacity',4,40,true],['holding',.1,10,false],['penalty',.1,20,false],['confidence',.25,4,false]].forEach(function(rule){var v=c[rule[0]];if(typeof v!=='number'||!Number.isFinite(v)||(rule[3]&&!Number.isSafeInteger(v))||v<rule[1]||v>rule[2])throw new Error(rule[0]+' ngoài miền ['+rule[1]+', '+rule[2]+'].');});
  if(c.kind==='fql'||c.kind==='mimic'){var defaults={bounds:'practical',confidence:1,capacity:20,holding:1,penalty:4};Object.keys(defaults).forEach(function(k){if(raw[k]!=null&&raw[k]!==defaults[k])throw new Error(k+' chỉ áp dụng cho HQL/Meta-HQL.');delete c[k];});}
  return c;
}
function readStressConfig(){
  var c={kind:$('stress-kind').value,scenario:$('stress-scenario').value,seed:readNumber('stress-seed','Seed',0,2147483643,true),seeds:readNumber('stress-seeds','Số seed',1,5,true),cycles:readNumber('stress-cycles','Số chu kỳ',1,20,true),load:readNumber('stress-load','Cường độ',.25,2,false),reference:$('stress-reference').value};
  if(c.kind==='hql'||c.kind==='meta')Object.assign(c,{capacity:readNumber('stress-capacity','Sức chứa',4,40,true),holding:readNumber('stress-holding','Phí giữ',.1,10,false),penalty:readNumber('stress-penalty','Phạt thiếu',.1,20,false),bounds:$('stress-bounds').value,confidence:readNumber('stress-confidence','Hệ số cận',.25,4,false)});
  return normalizeStress(c);
}
function stressSignature(c){return JSON.stringify(Object.keys(c).sort().map(function(k){return [k,c[k]];}));}
function stressDirty(){try{return !!stressState&&stressSignature(readStressConfig())!==stressSignature(stressState.config);}catch(e){return true;}}
function stressReplaying(){return stressState&&stressState.rows.length&&Number($('stress-replay').value)!==stressState.rows.length-1;}
function stopStress(){stressAuto=false;clearTimeout(stressTimer);updateStressButtons();}
function updateStressButtons(){
  var disabled=!ready||busy||stressBusy;
  $('stress-apply').disabled=disabled;
  $('stress-step').disabled=disabled||!stressState||stressState.finished||stressDirty()||stressReplaying();
  $('stress-auto').disabled=!ready||busy||(stressBusy&&!stressAuto)||!stressState||stressState.finished||stressDirty()||stressReplaying();
  $('stress-auto').textContent=stressAuto?'Tạm dừng':'Chạy toàn bộ';
  $('stress-json').disabled=$('stress-csv').disabled=disabled||!stressState||!stressState.completed;
  $('stress-replay').disabled=stressBusy||stressAuto||!stressState||!stressState.completed;
  $('stress-live').disabled=!stressReplaying();
  document.querySelectorAll('.stress-settings input,.stress-settings select').forEach(function(el){el.disabled=stressBusy;});
  $('stress-dirty').hidden=!stressDirty();
}
function stressDesign(){
  $('stress-lost-options').hidden=['fql','mimic'].includes($('stress-kind').value);
  $('stress-load-value').textContent=Number($('stress-load').value).toFixed(2)+'×';
  try{
    var c=readStressConfig(),scenario=stressScenarios[c.scenario],total=c.seeds*c.cycles*3;
    var nodes=[['Nguồn nhu cầu',scenario[0]+' · '+c.load+'×','stress-scenario'],['Mô hình',labels[c.kind]+' · H=3'+(c.kind==='mimic'?' · J=6':''),'stress-kind'],['Lặp ghép cặp',c.seeds+' seed · '+c.cycles*3+' ngày/seed','stress-seeds'],['Kiểm tra','Dòng hàng · chi phí · phản hồi','stress-reference'],['Kết quả',total+' bước · JSON / CSV','stress-cycles']];
    $('stress-design-flow').innerHTML=nodes.map(function(n){return '<button class="design-node" data-stress-focus="'+n[2]+'"><i></i><b>'+esc(n[0])+'</b><span>'+esc(n[1])+'</span></button>';}).join('');
    $('stress-scope').textContent=scenario[1]==='outside'?'Ngoài giả định':'Trong giả định';$('stress-scope').classList.toggle('outside',scenario[1]==='outside');
    $('stress-design-description').textContent=scenario[2]+(c.kind==='mimic'?' Bản học Mimic có hạn mức lệnh 2/SKU; chỉ hệ ảo reset.':'')+((c.kind==='fql'||c.kind==='mimic')?' Cường độ được chuyển thành xác suất trong support hữu hạn; không cắt ngọn một mẫu cầu.':'');
    $('stress-config-editor').value=JSON.stringify(c,null,2);
  }catch(e){$('stress-design-description').textContent=e.message;}
  updateStressButtons();
}
async function applyStress(){
  if(stressBusy||busy||!ready)return;stopStress();setError('');stressBusy=true;updateStressButtons();
  try{var result=await request({op:'stress_reset',config:readStressConfig()});stressState=result;renderStress(result);}
  catch(e){setError(e.message);}finally{stressBusy=false;updateStressButtons();}
}
async function stepStress(){
  if(stressBusy||!stressState||stressState.finished||stressDirty()||stressReplaying())return;
  stressBusy=true;updateStressButtons();setError('');var epoch=stressEpoch;
  try{var result=await request({op:'stress_step'});if(epoch!==stressEpoch)return;stressState=result;renderStress(result);if(result.finished)stopStress();}
  catch(e){setError(e.message);stopStress();}finally{stressBusy=false;updateStressButtons();if(stressAuto)stressTimer=setTimeout(stepStress,60);}
}
function renderStress(s){
  var percent=100*s.completed/s.total;
  $('stress-progress').setAttribute('aria-valuenow',String(Math.round(percent)));$('stress-progress').firstElementChild.style.width=percent+'%';
  $('stress-state').textContent=s.finished?'Hoàn tất '+s.total+' / '+s.total+' bước':s.completed+' / '+s.total+' bước';
  $('stress-empty').hidden=!!s.completed;$('stress-data').hidden=!s.completed;
  $('stress-result-label').textContent=labels[s.config.kind]+' · '+stressScenarios[s.config.scenario][0];
  var reference=s.rows.reduce(function(a,r){return a+r.reference_cost;},0),algorithm=s.rows.reduce(function(a,r){return a+r.learner_cost;},0);
  $('stress-ref-cost').textContent=fmt(reference);$('stress-alg-cost').textContent=fmt(algorithm);
  $('stress-difference').textContent=s.summary.mean_difference==null?'—':fmt(s.summary.mean_difference);
  $('stress-ci').textContent=s.summary.ci95?'CI 95% ['+fmt(s.summary.ci95[0])+', '+fmt(s.summary.ci95[1])+'] · '+s.summary.seeds_completed+' seed':'Cần ít nhất hai seed hoàn tất để có CI';
  var checkLabels={common_demand:'Cùng nhu cầu',finite_cost:'Chi phí hữu hạn',material_balance:'Cân bằng hàng',lost_sales_balance:'Cân bằng mất bán',learner_inventory:'Tồn learner',pipeline_and_cost:'Pipeline / chi phí',physical_never_resets:'Kho thực giữ số dư',virtual_clock:'Đồng hồ ảo'};
  $('stress-checks').innerHTML=Object.keys(s.checks).map(function(k){var c=s.checks[k];return '<span class="check-chip '+(c.passed<c.total?'failed':'')+'">'+esc(checkLabels[k]||k)+' · '+c.passed+'/'+c.total+'</span>';}).join('');
  $('stress-table').innerHTML=s.results.map(function(r){return '<tr><td>'+r.seed+'</td><td>'+fmt(r.reference_cost)+'</td><td>'+fmt(r.learner_cost)+'</td><td>'+fmt(r.difference)+'</td></tr>';}).join('');
  $('stress-replay').max=Math.max(0,s.rows.length-1);$('stress-replay').value=Math.max(0,s.rows.length-1);
  if(s.rows.length)renderStressRow(s.rows[s.rows.length-1]);
  updateStressButtons();
}
function renderStressRow(r){
  $('stress-replay-label').textContent='seed '+r.seed+' · ngày '+r.day;
  var nodes=[['Nguồn nhu cầu',pair(r.demand),'Mẫu đã quan sát'],['Lệnh thuật toán',pair(r.order),'Chốt trước nhu cầu'],['Kho thực',pair(r.stock),Array.isArray(r.backlog)?'Nợ '+pair(r.backlog)+' · đang về '+pair(r.pipeline):'Mất bán '+r.lost],['Chi phí ngày',fmt(r.learner_cost),'Đơn vị mô hình']];
  if(r.virtual)nodes.push(['FQL ảo',pair(r.virtual.net),r.virtual_reset?'Chỉ hệ ảo vừa reset':'Hệ thực và ảo cùng tiến']);
  $('stress-live-flow').innerHTML=nodes.map(function(n,i){return '<div class="'+(i===4?'virtual-node':'')+'"><b>'+esc(n[0])+'</b><strong>'+esc(n[1])+'</strong><small>'+esc(n[2])+'</small></div>';}).join('');
  document.querySelectorAll('.design-node').forEach(function(n,i){n.classList.toggle('active',i===4);});
}
function setStressForm(raw){
  var c=normalizeStress(raw);
  stressFields.forEach(function(k){if(c[k]!=null)$('stress-'+k).value=c[k];});
  stopStress();stressDesign();
}
document.querySelectorAll('.stress-settings input,.stress-settings select').forEach(function(el){el.addEventListener('input',function(){stopStress();stressDesign();});el.addEventListener('change',function(){stopStress();stressDesign();});});
$('stress-design-flow').addEventListener('click',function(e){var n=e.target.closest('[data-stress-focus]');if(!n)return;var field=$(n.dataset.stressFocus);if(field){field.focus();if(field.scrollIntoView)field.scrollIntoView({block:'center',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}});
$('stress-apply').onclick=applyStress;$('stress-step').onclick=stepStress;
$('stress-auto').onclick=function(){if(stressAuto){stopStress();return;}stressAuto=true;stepStress();};
async function exportStress(type){if(stressBusy)return;stressBusy=true;updateStressButtons();try{var r=await request({op:'stress_export'});downloadFile('stress-'+stressState.config.kind+'-seed'+stressState.config.seed+'.'+type,type==='json'?JSON.stringify(r.report,null,2):r.csv,type==='json'?'application/json':'text/csv;charset=utf-8');}catch(e){setError(e.message);}finally{stressBusy=false;updateStressButtons();}}
$('stress-json').onclick=function(){exportStress('json');};$('stress-csv').onclick=function(){exportStress('csv');};
$('stress-save-config').onclick=function(){try{downloadFile('stress-design.json',JSON.stringify(readStressConfig(),null,2),'application/json');}catch(e){setError(e.message);}};
$('stress-import').onclick=function(){try{var d=JSON.parse($('stress-config-editor').value);setStressForm(d.config||(d.report&&d.report.config)||d);setError('');}catch(e){setError('Không nạp được cấu hình: '+e.message);}};
$('stress-file').onchange=async function(){try{if(!this.files.length)return;if(this.files[0].size>2000000)throw new Error('Tệp cấu hình vượt 2 MB.');var d=JSON.parse(await this.files[0].text());setStressForm(d.config||(d.report&&d.report.config)||d);setError('');}catch(e){setError('Không đọc được tệp: '+e.message);}finally{this.value='';}};
$('stress-replay').oninput=function(){stopStress();if(stressState&&stressState.rows[this.value])renderStressRow(stressState.rows[this.value]);updateStressButtons();};
$('stress-live').onclick=function(){if(stressState&&stressState.rows.length){$('stress-replay').value=stressState.rows.length-1;renderStressRow(stressState.rows[stressState.rows.length-1]);updateStressButtons();}};
document.addEventListener('engine:status',updateStressButtons);
document.addEventListener('engine:reset',function(){stressEpoch++;stopStress();stressState=null;stressBusy=false;$('stress-state').textContent='Chưa áp dụng thiết kế';$('stress-data').hidden=true;$('stress-empty').hidden=false;$('stress-progress').firstElementChild.style.width='0%';$('stress-progress').setAttribute('aria-valuenow','0');updateStressButtons();});
stressDesign();
