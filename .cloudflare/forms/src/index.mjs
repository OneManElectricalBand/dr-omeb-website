const ORIGINS = new Set(['https://dr-omeb-website.pages.dev', 'https://onemanelectricalband.com', 'https://www.onemanelectricalband.com']);
const REASONS = new Set(['Booking', 'Press / Interview', 'Collaboration', "Rock n' Roll Church", 'General']);
const EMAIL = /^[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+$/;
const MAX_BODY = 16384;
class FormError extends Error { constructor(status, message) { super(message); this.status = status; } }
function field(body, key, max, required = false) {
  const value = body[key] ?? '';
  if (typeof value !== 'string' || value.length > max || (required && !value.trim())) throw new FormError(400, 'Please check the form fields and try again.');
  return value.trim();
}
async function readBody(request) {
  if (!request.headers.get('content-type')?.startsWith('application/json')) throw new FormError(415, 'Please submit the website form.');
  if (Number(request.headers.get('content-length')) > MAX_BODY) throw new FormError(413, 'Your message is too long.');
  const reader = request.body?.getReader();
  if (!reader) throw new FormError(400, 'The form is empty.');
  let size = 0; const chunks = [];
  try {
    for (;;) {
      const {value, done} = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > MAX_BODY) { await reader.cancel(); throw new FormError(413, 'Your message is too long.'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  try {
    const body = JSON.parse(new TextDecoder().decode(bytes));
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error();
    return body;
  } catch { throw new FormError(400, 'Please check the form and try again.'); }
}
async function digest(value) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), b => b.toString(16).padStart(2, '0')).join('');
}
export function createHandler(fetcher = fetch) {
  return async function handle(request, env) {
    const origin = request.headers.get('origin');
    const headers = {'Content-Type':'application/json; charset=utf-8', 'Cache-Control':'no-store', 'Vary':'Origin', 'X-Content-Type-Options':'nosniff'};
    if (ORIGINS.has(origin)) headers['Access-Control-Allow-Origin'] = origin;
    const respond = (status, data) => Response.json(data, {status, headers});
    const path = new URL(request.url).pathname;
    if (request.method === 'GET' && path === '/health') return respond(200, {ok:true});
    if (!ORIGINS.has(origin)) return respond(403, {message:'Please use the form on the Dr. OMEB website.'});
    if (request.method === 'OPTIONS') return new Response(null, {status:204, headers:{...headers,'Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type','Access-Control-Max-Age':'600'}});
    const ready = Boolean(env.TURNSTILE_SECRET_KEY && env.TURNSTILE_SITE_KEY);
    if (path === '/config' && request.method === 'GET') return respond(200, {siteKey:env.TURNSTILE_SITE_KEY, contact:ready && Boolean(env.EMAIL), signup:ready && Boolean(env.MAILERLITE_API_TOKEN) && env.MAILERLITE_DOUBLE_OPT_IN_READY === 'true'});
    if (!['/signup','/contact'].includes(path)) return respond(404, {message:'Not found.'});
    if (request.method !== 'POST') return respond(405, {message:'Please submit the website form.'});
    try {
      if (!ready || !env.FORM_LIMITER) throw new FormError(503, 'The form is temporarily unavailable. Please email hello@onemanelectricalband.com.');
      const ip = request.headers.get('CF-Connecting-IP');
      if (!ip) throw new FormError(400, 'Please reload the website and try again.');
      if (!(await env.FORM_LIMITER.limit({key:`ip:${ip}`})).success) throw new FormError(429, 'Please wait a minute before trying again.');
      const body = await readBody(request);
      if (field(body,'website',200)) throw new FormError(400, 'Unable to submit this form.');
      const email = field(body,'email',254,true).toLowerCase();
      if (!EMAIL.test(email)) throw new FormError(400, 'Please enter a valid email address.');
      const name = field(body,'name',100,path === '/contact');
      let reason, message, country, region;
      if (path === '/signup') {
        if (body.consent !== true) throw new FormError(400, 'Please confirm that you want to receive the mailing list.');
        if (!env.MAILERLITE_API_TOKEN || env.MAILERLITE_DOUBLE_OPT_IN_READY !== 'true') throw new FormError(503, 'Signup is temporarily unavailable. Please try again later.');
      } else {
        reason = field(body,'reason',50,true); message = field(body,'message',5000,true);
        country = field(body,'country',100); region = field(body,'region',100);
        if (!REASONS.has(reason) || !env.EMAIL) throw new FormError(400, 'Please choose a reason for your message.');
      }
      const token = field(body,'token',2048,true);
      const verification = await fetcher('https://challenges.cloudflare.com/turnstile/v0/siteverify', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({secret:env.TURNSTILE_SECRET_KEY,response:token,remoteip:ip}),signal:AbortSignal.timeout(10000)});
      if (!verification.ok) throw new Error('verification-unavailable');
      const result = await verification.json();
      if (!result.success || result.hostname !== new URL(origin).hostname || result.action !== path.slice(1)) throw new FormError(400, 'The security check expired or failed. Please try again.');
      if (!(await env.FORM_LIMITER.limit({key:`email:${await digest(email)}`})).success) throw new FormError(429, 'Please wait a minute before trying again.');
      if (path === '/contact') {
        await env.EMAIL.send({to:env.CONTACT_TO,from:env.CONTACT_FROM,replyTo:email,subject:`Dr. OMEB website: ${reason}`,text:`Name: ${name}\nEmail: ${email}\nCountry: ${country || 'Not provided'}\nState / Region: ${region || 'Not provided'}\nReason: ${reason}\n\n${message}\n\nSent through the Dr. OMEB website contact form.`});
        return respond(200,{message:'Your message has been sent. Thanks for getting in touch!'});
      }
      const mlHeaders = {'Authorization':`Bearer ${env.MAILERLITE_API_TOKEN}`,'Content-Type':'application/json','Accept':'application/json'};
      // Preserve opt-outs, suppressed addresses, and existing subscriber profile fields.
      const existing = await fetcher(`https://connect.mailerlite.com/api/subscribers/${encodeURIComponent(email)}`,{headers:mlHeaders,signal:AbortSignal.timeout(10000)});
      let subscriber = null;
      if (existing.ok) subscriber = (await existing.json()).data;
      else if (existing.status !== 404) throw new Error('subscriber-lookup-failed');
      if (subscriber && !['active','unconfirmed'].includes(subscriber.status)) return respond(200,{message:'If your address is eligible, look for a confirmation email. If you previously unsubscribed, email hello@onemanelectricalband.com for help rejoining.'});
      const payload = {email,groups:[env.MAILERLITE_GROUP_ID]};
      if (!subscriber && name) payload.fields = {name};
      const saved = await fetcher('https://connect.mailerlite.com/api/subscribers',{method:'POST',headers:mlHeaders,body:JSON.stringify(payload),signal:AbortSignal.timeout(10000)});
      if (!saved.ok) throw new Error('signup-unavailable');
      return respond(200,{message:'Thanks! If confirmation is needed, check your inbox and click the confirmation link. Already subscribed? You’re all set.'});
    } catch (error) {
      if (error instanceof FormError) return respond(error.status,{message:error.message});
      // Never log submitted content, email addresses, provider responses, or credentials.
      console.error(JSON.stringify({event:'form_failed',form:path.slice(1)}));
      return respond(502,{message:'We couldn’t confirm delivery. Please try again later or email hello@onemanelectricalband.com.'});
    }
  };
}
export default {fetch:createHandler()};
