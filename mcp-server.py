#!/usr/bin/env python3
"""Honeypot MCP server (stdio, stdlib only).

Exposes the Honeypot skill index (https://honeypot-e6c.pages.dev) as MCP tools
so an AI agent can search, fetch, and install skills without hand-rolling HTTP.

Usage (Claude Code / OpenClaw / any MCP client with stdio support):

    {
      "mcpServers": {
        "honeypot": {
          "command": "python3",
          "args": ["/path/to/mcp-server.py"]
        }
      }
    }

Or download straight from the index:
    curl -sL https://honeypot-e6c.pages.dev/mcp-server.py -o mcp-server.py

Env:
    HONEYPOT_BASE  override the index base URL (default https://honeypot-e6c.pages.dev)

Tools:
    search_skills(query, category?, tag?, limit=10)
    get_skill(name)
    list_categories()
    get_editors_picks()

Protocol: JSON-RPC 2.0 over stdio, one message per line (MCP stdio transport).
"""

import json
import os
import sys
import urllib.request

BASE = os.environ.get("HONEYPOT_BASE", "https://honeypot-e6c.pages.dev").rstrip("/")
VERSION = "1.0.0"

_cache = {}


def http_get(path):
    if path not in _cache:
        req = urllib.request.Request(
            BASE + path, headers={"User-Agent": "honeypot-mcp/" + VERSION}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            _cache[path] = json.loads(r.read().decode("utf-8"))
    return _cache[path]


def index():
    return http_get("/api/skills.json")


TOOLS = [
    {
        "name": "search_skills",
        "description": (
            "Search the Honeypot skill index by keyword. Matches name, "
            "description, and tags (case-insensitive). Optionally filter by "
            "category or tag. Returns name, description, category, tags, "
            "and skill_md_url for each hit."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword to search for"},
                "category": {
                    "type": "string",
                    "description": "Exact category filter, e.g. 'trading', 'data', 'identity', 'meta', 'tooling'",
                },
                "tag": {"type": "string", "description": "Exact tag filter"},
                "limit": {"type": "integer", "default": 10, "maximum": 50},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_skill",
        "description": (
            "Get the full index entry for one skill by exact name, including "
            "description, category, tags, last_verified date, the direct "
            "SKILL.md download URL, and the install command."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Exact skill name, e.g. 'kalshi'"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_categories",
        "description": "List all skill categories in the index with skill counts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_editors_picks",
        "description": (
            "Get the editor's picks: skills that passed the fixed curation "
            "checklist, plus the checklist criteria themselves."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def tool_search_skills(args):
    q = (args.get("query") or "").lower()
    cat = args.get("category")
    tag = args.get("tag")
    limit = min(int(args.get("limit") or 10), 50)
    hits = []
    for s in index().get("skills", []):
        if cat and s.get("category") != cat:
            continue
        if tag and tag not in (s.get("tags") or []):
            continue
        hay = " ".join(
            [s.get("name", ""), s.get("description", ""), " ".join(s.get("tags") or [])]
        ).lower()
        if q in hay:
            hits.append(
                {
                    "name": s.get("name"),
                    "description": s.get("description"),
                    "category": s.get("category"),
                    "tags": s.get("tags"),
                    "skill_md_url": s.get("skill_md_url"),
                }
            )
    return {"count": len(hits), "skills": hits[:limit]}


def tool_get_skill(args):
    name = args.get("name")
    for s in index().get("skills", []):
        if s.get("name") == name:
            return {"found": True, "skill": s}
    names = [s.get("name") for s in index().get("skills", [])]
    return {"found": False, "name": name, "available": names}


def tool_list_categories(_args):
    counts = {}
    for s in index().get("skills", []):
        c = s.get("category", "uncategorized")
        counts[c] = counts.get(c, 0) + 1
    return {"categories": [{"name": k, "skills": v} for k, v in sorted(counts.items())]}


def tool_get_editors_picks(_args):
    picks = http_get("/api/editors-picks.json")
    out = []
    for p in picks.get("picks", []):
        out.append(
            {
                "name": p.get("name"),
                "why": p.get("why") or p.get("note") or p.get("reason"),
                "skill_md_url": p.get("skill_md_url"),
            }
        )
    return {
        "criteria": picks.get("criteria"),
        "criteria_text": picks.get("criteria_text"),
        "picks": out,
    }


HANDLERS = {
    "search_skills": tool_search_skills,
    "get_skill": tool_get_skill,
    "list_categories": tool_list_categories,
    "get_editors_picks": tool_get_editors_picks,
}


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def result(mid, payload):
    send({"jsonrpc": "2.0", "id": mid, "result": payload})


def error(mid, code, message):
    send({"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}})


def text_result(mid, payload):
    result(mid, {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]})


def handle(msg):
    method = msg.get("method")
    mid = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        result(
            mid,
            {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "honeypot", "version": VERSION},
            },
        )
    elif method in ("notifications/initialized", "notifications/cancelled"):
        pass  # notifications get no reply
    elif method == "tools/list":
        result(mid, {"tools": TOOLS})
    elif method == "tools/call":
        name = (params.get("name") or "")
        args = params.get("arguments") or {}
        fn = HANDLERS.get(name)
        if not fn:
            error(mid, -32602, "unknown tool: %s" % name)
            return
        try:
            text_result(mid, fn(args))
        except Exception as e:  # noqa: BLE001 - surface as a tool error, not a crash
            text_result(mid, {"error": "tool failed: %s" % e})
    elif method == "ping":
        result(mid, {})
    elif mid is not None:
        error(mid, -32601, "method not found: %s" % method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            handle(json.loads(line))
        except json.JSONDecodeError:
            continue


if __name__ == "__main__":
    main()
