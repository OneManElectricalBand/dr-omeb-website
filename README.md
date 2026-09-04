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
- Native **Doctor's Notes** publication with seven editorially rebuilt launch articles
- RSS feed, canonical metadata, BlogPosting structured data and sitemap entries for Doctor's Notes
- First-stage 301 redirects for the seven completed legacy articles
- Responsive shared navigation, footer and Rock n' Roll Church visual system
- Existing SEO/schema direction carried into static pages

### Intentionally not live yet

- Congregation email signup: the email platform migration is still being decided.
- Contact / booking form submission: the Cloudflare form backend and anti-spam protection still need to be connected.
- Remaining Doctor's Notes legacy destinations: six posts need a replacement or relocation page, and nine retired posts need an intentional retirement treatment before Bandzoogle is cancelled. See `docs/doctors-notes-redirect-plan.md`.
- Final asset migration: a small number of non-blog preview assets currently load from existing Dr. OMEB/Bandzoogle CDN URLs and must be copied into this repository before Bandzoogle is cancelled.

## Cloudflare Pages

This is a no-build static site.

- Production branch: `main`
- Build command: leave blank
- Build output directory: `/` (repository root)

Do not attach `onemanelectricalband.com` until email, forms, all legacy URL decisions, redirects and asset localization have passed final review.
