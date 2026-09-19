# Dr. OMEB Website

Static rebuild of the primary Dr. OMEB / One Man Electrical Band website for deployment on Cloudflare Pages.

## Current migration status

This repository contains the Cloudflare Pages replacement for the Bandzoogle site. The primary domain remains on Bandzoogle until final cutover approval and DNS attachment.

### Included
- Home / Rock n' Roll Church
- About
- Music
- Merch
- Press Kit
- Contact
- Album Art
- Native **Diary of a Rock n' Roll Doctor** landing page and RSS feed
- Responsive shared navigation, footer and Rock n' Roll Church visual system
- Existing SEO/schema direction carried into static pages

### Mailing list
- Home and Contact pages use native forms protected by Cloudflare Turnstile.
- The Worker adds new subscribers to the existing Congregation group through MailerLite, with API double opt-in enabled.
- Confirmation email sender: OMEB Communications <hello@onemanelectricalband.com>. This is an account-wide API setting, approved by Mike.
- End-to-end signup and email confirmation passed September 19, 2026. Gmail verified SPF and DKIM.
- Contact form delivery to OMEB Gmail and visitor Reply-To passed. Contact messages do not subscribe visitors.
- Backend code, configuration, and tests: `.cloudflare/forms/`. Secrets are stored only in Cloudflare.

### Cutover readiness
- Bandzoogle file, music and gallery assets are backed up locally and in a private GitHub repository.
- All production website images used by this build are stored locally in this repository.
- MailerLite signup and contact delivery are verified through Cloudflare-protected forms.
- The native Diary remains the permanent blog destination; no external publishing platform is required for launch.

## Cloudflare Pages

This is a no-build static site.

- Production branch: `main`
- Build command: leave blank
- Build output directory: `/` (repository root)

Attach `onemanelectricalband.com` after the final preview, link, form and redirect checks pass.
