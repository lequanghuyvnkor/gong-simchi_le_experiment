'use strict';
var $ = function(id){return document.getElementById(id);};
var labels = {hql:'HQL',meta:'Meta-HQL',fql:'FQL',mimic:'Mimic-QL · bản học'};
var descriptions = {
  hql:'Một sản phẩm, hàng đến ngay. Tồn dư được ghi rồi reset cuối mỗi tập 3 ngày.',
  meta:'Một sản phẩm, hàng đến ngay. Kho thực giữ tồn khi đổi bản sao HQL.',
  fql:'Hai sản phẩm, giao sau 1 ngày, nhu cầu chưa đáp ứng thành nợ. Tập 3 ngày độc lập.',
  mimic:'Hai sản phẩm, kho thực liên tục. FQL ảo học theo khối J=6, nhu cầu lặp H=3.'
};
var scopes = {
  hql:'<p>Chọn mức tồn mục tiêu từ lưới nguyên 0–20. Bộ học HQL chỉ nhận doanh số riêng bị kiểm duyệt; nhu cầu thật chỉ dùng chấm chi phí.</p><p>Cuối ngày thứ ba: tính phí trên hàng dư, ghi số dư rồi reset tồn về 0. Giá mua, giá thanh lý và phí loại bỏ đều bằng 0 trong bản học.</p><p>Cận minh họa đổi hệ số để thấy tập ứng viên thu hẹp. Nó không mang bảo đảm lý thuyết của công thức cận gốc.</p>',
  meta:'<p>Ba bản sao HQL dịch pha chạy theo khối 1, 2, 4… episode. Khi chuyển, hệ thống có thể phải chờ đúng pha hoặc đợi tồn kho giảm.</p><p>Kho thực giữ hàng qua mọi ngày chờ và ranh giới episode ảo. Chỉ episode hoạt động hoàn tất mới cập nhật Q.</p><p>Cận thu hẹp nhanh và bảo vệ tập rỗng là quy ước của bản học, đã ghi trong mã nguồn.</p>',
  fql:'<p>Hai sản phẩm, chu kỳ nhu cầu 3 ngày; đơn mới đến ngày mai. Hàng về trả nợ cũ trước, sau đó phục vụ nhu cầu mới.</p><p>FQL quan sát nhu cầu đầy đủ. Cuối episode, nó cập nhật Q cho toàn bộ trạng thái/hành động trên lưới, theo thứ tự ngày 3, 2, 1.</p><p>Tồn, nợ và hàng đang về cuối ngày thứ ba được ghi lại; episode kế tiếp là một hợp đồng độc lập. Đây không phải hủy nợ miễn phí trong cửa hàng vận hành liên tục.</p>',
  mimic:'<p>Bản học dựa trên mô tả Mimic-QL của tác giả: FQL ảo chạy khối dài J=6, trong khi chu kỳ nhu cầu thật H=3. Cả hai hệ thống nhận cùng nhu cầu và cùng tiến thời gian.</p><p>Chỉ hệ ảo reset. Kho thực giữ toàn bộ tồn, nợ và hàng đang về. Lệnh bù được tính từ vị thế tồn (tồn ròng + pipeline) và lệnh ảo, rồi giới hạn bởi hạn mức lệnh mỗi sản phẩm.</p><p>Giới hạn lệnh và cách giải nghĩa công thức ghép là điều chỉnh minh họa, được xuất trong CSV. Chưa xác minh tương đương thuật toán công bố hoặc bảo đảm regret. Không đặt giới hạn giả rằng mọi lần đồng bộ đều xong trong một ngày.</p>'
};
var kind='hql', worker=null, ready=false, busy=false, auto=false, timer=null, seq=0;
var waiting=new Map(), views={hql:[],meta:[],fql:[],mimic:[]}, state=null, loadingTimer;
function esc(x){return String(x==null?'':x).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function fmt(x,n){return Number(x||0).toLocaleString('vi-VN',{minimumFractionDigits:n==null?2:n,maximumFractionDigits:n==null?2:n});}
function pair(x){return Array.isArray(x)?'A '+x[0]+' · B '+x[1]:String(x==null?'—':x);}
function setError(message){$('error').textContent=message||'';$('error').hidden=!message;}
function boot(){
  if(worker)worker.terminate();
  ready=false;busy=false;stopAuto();$('loading').hidden=false;$('retry').hidden=true;setError('');
  worker=new Worker('./engine.worker.js');
  clearTimeout(loadingTimer);
  loadingTimer=setTimeout(function(){$('loading-title').textContent='Bộ tính toán đang tải chậm';$('loading-detail').textContent='Bạn có thể xem sơ đồ video trong lúc chờ hoặc thử tải lại.';$('retry').hidden=false;},45000);
  worker.onmessage=function(event){
    var message=event.data;
    if(message.type==='progress'){$('loading-title').textContent=message.message;return;}
    if(message.type==='ready'){clearTimeout(loadingTimer);ready=true;$('loading').hidden=true;selectModel(kind);return;}
    if(message.type==='fatal'){clearTimeout(loadingTimer);$('loading-title').textContent='Chưa tải được bộ tính toán';$('loading-detail').textContent='Kiểm tra kết nối rồi thử lại. Các video diagram vẫn xem được.';$('retry').hidden=false;setError(message.message);return;}
    var p=waiting.get(message.id);if(!p)return;waiting.delete(message.id);
    if(message.type==='result')p.resolve(message.result);else p.reject(new Error(message.message));
  };
  worker.onerror=function(){setError('Bộ tính toán chưa sẵn sàng. Hãy thử tải lại.');$('retry').hidden=false;};
  updateButtons();
}
function request(payload){
  return new Promise(function(resolve,reject){if(!ready){reject(new Error('Bộ tính toán chưa tải xong.'));return;}var id=++seq;waiting.set(id,{resolve:resolve,reject:reject});worker.postMessage({id:id,payload:payload});});
}
function updateButtons(){
  var replay=state&&Number($('replay').value)!==state.day;
  $('step').disabled=!ready||busy||!state||state.finished||replay;
  $('auto').disabled=!ready||busy&&!auto||!state||state.finished||replay;
  $('q-show').disabled=!ready||busy||!state||!state.day||replay;
  $('export').disabled=!ready||busy||!state||!state.day;
  $('reset').disabled=!ready||busy;
  $('auto').textContent=auto?'Dừng tự chạy':'Tự chạy theo quyết định này';
  document.querySelectorAll('.model').forEach(function(b){b.disabled=busy;});
}
async function selectModel(next){
  if(busy)return;stopAuto();kind=next;setError('');
  document.querySelectorAll('.model').forEach(function(b){b.classList.toggle('active',b.dataset.model===kind);b.setAttribute('aria-pressed',String(b.dataset.model===kind));});
  $('model-badge').textContent=labels[kind];$('context-text').textContent=descriptions[kind];
  $('bound-setting').hidden=kind==='fql'||kind==='mimic';
  $('lost-controls').hidden=kind==='fql'||kind==='mimic';$('full-controls').hidden=kind==='hql'||kind==='meta';
  $('decision-description').textContent=kind==='hql'||kind==='meta'?'Chọn tổng hàng sẵn bán sau bổ sung.':'Chọn lượng đặt thêm cho từng sản phẩm.';
  $('q-phase').innerHTML=Array.from({length:kind==='mimic'?6:3},function(_,i){return '<option>'+(i+1)+'</option>';}).join('');
  $('q-action').max=kind==='hql'||kind==='meta'?20:kind==='fql'?15:8;
  $('q-detail').textContent='Chưa có episode hoàn tất. Q được phát lại từ trace đã lưu.';
  if(!ready){state=null;renderEmpty();return;}
  busy=true;updateButtons();
  try{var result=await request({op:'select',kind:kind});state=result;views[kind][result.day]=result;$('seed').value=result.seed;$('cycles').value=result.cycles;$('bounds').value=result.bounds;$('researcher').checked=result.researcher;$('replay').max=result.day;$('replay').value=result.day;render(result);syncControls();}
  catch(e){setError(e.message);}finally{busy=false;updateButtons();}
}
function syncControls(){
  if(!state)return;
  if(kind==='hql'||kind==='meta'){
    $('target').min=state.manual_opening;$('target').max=state.capacity;
    $('target').value=Math.min(state.capacity,Math.max(state.manual_opening,Number($('target').value)));
    $('target-min').textContent='Tồn hiện có: '+state.manual_opening;$('target-max').textContent='Sức chứa: '+state.capacity;
  }else{
    $('order-a').max=state.max_order[0];$('order-b').max=state.max_order[1];
    $('order-a').value=Math.min(Number($('order-a').value),state.max_order[0]);$('order-b').value=Math.min(Number($('order-b').value),state.max_order[1]);
    return;
  }
  $('target-value').textContent=$('target').value;$('order-preview').textContent=Math.max(0,Number($('target').value)-(state?state.manual_opening:3));
}
function stopAuto(){auto=false;clearTimeout(timer);if($('auto'))$('auto').textContent='Tự chạy theo quyết định này';}
async function step(){
  if(busy||!state||state.finished)return;
  busy=true;updateButtons();setError('');
  var action=kind==='hql'||kind==='meta'?Number($('target').value):[Number($('order-a').value),Number($('order-b').value)];
  try{var result=await request({op:'step',action:action});state=result;views[kind][result.day]=result;$('replay').max=result.day;$('replay').value=result.day;render(result);syncControls();pulse();if(result.finished)stopAuto();}
  catch(e){setError(e.message);stopAuto();}
  finally{busy=false;updateButtons();if(auto)timer=setTimeout(step,Number($('tempo').value));}
}
function renderEmpty(){diagram(null);$('day-badge').textContent='Chưa bắt đầu';$('step-summary').textContent='Chạy từng ngày để quan sát luồng hàng và phản hồi.';}
function render(s){
  $('flow-title').textContent='Luồng vận hành của '+labels[kind];
  $('day-badge').textContent='Ngày '+s.day+' / '+s.total_days;
  $('replay-day').textContent=s.day;
  $('live').disabled=!state||s.day===state.day;
  $('human-cost').textContent=fmt(s.sum_human);$('algorithm-cost').textContent=fmt(s.sum_algorithm);
  $('difference').textContent=fmt(s.sum_human-s.sum_algorithm);
  $('algorithm-cost-label').textContent=labels[kind].toUpperCase();
  $('cost-label').textContent=s.cost_label+' · đơn vị mô hình';
  $('status-note').textContent=kind==='meta'?(s.status.indexOf('wait')===0?'Đang chờ chuyển':'Đang chạy một bản HQL'):kind==='mimic'?(s.synchronized?'Hai trạng thái đang khớp':'Đang ghép hệ thực và hệ ảo'):s.label;
  diagram(s);chart(s);
  var a=s.algorithm,h=s.human;
  if(!a){$('step-summary').textContent='Thuật toán sẽ chốt quyết định trước khi nhu cầu của ngày xuất hiện.';}
  else if(kind==='hql'||kind==='meta'){
    var line='Thuật toán đặt thêm '+a.ordered+', bán '+a.sales+' và còn '+a.remaining+'. Bạn đặt thêm '+h.ordered+'.';
    if(a.discarded)line+=' Cuối tập: ghi '+a.discarded+' hàng dư rồi reset theo mô hình HQL.';
    if(kind==='meta'&&s.status.indexOf('wait')===0)line+=' Đây là ngày chờ chuyển; kho thực vẫn giữ hàng và không học từ ngày chờ.';
    $('step-summary').textContent=line;
  }else{
    var line2='Đơn mới '+pair(a.ordered)+' đến ngày mai. Cuối ngày: tồn '+pair(a.remaining)+'; nợ '+pair(a.backlog)+'.';
    if(kind==='fql'&&a.terminal)line2+=' Đã ghi số dư cuối hợp đồng; tập tiếp theo khởi tạo độc lập.';
    if(kind==='mimic'&&s.virtual_reset)line2+=' Hệ FQL ảo bắt đầu khối mới; kho thực giữ nguyên số dư.';
    if(kind==='mimic'&&s.limited.some(Boolean))line2+=' Yêu cầu bù vượt hạn mức: lệnh thực đã được giới hạn và ghi lại.';
    $('step-summary').textContent=line2;
  }
  updateButtons();
}
function node(x,y,w,h,title,value,style){
  return '<g><rect x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" rx="12" class="'+(style||'store')+'"/><text x="'+(x+14)+'" y="'+(y+25)+'" class="node-label">'+esc(title)+'</text><text x="'+(x+14)+'" y="'+(y+54)+'" class="node-value">'+esc(value)+'</text></g>';
}
function diagram(s){
  var a=s&&s.algorithm, full=kind==='fql'||kind==='mimic';
  var stock=a?pair(a.remaining):(s?pair(s.manual_opening):(full?'A 1 · B 1':'3'));
  var demand=a&&a.demand!=null?pair(a.demand):'Chưa quan sát';
  var sale=a?pair(a.sales):'—';
  var html='<svg viewBox="0 0 820 340" role="img" aria-label="Sơ đồ nhà cung cấp, kho, khách hàng và phản hồi cho bộ học"><defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10" fill="#78b5ca"/></marker></defs>';
  html+='<path class="edge" marker-end="url(#arrow)" d="M170 100 H300"/><path class="edge" marker-end="url(#arrow)" d="M510 100 H640"/><path class="signal" d="M715 150 V265 H510"/><path class="signal" d="M300 265 H90 V150"/>';
  html+=node(15,55,155,90,full?'Nhà cung cấp · trễ 1 ngày':'Nhà cung cấp · đến ngay',a?pair(a.ordered):'Chờ lệnh');
  html+=node(300,55,210,90,'Kho thực · tồn cuối ngày',stock);
  html+=node(640,55,165,90,'Khách hàng · nhu cầu',demand);
  html+='<text x="185" y="82" class="tiny">'+esc(full?'Đơn cho ngày mai':'Lượng bổ sung')+'</text><text x="540" y="82" class="tiny">Bán '+esc(sale)+'</text>';
  if(full){html+='<text x="308" y="171" class="tiny">Đang về: '+esc(a?pair(a.pipeline):'A 0 · B 0')+'</text><text x="648" y="171" class="tiny">Đơn nợ: '+esc(a?pair(a.backlog):'A 0 · B 0')+'</text>';}
  else html+='<text x="308" y="171" class="tiny">'+esc(kind==='hql'?'Reset kho cuối mỗi tập':'Giữ kho qua mọi ngày')+'</text><text x="648" y="171" class="tiny">Mất bán: '+esc(a&&a.lost!=null?a.lost:'bị kiểm duyệt')+'</text>';
  if(kind==='meta'&&s){
    s.arms.forEach(function(arm,i){var x=250+i*135;html+='<rect x="'+x+'" y="221" width="124" height="88" rx="9" fill="'+(arm.selected?'#fff1d8':'#f3f6f9')+'" stroke="'+(arm.alive?'#d8ba8e':'#dce3eb')+'"/><text x="'+(x+10)+'" y="244" class="tiny">HQL pha '+arm.arm+'</text><text x="'+(x+10)+'" y="268" class="tiny">'+arm.episodes+' tập · trần '+arm.entry_cap+'</text><text x="'+(x+10)+'" y="292" class="tiny">'+(arm.selected?'Đang được chọn':arm.alive?'Còn ứng viên':'Đã loại')+'</text>';});
  }else if(kind==='mimic'){
    html+=node(270,222,280,88,'FQL ảo · J=6',s&&s.virtual?pair(s.virtual.net):'A 0 · B 0','learner');
    html+='<text x="565" y="250" class="tiny">IP thực '+esc(s?pair(s.real_position):'—')+'</text><text x="565" y="274" class="tiny">IP ảo '+esc(s?pair(s.virtual_position):'—')+'</text><text x="565" y="298" class="tiny">'+esc(s&&s.virtual_reset?'Chỉ hệ ảo vừa reset':'Hai đồng hồ cùng tiến')+'</text>';
  }else{
    html+=node(300,222,210,88,full?'FQL · phản hồi đầy đủ':'HQL · doanh số riêng',s&&s.alpha?'α = '+fmt(s.alpha,3):'Thu thập episode','learner');
    html+='<text x="535" y="264" class="tiny">'+esc(full?'Quét Q từ pha cuối về đầu':'Mô phỏng ứng viên tồn thấp hơn')+'</text>';
  }
  html+='<circle r="5" class="packet"><animateMotion dur="2.4s" repeatCount="indefinite" path="M170 100 H300"/></circle><circle r="5" class="packet"><animateMotion dur="2.4s" begin=".8s" repeatCount="indefinite" path="M510 100 H640"/></circle><circle r="4" class="feedback-packet"><animateMotion dur="3s" repeatCount="indefinite" path="M715 150 V265 H510"/></circle></svg>';
  $('diagram').innerHTML=html;
  var svg=$('diagram').querySelector('svg');if(svg&&svg.pauseAnimations)svg.pauseAnimations();
}
function pulse(){var svg=$('diagram').querySelector('svg');if(!svg||window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;if(svg.unpauseAnimations)svg.unpauseAnimations();setTimeout(function(){if(svg.pauseAnimations)svg.pauseAnimations();},2200);}
function chart(s){
  var data=views[kind].filter(Boolean).filter(function(x){return x.day<=s.day;});
  if(data.length<2){$('cost-chart').innerHTML='<p class="empty">Chạy ngày đầu tiên để có điểm dữ liệu.</p>';return;}
  var all=data.flatMap(function(x){return [x.sum_human,x.sum_algorithm];}),lo=Math.min(0,Math.min.apply(null,all)),hi=Math.max.apply(null,all);
  if(hi===lo)hi=lo+1;
  var width=600,height=160,px=function(d){return 45+d.day/Math.max(1,s.day)*540;},py=function(v){return 140-(v-lo)/(hi-lo)*120;};
  var path=function(key){return data.map(function(d,i){return (i?'L':'M')+px(d).toFixed(2)+' '+py(d[key]).toFixed(2);}).join(' ');};
  $('cost-chart').innerHTML='<svg viewBox="0 0 '+width+' '+height+'" role="img" aria-label="Chi phí tích lũy của bạn và thuật toán"><path d="M45 20 V140 H585" fill="none" stroke="#dce5ee"/><path d="'+path('sum_human')+'" fill="none" stroke="#9aaebf" stroke-width="2.5"/><path d="'+path('sum_algorithm')+'" fill="none" stroke="#098ab7" stroke-width="3"/><text x="2" y="25" font-size="11" fill="#667e93">'+fmt(hi,0)+'</text><text x="2" y="142" font-size="11" fill="#667e93">'+fmt(lo,0)+'</text><text x="45" y="157" font-size="11" fill="#667e93">Ngày 0</text><text x="545" y="157" font-size="11" fill="#667e93">Ngày '+s.day+'</text><text x="380" y="17" font-size="11" fill="#7b91a3">Bạn</text><text x="450" y="17" font-size="11" fill="#0879ad">'+esc(labels[kind])+'</text></svg>';
}
async function showQ(){
  if(busy)return;busy=true;updateButtons();
  try{var q=await request({op:'q',phase:Number($('q-phase').value),action:Number($('q-action').value)});
    if(q.available_actions&&q.available_actions.length){$('q-action').value=q.available_actions[0];q=await request({op:'q',phase:Number($('q-phase').value),action:q.available_actions[0]});}
    if(q.message){$('q-detail').textContent=q.message;return;}
    $('q-detail').innerHTML='<div class="q-row"><span>Q cũ <b>'+fmt(q.old_q,4)+'</b></span><span>α <b>'+fmt(q.alpha,4)+'</b></span><span>Q mới <b>'+fmt(q.new_q,4)+'</b></span></div><p><code>Q mới = (1 − α) Q cũ + α (thưởng + V tiếp nối)</code></p><p>Ứng viên / lệnh '+esc(pair(q.action))+' · Thưởng '+fmt(q.reward,4)+' · V tiếp nối '+fmt(q.bootstrap,4)+(q.tau?' · τ='+q.tau:'')+'.</p><p class="footnote">Phát lại trace cập nhật đã lưu; thao tác này không học thêm.</p>';
  }catch(e){setError(e.message);}finally{busy=false;updateButtons();}
}
document.querySelectorAll('.model').forEach(function(b){b.addEventListener('click',function(){selectModel(b.dataset.model);});});
document.querySelectorAll('.nav').forEach(function(b){b.addEventListener('click',function(){stopAuto();document.querySelectorAll('.nav').forEach(function(x){x.classList.toggle('active',x===b);});['lab','films','learn'].forEach(function(v){$(v+'-view').hidden=v!==b.dataset.view;});});});
$('step').onclick=step;
$('auto').onclick=function(){if(auto){stopAuto();updateButtons();return;}auto=true;step();};
$('target').oninput=syncControls;
$('replay').oninput=function(){stopAuto();var view=views[kind][Number(this.value)];if(view)render(view);$('live').disabled=Number(this.value)===state.day;updateButtons();};
$('live').onclick=function(){if(state){$('replay').value=state.day;render(state);}};
$('q-show').onclick=showQ;
$('retry').onclick=boot;
$('scope-open').onclick=function(){$('scope-title').textContent=labels[kind]+' · quy ước';$('scope-body').innerHTML=scopes[kind];$('scope').showModal();};
$('scope-close').onclick=function(){$('scope').close();};
$('reset').onclick=async function(){
  if(busy)return;stopAuto();busy=true;updateButtons();setError('');
  try{var result=await request({op:'reset',kind:kind,options:{seed:Number($('seed').value),cycles:Number($('cycles').value),bounds:$('bounds').value,researcher:$('researcher').checked}});state=result;views[kind]=[];views[kind][0]=result;$('replay').max=0;$('replay').value=0;render(result);syncControls();$('q-detail').textContent='Lượt mới đã bắt đầu. Chưa có episode hoàn tất.';}
  catch(e){setError(e.message);}finally{busy=false;updateButtons();}
};
$('export').onclick=async function(){
  try{var result=await request({op:'export'});var url=URL.createObjectURL(new Blob([result.csv],{type:'text/csv;charset=utf-8'}));var a=document.createElement('a');a.href=url;a.download='inventory-'+kind+'-seed'+state.seed+'.csv';a.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);}catch(e){setError(e.message);}
};
var filmDescriptions={
  hql:'Nhu cầu bị kiểm duyệt, phản hồi một phía, cập nhật ngược và ranh giới episode.',
  meta:'Ba bản sao dịch pha, chuyển nhánh và kho thực giữ tồn trong ngày chờ.',
  fql:'Hai sản phẩm, đơn giao trễ, hàng về trả nợ và cập nhật Q cuối episode.',
  mimic:'Hai hệ thống cùng tiến: FQL ảo reset theo khối dài, kho thực ghép vị thế tồn với hạn mức lệnh.'
};
$('film-grid').innerHTML=Object.keys(labels).map(function(k){return '<article class="film"><video controls playsinline preload="metadata" poster="./media/'+k+'.png" aria-label="Sơ đồ động '+esc(labels[k])+'"><source src="./media/'+k+'.mp4" type="video/mp4">Trình duyệt chưa phát được video.</video><div class="film-body"><h3>'+esc(labels[k])+'</h3><p>'+esc(filmDescriptions[k])+'</p></div></article>';}).join('');
renderEmpty();boot();
