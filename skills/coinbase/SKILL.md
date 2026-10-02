---
name: "coinbase"
description: "Trade spot crypto on Coinbase Advanced Trade via the official REST API: list accounts and balances, get product prices, place and cancel limit/market orders, check order status and fills. Use when the user wants Coinbase trading, balances, or prices."
---

# Coinbase (Advanced Trade)

## Purpose
Manage Coinbase Advanced Trade spot trading: accounts/balances, product prices, limit/market orders, cancels, order status, fills.

## Tooling
No bundled CLI — call the official REST APIs directly with any HTTP client
(e.g. `curl`). Public market data needs no auth; everything under
`/api/v3/brokerage` needs the `Authorization: Bearer <JWT>` header from the
Auth section below.

```bash
PUB=https://api.exchange.coinbase.com   # public market data (no auth)
BASE=https://api.coinbase.com/api/v3/brokerage

curl -s "$PUB/products" | head -c 600              # list spot products (public)
curl -s "$PUB/products/BTC-USD/ticker"             # BTC price + bid/ask (public)
curl -s -H "Authorization: Bearer $JWT" \
  "$BASE/accounts?limit=250"                       # balances (auth)
```

Place, cancel, and query orders via `$BASE/orders`: POST to create, POST
`$BASE/orders/batch_cancel` to cancel, GET
`$BASE/orders/historical/{order_id}` for status — same JWT header on each.

## Auth
Credentials come from environment variables at runtime — never hardcoded, never written to files, logs, or memory.

- `COINBASE_API_KEY_NAME` — key name like `organizations/{orgId}/apiKeys/{keyId}`, from the CDP portal (Secret API Keys tab, signature algorithm **ECDSA**, permissions View + Trade — never Transfer for trading jobs)
- `COINBASE_API_PRIVATE_KEY_PEM` — EC private key PEM *contents* (shown once at key creation), or `COINBASE_API_PRIVATE_KEY_PATH` for a PEM file path
- `COINBASE_JWT_ISS` — JWT issuer override (default `cdp`)
- `COINBASE_BASE_URL` — optional override (default `https://api.coinbase.com`)

Every request sends `Authorization: Bearer <JWT>`: an ES256 JWT signed with the EC private key, fresh per request (header `{alg,kid,nonce,typ}`, claims `{sub,iss,nbf,exp=nbf+120,uri="METHOD api.coinbase.com/api/v3/brokerage/<path>"}`). The `uri` uses the full request path **without** the query string, and the bare API host (no scheme).

## Operating Rules
1. **Orders move real money.** Never place orders from an exploratory session — only with the user's explicit trading authority and stated limits.
2. Order size is in **base** currency units (`0.001` = 0.001 BTC), price in **quote** currency (USD). Limit orders are good-til-canceled; market orders are immediate-or-cancel (always pay taker).
3. Fees (entry tier — verify the current schedule before sizing): ~0.40% maker / ~0.60% taker.
4. Cancel goes through `batch_cancel`; a single id is fine.
5. On 401/403, check the JWT was attached (Authorization header present) before blaming the key — and confirm the key was created with the **ECDSA** algorithm, not Ed25519 (unsupported by Coinbase App APIs).
6. A static-mock sandbox exists at `https://api-sandbox.coinbase.com` (accounts + orders only, no live market) — useful for plumbing checks via `COINBASE_BASE_URL`.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
