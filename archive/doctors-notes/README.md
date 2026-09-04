# Portable Doctor's Notes Backup

This directory is a portable backup of the public **Doctor's Notes** archive from
`https://onemanelectricalband.com/blogs/diary-of-a-rock-n-roll-doctor`.

Generated: `2026-09-04T10:21:29Z`

## Contents

- `posts/` — readable Markdown copies with local image references.
- `raw-html/` — untouched HTML responses retained for exact recovery.
- `images/` — 45 unique images used by the backed-up posts.
- `manifest.json` — source URLs, post IDs, dates, file paths, image hashes, and any warnings.
- `backup-report.md` — human-readable inventory.

The Markdown files are the easiest source for rebuilding a native blog. The raw HTML
files are the safety copy when exact legacy formatting or embedded code must be recovered.
This backup is stored on a non-production Git branch so it is not part of the live site.
