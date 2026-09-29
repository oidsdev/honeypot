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
- Pick one `category` (trading, data, identity, meta, or propose a new one in the PR)
  and add `tags` plus a current `last_verified` date — these feed the JSON index.
- MIT-compatible license only. We can't index what we can't redistribute.

## Layout

- `index.html` — the site
- `api/skills.json` — the machine-readable index
- `llms.txt` — agent-readable description
- `skill-template.md` — blank SKILL.md template
- `skills/<name>/SKILL.md` — the indexed skills

## License

MIT — Orbital Desk LLC.
