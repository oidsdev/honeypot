# Honeypot

A free index of skills for AI agents. Machine-readable. No sign-up.

Live: https://honeypot-e6c.pages.dev

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
