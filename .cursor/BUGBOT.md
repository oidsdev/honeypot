# Bugbot review rules — Honeypot (oidsdev/honeypot)

Public directory of agent skills. Every skill is downloaded and executed by
strangers' agents, so the review bar is higher than a normal repo.

## Blocking (must flag)

- **Install commands must be safe.** Every `install` field in `api/skills.json`
  must use `curl -fSL` (fail on HTTP errors) against
  `https://raw.githubusercontent.com/oidsdev/honeypot/main/...` and write to a
  unique skill-specific filename (never overwrite a shared name like `SKILL.md`).
  Flag any `curl` without `-f`, any non-HTTPS URL, any `| sh` pipe.
- **No secrets or credentials** in any SKILL.md, JSON, HTML, or generated page.
  Flag API keys, tokens, passwords, private keys, even in examples.
- **No PII** in committed files or generated output. Flag real names, emails,
  addresses, phone numbers.
- **Frontmatter must be valid.** Every `skills/*/SKILL.md` needs `name` and
  `description` frontmatter. Flag missing or malformed frontmatter.
- **API schema consistency.** Every entry in `api/skills.json` must have:
  `name`, `description`, `install`, `license`. Flag missing fields.
- **Generated files must match the generator.** If `api/skills.json` changed
  but per-skill `index.html` pages were not regenerated via `gen.py`, flag it.

## Non-blocking (suggest)

- Copy must be brief, human, wry. No em dashes. No AI-sounding prose
  ("delve", "tapestry", "unlock", "game-changer").
- Skill descriptions should say what the skill does in one sentence.
- If a skill requires local setup (binaries, env vars), it must say so
  visibly in the SKILL.md, not just in the install command.

## Context

- `gen.py` generates per-skill pages, sitemap.xml, and category JSON from
  `api/skills.json`. Always regenerate after changing skills.json.
- The site deploys to Cloudflare Pages. `submitters.md` was deleted and must
  never return.
