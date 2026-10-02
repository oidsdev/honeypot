---
name: "kalshi"
description: "Trade Kalshi prediction markets via the official REST API: discover events and markets, read orderbooks, check balance and positions, place and cancel orders. Use when the user wants Kalshi trading, market prices, or portfolio status."
---

# Kalshi

## Purpose
Manage Kalshi event-contract trades: discover markets, inspect orderbooks, view portfolio, place and cancel orders.

## Tooling
No bundled CLI — call the official REST API directly with any HTTP client
(e.g. `curl`). Public endpoints need no auth; portfolio endpoints need the
three `KALSHI-ACCESS-*` headers from the Auth section below.

```bash
BASE=https://api.elections.kalshi.com/trade-api/v2

curl -s "$BASE/exchange/status"                          # exchange status (public)
curl -s "$BASE/events?limit=10"                          # open events (public)
curl -s "$BASE/markets?series_ticker=KXGDPYEAR&limit=10" # markets (public)
curl -s "$BASE/markets/KXGDPYEAR-26/orderbook?depth=5"    # orderbook (public)
```

Authenticated calls: `GET $BASE/portfolio/balance`, `GET
$BASE/portfolio/positions`, `GET $BASE/portfolio/orders`,
`POST $BASE/portfolio/events/orders` to place, `DELETE
$BASE/portfolio/events/orders/{order_id}` to cancel. Swap the base for
`https://demo-api.kalshi.co/trade-api/v2` for dry runs.

## Auth
Credentials come from environment variables at runtime — never hardcoded, never written to files, logs, or memory.

- `KALSHI_API_KEY_ID` — API key UUID, from Kalshi Settings > API
- `KALSHI_PRIVATE_KEY_PEM` — RSA private key PEM *contents* (shown only once at key creation), or `KALSHI_PRIVATE_KEY_PATH` for a PEM file path
- `KALSHI_ENV` — `demo` | `production` (default `production`)
- `KALSHI_BASE_URL` — optional override

Authenticated requests sign `timestamp + METHOD + path` (no delimiters, path
without the query string) with RSA-PSS-SHA256, sent as three headers:
`KALSHI-ACCESS-KEY` (key UUID), `KALSHI-ACCESS-TIMESTAMP` (current POSIX time
in milliseconds), `KALSHI-ACCESS-SIGNATURE` (base64 signature).

## Operating Rules
1. **Prices are in cents, 1–99.** Every contract pays **$1.00** if correct, **$0** if wrong (e.g. YES at 65¢ costs $0.65, pays $1.00 on a YES outcome → 35¢ profit).
2. **Before placing any order, present ticker / side (YES|NO) / action (buy|sell) / count / price / total cost (= count × price) and require the user's explicit confirmation.** Never skip this, never batch it silently.
3. Prefer the demo exchange for dry runs unless the user explicitly wants production.
4. Always compute and state total cost and max payout: cost = count × price cents; max payout = count × $1.00.
5. Verify a position exists (via `positions`) before selling.
6. On 401/403, check that the signature headers were built (sign the path without the query string, and confirm the key was created for the right environment), not just that the key is right.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
