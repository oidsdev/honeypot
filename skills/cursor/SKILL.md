---
name: "cursor"
description: "Cursor Cloud Agents API: launch background coding agents on GitHub repos, check run status, collect PRs. Use when the user asks for Cursor, cloud agents, or background coding runs."
---

# Cursor Cloud Agents

## Purpose
Drive Cursor Cloud Agents programmatically: launch an agent on a GitHub
repo with a prompt, poll its run, and collect the pull request it opens.
Good for delegating well-scoped coding tasks (fixes, docs, tests, small
features) to a background agent while you keep working.

## Tooling
Call the REST API at `https://api.cursor.com` (v1) directly, or wrap it in
a thin CLI. The core calls:

```bash
BASE=https://api.cursor.com
AUTH="Authorization: Bearer $CURSOR_API_KEY"

curl -s -H "$AUTH" "$BASE/v1/me"                            # auth check
curl -s -H "$AUTH" "$BASE/v1/repositories"                  # connected GitHub repos
curl -s -H "$AUTH" "$BASE/v1/models"                        # available models

# Launch: creates the agent AND enqueues its first run.
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" -d '{
  "prompt": {"text": "Fix the failing test in tests/test_api.py"},
  "repos": [{"url": "https://github.com/you/your-repo"}],
  "autoCreatePR": true,
  "skipReviewerRequest": true,
  "mode": "agent"
}' "$BASE/v1/agents"        # -> {agent: {id}, run: {id, status}}

curl -s -H "$AUTH" "$BASE/v1/agents/<agent_id>/runs/<run_id>"   # status, duration, PR URLs
curl -s -H "$AUTH" "$BASE/v1/agents/<agent_id>/runs"            # all runs for an agent
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"prompt": {"text": "Now add a test for the fix"}}' \
  "$BASE/v1/agents/<agent_id>/runs"                             # follow-up run on same agent
curl -s -X POST -H "$AUTH" "$BASE/v1/agents/<agent_id>/runs/<run_id>/cancel"
curl -s -H "$AUTH" "$BASE/v1/agents/<agent_id>/usage"           # token usage
```

The launch response carries `agent.id` and `run.id` — save both; every
later call needs them. A finished run's status response includes its PR
URL(s) and branch.

## Auth
- Create an API key in your Cursor account settings and pass it as a
  Bearer token from an environment variable at runtime — never hardcoded,
  never written to files, logs, or memory.
- `GET /v1/me` is the cheap auth check. A 401/403 with the header attached
  means the key itself is wrong or revoked — rotate it in settings.

## Operating Rules
1. **The GitHub repo must already be connected** to the Cursor account —
   check `GET /v1/repositories` before launching; there is no API-side
   way to connect a new repo.
2. **Don't pin a `model` unless you mean it.** Omitting it uses the
   account's default models and included usage pool; an explicit model can
   draw from a different (metered) pool. Check `GET /v1/models` first.
3. With `autoCreatePR`, a completed run opens a PR. **Agents push branches;
   humans merge.** Review every PR before it lands — never auto-merge
   agent output.
4. Keep prompts PR-sized: one task, clear acceptance criteria, named files
   where you know them. A follow-up run on the same agent is cheaper than
   a fresh launch when context carries over.
5. The API is public beta — if calls start failing in new ways, check the
   current endpoint docs at https://cursor.com/docs/cloud-agent/api/endpoints
   before blaming the key.
6. Report PR URLs and run status, never the API key.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
