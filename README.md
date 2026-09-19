# Dr. OMEB Website

Static rebuild of the primary Dr. OMEB / One Man Electrical Band website for deployment on Cloudflare Pages.

## Current migration status

This repository is the preview/staging build. The live Bandzoogle site remains the production source until cutover is approved.

### Included
- Home / Rock n' Roll Church
- About
- Music
- Merch
- Press Kit
- Contact
- Album Art
- Blog placeholder for **Diary of a Rock n' Roll Doctor** on Substack
- Responsive shared navigation, footer and Rock n' Roll Church visual system
- Existing SEO/schema direction carried into static pages

### Mailing list
- Home and Contact pages use native forms protected by Cloudflare Turnstile.
- The Worker adds new subscribers to the existing Congregation group through MailerLite, with API double opt-in enabled.
- Confirmation email sender: OMEB Communications <hello@onemanelectricalband.com>. This is an account-wide API setting, approved by Mike.
- End-to-end signup and email confirmation passed September 19, 2026. Gmail verified SPF and DKIM.
- Contact form delivery to OMEB Gmail and visitor Reply-To passed. Contact messages do not subscribe visitors.
- Backend code, configuration, and tests: `.cloudflare/forms/`. Secrets are stored only in Cloudflare.

### Intentionally not live yet
- Substack destination: publication URL has not yet been finalized.
- Final asset migration: a small number of preview assets currently load from existing Dr. OMEB/Bandzoogle CDN URLs and must be copied into this repository before Bandzoogle is cancelled.

## Cloudflare Pages

This is a no-build static site.

- Production branch: `main`
- Build command: leave blank
- Build output directory: `/` (repository root)

Do not attach `onemanelectricalband.com` until email, forms, Substack URL, redirects and asset localization have passed final review.
