# Honeypot

A free index of skills for AI agents. Machine-readable. No sign-up.

Live: https://honeypot-e6c.pages.dev

## Fetch it by machine

The index is one JSON file. `schema_version` is `"1"`; entries live under `.skills`.

```sh
# everything
curl -sL https://honeypot-e6c.pages.dev/api/skills.json | jq '.skills[] | .name'

# one category only (cheaper than filtering client-side)
curl -sL https://honeypot-e6c.pages.dev/api/by-category/trading.json | jq '.skills[] | .name'

# install one skill
curl -sL https://honeypot-e6c.pages.dev/api/skills.json \
  | jq -r '.skills[] | select(.name=="kalshi") | .install'
# then run the command it prints
```

### Linkable searches

The site takes the same filters as URL params, so any view can be shared or bookmarked:

- `?q=` — text match on name, description, and tags
- `?tag=` — exact tag
- `?category=` — exact category

Params combine: `https://honeypot-e6c.pages.dev/?category=trading&tag=prediction-markets`.
Filtering happens in the browser, so `curl` on that URL returns the unfiltered page.
To get the same result from a script, apply the filters to the JSON:

```sh
# same as /?q=odds&tag=sports-data&category=data
curl -sL https://honeypot-e6c.pages.dev/api/skills.json | jq '.skills[]
  | select(.category=="data")
  | select(.tags | index("sports-data"))
  | select((.name+" "+.description+" "+(.tags|join(" "))) | ascii_downcase | contains("odds"))
  | .name'
```

Each entry has `name`, `description`, `category`, `tags`, `last_verified` (date),
`skill_md_url`, and `install`. New additions: `/api/changelog.json` and `/feed.xml` (RSS).

Editor's picks live at `/api/editors-picks.json`. There's no score: a skill is a pick
when it passes every check in `PICK_CRITERIA` in `scripts/gen.py` (description length,
tags, verified recently, SKILL.md link). The file carries the checklist itself as
`criteria` and `criteria_text`, and the site prints that text as-is.

Every card on the site shows its `last_verified` date. Anything not re-verified in
`STALE_AFTER_DAYS` (180, set in `scripts/gen.py` and published as `stale_after_days`
in `/api/editors-picks.json`) gets a "stale" badge and drops out of the picks.
Freshness is date-based only; nothing pings the skills.
The same JSON is mirrored at
`https://raw.githubusercontent.com/oidsdev/honeypot/main/api/skills.json`.

## Submit a skill

1. Write your skill as a `SKILL.md`. Start from [skill-template.md](skill-template.md).
2. Fork this repo.
3. Add it at `skills/<your-skill>/SKILL.md`.
4. Open a pull request. We merge fast.
5. Add the badge to your repo:

```markdown
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
```

Requirements (learned the hard way — PRs missing these get bounced):
- Frontmatter must include `name` and `description`. Directory CLIs (e.g. skills.sh)
  silently skip files without them.
- Pick one `category` (trading, data, identity, meta, tooling, or propose a new one in the PR)
  and add `tags` plus a current `last_verified` date — these feed the JSON index.
- MIT-compatible license only. We can't index what we can't redistribute.
- Spam, duplicates, and anything malicious get closed. Every listing is PR-gated and
  read before it merges.

## Layout

- `index.html` — the site
- `api/skills.json` — the machine-readable index
- `categories/<category>/` — landing page for each of the 8 largest categories (generated)
- `scripts/gen.py` — rebuilds everything derived from `skills.json` (run after any change)
- `llms.txt` — agent-readable description
- `skill-template.md` — blank SKILL.md template
- `skills/<name>/SKILL.md` — the indexed skills

## License

MIT — Orbital Desk LLC.
