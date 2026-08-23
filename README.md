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

### Intentionally not live yet
- Congregation email signup: email platform migration is still being decided.
- Contact / booking form submission: Cloudflare form backend and anti-spam protection still need to be connected.
- Substack destination: publication URL has not yet been finalized.
- Final asset migration: a small number of preview assets currently load from existing Dr. OMEB/Bandzoogle CDN URLs and must be copied into this repository before Bandzoogle is cancelled.

## Cloudflare Pages

This is a no-build static site.

- Production branch: `main`
- Build command: leave blank
- Build output directory: `/` (repository root)

Do not attach `onemanelectricalband.com` until email, forms, Substack URL, redirects and asset localization have passed final review.
