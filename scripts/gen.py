#!/usr/bin/env python3
"""Rebuild Honeypot's derived static files from api/skills.json.

- api/by-category/<category>.json — per-category indexes (same schema envelope)
- api/changelog.json — append-only record of added skills
- feed.xml — RSS 2.0 of newly added skills
- sitemap.xml — static pages + API endpoints for crawlers

Run from the repo root:  python3 scripts/gen.py
Run it whenever skills.json changes (a weekly cron regenerates changelog/feed).
Static output only; no network, no secrets.
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "api"
SKILLS_JSON = API / "skills.json"
CHANGELOG_JSON = API / "changelog.json"
FEED_XML = ROOT / "feed.xml"
BY_CATEGORY = API / "by-category"
SITEMAP_XML = ROOT / "sitemap.xml"

SITE = "https://honeypot-e6c.pages.dev"
REQUIRED = ["name", "description", "category", "skill_md_url", "install", "tags", "last_verified"]


def git_added(path: str) -> str:
    """First-commit date (YYYY-MM-DD) of a tracked file, else today."""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%ad", "--date=short", "--", path],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip().splitlines()
        return out[-1].strip() if out else date.today().isoformat()
    except Exception:
        return date.today().isoformat()


def main() -> int:
    doc = json.loads(SKILLS_JSON.read_text())
    if not isinstance(doc, dict) or doc.get("schema_version") != "1":
        print("ERROR: api/skills.json must be an object with schema_version '1'", file=sys.stderr)
        return 1
    skills = doc["skills"]
    names = [s["name"] for s in skills]
    if len(names) != len(set(names)):
        print("ERROR: duplicate skill names", file=sys.stderr)
        return 1
    for s in skills:
        missing = [k for k in REQUIRED if k not in s]
        if missing:
            print(f"ERROR: entry {s.get('name')} missing {missing}", file=sys.stderr)
            return 1

    updated = doc.get("updated", date.today().isoformat())

    # 1. per-category indexes
    BY_CATEGORY.mkdir(exist_ok=True)
    cats = sorted({s["category"] for s in skills})
    for cat in cats:
        cat_doc = {
            "schema_version": "1",
            "category": cat,
            "updated": updated,
            "skills": [s for s in skills if s["category"] == cat],
        }
        (BY_CATEGORY / f"{cat}.json").write_text(json.dumps(cat_doc, indent=4) + "\n")
    # drop stale category files
    for f in BY_CATEGORY.glob("*.json"):
        if f.stem not in cats:
            f.unlink()

    # 2. changelog (append-only; backfill from git history on first run)
    if CHANGELOG_JSON.exists():
        changelog = json.loads(CHANGELOG_JSON.read_text())
    else:
        changelog = {"schema_version": "1", "entries": []}
    seen = {e["name"] for e in changelog["entries"]}
    added = 0
    for s in skills:
        if s["name"] not in seen:
            changelog["entries"].append({
                "date": git_added(f"skills/{s['name']}/SKILL.md"),
                "name": s["name"],
                "action": "added",
                "description": s["description"],
                "skill_md_url": s["skill_md_url"],
            })
            added += 1
    changelog["entries"].sort(key=lambda e: (e["date"], e["name"]))
    changelog["generated"] = date.today().isoformat()
    CHANGELOG_JSON.write_text(json.dumps(changelog, indent=4) + "\n")

    # 3. RSS feed from changelog
    items = []
    for e in reversed(changelog["entries"]):
        items.append(
            "    <item>\n"
            f"      <title>{escape(e['name'])} — skill added to Honeypot</title>\n"
            f"      <link>{SITE}/api/skills.json</link>\n"
            f"      <guid isPermaLink=\"false\">honeypot-{escape(e['name'])}-{escape(e['date'])}</guid>\n"
            f"      <pubDate>{escape(e['date'])}T00:00:00Z</pubDate>\n"
            f"      <description>{escape(e['description'])}</description>\n"
            "    </item>"
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>Honeypot — new skills</title>\n"
        f"    <link>{SITE}/</link>\n"
        "    <description>Skills newly added to the Honeypot index for AI agents.</description>\n"
        "    <language>en</language>\n"
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )
    FEED_XML.write_text(feed)

    # 4. sitemap (static pages + API endpoints, stays fresh automatically)
    today = date.today().isoformat()
    urls = [
        ("/", today),
        ("/llms.txt", today),
        ("/skill-template.md", today),
        ("/submitters.md", today),
        ("/badge.svg", today),
        ("/api/skills.json", updated),
        ("/api/changelog.json", today),
        ("/feed.xml", today),
    ] + [(f"/api/by-category/{cat}.json", updated) for cat in cats]
    sm = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{lm}</lastmod></url>\n" for u, lm in urls)
        + "</urlset>\n"
    )
    SITEMAP_XML.write_text(sm)

    # 5. validate everything we wrote
    for p in [SKILLS_JSON, CHANGELOG_JSON, *BY_CATEGORY.glob("*.json")]:
        json.loads(p.read_text())
    from xml.dom import minidom
    minidom.parseString(SITEMAP_XML.read_text())

    print(f"skills: {len(skills)} | categories: {', '.join(cats)} | "
          f"changelog entries: {len(changelog['entries'])} (+{added} new) | feed items: {len(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
