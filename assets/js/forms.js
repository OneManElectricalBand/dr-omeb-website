(() => {
  'use strict';
  const endpoint = 'https://dr-omeb-forms.onemanelectricalband.workers.dev';
  const forms = [...document.querySelectorAll('[data-omeb-form]')];
  if (!forms.length) return;
  let config;
  async function setup() {
    const response = await fetch(`${endpoint}/config`, {signal: AbortSignal.timeout(12000)});
    if (!response.ok) throw new Error();
    config = await response.json();
    if (!config.siteKey) throw new Error();
    await new Promise((resolve, reject) => {
      window.omebTurnstileReady = resolve;
      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=omebTurnstileReady&render=explicit';
      script.async = true; script.onerror = reject; document.head.append(script);
    });
    forms.forEach(form => {
      const kind = form.dataset.omebForm;
      const status = form.querySelector('[role="status"]');
      const button = form.querySelector('button[type="submit"]');
      if (!config[kind]) { status.textContent = 'This form is temporarily unavailable. Please email hello@onemanelectricalband.com.'; return; }
      let token = ''; let submitting = false;
      const widget = window.turnstile.render(form.querySelector('[data-turnstile]'), {
        sitekey: config.siteKey, action: kind, theme: 'dark', size: 'flexible',
        callback(value) { token = value; button.disabled = submitting; if (status.textContent.startsWith('Security check')) status.textContent = ''; },
        'expired-callback'() { token = ''; button.disabled = true; status.textContent = 'Security check expired. Please verify again.'; window.turnstile.reset(widget); },
        'error-callback'() { token = ''; button.disabled = true; status.textContent = 'Security check could not load. Please reload or email hello@onemanelectricalband.com.'; }
      });
      form.addEventListener('submit', async event => {
        event.preventDefault();
        if (submitting || !token || !form.reportValidity()) return;
        submitting = true; button.disabled = true; status.textContent = 'Sending…';
        const data = Object.fromEntries(new FormData(form));
        data.token = token; data.consent = form.elements.namedItem('consent')?.checked === true;
        try {
          const result = await fetch(`${endpoint}/${kind}`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),signal:AbortSignal.timeout(35000)});
          const payload = await result.json();
          status.textContent = payload.message || 'Please try again later.';
          if (result.ok) {
            form.reset();
            // The signup event records an accepted request; email confirmation happens later.
            window.gtag?.('event', kind === 'signup' ? 'newsletter_signup_requested' : 'contact_form_sent');
          }
        } catch { status.textContent = 'We couldn’t confirm delivery. Please try again later or email hello@onemanelectricalband.com.'; }
        finally { submitting = false; token = ''; window.turnstile.reset(widget); }
      });
    });
  }
  // A missing script must never turn a submission into an unprotected request.
  forms.forEach(form => form.addEventListener('submit', event => event.preventDefault()));
  setup().catch(() => forms.forEach(form => { form.querySelector('[role="status"]').textContent = 'The form could not load. Please reload or email hello@onemanelectricalband.com.'; }));
})();
