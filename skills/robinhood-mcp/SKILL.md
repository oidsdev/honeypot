---
name: "robinhood-mcp"
description: "Trade Robinhood via the official Agentic Trading MCP server (OAuth DCR + PKCE). Read balances, positions, orders; place long equity/option orders in the Agentic account."
icon: "robinhood"
metadata: { "includeInPrompt": false }
---

# Robinhood MCP

## Purpose
Connect to Robinhood's official Agentic Trading MCP server
(`https://agent.robinhood.com/mcp/trading`) — the sanctioned route for
agentic trading. Reads span all Robinhood accounts (balances, positions,
orders); **order placement is confined to the funded Agentic account**.
Today the server supports long equities and options orders only
(agentic crypto was announced, not yet live as of 2026-09-25).

Do NOT use unofficial routes (`robin_stocks` and similar reverse-engineer
the private app API and violate the customer agreement — account risk).

## Tooling
Use `exec` to run (`~/workspace/bin` is on PATH):

```sh
robinhood-mcp <subcommand> [options]
```

### Connection management

```sh
robinhood-mcp status
robinhood-mcp authorize-url
robinhood-mcp exchange-code --code <code>
robinhood-mcp refresh
robinhood-mcp disconnect
```

### MCP operations

```sh
robinhood-mcp list-tools
robinhood-mcp call-tool --name <tool> --arguments-json '<json-object>'
```

`--arguments-json` must be a JSON object; arrays or scalars are rejected. Use
`list-tools` first to discover the tool catalogue and each tool's
`inputSchema`. Never guess tool names.

## Auth
OAuth 2.1 authorization code + PKCE S256 with **Dynamic Client
Registration** (RFC 7591) — verified live 2026-09-25:
- Authorization server metadata:
  `https://agent.robinhood.com/.well-known/oauth-authorization-server`
- `authorization_endpoint`: `https://robinhood.com/oauth`
- `token_endpoint`: `https://api.robinhood.com/oauth2/token/`
- `registration_endpoint`:
  `https://agent.robinhood.com/oauth/trading/register` (open, no secret)
- Public client (`token_endpoint_auth_methods_supported: ["none"]`);
  PKCE is what protects the exchange. Scope is fixed: `internal`.

OAuth state lives in `~/.config/robinhood-mcp/state.json` (mode 0600).
The credential never leaves this VM. (Unlike Meta's built-in connectors,
this CLI keeps its own OAuth state because authd credential writes are
not available to sandbox callers.)

## First-use setup flow

1. Run `robinhood-mcp status`.
2. If status is `not_connected`, run `robinhood-mcp authorize-url`.
   It prints an `authorize_url` plus step-by-step instructions.
3. The user opens the URL in their own browser, signs in to Robinhood,
   and approves the connection. If the browser asks for in-app approval,
   they approve in the Robinhood mobile app.
4. After approval the browser tries to open
   `http://127.0.0.1:18765/callback` and fails — the user copies the
   `code` value from the address bar.
5. Run `robinhood-mcp exchange-code --code <code>`.
6. Re-run `robinhood-mcp status`. When it flips to `connected` the output
   includes the server info and discovered tool catalogue.

The user needs a funded **Agentic account** (created in the Robinhood
app under the Agentic Trading settings) before any order placement —
reads work without one.

## Operating Rules
1. Run `robinhood-mcp status` before any MCP work. If not `connected`,
   complete the setup flow first.
2. Call `list-tools` before `call-tool` unless you already know the tool
   name and its argument shape. Never guess tool names.
3. `arguments-json` must be a JSON object; wrap every argument appropriately.
4. Token refresh is automatic on expiry and on a single 401 retry. If
   `call-tool` keeps failing with 401, run `robinhood-mcp refresh`
   explicitly or ask the user to re-authorize.
5. Read-only exploration first: balances, positions, and order history
   before designing any strategy. Never place an order the user's mandate
   does not cover.
6. Every trade mention names the venue ("Robinhood — ..."), same as the
   Kalshi / Polymarket US standing rule.
