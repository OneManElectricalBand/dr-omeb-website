(() => {
const root=document.getElementById('church-preview');
const rooms={arrival:{image:'/assets/church/58822f13c94d.webp',kicker:'The doors are open',title:'Your Sunday plans just got louder.',description:'Classic rock, guitar solos, requests, and a room full of people who get it. Explore the Church, then join Dr. OMEB live on Sunday.',action:'Watch on TikTok ↗',url:'https://www.tiktok.com/@onemanelectricalband',caption:'Explore the Church · Choose a destination in the room or below.'},stage:{image:'/assets/church/9ee0d912b6d3.webp',kicker:'Front and center',title:'Rainbow in the Dark',description:'Dr. OMEB takes on the guitar solo. Take your seat and turn it up.',action:'Play clip on YouTube ↗',url:'https://www.youtube.com/shorts/AO9CQCGRBno',caption:'The stage · Sound and playback controls are below the room.'},merch:{image:'/assets/church/673f41cd408a.webp',kicker:'Wear it loud',title:'The official merch booth.',description:'Dr. OMEB and Rock n’ Roll Church gear. Select a hanging shirt to open its official product page.',action:'Shop official merch ↗',url:'https://onemanelectricalband.com/merch/',caption:'Merch booth · Select a shirt to shop.'},backstage:{image:'/assets/church/e619eb63414b.webp',kicker:'Recent releases & music videos',title:'Turn it up backstage.',description:'Watch Symptom of the Universe, Close My Eyes Forever, You Took the Words Right Out of My Mouth, and Sign of the Times. Select a cover or a song below to watch on YouTube.',action:'Watch Symptom of the Universe ↗',url:'https://youtu.be/z1HqOYG-p-o',caption:'Backstage · Select a cover to watch the music video on YouTube.'},lounge:{image:'/assets/church/82abf485ba1c.webp',kicker:'You belong here',title:'Join the Congregation.',description:'Sunday reminders, new music, and news from Dr. OMEB. No spam. No altar call. Just rock.',action:'Join the mailing list ↗',url:'https://onemanelectricalband.com/#congregation',caption:'The Congregation · Your place in Rock n’ Roll Church.'}};
const image=root.querySelector('#church-room-image');
const v=root.querySelector('#performance');
const sound=root.querySelector('#sound-button'), pause=root.querySelector('#pause-button'), status=root.querySelector('#playback-status');
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let request=0, userPaused=reduced, soundEnabled=false;
root.dataset.room='arrival';
function track(name,params){if(window.gtag)window.gtag('event',name,params);}
root.querySelector('#church-menu').addEventListener('click',event=>{
 const open=root.querySelector('#church-main-links').classList.toggle('open');
 event.currentTarget.setAttribute('aria-expanded',String(open));event.currentTarget.textContent=open?'✕ Close':'☰ Menu';
});
function update(){sound.textContent=v.muted?'Sound off · Enable sound':'Sound on · Mute';sound.setAttribute('aria-pressed',String(!v.muted));pause.textContent=v.paused?'Play video':'Pause video';}
function play(){if(!v.getAttribute('src'))v.src=v.dataset.src;const p=v.play();if(p)p.then(()=>{status.textContent='';update();}).catch(()=>{status.textContent='Tap Play video to start.';update();});}
function setPlayback(key){const visible=key==='arrival'||key==='stage';root.querySelector('.playback').hidden=!visible;v.muted=!(soundEnabled&&key==='stage');if(visible&&!userPaused)play();else v.pause();update();}
sound.addEventListener('click',()=>{soundEnabled=v.muted;v.muted=!soundEnabled;userPaused=false;play();update();});
pause.addEventListener('click',()=>{userPaused=!v.paused;if(userPaused)v.pause();else play();update();});
v.addEventListener('play',update);v.addEventListener('pause',update);
v.addEventListener('error',()=>{status.textContent='Clip unavailable here. Use the YouTube link below.';update();});
root.querySelectorAll('button[data-room]').forEach(button=>button.addEventListener('click',async()=>{
 const key=button.dataset.room,r=rooms[key],token=++request;
 root.querySelector('.scene').setAttribute('aria-busy','true');
 const next=new Image();next.src=r.image;
 try{await next.decode();}catch(e){if(token===request){status.textContent='Room image could not load. Please try again.';root.querySelector('.scene').removeAttribute('aria-busy');}return;}
 if(token!==request)return;
 image.src=r.image;image.alt=r.title;root.dataset.room=key;
 root.querySelector('.scene').removeAttribute('aria-busy');
 root.querySelector('#church-hotspots').hidden=key!=='arrival';
 root.querySelector('#product-links').hidden=key!=='merch';root.querySelector('#shop-list').hidden=key!=='merch';root.querySelector('#art-links').hidden=key!=='backstage';
 ['kicker','title','description','caption'].forEach(field=>root.querySelector('#church-'+field).textContent=r[field]);
 const a=root.querySelector('#church-action');a.textContent=r.action;
 a.href=r.url.replace('https://onemanelectricalband.com','');
 if(a.getAttribute('href').startsWith('/')){a.removeAttribute('target');a.removeAttribute('rel');}else{a.target='_blank';a.rel='noopener';}
 root.querySelectorAll('.nav button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.room===key)));
 setPlayback(key);track('church_room_view',{room_name:key});
}));
root.addEventListener('click',e=>{const a=e.target.closest('a');if(a)track('church_link_click',{link_url:a.href,link_text:a.textContent.trim()||a.getAttribute('aria-label'),room_name:root.dataset.room});});
update();
if(!reduced){const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){setPlayback(root.dataset.room);observer.disconnect();}},{threshold:.1});observer.observe(root.querySelector('.scene'));}
})();