
# Doctor's Notes Legacy URL Plan

Updated: 2026-09-04

The Bandzoogle site remains the production source until the static-site cutover is approved. No legacy post should disappear before its destination exists and the redirect has been tested.

## Ready for cutover

| Legacy post | Decision | New destination |
|---|---|---|
| How TikTok Livestreaming Rewired My Marketing Brain | Keep / revise | `/blog/how-tiktok-livestreaming-rewired-my-marketing-brain/` |
| I Gave a Man Free Marketing Advice. He Blocked Me. | Reframe | `/blog/nobody-owes-you-attention/` |
| My Unpublished 2019 PhD Dissertation Still Holds Up... | Keep / fact-check | `/blog/streaming-royalties-better-room/` |
| I Spent $283 on TikTok Ads... | Keep / methodology correction | `/blog/tiktok-ads-experiment/` |
| Your Brand Is Losing a War for Attention... | Keep / revise | `/blog/kiss-war-for-attention/` |
| Why AI Belongs in the Hands of Creative People | Reframe | `/blog/ai-does-not-replace-taste/` |
| How I Made a $500K Music Video... | Reframe | `/blog/ai-music-video-independent-artist/` |

The root `_redirects` file contains only these completed routes plus the old archive landing page.

## Build before redirecting

| Legacy post | Decision | Planned destination |
|---|---|---|
| I Made My Acoustic Sound Like Black Sabbath | Rebuild as evergreen tutorial | `/blog/acoustic-guitar-black-sabbath-fm9-signal-chain/` |
| Marketing Doctor Analyzes Liliac's “Carol of the Bells” | Seasonal rewrite | `/blog/why-liliac-carol-of-the-bells-works/` |
| Rock Legend Joins Local Band | Rebuild as milestone | A dedicated Vinny Appice collaboration page under Press / Milestones |
| Deck the War Pigs: A Christmas Parody | Move to music catalog | A dedicated song/video page under Music |
| AI in the Classroom: Stop Panicking, Start Preparing | Consolidate / relocate | Professional education or consulting archive outside Doctor's Notes |
| Red Light, Green Light: How I'm Structuring AI Use in My Classes | Consolidate / relocate | Same definitive AI-in-education resource as above |

## Retire from the public publication

These posts remain in the durable backup. Do not redirect them to an unrelated article merely to avoid a 404; that would create a poor user experience and a misleading SEO signal.

- Marketing That Rocks w/ Dr. C — February 2025 Edition
- A Parent's Guide to Artificial Intelligence
- A Practical Guide to Incorporating AI and ChatGPT in Everyday Life
- ChatGPT for Course Prep, Assignments, Grading, and More
- Why Teachers and Students Should Be Using ChatGPT
- How I Used AI to Do Market Research on the Music Industry
- The Death of the NAMM Show?
- Marketing Doctor Analyzes The Smashing Pumpkins: ZERO to Bulletproof
- Marketing Doctor's Shocking Reaction to Dave Mustaine's Rant

Before cutover, choose one of the following for each retired URL:

1. Create a useful archival or replacement page and issue a 301 redirect.
2. Serve a purpose-built “This note has been retired” page with links to the closest useful section.
3. Use a Cloudflare Worker if a true HTTP 410 response is strategically preferred; Pages `_redirects` is intended for redirects and rewrites, not a 410 retirement response.

## Cutover checklist

- Preview every native article on desktop and mobile.
- Confirm every image is local and loads without Bandzoogle.
- Test every active redirect with and without a trailing slash.
- Add destinations and redirects for the six “build before redirecting” posts.
- Decide the retirement treatment for the nine thin or off-brand posts.
- Submit the updated sitemap after the production domain moves to Cloudflare Pages.
- Keep the full 22-post backup outside the production branch as the recovery source.
