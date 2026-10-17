"""Rebuild the site in a temporary copy and check the generated tree.

Run from the repo root: python3 -m pytest tests/test_gen.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Outputs a mis-rooted gen.py would overwrite. Checked after every test.
WATCH = (
    "index.html",
    "sitemap.xml",
    "feed.xml",
    "llms-full.txt",
    "api/skills.json",
    "api/changelog.json",
    "api/editors-picks.json",
)

# Categories the removal fixture may drop. Trading and payments stay put.
SAFE_CATEGORIES = frozenset({"tooling", "meta", "data", "identity", "comms"})

SKIP_DIRS = frozenset({".git", "__pycache__", ".pytest_cache"})

REGION = re.compile(
    r"<!-- gen:([a-z0-9-]+) -->(.*?)<!-- /gen:\1 -->",
    re.DOTALL,
)
TOC_ALL = re.compile(r'<a href="\./">all</a> <span class="n">\((\d+)\)</span>')
TOC_CAT = re.compile(
    r'<a href="\?category=[^"]*">([^<]*)</a> <span class="n">\((\d+)\)</span>'
)


def _ignore_junk(_directory, names):
    return {name for name in names if name in SKIP_DIRS or name.endswith(".pyc")}


def snapshot(repo: Path) -> dict:
    files = {}
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo)
        if any(part in SKIP_DIRS for part in rel.parts) or path.suffix == ".pyc":
            continue
        files[rel.as_posix()] = path.read_bytes()
    return files


def run_gen(repo: Path) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Do not walk up into the real checkout if this copy has no .git.
    env["GIT_CEILING_DIRECTORIES"] = str(repo.resolve().parent)
    proc = subprocess.run(
        [sys.executable, str(repo / "scripts" / "gen.py")],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"gen.py exited {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


def load_skills(repo: Path) -> list:
    doc = json.loads((repo / "api" / "skills.json").read_text())
    assert isinstance(doc, dict) and doc.get("schema_version") == "1"
    skills = doc["skills"]
    assert isinstance(skills, list) and skills
    return skills


def region(html: str, name: str) -> str:
    found = {m.group(1): m.group(2) for m in REGION.finditer(html)}
    assert name in found, f"index.html is missing gen:{name} markers"
    return found[name]


def skill_names_in_sitemap(text: str) -> list:
    root = ET.fromstring(text)
    names = []
    for el in root.iter():
        if not el.tag.endswith("loc") or not el.text:
            continue
        parts = urlparse(el.text).path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "skills":
            names.append(parts[1])
    return names


def card_names(cards_html: str) -> list:
    return [unescape(name) for name in re.findall(r"<h3>(.*?)</h3>", cards_html)]


@pytest.fixture
def repo(tmp_path):
    before = {rel: (ROOT / rel).read_bytes() for rel in WATCH}
    dest = tmp_path / "repo"
    shutil.copytree(ROOT, dest, ignore=_ignore_junk)
    yield dest
    after = {rel: (ROOT / rel).read_bytes() for rel in WATCH}
    assert after == before, "gen.py tests wrote into the real checkout"


@pytest.fixture
def generated(repo):
    run_gen(repo)
    return repo


def test_second_run_produces_zero_diff(repo):
    run_gen(repo)
    first = snapshot(repo)
    run_gen(repo)
    second = snapshot(repo)
    changed = sorted(set(first) | set(second))
    changed = [path for path in changed if first.get(path) != second.get(path)]
    assert changed == []


def test_every_skill_has_page_sitemap_entry_and_card(generated):
    skills = load_skills(generated)
    names = [s["name"] for s in skills]
    index = (generated / "index.html").read_text()
    sitemap = (generated / "sitemap.xml").read_text()

    missing_pages = [
        name for name in names
        if not (generated / "skills" / name / "index.html").is_file()
    ]
    assert missing_pages == []
    for name in names:
        page = (generated / "skills" / name / "index.html").read_text()
        assert f"<h1>{name}</h1>" in page

    assert skill_names_in_sitemap(sitemap) == names
    assert card_names(region(index, "cards")) == names


def test_index_category_counts_match_skills_json(generated):
    skills = load_skills(generated)
    expected = Counter(s["category"] for s in skills)
    toc = region((generated / "index.html").read_text(), "toc")

    all_count = TOC_ALL.search(toc)
    assert all_count is not None
    assert int(all_count.group(1)) == len(skills)

    pairs = [(unescape(label), int(n)) for label, n in TOC_CAT.findall(toc)]
    labels = [label for label, _ in pairs]
    assert len(labels) == len(set(labels))
    assert dict(pairs) == dict(expected)


def test_feed_xml_is_well_formed(generated):
    root = ET.parse(generated / "feed.xml").getroot()
    assert root.tag == "rss"
    assert root.find("channel") is not None


def test_removing_skill_removes_homepage_card(repo):
    path = repo / "api" / "skills.json"
    doc = json.loads(path.read_text())
    candidates = sorted(
        (s for s in doc["skills"] if s.get("category") in SAFE_CATEGORIES),
        key=lambda s: s["name"],
    )
    assert candidates, "skills.json has no safe category to drop a skill from"
    removed = candidates[0]
    doc["skills"] = [s for s in doc["skills"] if s["name"] != removed["name"]]
    path.write_text(json.dumps(doc, indent=4) + "\n")

    run_gen(repo)

    html = (repo / "index.html").read_text()
    cards = region(html, "cards")
    remaining = [s["name"] for s in doc["skills"]]
    assert removed["name"] not in card_names(cards)
    assert card_names(cards) == remaining
    assert region(html, "count") == f"{len(remaining)} of {len(remaining)} skills"
