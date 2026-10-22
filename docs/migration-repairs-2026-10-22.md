# Migration repairs — October 22, 2026

Bandzoogle has been canceled. Production repairs use this repository, the preserved blog branch, the private media backup and verified public videos only.

## Changes

- All 22 music-record IDs from the preserved download manifest redirect permanently to matching anchors on `/music/`, including duplicate IDs. Exact `/track/ID` and `/track/ID/*` requests are supported.
- Added catalog entries for Johanna, Nights in White Satin, Lucy in the Sky with Diamonds, Ziggy Stardust and Deck the War Pigs. Destinations are public videos, not private audio masters. The Johanna link is explicitly an archival Bobby Mackey collaboration performance; it is not labeled as the identical audio version formerly hosted on Bandzoogle.
- Existing published recordings now have stable song anchors for migrated links.
- Old Deck the War Pigs article variants redirect to its song entry, following the original relocation plan.
- Legacy Diary RSS and pagination/index routes resolve to the native feed and blog index.
- Removed broad redirects that sent unrelated old articles to the blog homepage. Seven approved article mappings remain intact.
- The 404 page remains a real, noindexed HTTP 404, with contextual help for old articles and event listings, plus links to music, Diary and Church.
- New GA4 events: `page_not_found`, `merch_outbound_click` and `music_outbound_click`. Existing key-event definitions, newsletter request events and Church interaction events are unchanged. New events omit query strings; error-event referrers include hostname only. Automatic GA4 outbound events may still fire separately.

## Evidence

- Blog backup: `blog-backup-2026-09-04`, commit `9bca0033706471e6faf62dcab09060d099081f47`.
- Earlier editorial decisions: `native-doctors-notes-v1:docs/doctors-notes-redirect-plan.md`.
- Track mapping: `Music/download-manifest.json` in the private Bandzoogle backup repository. Only public titles and IDs are used; original audio remains private.
- Public videos on Dr. OMEB's channel: Johanna `JKujV9lvj2E`; Nights in White Satin `Yh1e8iqbick`; Lucy `ZiGNVejz8qg`; Ziggy `hTso8Irr024`. Deck the War Pigs `zJXf4Hh4zBQ` comes from the preserved original article embed.

## Intentional remaining exclusions

- Past event URLs without an archival destination retain HTTP 404.
- Nine retired articles remain unpublished, with originals preserved on the backup branch.
- Acoustic Black Sabbath and Liliac rewrites, the Vinny Appice milestone page, and AI education consolidation remain editorial work. Missing replacements are not redirected to unrelated content.
- `/index.php` remains a real 404; it is not a documented former homepage alias.
- Core Web Vitals has insufficient field data; no speed defect was established.
- Google updates stored exclusion examples after recrawling; historical rows will not disappear immediately.

## Validation

Run `python scripts/check_site_links.py`, `python scripts/check_migration_redirects.py` and `node scripts/check_migration_events.js`. After deployment verify track aliases, preserved article redirects, feed routes, canonical destinations, a retired article, a past event and an arbitrary missing URL. Check the production deployment commit against the repair commit.
