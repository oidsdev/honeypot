#!/usr/bin/env python3
"""Lint one submitted skill.

    python3 scripts/lint_skill.py skills/<name>
    python3 scripts/lint_skill.py --fixtures

Reads SKILL.md. Prints pass, or fail plus line-numbered reasons.
Exit 0 on pass, 1 on fail, 2 on bad usage. Stdlib only.
"""

import re
import sys
from pathlib import Path

DESC_MIN = 20
DESC_MAX = 300

# Case-insensitive substrings. Any hit in SKILL.md fails the file.
BANNED_PHRASES = (
    "ignore previous instructions",
    "disregard all prior",
    "you are now unrestricted",
    "cutting-edge solution",
    "game-changer",
)

BLOCK_SCALARS = {">", ">-", ">+", "|", "|-", "|+"}
LINK_RE = re.compile(r"!?\[[^\[\]]*\]\(([^)]*)\)")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = ROOT / "fixtures" / "skill-lint"

# (dir name, expected issues as (line, message)). Empty means pass.
FIXTURES = (
    ("pass-min", ()),
    ("pass-link", ()),
    ("pass-max", ()),
    (
        "fail-description",
        (
            (1, "missing frontmatter field: name"),
            (2, "description is 5 characters (need 20-300)"),
            (7, "banned phrase: game-changer"),
        ),
    ),
    (
        "fail-link",
        ((8, "relative link not found: missing-guide.md"),),
    ),
)


def usage() -> str:
    phrases = ", ".join(BANNED_PHRASES)
    return (
        "usage: python3 scripts/lint_skill.py <skill-dir-or-SKILL.md> | --fixtures\n"
        f"description: {DESC_MIN}-{DESC_MAX} characters\n"
        f"banned phrases: {phrases}"
    )


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(lines: list[str]) -> tuple[dict[str, tuple[int, str]], str | None]:
    """Map key -> (line, raw value). Error is set when the block is missing or open."""
    if not lines or lines[0].strip() != "---":
        return {}, "missing frontmatter"
    fields: dict[str, tuple[int, str]] = {}
    for idx, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return fields, None
        if not line.strip() or line[0] in " \t" or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key and key not in fields:
            fields[key] = (idx, value.strip())
    return fields, "unclosed frontmatter"


def fence_mask(lines: list[str]) -> list[bool]:
    """True on lines inside a ``` or ~~~ block. Fence markers themselves are false."""
    inside = False
    mask = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            mask.append(False)
            inside = not inside
        else:
            mask.append(inside)
    return mask


def local_path(raw: str) -> str | None:
    """Relative file path to check, or None when the link is not a local file."""
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("<"):
        end = raw.find(">")
        token = raw[1:end] if end != -1 else raw[1:]
    else:
        token = raw.split()[0]
    token = token.strip()
    if not token or token.startswith(("#", "/", "//")):
        return None
    if SCHEME_RE.match(token):
        return None
    path = token.split("#", 1)[0].split("?", 1)[0]
    return path or None


def frontmatter_issues(lines: list[str]) -> list[tuple[int, str]]:
    fields, error = parse_frontmatter(lines)
    issues: list[tuple[int, str]] = []
    if error == "missing frontmatter":
        return [(1, error)]
    if error:
        issues.append((1, error))

    name = fields.get("name")
    if name is None or not unquote(name[1]).strip():
        issues.append((1 if name is None else name[0], "missing frontmatter field: name"))

    desc = fields.get("description")
    if desc is None or not unquote(desc[1]).strip():
        issues.append((1 if desc is None else desc[0], "missing frontmatter field: description"))
        return issues

    line, raw = desc
    text = unquote(raw).strip()
    if text in BLOCK_SCALARS:
        issues.append((line, "description must be a single line"))
        return issues
    length = len(text)
    if length < DESC_MIN or length > DESC_MAX:
        issues.append((line, f"description is {length} characters (need {DESC_MIN}-{DESC_MAX})"))
    return issues


def phrase_issues(lines: list[str]) -> list[tuple[int, str]]:
    issues = []
    for idx, line in enumerate(lines, start=1):
        folded = line.casefold()
        for phrase in BANNED_PHRASES:
            if phrase.casefold() in folded:
                issues.append((idx, f"banned phrase: {phrase}"))
    return issues


def link_issues(skill_md: Path, lines: list[str]) -> list[tuple[int, str]]:
    issues = []
    base = skill_md.parent
    for idx, (line, skipped) in enumerate(zip(lines, fence_mask(lines)), start=1):
        if skipped:
            continue
        for match in LINK_RE.finditer(line):
            rel = local_path(match.group(1))
            if rel is None:
                continue
            if not (base / rel).resolve().is_file():
                issues.append((idx, f"relative link not found: {rel}"))
    return issues


def locate(path: Path) -> Path:
    if path.name == "SKILL.md":
        return path
    return path / "SKILL.md"


def lint(path: Path) -> list[tuple[int, str]]:
    skill_md = locate(path)
    if not skill_md.is_file():
        return [(1, "SKILL.md not found")]
    try:
        text = skill_md.read_text(encoding="utf-8-sig")
    except OSError:
        return [(1, "SKILL.md not readable")]
    lines = text.splitlines()
    issues = frontmatter_issues(lines)
    issues.extend(phrase_issues(lines))
    issues.extend(link_issues(skill_md, lines))
    return sorted(set(issues))


def report(skill_md: Path, issues: list[tuple[int, str]]) -> str:
    if not issues:
        return "pass"
    body = "\n".join(f"{skill_md}:{line}: {message}" for line, message in issues)
    return "fail\n" + body


def run_fixtures() -> int:
    passes = sum(1 for _, expected in FIXTURES if not expected)
    fails = len(FIXTURES) - passes
    if len(FIXTURES) != 5 or passes != 3 or fails != 2:
        print("fail fixture set must be 3 pass and 2 fail", file=sys.stderr)
        return 1
    ok = True
    for name, expected in FIXTURES:
        got = tuple(lint(FIXTURE_DIR / name))
        status = "pass" if not got else "fail"
        print(f"{status} {name}")
        if got != expected:
            ok = False
            print(f"  expected: {expected}")
            print(f"  actual:   {got}")
    if not ok:
        return 1
    print("5 fixtures ok")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in {"-h", "--help"}:
        print(usage())
        return 0
    if len(argv) != 2:
        print(usage(), file=sys.stderr)
        return 2
    if argv[1] == "--fixtures":
        return run_fixtures()
    path = Path(argv[1])
    issues = lint(path)
    print(report(locate(path), issues))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
