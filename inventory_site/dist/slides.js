'use strict';
var slideDeck=null,slideDeckPromise=null,slideIndex=0,slideZoom=false;
function deckButtons(){
  var available=!!slideDeck;
  $('deck-prev').disabled=!available||slideIndex===0;$('deck-next').disabled=!available||slideIndex===slideDeck.slides.length-1;
  ['deck-select','deck-zoom','deck-fullscreen'].forEach(function(id){$(id).disabled=!available;});
}
function showSlide(index){
  if(!slideDeck)return;
  slideIndex=Math.min(Math.max(index,0),slideDeck.slides.length-1);
  var slide=slideDeck.slides[slideIndex],img=$('deck-image');
  $('deck-loading').hidden=false;$('deck-loading').textContent='Đang tải slide '+slide.number+'…';
  img.alt='Slide '+slide.number+': '+slide.title;img.src=slide.image;img.hidden=false;
  $('deck-counter').textContent=slide.number+' / '+slideDeck.count;$('deck-select').value=slideIndex;
  $('deck-title').textContent=slide.title;$('deck-text-content').textContent=slide.text;
  document.querySelectorAll('[data-slide-index]').forEach(function(button){var selected=Number(button.dataset.slideIndex)===slideIndex;button.classList.toggle('active',selected);button.setAttribute('aria-current',selected?'page':'false');});
  deckButtons();
  // Warm only the adjacent slide; the rest of the deck stays lazy.
  if(slideIndex+1<slideDeck.count){var next=new Image();next.src=slideDeck.slides[slideIndex+1].image;}
}
async function loadSlides(){
  if(slideDeck){showSlide(slideIndex);return slideDeck;}
  if(slideDeckPromise)return slideDeckPromise;
  $('deck-retry').hidden=true;$('deck-loading').hidden=false;
  slideDeckPromise=(async function(){
    try{
      var response=await fetch('./resources/slides_manifest.json');
      if(!response.ok)throw new Error('Không tải được danh mục slide.');
      var deck=await response.json();
      if(!deck.slides||!deck.count||deck.slides.length!==deck.count)throw new Error('Danh mục slide không hợp lệ.');
      slideDeck=deck;
      $('deck-select').innerHTML=deck.slides.map(function(slide,i){return '<option value="'+i+'">'+slide.number+'. '+esc(slide.title)+'</option>';}).join('');
      $('deck-thumbnails').innerHTML=deck.slides.map(function(slide,i){return '<button class="deck-thumb" data-slide-index="'+i+'" aria-label="Mở slide '+slide.number+': '+esc(slide.title)+'"><img src="'+esc(slide.thumbnail)+'" alt="" loading="lazy" width="240" height="135"><span>'+slide.number+'. '+esc(slide.title)+'</span></button>';}).join('');
      showSlide(slideIndex);return deck;
    }catch(e){$('deck-loading').textContent='Chưa tải được slide. Bạn có thể thử lại hoặc mở bản PDF.';$('deck-status').textContent=e.message;$('deck-retry').hidden=false;slideDeckPromise=null;return null;}
  })();
  return slideDeckPromise;
}
function setDeckZoom(on){slideZoom=on;$('deck-stage').classList.toggle('zoomed',on);$('deck-zoom').textContent=on?'Vừa khung':'Phóng to';$('deck-zoom').setAttribute('aria-pressed',String(on));}
async function closeDeckPresentation(){
  if(document.fullscreenElement===$('deck-shell')&&document.exitFullscreen){try{await document.exitFullscreen();}catch(e){/* CSS presentation can still close. */}}
  $('deck-shell').classList.remove('presentation-mode');$('deck-exit').hidden=true;$('deck-fullscreen').textContent='Toàn màn hình';$('deck-status').textContent='';
}
async function presentDeck(){
  var shell=$('deck-shell');
  if(shell.classList.contains('presentation-mode')){await closeDeckPresentation();return;}
  setDeckZoom(false);shell.classList.add('presentation-mode');$('deck-exit').hidden=false;$('deck-fullscreen').textContent='Thoát toàn màn hình';
  $('deck-status').textContent='Phím trái/phải để chuyển · Esc để thoát';
  if(shell.requestFullscreen){try{await shell.requestFullscreen();}catch(e){$('deck-status').textContent='Trình chiếu trong tab · Esc để thoát';}}
  else $('deck-status').textContent='Trình chiếu trong tab · Esc để thoát';
  $('deck-stage').focus();
}
$('deck-prev').onclick=function(){showSlide(slideIndex-1);};$('deck-next').onclick=function(){showSlide(slideIndex+1);};
$('deck-select').onchange=function(){showSlide(Number(this.value));};
$('deck-thumbnails').onclick=function(event){var button=event.target.closest('[data-slide-index]');if(button)showSlide(Number(button.dataset.slideIndex));};
$('deck-zoom').onclick=function(){setDeckZoom(!slideZoom);};$('deck-fullscreen').onclick=presentDeck;$('deck-exit').onclick=closeDeckPresentation;
$('deck-retry').onclick=loadSlides;
$('deck-image').onload=function(){$('deck-loading').hidden=true;};
$('deck-image').onerror=function(){$('deck-loading').hidden=false;$('deck-loading').textContent='Chưa tải được ảnh slide. Hãy chọn lại slide hoặc mở PDF.';};
document.addEventListener('keydown',function(event){
  var deck=$('deck-shell'),withinDeck=$('slides-view').contains(event.target),presenting=deck.classList.contains('presentation-mode');
  if(typeof currentView==='undefined'||currentView!=='present'||!slideDeck||(!withinDeck&&!presenting)||event.ctrlKey||event.metaKey||event.altKey)return;
  if(event.key==='Escape'){closeDeckPresentation();return;}
  if(event.target.closest&&event.target.closest('input,select,textarea,[contenteditable="true"]'))return;
  if(['ArrowRight','PageDown'].includes(event.key)){event.preventDefault();showSlide(slideIndex+1);}
  if(['ArrowLeft','PageUp'].includes(event.key)){event.preventDefault();showSlide(slideIndex-1);}
  if(event.key==='Home'){event.preventDefault();showSlide(0);}
  if(event.key==='End'){event.preventDefault();showSlide(slideDeck.count-1);}
});
document.addEventListener('fullscreenchange',function(){if(!document.fullscreenElement&&$('deck-shell').classList.contains('presentation-mode'))closeDeckPresentation();});
deckButtons();
