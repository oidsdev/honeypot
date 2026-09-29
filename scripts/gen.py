#!/usr/bin/env python3
"""Rebuild Honeypot's derived static files from api/skills.json.

- api/by-category/<category>.json — per-category indexes (same schema envelope)
- api/changelog.json — append-only record of added skills
- feed.xml — RSS 2.0 of newly added skills
- sitemap.xml — static pages + skill pages + API endpoints for crawlers
- skills/<name>/index.html — per-skill page (SEO tags, JSON-LD, backlinks)
- llms-full.txt — every SKILL.md concatenated for crawlers
- api/editors-picks.json — skills passing the published PICK_CRITERIA checklist

Run from the repo root:  python3 scripts/gen.py
Run it whenever skills.json changes (a weekly cron regenerates changelog/feed).
Static output only; no network, no secrets.
"""
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "api"
SKILLS_JSON = API / "skills.json"
CHANGELOG_JSON = API / "changelog.json"
FEED_XML = ROOT / "feed.xml"
BY_CATEGORY = API / "by-category"
SITEMAP_XML = ROOT / "sitemap.xml"
LLMS_FULL = ROOT / "llms-full.txt"
EDITORS_PICKS = API / "editors-picks.json"
SKILLS_DIR = ROOT / "skills"

SITE = "https://honeypot-e6c.pages.dev"
REQUIRED = ["name", "description", "category", "skill_md_url", "install", "tags", "last_verified"]

# Editor's picks checklist. Published verbatim in api/editors-picks.json and on
# the site, so change it here and nowhere else. A skill is a pick when it passes
# every check. No weights, no scores.
PICK_MIN_DESCRIPTION = 40   # characters
PICK_MIN_TAGS = 1
STALE_AFTER_DAYS = 180      # also drives the "stale" badge on index.html


def verified_within(s: dict, today: date, days: int) -> bool:
    try:
        return today - date.fromisoformat(s["last_verified"]) <= timedelta(days=days)
    except (TypeError, ValueError):
        return False


PICK_CRITERIA = [
    ("description", f"description is at least {PICK_MIN_DESCRIPTION} characters",
     lambda s, today: len(s["description"]) >= PICK_MIN_DESCRIPTION),
    ("tags", f"has at least {PICK_MIN_TAGS} tag",
     lambda s, today: len(s["tags"]) >= PICK_MIN_TAGS),
    ("fresh", f"verified in the last {STALE_AFTER_DAYS} days",
     lambda s, today: verified_within(s, today, STALE_AFTER_DAYS)),
    ("skill_md", "links a SKILL.md",
     lambda s, today: bool(s["skill_md_url"])),
]


def editors_picks(skills: list, today: date) -> dict:
    rules = [rule for _, rule, _ in PICK_CRITERIA]
    text = ("Picked by checklist, not by score. A skill makes the list when it passes every check: "
            + "; ".join(rules) + ".")
    picks = [
        {k: s[k] for k in ("name", "description", "category", "skill_md_url", "install", "last_verified")}
        for s in sorted(skills, key=lambda x: x["name"])
        if all(check(s, today) for _, _, check in PICK_CRITERIA)
    ]
    return {
        "schema_version": "1",
        "as_of": today.isoformat(),
        "stale_after_days": STALE_AFTER_DAYS,
        "criteria": [{"id": cid, "rule": rule} for cid, rule, _ in PICK_CRITERIA],
        "criteria_text": text,
        "picks": picks,
    }


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


def skill_page(s: dict) -> str:
    """Static per-skill page: SEO tags, JSON-LD, links back to index + category."""
    name = s["name"]
    desc = s["description"]
    cat = s["category"]
    tags = ", ".join(s["tags"])
    install = s["install"]
    md_url = s["skill_md_url"]
    verified = s["last_verified"]
    esc_t = escape(desc)
    esc_i = escape(install)
    ld = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": name,
        "description": desc,
        "codeRepository": "https://github.com/oidsdev/honeypot",
        "license": "https://opensource.org/licenses/MIT",
        "dateModified": verified,
        "isPartOf": {
            "@type": "WebSite",
            "name": "Honeypot",
            "url": SITE,
        },
    }
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(name)} — a skill on Honeypot</title>
<meta name="description" content="{esc_t}">
<meta property="og:title" content="{escape(name)} — a skill on Honeypot">
<meta property="og:description" content="{esc_t}">
<meta property="og:url" content="{SITE}/skills/{escape(name)}/">
<meta property="og:type" content="article">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='14' fill='%231a1a1a'/%3E%3Ccircle cx='16' cy='16' r='5' fill='%23fff'/%3E%3C/svg%3E">
<script type="application/ld+json">
{json.dumps(ld, indent=2)}
</script>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 38rem; margin: 4rem auto; padding: 0 1rem; line-height: 1.6; color: #1a1a1a; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 0; }}
  a {{ color: #1a1a1a; }}
  code.install {{ display: block; font-size: 0.8rem; background: #f5f5f5; padding: 0.75rem; border-radius: 4px; margin: 1rem 0; overflow-x: auto; white-space: nowrap; }}
  .meta {{ font-size: 0.85rem; color: #666; }}
  footer {{ margin-top: 3rem; font-size: 0.85rem; color: #666; }}
</style>
</head>
<body>
<main>
  <h1>{escape(name)}</h1>
  <p>{esc_t}</p>
  <p class="meta">Category: <a href="/api/by-category/{escape(cat)}.json">{escape(cat)}</a> &middot; Tags: {escape(tags)} &middot; Verified {escape(verified)}</p>
  <h2>Install</h2>
  <code class="install">{esc_i}</code>
  <p>Read the full skill: <a href="{escape(md_url)}">SKILL.md</a></p>
  <p><a href="/">Honeypot</a> — a free, open index of skills for AI agents. Machine-readable. No sign-up, no tracking.</p>
</main>
<footer>
  Indexed on <a href="{SITE}">Honeypot</a>. Want your skill listed? <a href="https://github.com/oidsdev/honeypot#submit-a-skill">Submit a pull request</a>.
</footer>
</body>
</html>
"""


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

    # 4. per-skill static pages (SEO + JSON-LD, links back to index/category)
    skill_urls = []
    for s in skills:
        page = SKILLS_DIR / s["name"] / "index.html"
        page.write_text(skill_page(s))
        skill_urls.append((f"/skills/{s['name']}/", s["last_verified"]))

    # 5. llms-full.txt — every SKILL.md in one file for crawlers
    parts = [
        "# Honeypot — full skill text",
        "# Generated from skills/<name>/SKILL.md. Per-skill source of truth lives there.",
        "# https://honeypot-e6c.pages.dev",
        "",
    ]
    for s in sorted(skills, key=lambda x: x["name"]):
        md_path = SKILLS_DIR / s["name"] / "SKILL.md"
        parts.append(f"# ===== {s['name']} =====")
        parts.append(md_path.read_text().rstrip())
        parts.append("")
    LLMS_FULL.write_text("\n".join(parts))

    # 6. editor's picks (deterministic checklist above; same date as the sitemap)
    today = date.today().isoformat()
    picks_doc = editors_picks(skills, date.fromisoformat(today))
    EDITORS_PICKS.write_text(json.dumps(picks_doc, indent=4) + "\n")

    # 7. sitemap (static pages + skill pages + API endpoints, stays fresh automatically)
    urls = [
        ("/", today),
        ("/llms.txt", today),
        ("/llms-full.txt", today),
        ("/skill-template.md", today),
        ("/submitters.md", today),
        ("/badge.svg", today),
        ("/api/skills.json", updated),
        ("/api/changelog.json", today),
        ("/api/editors-picks.json", today),
        ("/feed.xml", today),
        ("/faq/", today),
    ] + [(f"/api/by-category/{cat}.json", updated) for cat in cats] + skill_urls
    sm = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{lm}</lastmod></url>\n" for u, lm in urls)
        + "</urlset>\n"
    )
    SITEMAP_XML.write_text(sm)

    # 8. validate everything we wrote
    for p in [SKILLS_JSON, CHANGELOG_JSON, EDITORS_PICKS, *BY_CATEGORY.glob("*.json")]:
        json.loads(p.read_text())
    from xml.dom import minidom
    minidom.parseString(SITEMAP_XML.read_text())
    assert LLMS_FULL.exists() and LLMS_FULL.stat().st_size > 0
    for s in skills:
        assert (SKILLS_DIR / s["name"] / "index.html").exists()

    print(f"skills: {len(skills)} | categories: {', '.join(cats)} | "
          f"changelog entries: {len(changelog['entries'])} (+{added} new) | feed items: {len(items)} | "
          f"editor's picks: {len(picks_doc['picks'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
