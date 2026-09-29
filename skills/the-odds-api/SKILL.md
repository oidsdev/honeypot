---
name: "the_odds_api"
description: "Use The Odds Api when the user asks for The Odds Api or this provider's API."
---

# The Odds Api

## Purpose
Fetch sharp sportsbook odds (default: Pinnacle) and remove the vig to get fair,
no-vig prices for comparing against Kalshi sports markets. Used by the
autonomous Kalshi trading loop: pull cheap bulk `h2h` odds for a sport, devig
with `bin/devig`, then compare the fair price (in cents) against the Kalshi
market for the same game. Trade only when the edge clears the standing
Kalshi rules (4-5c fee-adjusted edge, 25-70c entry band, maker orders only).

## Credit budget (500/month free Starter)
- `sports` and `events` are FREE - use them for discovery, never spend on these.
- `odds` costs (#markets) x (#regions). One market + one region = 1 credit.
- Keep pulls minimal: `h2h` only, `--regions us`, `--bookmakers pinnacle`.
- Odds responses are cached on disk for 15 min; replays within a sweep are free.
- Check the `quota:` line on stderr after every call; stop if remaining is low.

## Workflow
1. `bin/odds-api sports` - list sport keys (free).
2. `bin/odds-api odds --sport baseball_mlb --regions us --markets h2h \
   --bookmakers pinnacle --out /tmp/odds.json`  (1 credit)
3. `bin/devig /tmp/odds.json --bookmaker pinnacle --compact` - fair prices in cents.
4. Look up the matching Kalshi market with the kalshi skill, compare fair cents
   vs Kalshi ask/bid, and trade only on qualifying edges.

## Tooling
Add service-specific CLIs under `~/workspace/skills/the-odds-api/bin/`.

Python CLIs must import `/opt/hatch/skills/skill-creator/bin/dynamic_credentials.py` and call `add_surrogate_to_request(...)`, `url_with_surrogate_query_param(...)`, or `url_with_surrogate_path_segment(...)` before authenticated requests, matching where the provider reads the key. If they use `urllib`, read JSON responses with `read_json_response(resp)` from the same helper instead of calling `resp.read()` directly. They must send only `hsurr:*` values, and only to the hosts below.

## Auth
The connector is already stored; nothing here collects one. Never ask the user to paste a raw key in chat, set a secret environment variable, pass a secret flag, or write an auth file.

A 401 or 403 is a question about the request before it is a question about the key. Check that the credential was attached at all: a request built without the helpers named under Tooling carries nothing, and that looks exactly like a wrong or under-scoped token. Only once a request that did carry the credential is still rejected, call `credentials.request_api_access` with `reconnect` to replace it. The connector is stored as `custom.the-odds-api-2` (the original `custom.the-odds-api` connector's capture session would not accept a replacement key, so a fresh connector was minted 2026-09-23).

**2026-09-23 status: connectors are BROKEN.** Meta's capture form errors with "there is a problem" on submit (user tried 3x: original, -2, -3); the capture session_id is sticky across all minting calls so no fresh form is possible; `-2` never completed (403); `-3` errors on submit. David chose MANUAL mode: run odds pulls via direct API calls using the key he provided in chat (verified working 2026-09-23, 500 credits). Use the key transiently — pass it directly in the request for the immediate task only. NEVER write the raw key to files, memory, env vars, logs, or code. Do not use the `bin/odds-api` CLI (it depends on the broken connector).

## Operating Rules
1. Use this skill when the user asks for The Odds Api or this provider's API.
2. Restrict authenticated requests to: api.the-odds-api.com.
3. Do not print, log, or persist raw credentials.
4. If auth is missing or rejected, follow the Auth section rather than asking for a key.
