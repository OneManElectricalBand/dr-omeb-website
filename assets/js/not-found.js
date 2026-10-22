(() => {
  'use strict';
  const path = window.location.pathname;
  const message = document.getElementById('not-found-message');
  if (message && /^\/(?:event|go\/events)\//.test(path)) {
    message.textContent = 'This show listing is no longer available. Join the Congregation at Rock n\' Roll Church for the current live experience.';
  } else if (message && /^\/(?:blogs\/|blog\/blog\/|diary-of-a-rock-n-roll-doctor\/blog\/)/.test(path)) {
    message.textContent = 'This older article is no longer available at this address. Explore the current Diary of a Rock n\' Roll Doctor below.';
  }
  let referrerHost = '';
  try { referrerHost = document.referrer ? new URL(document.referrer).hostname : ''; } catch { /* An invalid referrer does not block the error page. */ }
  // No query strings, referrer paths, form values or email addresses in this event.
  window.gtag?.('event', 'page_not_found', {
    missing_path: path,
    referrer_host: referrerHost
  });
})();
