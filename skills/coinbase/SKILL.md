---
name: "coinbase"
description: "Trade spot crypto on Coinbase Advanced Trade via the official REST API: list accounts and balances, get product prices, place and cancel limit/market orders, check order status and fills. Use when the user wants Coinbase trading, balances, or prices."
---

# Coinbase (Advanced Trade)

## Purpose
Manage Coinbase Advanced Trade spot trading: accounts/balances, product prices, limit/market orders, cancels, order status, fills.

## Tooling
CLI: `~/workspace/skills/coinbase/bin/coinbase` (stdlib + `requests`; pure-python P-256 ECDSA for the per-request ES256 JWT — no crypto dependency).

```bash
bin/coinbase products --limit 10        # list spot products (public, no auth)
bin/coinbase price BTC-USD              # price + bid/ask (public, no auth)
bin/coinbase accounts                   # balances with available amounts (auth)
bin/coinbase place-order --product BTC-USD --side buy --size 0.001 --price 90000
bin/coinbase place-order --product ETH-USD --side sell --size 0.05 --market
bin/coinbase cancel-order <order_id>    # cancel via batch_cancel (auth)
bin/coinbase order <order_id>           # order status (auth)
bin/coinbase fills --product-id BTC-USD --limit 20   # recent fills (auth)
```

Append `--json` to any command for raw API output.

## Auth
Credentials come from environment variables at runtime, injected by the agent from the Secure Vault. **Never write them to files, logs, or memory; never print them.**

- `COINBASE_API_KEY_NAME` — key name like `organizations/{orgId}/apiKeys/{keyId}`, from the CDP portal (Secret API Keys tab, signature algorithm **ECDSA**, permissions View + Trade — never Transfer for trading jobs)
- `COINBASE_API_PRIVATE_KEY_PEM` — EC private key PEM *contents* (shown once at key creation), or `COINBASE_API_PRIVATE_KEY_PATH` for a PEM file path
- `COINBASE_JWT_ISS` — JWT issuer override (default `cdp`)
- `COINBASE_BASE_URL` — optional override (default `https://api.coinbase.com`)

Every request sends `Authorization: Bearer <JWT>`: an ES256 JWT signed with the EC private key, fresh per request (header `{alg,kid,nonce,typ}`, claims `{sub,iss,nbf,exp=nbf+120,uri="METHOD api.coinbase.com/api/v3/brokerage/<path>"}`). See `references/api-notes.md` for the exact scheme.

## Operating Rules
1. **place-order moves real money.** Never place orders from an exploratory session — only under a job carrying David's standing trading authority with explicit limits.
2. `--size` is in **base** currency units (`0.001` = 0.001 BTC), `--price` in **quote** currency (USD). Limit orders are good-til-canceled; `--market` sends an immediate-or-cancel market order (always pays taker).
3. Fees (entry tier — verify the current schedule before sizing): ~0.40% maker / ~0.60% taker.
4. Cancel goes through `batch_cancel`; a single id is fine.
5. On 401/403, check the JWT was attached (Authorization header present) before blaming the key — and confirm the key was created with the **ECDSA** algorithm, not Ed25519 (unsupported by Coinbase App APIs).
6. A static-mock sandbox exists at `https://api-sandbox.coinbase.com` (accounts + orders only, no live market) — useful for plumbing checks via `COINBASE_BASE_URL`.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
