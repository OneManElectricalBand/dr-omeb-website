(() => {
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }));
  }

  document.querySelectorAll('[data-year]').forEach(el => el.textContent = new Date().getFullYear());

  document.querySelectorAll('.migration-form').forEach(form => {
    form.addEventListener('submit', e => e.preventDefault());
  });

  const badge = document.querySelector('[data-next-service]');
  if (badge) {
    const tz = 'America/New_York';
    const formatter = new Intl.DateTimeFormat('en-US', {timeZone: tz, weekday:'short', hour:'numeric', minute:'2-digit', hour12:true});
    const now = new Date();
    const schedules = [
      {day:0,hour:9,label:'Sunday Service'},
      {day:2,hour:15,label:'Midweek Service'},
      {day:4,hour:15,label:'Midweek Service'}
    ];
    const parts = new Intl.DateTimeFormat('en-US',{timeZone:tz,weekday:'short',hour:'numeric',hourCycle:'h23'}).formatToParts(now);
    const dayNames=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const today=dayNames.indexOf(parts.find(p=>p.type==='weekday').value);
    const hour=Number(parts.find(p=>p.type==='hour').value);
    let best=null;
    schedules.forEach(s=>{
      let days=(s.day-today+7)%7;
      if(days===0 && hour>=s.hour+4) days=7;
      const score=days*24+(s.hour-hour);
      if(!best || score<best.score) best={...s,score};
    });
    if(best){
      const date=new Date(now.getTime()+Math.max(0,best.score)*3600000);
      badge.textContent=`Next: ${best.label} · ${formatter.format(date)} ET`;
    }
  }
})();
