---
name: "polymarket"
description: "Trade Polymarket US (polymarket.us, the CFTC-regulated US exchange) via the official retail REST API: discover events and markets, read orderbooks, check balances and positions, place and cancel limit orders. Use when the user wants Polymarket US trading, market prices, or portfolio status. This is NOT polymarket.com (international) — different API, auth, and custody."
---

# Polymarket US

## Purpose
Manage Polymarket US event-contract trades: discover markets, inspect orderbooks, view portfolio, place and cancel orders. Polymarket US is the CFTC-regulated Designated Contract Market operated by QCX LLC — fiat USD, fully off-chain, Ed25519 API-key auth.

## Tooling
CLI: `~/workspace/skills/polymarket/bin/polymarket` (auto-uses its own venv; stdlib HTTP + `pynacl` for Ed25519 signing).

```bash
bin/polymarket events --limit 10                        # list events (public)
bin/polymarket markets --limit 10                       # list markets (public)
bin/polymarket search "Chicago temperature"             # search events/markets (public)
bin/polymarket market <slug>                            # market details via search (public)
bin/polymarket book <slug>                              # order book (public)
bin/polymarket bbo <slug>                               # best bid/offer + stats (public)
bin/polymarket settlement <slug>                        # settlement price (public; path unverified)
bin/polymarket fees --qty 100 --price 50                # local fee estimate (no API call)
bin/polymarket balance                                  # account balances (auth)
bin/polymarket positions                                # open positions (auth)
bin/polymarket orders                                   # open orders (auth)
bin/polymarket order --slug S --intent buy-long --qty 10 --price 65 [--dry-run]
bin/polymarket cancel <order_id> --slug S            # cancel one order (slug required)
bin/polymarket cancel-all                           # cancel all open orders (auth)
```

Append `--json` anywhere for raw API output. `order --dry-run` prints the signed request body without sending.

## Auth
Credentials come from environment variables at runtime. **Never write them to files, logs, or memory; never print them.**

- `POLYMARKET_KEY_ID` — API key UUID, from https://polymarket.us/developer
- `POLYMARKET_SECRET_KEY` — base64 Ed25519 private key (shown **once** at key creation)
- `POLYMARKET_AUTH_BASE` — optional override (default `https://api.polymarket.us`)
- `POLYMARKET_PUBLIC_BASE` — optional override (default `https://gateway.polymarket.us`)

Storage: `~/.polymarket/key_id` and `~/.polymarket/secret`, mode 0600 (live, created 2026-09-24). **Never write them to files, logs, or memory; never print them.**

Authenticated requests sign `f"{timestamp_ms}{METHOD}{path}"` with Ed25519 (base64), sending `X-PM-Access-Key` / `X-PM-Timestamp` / `X-PM-Signature`. Timestamps must be within **30s** of server time. See `references/api-notes.md`.

## Operating Rules
1. **Prices are in cents, 1–99.** Every contract pays **$1.00** if correct, **$0** if wrong. Long = bought YES contracts (profit if outcome occurs); short = sold YES contracts (profit if it doesn't).
2. **Standing authority (2026-09-24):** David authorized autonomous real-money trading on Polymarket US mirroring the Kalshi mandate — no per-trade confirmation needed. Hard limits (confirmed 2026-09-24): ≤$20 total risk (full bankroll), $0.40–$1.00 per directional trade (max $2.00), 25–70¢ entry band, max 3–5 open, resting maker limit orders only, never add funds, never martingale/average down, no wash trading or spoofing (CFTC venue). Log each order's slug/intent/qty/price/cost to the daily memory log instead of asking.
3. **Maker-only.** Taker fee is Θ=0.0695 × C × p × (1−p) (up to $1.74/100 @ 50¢); makers earn a rebate Θ=−0.0125 (up to $0.31/100 @ 50¢), credited at fill. Never take except to close a position David explicitly names.
4. **No sandbox exists** per the docs — every order is real money. Use `order --dry-run` and the `fees` calculator before any first live order on a new path.
5. Verify a position exists (via `positions`) before closing it.
6. Rate limit: **20 req/s per API key** (429 on breach) — back off, prefer the WebSocket for streaming. Orders not processed within 5s are rejected by a latency stopgap ("Global Rate Limit Exceeded" message) — retry logic must distinguish this from a real rate limit.
7. Weekly maintenance window **Thursday 6–8am ET** — avoid scheduling sweeps then.
8. **Settlement sources differ from Kalshi.** Polymarket US weather markets settle on NWS Climatological Reports (e.g. KMDW CLI), Kalshi on The Weather Company. Never treat same-topic cross-venue positions as arbitrage.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
