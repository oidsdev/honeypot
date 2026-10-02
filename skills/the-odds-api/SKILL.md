---
name: "the_odds_api"
description: "Use The Odds Api when the user asks for The Odds Api or this provider's API."
---

# The Odds Api

## Purpose
Fetch sportsbook odds (default: Pinnacle) and remove the vig to get fair,
no-vig prices — useful for comparing a sportsbook's fair price against a
prediction-market price for the same game.

## Credit budget (500/month free Starter)
- `sports` and `events` are FREE - use them for discovery, never spend on these.
- `odds` costs (#markets) x (#regions). One market + one region = 1 credit.
- Keep pulls minimal: `h2h` only, `regions=us`, `bookmakers=pinnacle`.
- Cache odds responses locally (e.g. 15 min); replays within the window are free.
- Check the remaining quota in each response; stop if it runs low.

## Workflow
1. `curl "https://api.the-odds-api.com/v4/sports?apiKey=$KEY"` — list sport keys (free).
2. `curl "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds?apiKey=$KEY&regions=us&markets=h2h&bookmakers=pinnacle"` — odds (1 credit).
3. De-vig: for two-outcome decimal odds `d1`, `d2`: implied `p1=1/d1`, `p2=1/d2`, overround `=p1+p2`; fair `p1=p1/overround`. Multiply by 100 for fair cents.
4. Compare the fair price against the prediction-market price for the same game.

## Tooling
No bundled CLI — call `https://api.the-odds-api.com/v4/...` directly with any
HTTP client, passing your API key as the `apiKey` query parameter (see examples
in Workflow).

## Auth
Get a free API key at the-odds-api.com (Starter plan: 500 credits/month) and
pass it as the `apiKey` query parameter. Read the key from the user's
environment or secrets store at runtime — never hardcode it, never ask the
user to paste a raw key in chat, and never write it to files, logs, or memory.

A 401 or 403 is a question about the request before it is a question about the
key: first check that the `apiKey` parameter was actually attached.

## Operating Rules
1. Use this skill when the user asks for The Odds Api or this provider's API.
2. Restrict authenticated requests to: api.the-odds-api.com.
3. Do not print, log, or persist raw credentials.
4. If auth is missing or rejected, follow the Auth section rather than asking for a key.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
