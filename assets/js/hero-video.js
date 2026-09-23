(() => {
  'use strict';
  const video = document.querySelector('#hero-video');
  const button = document.querySelector('.hero-motion');
  if (!video || !button) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const update = () => { button.textContent = video.paused ? 'Play video' : 'Pause video'; };
  const play = async () => {
    if (!video.getAttribute('src')) {
      video.src = window.matchMedia('(max-width: 760px)').matches
        ? video.dataset.mobileSrc : video.dataset.desktopSrc;
    }
    try { await video.play(); } catch { /* Keep the poster and manual play control. */ }
    update();
  };
  button.hidden = false;
  button.addEventListener('click', () => { if (video.paused) play(); else video.pause(); });
  video.addEventListener('play', update);
  video.addEventListener('pause', update);
  video.addEventListener('error', () => {
    video.pause();
    video.removeAttribute('src');
    video.load();
    update();
  });
  reducedMotion.addEventListener('change', event => { if (event.matches) video.pause(); });
  if (!reducedMotion.matches && !navigator.connection?.saveData) play();
})();
