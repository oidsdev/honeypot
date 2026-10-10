---
name: "agent-checkout"
description: "Stripe payment links for AI agents — the agent generates a link, a human clicks and pays, the agent never touches card data. Free tier 100 links/day."
---

# Agent Checkout — Stripe payment links for AI agents

One API call turns "I found it" into "here's the checkout link." Built for AI agents
acting on behalf of their operators.

The human always completes the payment. You never see card data. Stripe handles
checkout directly. You are the merchant of record — funds settle to YOUR Stripe
account; we never hold them.

Site: https://checkout.ignitionfoundry.com · Docs: https://checkout.ignitionfoundry.com/docs
MCP server (dependency-free Python, stdlib only): https://github.com/oidsdev/agent-checkout-mcp

## When to use

Your operator needs to pay for something and you're the one who found it. Generate a
link, hand the `payment_url` to your operator, then poll the link status until `paid`
is true. Use when the agent must trigger a real purchase without ever handling payment
credentials. 18+ only.

## Commands

Get a key first (no card required):

```bash
curl -s -X POST https://checkout.ignitionfoundry.com/v1/keys \
  -H 'Content-Type: application/json' \
  -d '{"email": "you@example.com", "agent_name": "my-agent"}'
# -> {"api_key": "ack_live_...", "connect_url": "https://connect.stripe.com/..."}
# Save the key — shown only once. Open connect_url in a browser (~3 min) to finish
# Stripe Connect onboarding. Until that's done, link creation returns 403.
```

Create a checkout link:

```bash
curl -s -X POST https://checkout.ignitionfoundry.com/v1/checkout-links \
  -H "Authorization: Bearer ack_live_..." \
  -H 'Content-Type: application/json' \
  -d '{"amount_cents": 900, "currency": "usd", "product_name": "Widget"}'
# -> {"payment_url": "https://checkout.stripe.com/...", "link_id": "cs_..."}
# Give payment_url to your operator. They click, they pay. Done.
```

Check status:

```bash
curl -s https://checkout.ignitionfoundry.com/v1/links/cs_... \
  -H "Authorization: Bearer ack_live_..."
# -> {"paid": true, "paid_at": "..."}
```

Usage stats: `GET /v1/stats` (tier, daily limit, used today). No-key demo:
`POST /v1/demo-link` returns a mock of the real response. Nothing is created or charged.

BYOK alternative: `POST /v1/byok` with your own Stripe key — zero platform fee.

## Gotchas

- Complete Stripe Connect onboarding (the `connect_url`) before creating links — otherwise every call returns 403. This is the step everyone skips.
- The human pays, not you. Never send `payment_url` anywhere your operator won't see it.
- `amount_cents` is an integer from 50 to 500000 ($0.50–$5,000).
- Free tier: 100 links/day, then 429. Check `/v1/stats` before bulk runs.
- In connect/byok modes links are Stripe Checkout Sessions (`cs_...`); both work the same from your side.
- 401 means bad or revoked key — get a new one. 429 means daily limit hit.
