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

## Layout

- `index.html` — the site
- `api/skills.json` — the machine-readable index
- `llms.txt` — agent-readable description
- `skill-template.md` — blank SKILL.md template
- `skills/<name>/SKILL.md` — the indexed skills

## License

MIT — Orbital Desk LLC.
