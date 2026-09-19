# Dr. OMEB website forms

Worker: `dr-omeb-forms`
Endpoint: `https://dr-omeb-forms.onemanelectricalband.workers.dev`

The static Pages site uses this separate Worker for `/contact` and `/signup`.
No production domain routes are attached. Keep Bandzoogle DNS and hosting intact
until the separate migration checklist is complete.

## Configuration

- Turnstile: managed widget, `dr-omeb-website.pages.dev` and
  `onemanelectricalband.com` (includes subdomains).
- Secret `TURNSTILE_SECRET_KEY`: stored in Cloudflare, never committed.
- Secret `MAILERLITE_API_TOKEN`: required before enabling signup.
- `MAILERLITE_DOUBLE_OPT_IN_READY` must remain `false` until MailerLite's
  **Account settings → Subscribe settings → Double opt-in for API and
  integrations** is confirmed on. That setting applies to all API integrations.
- Email binding can send only to the verified OMEB Gmail destination and only
  from `hello@onemanelectricalband.com`.
- MailerLite group: `197691176067794357` (The Congregation).

The API verifies the Turnstile token, exact hostname, and form-specific action
before calling either provider. Tokens are single-use under Siteverify. It also
limits payload size, checks a honeypot, and applies Cloudflare's approximate
per-location rate limit of five requests per minute by IP and hashed email.
Provider errors fail closed. Logs exclude messages, addresses, and secrets.

Contact messages set Reply-To to the visitor and never subscribe the visitor.
Signup preserves existing profile data and never reactivates unsubscribed,
bounced, or junk addresses. Those visitors are directed to contact Mike.

## Deploy and verify

Using Wrangler 4:

```sh
node --test .cloudflare/forms/test/forms.test.mjs
wrangler deploy --dry-run -c .cloudflare/forms/wrangler.jsonc
wrangler deploy -c .cloudflare/forms/wrangler.jsonc
wrangler secret put TURNSTILE_SECRET_KEY -c .cloudflare/forms/wrangler.jsonc
wrangler secret put MAILERLITE_API_TOKEN -c .cloudflare/forms/wrangler.jsonc
```

Do not publish the replacement frontend until the MailerLite secret and API
double opt-in are configured. Then test contact receipt and reply-to, a new
double-opt-in signup, and layouts on desktop and mobile at the Pages preview.
The existing main domain should still serve Bandzoogle during these tests.

As of September 19, 2026: Worker, Turnstile, and frontend deployed. MailerLite
token connected; API double opt-in enabled. Mike approved the account-wide API
confirmation sender change to hello@onemanelectricalband.com.

Eight backend tests pass; remote invalid-token rejection verified. Contact
submission arrived in Gmail with correct Reply-To and passing SPF/DKIM. A new
test signup entered the Congregation group as unconfirmed, received its email
with passing SPF/DKIM, and became active only after its confirmation link was
opened. The test alias was then unsubscribed to prevent duplicate campaign mail.
Desktop form layouts checked. The browser viewport override did not apply, so
an actual mobile rendering check remains outstanding. No production DNS changes.
