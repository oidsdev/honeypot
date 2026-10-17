#!/usr/bin/env python3
"""Stdio checks for the Honeypot MCP server.

Launches mcp-server.py, speaks JSON-RPC over stdin/stdout, and compares
tool results with api/skills.json and api/editors-picks.json. The child
is pointed at a local static server of this repo (HONEYPOT_BASE) so those
files are the source of truth.

    python3 tests/test_mcp_server.py

Exit 0 when every check passes, 1 otherwise.
"""

import json
import os
import queue
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "mcp-server.py"
SEARCH_QUERY = "oids"  # the one search fixture
DOCUMENTED_TOOLS = (
    "search_skills",
    "get_skill",
    "list_categories",
    "get_editors_picks",
)
BOGUS_SLUG = "not-a-real-skill"


def shorten(text, limit=160):
    flat = " ".join(str(text).split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 3] + "..."


def load_json(name):
    path = ROOT / "api" / name
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def categories_from_index(skills):
    counts = {}
    for skill in skills:
        category = skill.get("category", "uncategorized")
        counts[category] = counts.get(category, 0) + 1
    return [{"name": key, "skills": counts[key]} for key in sorted(counts)]


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        return


class Client:
    def __init__(self, proc):
        self.proc = proc
        self.next_id = 1
        self.lines = queue.Queue()
        self.stderr_lines = []
        self.stderr_lock = threading.Lock()
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self):
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def _read_stderr(self):
        for line in self.proc.stderr:
            with self.stderr_lock:
                self.stderr_lines.append(line)

    def stderr_mark(self):
        with self.stderr_lock:
            return len(self.stderr_lines)

    def stderr_since(self, mark):
        with self.stderr_lock:
            return "".join(self.stderr_lines[mark:])

    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._write(msg)

    def request(self, method, params=None, timeout=15):
        if self.proc.poll() is not None:
            raise RuntimeError("server exited (%s)" % self.proc.returncode)
        mid = self.next_id
        self.next_id += 1
        msg = {"jsonrpc": "2.0", "id": mid, "method": method}
        if params is not None:
            msg["params"] = params
        self._write(msg)
        line = self._readline(timeout)
        try:
            resp = json.loads(line)
        except json.JSONDecodeError:
            raise AssertionError("response was not JSON: %s" % shorten(line))
        if resp.get("id") != mid:
            raise AssertionError(
                "response id %r did not match request %s" % (resp.get("id"), mid)
            )
        return resp

    def call_tool(self, name, arguments=None):
        resp = self.request(
            "tools/call", {"name": name, "arguments": arguments or {}}
        )
        if "error" in resp and "result" not in resp:
            message = resp["error"].get("message", resp["error"])
            raise AssertionError("tool error: %s" % shorten(message))
        return self.parse_tool(resp), resp

    def parse_tool(self, resp):
        result = resp.get("result")
        if not isinstance(result, dict):
            raise AssertionError("missing tool result")
        content = result.get("content") or []
        if not content or content[0].get("type") != "text":
            raise AssertionError("tool result has no text content")
        text = content[0].get("text") or ""
        if "Traceback" in text:
            raise AssertionError("traceback in tool result")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise AssertionError("tool text was not JSON: %s" % shorten(text))

    def _write(self, msg):
        try:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            raise RuntimeError("server exited (%s)" % self.proc.poll())

    def _readline(self, timeout):
        try:
            line = self.lines.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError("no response within %ss" % timeout)
        if line is None:
            raise RuntimeError("server closed stdout (exit %s)" % self.proc.poll())
        return line


def start():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    env = os.environ.copy()
    for key in (
        "http_proxy",
        "https_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "all_proxy",
    ):
        env.pop(key, None)
    env["NO_PROXY"] = "127.0.0.1,localhost"
    env["HONEYPOT_BASE"] = "http://127.0.0.1:%s" % port
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=1,
    )
    return httpd, proc, Client(proc)


def stop(proc, httpd):
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
    if httpd is not None:
        httpd.shutdown()
        httpd.server_close()


def skill_by_name(skills, name):
    for skill in skills:
        if skill.get("name") == name:
            return skill
    return None


def check_initialize(client, _skills, _picks):
    resp = client.request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "honeypot-mcp-test", "version": "0"},
        },
    )
    if "error" in resp and "result" not in resp:
        raise AssertionError(shorten(resp["error"]))
    info = (resp.get("result") or {}).get("serverInfo") or {}
    name = info.get("name")
    version = info.get("version")
    if not isinstance(name, str) or not name.strip():
        raise AssertionError("missing server name")
    if name != "honeypot":
        raise AssertionError("server name %r" % name)
    if not isinstance(version, str) or not version.strip():
        raise AssertionError("missing server version")
    client.notify("notifications/initialized")


def check_tools_list(client, _skills, _picks):
    resp = client.request("tools/list")
    tools = (resp.get("result") or {}).get("tools")
    if not isinstance(tools, list):
        raise AssertionError("tools/list did not return a list")
    names = [tool.get("name") for tool in tools]
    if len(names) != len(DOCUMENTED_TOOLS) or set(names) != set(DOCUMENTED_TOOLS):
        raise AssertionError("tools %s" % names)


def check_list_categories(client, skills, _picks):
    payload, _resp = client.call_tool("list_categories")
    got = payload.get("categories")
    expected = categories_from_index(skills)
    if got != expected:
        raise AssertionError(
            "categories %s != %s" % (shorten(got), shorten(expected))
        )


def check_search_skills(client, skills, _picks):
    known = skill_by_name(skills, SEARCH_QUERY)
    if known is None:
        raise AssertionError(
            "search fixture %r is not a skill name in api/skills.json" % SEARCH_QUERY
        )
    payload, _resp = client.call_tool(
        "search_skills", {"query": SEARCH_QUERY, "limit": 50}
    )
    hits = payload.get("skills") or []
    match = [hit for hit in hits if hit.get("name") == known["name"]]
    if not match:
        raise AssertionError(
            "query %r did not return %s" % (SEARCH_QUERY, known["name"])
        )
    if match[0].get("description") != known.get("description"):
        raise AssertionError("description mismatch for %s" % known["name"])


def check_get_skill(client, skills, _picks):
    real = None
    for skill in skills:
        if skill.get("name") and skill.get("description"):
            real = skill
            break
    if real is None:
        raise AssertionError("api/skills.json has no skill with a description")
    payload, _resp = client.call_tool("get_skill", {"name": real["name"]})
    if payload.get("found") is not True:
        raise AssertionError("get_skill did not find %s" % real["name"])
    got = (payload.get("skill") or {}).get("description")
    if got != real["description"]:
        raise AssertionError(
            "description %s != %s" % (shorten(got), shorten(real["description"]))
        )

    names = {skill.get("name") for skill in skills}
    bogus = BOGUS_SLUG
    while bogus in names:
        bogus += "-x"
    mark = client.stderr_mark()
    resp = client.request(
        "tools/call", {"name": "get_skill", "arguments": {"name": bogus}}
    )
    stderr = client.stderr_since(mark)
    blob = json.dumps(resp)
    if "Traceback" in blob or "Traceback" in stderr:
        raise AssertionError("traceback for bogus slug")
    if client.proc.poll() is not None:
        raise AssertionError("server exited on bogus slug (%s)" % client.proc.returncode)
    miss = client.parse_tool(resp)
    if miss.get("found") is not False:
        raise AssertionError("expected a not-found result, got %s" % shorten(miss))
    if miss.get("name") != bogus:
        raise AssertionError("not-found result named %r" % miss.get("name"))

    follow, _resp = client.call_tool("get_skill", {"name": real["name"]})
    if follow.get("found") is not True:
        raise AssertionError("server did not answer a follow-up get_skill")
    if (follow.get("skill") or {}).get("description") != real["description"]:
        raise AssertionError("follow-up get_skill returned the wrong description")


def check_editors_picks(client, _skills, picks_doc):
    payload, _resp = client.call_tool("get_editors_picks")
    expected = [pick.get("name") for pick in picks_doc.get("picks") or []]
    got = [pick.get("name") for pick in payload.get("picks") or []]
    if got != expected:
        raise AssertionError("slugs %s != %s" % (shorten(got), shorten(expected)))


CHECKS = (
    ("initialize", check_initialize),
    ("tools/list", check_tools_list),
    ("list_categories", check_list_categories),
    ("search_skills", check_search_skills),
    ("get_skill", check_get_skill),
    ("get_editors_picks", check_editors_picks),
)


def main():
    skills_doc = load_json("skills.json")
    picks_doc = load_json("editors-picks.json")
    skills = skills_doc.get("skills") or []
    httpd = None
    proc = None
    results = []
    try:
        httpd, proc, client = start()
        for name, fn in CHECKS:
            try:
                fn(client, skills, picks_doc)
            except Exception as exc:  # noqa: BLE001 - one line per check
                results.append((name, False, shorten(exc)))
            else:
                results.append((name, True, ""))
    except Exception as exc:  # noqa: BLE001 - harness failure still prints a summary
        print("FAIL setup: %s" % shorten(exc))
        return 1
    finally:
        stop(proc, httpd)

    failed = 0
    for name, ok, detail in results:
        if ok:
            print("PASS %s" % name)
        else:
            failed += 1
            print("FAIL %s: %s" % (name, detail))
    if failed:
        print("%d failed" % failed)
        return 1
    print("%d passed" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
