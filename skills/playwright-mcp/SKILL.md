---
name: "playwright-mcp"
description: "Drive a local browser through Microsoft's Playwright MCP server. Use when an agent needs to open a page and act on it."
---

# Playwright MCP

Open pages and click or type through [Playwright MCP](https://github.com/microsoft/playwright-mcp), Microsoft's MCP server for browser automation (`@playwright/mcp`, Apache-2.0). The server hands back an accessibility snapshot. Actions use element refs from that snapshot.

## When to use

A task needs a real page: open a URL, read what is on it, fill a form, or check that a control is there. The MCP client must already be able to start a local stdio server.

## Install

Node.js 18 or newer. Confirm the package, then install the browser it launches.

```sh
node -v
npx -y @playwright/mcp@latest --version
npx -y @playwright/mcp@latest install-browser chromium
```

Point the MCP client at the server. `--headless` matters on a machine with no display. Headed is the default. `-y` lets `npx` install the package without a prompt.

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest", "--headless"]
    }
  }
}
```

## Commands

Call these tools through the MCP client. Names and fields below are the ones the server publishes.

1. `browser_navigate` with `url`. The result includes a snapshot. Each element has a ref.
2. On a large page, `browser_find` with `text` returns matching nodes and their refs.
3. `browser_click` or `browser_type` with `target` set to a ref from that latest snapshot. `browser_type` also takes `text`.

`browser_snapshot` captures the tree again. Pass `depth` when the full tree is too large.

## Gotchas

- Use a ref from the latest snapshot. A click or navigation that changes the page needs a new snapshot before the next `target`.
- `browser_take_screenshot` is for looking. Clicks and typing take a snapshot ref.
- Core tools are on by default. `vision`, `pdf`, `devtools`, `network`, `storage`, `testing`, and `config` stay off until you add them with `--caps`.
- `browser_run_code_unsafe` runs arbitrary JavaScript in the server process. Leave it alone.
- The server binds to localhost. It is not a security boundary. Leave `--host` at the default.
- File access stays inside the workspace roots, and `file://` URLs are blocked. Turn on unrestricted file access only when the user asked for that.
- A normal run stores a profile under `~/.cache/ms-playwright/` on Linux. Pass `--isolated` when the session should stay in memory.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
