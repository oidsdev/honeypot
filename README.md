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

- `?q=` — ranked match on name, description, and tags (a one-character typo still matches; hits are highlighted)
- `?tag=` — exact tag
- `?category=` — exact category

Params combine: `https://honeypot-e6c.pages.dev/?category=trading&tag=prediction-markets`.
Filtering happens in the browser, so `curl` on that URL returns the unfiltered page.
The page ranks matches and tolerates a one-character typo. A script can apply the
same category and tag filters, plus a plain substring check, to the JSON:

```sh
# substring stand-in for ?q= (the page ranks; this check does not)
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
4. Lint it from the repo root:

```sh
python3 scripts/lint_skill.py skills/<your-skill>
```

`pass` is clean. `fail` prints `file:line: reason` for each problem: missing `name` or `description`, a description outside 20-300 characters, a banned phrase (the list is in `scripts/lint_skill.py`), or a relative link that does not resolve to a file.
5. Open a pull request. We merge fast.
6. Add the badge to your repo:

```markdown
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
```

Per-skill badges live at `/badge/<skill>.svg`. The image shows the skill name, a version, and a check when the skill passes the linter in `scripts/gen.py`.

```markdown
[![cron on Honeypot](https://honeypot-e6c.pages.dev/badge/cron.svg)](https://honeypot-e6c.pages.dev/skills/cron/)
```

Version is the optional `version` field in the SKILL.md frontmatter. With no `version`, the badge shows `last_verified`. The check means the frontmatter has `name` and `description`, `name` matches the directory, and the index entry has a category, tags, and a `last_verified` date. The SVG is static and cached for a day.

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
- `search.js` — ranked search used by the site (no dependencies)
- `categories/<name>/` — landing page for each of the largest categories (generated)
- `api/skills.json` — the machine-readable index
- `scripts/gen.py` — rebuilds everything derived from `skills.json` (run after any change)
- `scripts/lint_skill.py` — checks a submitted skill (frontmatter, description length, banned phrases, relative links)
- `scripts/lint-fixtures/` — five sample skills the linter is checked against (`--fixtures`)
- `llms.txt` — agent-readable description
- `skill-template.md` — blank SKILL.md template
- `skills/<name>/SKILL.md` — the indexed skills
- `tests/test_search.js` — `node tests/test_search.js`
- `badge/<name>.svg` — per-skill badge, written by `scripts/gen.py`
- `_headers` — cache header for `/badge/*` (one day)

## License

MIT — Orbital Desk LLC.
