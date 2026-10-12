---
name: "context7"
description: "Look up current library docs through Upstash Context7. Use when an agent needs the current API for a package."
---

# Context7

Fetch current documentation for a library from [Context7](https://github.com/upstash/context7) (MIT, Upstash). The `ctx7` CLI and the `@upstash/context7-mcp` server read the same index. Use the CLI for a one-off lookup. Point an MCP client at the server when the agent should call the tools itself.

## When to use

The task depends on the current API of a library, framework, SDK, or CLI: a signature, a config field, or a setup step. The query goes to Context7, so keep private code out of it.

## Install

The CLI needs Node.js 22.13 or newer. The MCP package needs Node.js 20.18.1 or newer.

```sh
node -v
npx -y ctx7@latest --version
npx -y @upstash/context7-mcp@latest --version
```

Checked on 2026-10-12: `ctx7` 0.6.0 and `@upstash/context7-mcp` 4.3.0. `@latest` moves.

Stdio config for an MCP client. Calls without a key returned results. A key from the Context7 dashboard raises the rate limit. If the user already has one, pass it the way that client expects. Leave the key out of this file.

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

## Commands

Resolve a name, then query that id. `--json` prints output an agent can parse.

```sh
npx -y ctx7@latest library react "useEffect cleanup" --json
npx -y ctx7@latest docs /react/react "useEffect cleanup function" --json
```

`ctx7 docs` takes `--language` (for example `Python`) so examples in that language rank first.

MCP tools, with the fields the 4.3.0 package publishes:

1. `resolve-library-id` with `libraryName` and `query`.
2. `query-docs` with `libraryId` from that result, a `query` about one topic, and optional `language`.

Skip the resolve step only when the user already gave an id shaped like `/org/project` or `/org/project/version`.

## Gotchas

- Several libraries can share a name. Prefer the id whose name matches, with more snippets and a higher reputation score.
- Use the library's usual punctuation in `libraryName`, such as `Next.js`.
- An old id can redirect. `/facebook/react` answered with a redirect to `/react/react`. Query the new id.
- One topic per query. The MCP tool text says to stop after 3 calls to either tool on the same question.
- A failed upstream call sets the tool error flag on `query-docs`. An empty "no documentation" result is a normal answer.
- The query is sent to Context7. Leave out keys, passwords, and private code.
- `ctx7 setup` and `ctx7 login` change agent config and can open a browser login. Run them only when the user asked to install Context7.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
