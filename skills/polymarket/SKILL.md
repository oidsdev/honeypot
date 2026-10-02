---
name: "polymarket"
description: "Trade Polymarket US (polymarket.us, the CFTC-regulated US exchange) via the official retail REST API: discover events and markets, read orderbooks, check balances and positions, place and cancel limit orders. Use when the user wants Polymarket US trading, market prices, or portfolio status. This is NOT polymarket.com (international) — different API, auth, and custody."
---

# Polymarket US

## Purpose
Manage Polymarket US event-contract trades: discover markets, inspect orderbooks, view portfolio, place and cancel orders. Polymarket US is the CFTC-regulated Designated Contract Market operated by QCX LLC — fiat USD, fully off-chain, Ed25519 API-key auth.

## Tooling
No bundled CLI — call the official REST APIs directly with any HTTP client
(e.g. `curl`). Public market data lives on the gateway host (no auth);
trading calls go to the API host with the `X-PM-*` headers from the Auth
section below.

```bash
PUB=https://gateway.polymarket.us

curl -s "$PUB/v1/events?limit=10"                        # events (public)
curl -s "$PUB/v1/markets?limit=10"                       # markets (public)
curl -s "$PUB/v1/search?query=Chicago%20temperature&limit=5"  # search (public)
curl -s "$PUB/v1/markets/<slug>/book"                    # order book (public)
curl -s "$PUB/v1/markets/<slug>/bbo"                     # best bid/offer (public)
```

Authenticated calls (`https://api.polymarket.us` + `/v1` paths):
`GET /v1/account/balances`, `GET /v1/portfolio/positions`,
`GET /v1/orders/open`, `POST /v1/orders` to place,
`DELETE /v1/orders/{id}` to cancel one, `DELETE /v1/orders` to cancel all.

## Auth
Credentials come from environment variables at runtime — never hardcoded, never written to files, logs, or memory.

- `POLYMARKET_KEY_ID` — API key UUID, from https://polymarket.us/developer
- `POLYMARKET_SECRET_KEY` — base64 Ed25519 private key (shown **once** at key creation)
- `POLYMARKET_AUTH_BASE` — optional override (default `https://api.polymarket.us`)
- `POLYMARKET_PUBLIC_BASE` — optional override (default `https://gateway.polymarket.us`)

Authenticated requests sign `f"{timestamp_ms}{METHOD}{path}"` with Ed25519 (base64), sending `X-PM-Access-Key` / `X-PM-Timestamp` / `X-PM-Signature`. Timestamps must be within **30s** of server time.

## Operating Rules
1. **Prices are in cents, 1–99.** Every contract pays **$1.00** if correct, **$0** if wrong. Long = bought YES contracts (profit if outcome occurs); short = sold YES contracts (profit if it doesn't).
2. **Every order is real money — no sandbox exists.** Before placing any order, present market / side / size / price / total cost and require the user's explicit confirmation. Never skip this, never batch it silently.
3. **Maker-only.** Taker fee is Θ=0.0695 × C × p × (1−p) (up to $1.74/100 @ 50¢); makers earn a rebate Θ=−0.0125 (up to $0.31/100 @ 50¢), credited at fill. Never take except to close a position the user explicitly names.
4. Use the fee math in rule 3 to sanity-check cost before any first live order on a new path.
5. Verify a position exists (via `positions`) before closing it.
6. Rate limit: **20 req/s per API key** (429 on breach) — back off, prefer the WebSocket for streaming. Orders not processed within 5s are rejected by a latency stopgap ("Global Rate Limit Exceeded" message) — retry logic must distinguish this from a real rate limit.
7. Weekly maintenance window **Thursday 6–8am ET** — avoid scheduling sweeps then.
8. **Settlement sources differ from Kalshi.** Polymarket US weather markets settle on NWS Climatological Reports (e.g. KMDW CLI), Kalshi on The Weather Company. Never treat same-topic cross-venue positions as arbitrage.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
