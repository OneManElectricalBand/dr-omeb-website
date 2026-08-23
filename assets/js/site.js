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

  document.querySelectorAll('.footer-links').forEach(footer => {
    if (!footer.querySelector('a[href="/terms/"]')) {
      const legal = document.createElement('a');
      legal.href = '/terms/';
      legal.textContent = 'Terms & Privacy';
      footer.appendChild(legal);
    }
  });

  document.querySelectorAll('.migration-form').forEach(form => {
    form.addEventListener('submit', e => e.preventDefault());
  });

  const badge = document.querySelector('[data-next-service]');
  if (badge) {
    const tz = 'America/New_York';
    const parts = new Intl.DateTimeFormat('en-US', {timeZone:tz,weekday:'short',hour:'numeric',hourCycle:'h23'}).formatToParts(new Date());
    const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const day = days.indexOf(parts.find(p => p.type === 'weekday').value);
    const hour = Number(parts.find(p => p.type === 'hour').value);
    const services = [{day:0,hour:9,label:'Sunday · 9:00 AM ET'},{day:2,hour:15,label:'Tuesday · 3:00 PM ET'},{day:4,hour:15,label:'Thursday · 3:00 PM ET'}];
    let next = null;
    services.forEach(s => {
      let deltaDays = (s.day - day + 7) % 7;
      if (deltaDays === 0 && hour >= s.hour + 4) deltaDays = 7;
      const score = deltaDays * 24 + (s.hour - hour);
      if (!next || score < next.score) next = {...s, score};
    });
    if (next) badge.textContent = `Next Service · ${next.label}`;
  }
})();
