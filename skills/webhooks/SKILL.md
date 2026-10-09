---
name: "webhooks"
description: "Accept webhook POSTs on localhost, answer quickly, and ignore duplicate retries. Use when another service needs to notify this machine."
---

# Webhooks

Listen on localhost for JSON POST requests, store each new event, and answer `204` before doing slow work. A second delivery of the same `id` is ignored.

## When to use

Some other program needs to notify this machine with an HTTP POST, and you can point it at `127.0.0.1`. The listener below is the standard-library handler for that. It writes events to `events.jsonl` in the current directory.

## Install

Python 3 is the only dependency. There is no package to install.

```sh
python3 -c "import http.server; print('ok')"
```

Save this as `webhook_receive.py`:

```python
#!/usr/bin/env python3
"""Receive webhook POSTs on localhost and append new events to events.jsonl."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8787
OUT = Path("events.jsonl")
MAX_BODY = 1_000_000


def known_ids():
    if not OUT.exists():
        return set()
    ids = set()
    for line in OUT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_id = event.get("id")
        if isinstance(event_id, str):
            ids.add(event_id)
    return ids


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.split("?", 1)[0] != "/hook":
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if n <= 0 or n > MAX_BODY:
            self.send_error(413 if n > MAX_BODY else 400)
            return
        raw = self.rfile.read(n)
        try:
            event = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400)
            return
        if not isinstance(event, dict):
            self.send_error(400)
            return
        event_id = event.get("id")
        if isinstance(event_id, str) and event_id in known_ids():
            self.send_response(204)
            self.end_headers()
            return
        with OUT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, separators=(",", ":")) + "\n")
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
```

## Commands

Start the listener, then send an event. A repeat of the same `id` still returns `204` and does not add a second line.

```sh
python3 webhook_receive.py
```

```sh
curl -sS -D - -o /dev/null -X POST http://127.0.0.1:8787/hook \
  -H 'Content-Type: application/json' \
  -d '{"id":"evt_1","type":"ping"}'
```

Read what was stored:

```sh
cat events.jsonl
```

## Gotchas

- The server binds to `127.0.0.1` only. A sender on another machine cannot reach it until you change `HOST` on purpose.
- Answer with `204` as soon as the event is stored. A non-2xx status is a signal for the sender to retry.
- The same `id` is stored once. The second POST still returns `204`, which tells the sender to stop retrying.
- Bodies that are empty, not JSON, or not an object get `400`. Bodies over 1,000,000 bytes get `413`.
- The handler stores the JSON. It does not execute it.

---
Also on Honeypot — a free, open index of skills for AI agents: https://honeypot-e6c.pages.dev
[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)
