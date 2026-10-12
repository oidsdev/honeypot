#!/usr/bin/env python3
"""Rebuild Honeypot's derived static files from api/skills.json.

- api/by-category/<category>.json — per-category indexes (same schema envelope)
- api/changelog.json — append-only record of added skills
- feed.xml — RSS 2.0 of newly added skills
- sitemap.xml — static pages + skill pages + API endpoints for crawlers
- skills/<name>/index.html — per-skill page (SEO tags, JSON-LD, backlinks)
- categories/<category>/index.html — landing page for each of the largest categories
- llms-full.txt — every SKILL.md concatenated for crawlers
- api/editors-picks.json — skills passing the published PICK_CRITERIA checklist
- badge/<name>.svg — per-skill badge (name, version, verified check)
- index.html — the homepage's dynamic regions (picks section, category TOC,
  filter options, result count, skill cards) pre-rendered between
  <!-- gen:* --> markers, so first paint already holds the full layout and
  the client-side render() replaces it with identical markup (no layout
  shift). The inline script in index.html must stay byte-compatible with
  the templates below; if the markers are missing, index regen is skipped
  with a warning rather than failing the run.

Run from the repo root:  python3 scripts/gen.py
Run it whenever skills.json changes (a weekly cron regenerates changelog/feed).
Static output only; no network, no secrets.
"""
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote
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
BADGE_DIR = ROOT / "badge"

# Optional SKILL.md frontmatter key. Shown on the badge when it is a short token.
# Otherwise the badge shows last_verified.
VERSION_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,31}$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Glyph advances in tenths of a pixel at 11px: the wider of Inter and
# Liberation Sans, plus a quarter pixel. Unknown characters use 8px.
# text_width() rounds up so the label stays inside the badge rect.
CHAR_WIDTH = {
    "a": 65, "b": 70, "c": 66, "d": 70, "e": 67, "f": 44, "g": 70, "h": 68,
    "i": 30, "j": 30, "k": 63, "l": 30, "m": 99, "n": 68, "o": 69, "p": 70,
    "q": 70, "r": 44, "s": 61, "t": 39, "u": 68, "v": 65, "w": 93, "x": 63,
    "y": 65, "z": 64, "A": 79, "B": 76, "C": 83, "D": 82, "E": 76, "F": 70,
    "G": 89, "H": 85, "I": 34, "J": 66, "K": 77, "L": 65, "M": 102, "N": 86,
    "O": 89, "P": 76, "Q": 89, "R": 82, "S": 76, "T": 74, "U": 85, "V": 79,
    "W": 111, "X": 78, "Y": 78, "Z": 72, "0": 72, "1": 64, "2": 70, "3": 71,
    "4": 74, "5": 68, "6": 71, "7": 65, "8": 71, "9": 71, "-": 54, ".": 35,
    "_": 64, "+": 76, " ": 34,
}
BADGE_FONT = "system-ui, -apple-system, sans-serif"
CATEGORIES_DIR = ROOT / "categories"
INDEX_HTML = ROOT / "index.html"

SITE = "https://honeypot-e6c.pages.dev"
REQUIRED = ["name", "description", "category", "skill_md_url", "install", "tags", "last_verified"]

# Static landing pages for the largest categories only. Ranked by skill count,
# then name, from api/skills.json. No hand-picked list.
TOP_CATEGORY_PAGES = 8
CATEGORY_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

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


def xml_text(s: str) -> str:
    """Escape text for SVG attributes and character data."""
    return escape(s, {"\"": "&quot;", "'": "&apos;"})


def text_width(s: str) -> int:
    tenths = sum(CHAR_WIDTH.get(c, 80) for c in s)
    return (tenths + 9) // 10


def parse_frontmatter(text: str) -> dict | None:
    """Return simple `key: value` frontmatter, or None if it is missing or broken."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            return None
        key, val = line.split(":", 1)
        key = key.strip()
        if not key or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key):
            return None
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        meta[key] = val
    return None


def read_frontmatter(name: str) -> dict | None:
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.is_file():
        return None
    return parse_frontmatter(path.read_text())


def lint_skill(s: dict) -> list[str]:
    """Checks a skill must pass before its badge draws a verified check.

    Frontmatter needs `name` and `description`, and `name` must match the
    directory. The index entry needs a category, at least one tag, and a
    `last_verified` date. Optional `version` must be a short token when set.
    """
    name = s.get("name") or ""
    errors = []
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.is_file():
        return ["SKILL.md missing"]
    fm = parse_frontmatter(path.read_text())
    if fm is None:
        return ["frontmatter missing or unclosed"]
    if not fm.get("name"):
        errors.append("frontmatter name missing")
    elif fm["name"] != name:
        errors.append("frontmatter name does not match the directory")
    if not fm.get("description", "").strip():
        errors.append("frontmatter description missing")
    version = fm.get("version", "").strip()
    if version and not VERSION_TOKEN.fullmatch(version):
        errors.append("version is not a short token")
    if not s.get("category"):
        errors.append("category missing")
    if not s.get("tags"):
        errors.append("tags missing")
    verified_on = s.get("last_verified")
    if not isinstance(verified_on, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified_on):
        errors.append("last_verified is not a date")
    else:
        try:
            date.fromisoformat(verified_on)
        except ValueError:
            errors.append("last_verified is not a date")
    return errors


def skill_version(s: dict, fm: dict | None) -> str:
    """Badge version: frontmatter `version` when valid, else `last_verified`."""
    if fm:
        version = fm.get("version", "").strip()
        if version and VERSION_TOKEN.fullmatch(version):
            return version
    verified_on = s.get("last_verified") or ""
    return verified_on if isinstance(verified_on, str) else ""


def badge_embed(name: str) -> str:
    return f"[![{name} on Honeypot]({SITE}/badge/{name}.svg)]({SITE}/skills/{name}/)"


def badge_svg(name: str, version: str, verified: bool) -> str:
    """Minimal dark pill: mark, skill name, version, and a check when verified."""
    name_x = 22
    cursor = name_x + text_width(name)
    version_x = None
    if version:
        version_x = cursor + 6
        cursor = version_x + text_width(version)
    check_x = None
    if verified:
        check_x = cursor + 6
        cursor = check_x + 9
    width = cursor + 7
    label = f"{name} {version}".strip()
    if verified:
        label += ", verified"
    label_esc = xml_text(label)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{label_esc}">',
        f"  <title>{label_esc}</title>",
        f'  <rect width="{width}" height="20" rx="3" fill="#1a1a1a"/>',
        '  <circle cx="12" cy="10" r="5" fill="#ffffff"/>',
        '  <circle cx="12" cy="10" r="1.8" fill="#1a1a1a"/>',
        f'  <text x="{name_x}" y="14" font-family="{BADGE_FONT}" font-size="11" fill="#ffffff">{xml_text(name)}</text>',
    ]
    if version_x is not None:
        lines.append(
            f'  <text x="{version_x}" y="14" font-family="{BADGE_FONT}" font-size="11" fill="#c8c8c8">{xml_text(version)}</text>'
        )
    if check_x is not None:
        lines.append(
            f'  <path id="verified" d="M0.5 4.2 L2.8 7 L8 1.2" transform="translate({check_x},6)" '
            'fill="none" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def self_check() -> None:
    fm = parse_frontmatter('---\nname: "cron"\ndescription: "hi"\nversion: "1.2.0"\n---\n')
    assert fm == {"name": "cron", "description": "hi", "version": "1.2.0"}
    assert parse_frontmatter("---\nname: x\n") is None
    assert parse_frontmatter("hello") is None
    ok = badge_svg("cron", "2026-10-09", True)
    plain = badge_svg("cron", "2026-10-09", False)
    assert 'id="verified"' in ok and 'id="verified"' not in plain
    assert "cron" in ok and "2026-10-09" in ok
    escaped = badge_svg('a"b', "1<2", False)
    assert "a&quot;b" in escaped and "1&lt;2" in escaped
    assert "<script" not in ok
    from xml.dom import minidom
    for doc in (ok, plain, escaped):
        minidom.parseString(doc)
    width = int(re.search(r'width="(\d+)"', ok).group(1))
    assert width >= 22 + text_width("cron") + 8 + text_width("2026-10-09") + 7 + 9
def esc(s) -> str:
    """Mirror of index.html's esc(): same replacements, same order."""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def uri_component(s) -> str:
    """Mirror of JS encodeURIComponent()."""
    return quote(str(s), safe="-_.!~*'()")


def card_is_stale(s: dict, today: date) -> bool:
    """Mirror of index.html's isStale() with staleAfterDays = STALE_AFTER_DAYS."""
    try:
        age = (today - date.fromisoformat(s.get("last_verified") or "")).days
    except ValueError:
        return True  # JS: unparseable date -> age null -> stale
    return age > STALE_AFTER_DAYS


BADGE_MD = "[![Indexed on Honeypot](https://honeypot-e6c.pages.dev/badge.svg)](https://honeypot-e6c.pages.dev)"


def index_card(s: dict, today: date) -> str:
    """One skill card, byte-identical to index.html render()'s output."""
    out = '<div class="card">'
    out += "<h3>" + esc(s["name"]) + "</h3>"
    out += "<p>" + esc(s["description"]) + "</p>"
    out += '<span class="tag">' + esc(s["category"]) + "</span>"
    if s.get("skill_md_url"):
        out += '<a class="src" href="' + esc(s["skill_md_url"]) + '">SKILL.md</a>'
    if s.get("last_verified"):
        out += '<span class="verified">verified ' + esc(s["last_verified"]) + "</span>"
    if card_is_stale(s, today):
        out += (
            '<span class="tag stale" title="Not re-verified in over '
            + str(STALE_AFTER_DAYS)
            + ' days">stale</span>'
        )
    if s.get("install"):
        out += (
            '<div class="install"><code>' + esc(s["install"]) + "</code>"
            + '<button type="button" class="copy" data-copy="' + esc(s["install"])
            + '" aria-label="Copy install command for ' + esc(s["name"]) + '">copy</button></div>'
        )
    out += (
        '<details class="badge"><summary>add badge</summary><code>'
        + esc(BADGE_MD)
        + "</code></details>"
    )
    out += "</div>"
    return out


def index_regions(skills: list, picks_doc: dict, today: date) -> dict:
    """The dynamic regions of index.html, rendered from the same data the
    page's inline script fetches (api/skills.json + editors-picks.json), so
    the pre-render and the client render agree."""
    counts = {}
    for s in skills:
        counts[s["category"]] = counts.get(s["category"], 0) + 1
    toc = '<li><a href="./">all</a> <span class="n">(' + str(len(skills)) + ")</span></li>"
    toc += "".join(
        '<li><a href="?category=' + uri_component(c) + '">' + esc(c)
        + '</a> <span class="n">(' + str(counts[c]) + ")</span></li>"
        for c in sorted(counts)
    )
    cat_options = "".join(
        '<option value="' + esc(c) + '">' + esc(c) + "</option>" for c in sorted(counts)
    )
    all_tags = sorted({t for s in skills for t in s.get("tags") or []})
    tag_options = "".join(
        '<option value="' + esc(t) + '">' + esc(t) + "</option>" for t in all_tags
    )
    picks = picks_doc.get("picks") or []
    if picks:
        items = "".join(
            '<li><a href="skills/' + uri_component(p["name"]) + '/">'
            + esc(p["name"]) + "</a> " + esc(p["description"]) + "</li>"
            for p in picks
        )
        picks_section = (
            '<section id="picks">\n'
            "    <h2>Editor's picks</h2>\n"
            '    <ul id="picks-list">' + items + "</ul>\n"
            '    <p class="note"><span id="picks-note">' + esc(picks_doc.get("criteria_text", ""))
            + '</span> Raw list: <a href="/api/editors-picks.json"><code>/api/editors-picks.json</code></a></p>\n'
            "  </section>"
        )
    else:
        picks_section = (
            '<section id="picks" hidden>\n'
            "    <h2>Editor's picks</h2>\n"
            '    <ul id="picks-list"></ul>\n'
            '    <p class="note"><span id="picks-note"></span> Raw list: '
            '<a href="/api/editors-picks.json"><code>/api/editors-picks.json</code></a></p>\n'
            "  </section>"
        )
    return {
        "picks": picks_section,
        "toc": toc,
        "cat-options": cat_options,
        "tag-options": tag_options,
        "count": str(len(skills)) + " of " + str(len(skills)) + " skills",
        "cards": "".join(index_card(s, today) for s in skills),
    }


def render_index(skills: list, picks_doc: dict, today: date) -> bool:
    """Splice index_regions() into index.html between <!-- gen:* --> markers.
    Returns False (with a warning) if the markers are gone, so a hand-edit
    that drops them degrades to the old client-rendered page instead of
    breaking the whole regen."""
    html = INDEX_HTML.read_text()
    for name, content in index_regions(skills, picks_doc, today).items():
        pattern = re.compile(
            r"(<!-- gen:" + name + r" -->).*?(<!-- /gen:" + name + r" -->)", re.DOTALL
        )
        html, n = pattern.subn(lambda m: m.group(1) + content + m.group(2), html)
        if n != 1:
            print(f"WARNING: index.html is missing its gen:{name} markers; "
                  "skipping homepage pre-render", file=sys.stderr)
            return False
    INDEX_HTML.write_text(html)
    return True


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


def largest_categories(skills: list) -> list:
    """Up to TOP_CATEGORY_PAGES category slugs, largest first."""
    counts = {}
    for s in skills:
        counts[s["category"]] = counts.get(s["category"], 0) + 1
    ranked = sorted(counts, key=lambda c: (-counts[c], c))
    safe = [c for c in ranked if CATEGORY_SLUG.fullmatch(c)]
    return safe[:TOP_CATEGORY_PAGES]


def _check_largest() -> None:
    """Cap, tie-break, and slug filter. Independent of the live index."""
    rows = []
    for cat, n in (
        ("z", 1), ("m", 5), ("a", 5), ("Bad Name", 9), ("q", 4),
        ("b", 3), ("c", 3), ("d", 2), ("e", 2), ("f", 2), ("g", 1),
    ):
        rows.extend({"category": cat} for _ in range(n))
    got = largest_categories(rows)
    assert got == ["a", "m", "q", "b", "c", "d", "e", "f"], got
    assert "Bad Name" not in got and "g" not in got and "z" not in got


def category_page(cat: str, cat_skills: list) -> str:
    """Static category page: skill count, one line per skill, link to the full index."""
    cat_skills = sorted(cat_skills, key=lambda s: s["name"])
    n = len(cat_skills)
    noun = "skill" if n == 1 else "skills"
    blurb = f"{n} {noun} in the {cat} category."
    items = "\n".join(
        f'    <li><a href="/skills/{escape(s["name"])}/">{escape(s["name"])}</a> '
        f'{escape(s["description"])}</li>'
        for s in cat_skills
    )
    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"{cat} skills on Honeypot",
        "description": blurb,
        "url": f"{SITE}/categories/{cat}/",
        "isPartOf": {
            "@type": "WebSite",
            "name": "Honeypot",
            "url": SITE,
        },
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": n,
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i,
                    "name": s["name"],
                    "description": s["description"],
                    "url": f"{SITE}/skills/{s['name']}/",
                }
                for i, s in enumerate(cat_skills, start=1)
            ],
        },
    }
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(cat)} — skills on Honeypot</title>
<meta name="description" content="{escape(blurb)}">
<meta property="og:title" content="{escape(cat)} — skills on Honeypot">
<meta property="og:description" content="{escape(blurb)}">
<meta property="og:url" content="{SITE}/categories/{escape(cat)}/">
<meta property="og:type" content="website">
<link rel="canonical" href="{SITE}/categories/{escape(cat)}/">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='14' fill='%231a1a1a'/%3E%3Ccircle cx='16' cy='16' r='5' fill='%23fff'/%3E%3C/svg%3E">
<script type="application/ld+json">
{json.dumps(ld, indent=2)}
</script>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 38rem; margin: 4rem auto; padding: 0 1rem; line-height: 1.6; color: #1a1a1a; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 0; }}
  a {{ color: #1a1a1a; }}
  ul {{ padding-left: 1.2rem; margin: 1rem 0; }}
  li {{ margin: 0.4rem 0; }}
  .meta {{ font-size: 0.85rem; color: #666; }}
  footer {{ margin-top: 3rem; font-size: 0.85rem; color: #666; }}
</style>
</head>
<body>
<main>
  <h1>{escape(cat)}</h1>
  <p class="meta">{n} {noun}</p>
  <ul>
{items}
  </ul>
  <p><a href="/">Full index</a></p>
  <p class="meta">Machine-readable list: <a href="/api/by-category/{escape(cat)}.json"><code>/api/by-category/{escape(cat)}.json</code></a></p>
</main>
<footer>
  Indexed on <a href="{SITE}">Honeypot</a>. Want your skill listed? <a href="https://github.com/oidsdev/honeypot#submit-a-skill">Submit a pull request</a>.
</footer>
</body>
</html>
"""


def skill_page(s: dict, category_page: bool = False) -> str:
    """Static per-skill page: SEO tags, JSON-LD, links back to index + category."""
    name = s["name"]
    desc = s["description"]
    cat = s["category"]
    tags = ", ".join(s["tags"])
    install = s["install"]
    md_url = s["skill_md_url"]
    verified = s["last_verified"]
    version = skill_version(s, read_frontmatter(name))
    passed = not lint_skill(s)
    label = f"{name} {version}".strip()
    if passed:
        label += ", verified"
    esc_t = escape(desc)
    esc_i = escape(install)
    esc_label = escape(label)
    esc_embed = escape(badge_embed(name))
    cat_href = (
        f"/categories/{escape(cat)}/"
        if category_page
        else f"/api/by-category/{escape(cat)}.json"
    )
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
<title>{escape(name)} - a skill on Honeypot</title>
<meta name="description" content="{esc_t}">
<meta property="og:title" content="{escape(name)} - a skill on Honeypot">
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
  <p class="meta">Category: <a href="{cat_href}">{escape(cat)}</a> &middot; Tags: {escape(tags)} &middot; Verified {escape(verified)}</p>
  <h2>Install</h2>
  <code class="install">{esc_i}</code>
  <h2>Badge</h2>
  <p><img src="/badge/{escape(name)}.svg" alt="{esc_label}" height="20"></p>
  <code class="install">{esc_embed}</code>
  <p>Read the full skill: <a href="{escape(md_url)}">SKILL.md</a></p>
  <p><a href="/">Honeypot</a> - a free, open index of skills for AI agents. Machine-readable. No sign-up, no tracking.</p>
</main>
<footer>
  Indexed on <a href="{SITE}">Honeypot</a>. Want your skill listed? <a href="https://github.com/oidsdev/honeypot#submit-a-skill">Submit a pull request</a>.
</footer>
</body>
</html>
"""


def main() -> int:
    self_check()
    _check_largest()
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
    today_d = date.today()
    picks_doc = editors_picks(skills, today_d)

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
            f"      <title>{escape(e['name'])} - skill added to Honeypot</title>\n"
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
        "    <title>Honeypot - new skills</title>\n"
        f"    <link>{SITE}/</link>\n"
        "    <description>Skills newly added to the Honeypot index for AI agents.</description>\n"
        "    <language>en</language>\n"
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )
    FEED_XML.write_text(feed)

    # 4. category landing pages (largest categories), per-skill badges and pages
    BADGE_DIR.mkdir(exist_ok=True)
    page_cats = largest_categories(skills)
    page_cat_set = set(page_cats)
    counts = {}
    for s in skills:
        counts[s["category"]] = counts.get(s["category"], 0) + 1
    CATEGORIES_DIR.mkdir(exist_ok=True)
    for cat in page_cats:
        dest = CATEGORIES_DIR / cat
        dest.mkdir(exist_ok=True)
        (dest / "index.html").write_text(
            category_page(cat, [s for s in skills if s["category"] == cat])
        )
    for dest in CATEGORIES_DIR.iterdir():
        if not dest.is_dir() or dest.name in page_cat_set:
            continue
        page = dest / "index.html"
        if page.exists():
            page.unlink()
        try:
            dest.rmdir()
        except OSError:
            pass

    skill_urls = []
    badge_urls = []
    verified_n = 0
    for s in skills:
        if not SKILL_NAME.fullmatch(s["name"]):
            print(f"ERROR: skill name {s['name']!r} cannot be a badge path", file=sys.stderr)
            return 1
        errors = lint_skill(s)
        version = skill_version(s, read_frontmatter(s["name"]))
        if errors:
            print(f"badge lint {s['name']}: {'; '.join(errors)}")
        else:
            verified_n += 1
        (BADGE_DIR / f"{s['name']}.svg").write_text(badge_svg(s["name"], version, not errors))
        badge_urls.append((f"/badge/{s['name']}.svg", s["last_verified"]))
        page = SKILLS_DIR / s["name"] / "index.html"
        page.write_text(skill_page(s, category_page=s["category"] in page_cat_set))
        skill_urls.append((f"/skills/{s['name']}/", s["last_verified"]))
    for f in BADGE_DIR.glob("*.svg"):
        if f.stem not in set(names):
            f.unlink()

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
    today = today_d.isoformat()
    EDITORS_PICKS.write_text(json.dumps(picks_doc, indent=4) + "\n")

    # 7. sitemap (static pages + skill pages + API endpoints, stays fresh automatically)
    urls = [
        ("/", today),
        ("/llms.txt", today),
        ("/llms-full.txt", today),
        ("/skill-template.md", today),
        ("/badge.svg", today),
    ] + badge_urls + [
        ("/api/skills.json", updated),
        ("/api/changelog.json", today),
        ("/api/editors-picks.json", today),
        ("/feed.xml", today),
        ("/faq/", today),
    ] + [(f"/categories/{cat}/", updated) for cat in page_cats] + [
        (f"/api/by-category/{cat}.json", updated) for cat in cats
    ] + skill_urls
    sm = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{lm}</lastmod></url>\n" for u, lm in urls)
        + "</urlset>\n"
    )
    SITEMAP_XML.write_text(sm)

    # 8. homepage pre-render (CLS fix: dynamic regions ship as static HTML)
    render_index(skills, picks_doc, today_d)

    # 9. validate everything we wrote
    for p in [SKILLS_JSON, CHANGELOG_JSON, EDITORS_PICKS, *BY_CATEGORY.glob("*.json")]:
        json.loads(p.read_text())
    from xml.dom import minidom
    minidom.parseString(SITEMAP_XML.read_text())
    assert LLMS_FULL.exists() and LLMS_FULL.stat().st_size > 0
    for s in skills:
        assert (SKILLS_DIR / s["name"] / "index.html").exists()
        badge_path = BADGE_DIR / f"{s['name']}.svg"
        badge_doc = badge_path.read_text()
        minidom.parseString(badge_doc)
        assert s["name"] in badge_doc
        if lint_skill(s):
            assert 'id="verified"' not in badge_doc
        else:
            assert 'id="verified"' in badge_doc
    safe_cats = [c for c in cats if CATEGORY_SLUG.fullmatch(c)]
    assert page_cats == sorted(safe_cats, key=lambda c: (-counts[c], c))[:TOP_CATEGORY_PAGES]
    for cat in page_cats:
        html = (CATEGORIES_DIR / cat / "index.html").read_text()
        assert f"{counts[cat]} skill" in html
        assert 'href="/">Full index</a>' in html
        for s in skills:
            if s["category"] == cat:
                assert f'/skills/{s["name"]}/' in html
                assert escape(s["description"]) in html

    print(f"skills: {len(skills)} | categories: {', '.join(cats)} | "
          f"category pages: {', '.join(page_cats)} | "
          f"changelog entries: {len(changelog['entries'])} (+{added} new) | feed items: {len(items)} | "
          f"editor's picks: {len(picks_doc['picks'])} | "
          f"badges: {verified_n}/{len(skills)} verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
