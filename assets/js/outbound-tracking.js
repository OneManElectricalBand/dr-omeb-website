(() => {
  'use strict';
  const musicHosts = new Set(['open.spotify.com', 'music.apple.com', 'music.amazon.com', 'www.youtube.com', 'youtube.com', 'youtu.be']);
  document.addEventListener('click', event => {
    const link = event.target.closest?.('a[href]');
    if (!link) return;
    let destination;
    try { destination = new URL(link.href, window.location.href); } catch { return; }
    if (!['https:', 'http:'].includes(destination.protocol)) return;
    const host = destination.hostname;
    const merch = host === 'curryink.com' || host === 'www.curryink.com';
    if (!merch && !musicHosts.has(host)) return;
    window.gtag?.('event', merch ? 'merch_outbound_click' : 'music_outbound_click', {
      destination_host: host,
      destination_path: destination.pathname,
      source_path: window.location.pathname
    });
  });
})();
