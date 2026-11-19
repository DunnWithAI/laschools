# Deploying

The site is a Cloudflare Worker that serves the static files in `site/` as-is
(`wrangler.jsonc`). There is no build step on Cloudflare: `site/index.html` and
`site/data.json` are committed. Rebuild `site/data.json` locally with the scripts in
`scripts/` (see the README), commit it, and push.

Live at https://laschools.dunn.us. Workers Builds was connected to the repo on 19 November 2026.

## What happens when

| Event | What Cloudflare does |
| --- | --- |
| Push or merge to `main` | Publishes `site/` to laschools.dunn.us. |
| Push to another branch, or a PR | Uploads a preview version; the link shows as a check on the PR. |

## Cloudflare settings

Workers & Pages → laschools → Settings → Build:

| Setting | Value |
| --- | --- |
| Git repository | `DunnWithAI/laschools` |
| Production branch | `main` |
| Build command | (none) |
| Deploy command | `npx wrangler deploy` |
| Preview command (other branches) | `npx wrangler preview` (Enable Preview builds is on) |
| Root directory | `/` |

## The "Updated" date

`scripts/build_page_data.py` sets the footer's "Updated" date to the day it runs, but only
when `site/data.json` actually changes.

## Deploying by hand

    npx wrangler deploy

A later push to `main` replaces whatever was deployed this way.
