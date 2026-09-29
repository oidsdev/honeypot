---
name: "kalshi"
description: "Trade Kalshi prediction markets via the official REST API: discover events and markets, read orderbooks, check balance and positions, place and cancel orders. Use when the user wants Kalshi trading, market prices, or portfolio status."
---

# Kalshi

## Purpose
Manage Kalshi event-contract trades: discover markets, inspect orderbooks, view portfolio, place and cancel orders.

## Tooling
CLI: `~/workspace/skills/kalshi/bin/kalshi` (auto-uses its own venv; stdlib HTTP + `cryptography` for signing).

```bash
bin/kalshi status                                   # exchange status (public)
bin/kalshi events --limit 10                        # list open events (public)
bin/kalshi markets --series KXGDPYEAR --limit 10    # list markets (public)
bin/kalshi markets --event KXGDPYEAR-26 --limit 10  # markets in one event (public)
bin/kalshi market <ticker>                          # market details (public)
bin/kalshi orderbook <ticker> --depth 5             # orderbook (public)
bin/kalshi balance                                  # portfolio balance (auth)
bin/kalshi positions                                # open positions (auth)
bin/kalshi orders                                   # resting orders (auth)
bin/kalshi order --ticker T --side yes --action buy --count 10 --price 65
bin/kalshi cancel <order_id>                        # cancel an order (auth)
```

Append `--json` to any command for raw API output. Add `--env demo` (or set `KALSHI_ENV=demo`) to use the demo exchange.

## Auth
Credentials come from environment variables at runtime, injected by the agent from the Secure Vault. **Never write them to files, logs, or memory; never print them.**

- `KALSHI_API_KEY_ID` — API key UUID, from Kalshi Settings > API
- `KALSHI_PRIVATE_KEY_PEM` — RSA private key PEM *contents* (shown only once at key creation), or `KALSHI_PRIVATE_KEY_PATH` for a PEM file path
- `KALSHI_ENV` — `demo` | `production` (default `production`)
- `KALSHI_BASE_URL` — optional override

Authenticated requests sign `timestamp + METHOD + path` with RSA-PSS-SHA256; see `references/api-notes.md` for the exact scheme.

## Operating Rules
1. **Prices are in cents, 1–99.** Every contract pays **$1.00** if correct, **$0** if wrong (e.g. YES at 65¢ costs $0.65, pays $1.00 on a YES outcome → 35¢ profit).
2. **Before placing any order, present ticker / side (YES|NO) / action (buy|sell) / count / price / total cost (= count × price) and require the user's explicit confirmation.** Never skip this, never batch it silently.
   - Standing exception (2026-09-22): David granted autonomous real-money trading authority — no per-trade confirmation needed. Hard limits still apply: ≤$75 total risk, ~$3.60/directional trade (scaling only on sustained wins), $5 daily stop (~$67.76), resting limit orders only, never add funds, never martingale/average down. When acting under a scheduled sweep, log each order's ticker/side/count/price/cost to the daily memory log instead of asking.
3. Prefer `KALSHI_ENV=demo` for dry runs unless the user explicitly wants production.
4. Always compute and state total cost and max payout: cost = count × price cents; max payout = count × $1.00.
5. Verify a position exists (via `positions`) before selling.
6. On 401/403, check that the signature headers were built (path must include the query string), not just that the key is right. See `references/api-notes.md`.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
