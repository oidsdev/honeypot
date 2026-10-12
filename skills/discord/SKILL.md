---
name: "discord"
description: "Use the Discord Bot API from an agent: read and post messages, list servers and channels, add reactions, and build an invite link. Use when the user wants Discord posting, monitoring, or a bot set up."
---

# Discord (Bot API)

## Purpose
Give an agent a presence on Discord through an official **bot application**:
see which servers the bot is in, list channels, read recent messages, post,
and react. This is the only sanctioned route — automating a personal user
account (a "self-bot") violates Discord's Terms of Service and gets the
account banned.

## Setup
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   and create an application, then add a **Bot** to it.
2. Copy the bot token (shown once) and store it in a local file with mode
   0600, e.g. `~/.discord-bot-token`. Never commit it, log it, or paste it
   into chat.
3. Under **Bot → Privileged Gateway Intents**, enable the intents you need:
   - **Server Members** — list/enumerate guild members
   - **Message Content** — read message text via the Gateway (REST history
     reads work without it, but anything event-driven needs it)
   - **Presence** — see member online status
4. Invite the bot to a server with the OAuth2 URL (see Tooling). A **server
   admin** must open it and pick the server — bots cannot accept normal
   `discord.gg` invite links and cannot join servers on their own.

## Tooling
Plain REST against `https://discord.com/api/v10` with any HTTP client.
Every request sends `Authorization: Bot <token>`. A small wrapper script
with subcommands (`info`, `guilds`, `channels`, `read`, `post`, `react`,
`invite`) keeps the calls one line each; the raw endpoints are:

```bash
BASE=https://discord.com/api/v10
AUTH="Authorization: Bot $(cat ~/.discord-bot-token)"

curl -s -H "$AUTH" "$BASE/users/@me"                       # who am I (bot identity)
curl -s -H "$AUTH" "$BASE/users/@me/guilds"                # servers the bot is in
curl -s -H "$AUTH" "$BASE/guilds/<guild_id>/channels"      # channels in a server
curl -s -H "$AUTH" "$BASE/channels/<channel_id>/messages?limit=20"   # recent messages
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"content":"hello"}' "$BASE/channels/<channel_id>/messages"    # post
curl -s -X PUT -H "$AUTH" \
  "$BASE/channels/<channel_id>/messages/<message_id>/reactions/%F0%9F%91%8D/@me"  # react (URL-encoded emoji)
```

Invite URL (permissions are a bitfield; `3072` = View Channel + Send
Messages, a sensible read/post minimum):

```text
https://discord.com/oauth2/authorize?client_id=<your_application_id>&permissions=3072&scope=bot
```

Creating channels, roles, or webhooks needs the matching permissions in
that bitfield (e.g. Manage Channels). If a call returns 403, the bot's
permissions in that server are the first suspect, not the token.

## Auth
- Token lives in a local 0600 file and is read at runtime — never hardcoded,
  never written to logs or memory.
- If the token is reset in the Developer Portal, update the file; the old
  token dies immediately.
- A 401 means the token is wrong or revoked. A 403 means the bot lacks a
  permission (or isn't in that server/channel at all).

## Operating Rules
1. **Bots only.** Never automate a user account, and never ask a user for
   their personal Discord token.
2. The bot can only act in servers it has been invited to. To reach a new
   server, an admin there must open the invite URL — there is no workaround.
3. Respect rate limits: on HTTP 429, wait the `retry_after` seconds in the
   response body instead of retrying immediately.
4. Disclose the bot as a bot where it interacts with people (profile bio is
   a good place) — several jurisdictions require bot disclosure when a bot
   communicates to sell or influence.
5. Follow each server's own rules (self-promotion channels, posting
   frequency) — a bot that spams gets removed, and the removal is usually
   permanent.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
