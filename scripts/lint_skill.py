#!/usr/bin/env python3
"""Lint a submitted Honeypot skill.

Checks one SKILL.md for required frontmatter (name, description), description
length, banned phrases, and relative links that resolve to a file next to it.
https links, mailto links, and in-page #anchors are skipped. Fenced code
blocks and inline code are not scanned.

Usage (from the repo root):
    python3 scripts/lint_skill.py skills/<name>
    python3 scripts/lint_skill.py path/to/SKILL.md
    python3 scripts/lint_skill.py --fixtures

Exit 0 on pass, 1 on fail, 2 on bad usage.
`pass` or `fail` is the first line. Each problem follows as file:line: reason.
"""
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DESC_MIN = 20
DESC_MAX = 300

# Submission voice filter. Edit this list and nowhere else.
# Matched case-insensitively, as a whole word or phrase.
# A space and a hyphen count as the same separator.
BANNED_PHRASES = (
    "delve",
    "tapestry",
    "unlock",
    "game-changer",
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "lint-fixtures"

_KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$")
_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]*)\)")
_REF = re.compile(r"^\[([^\]]+)\]:\s*(.+)$")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_CODE = re.compile(r"`[^`]*`")


def _phrase_pattern(phrase: str) -> re.Pattern:
    parts = [re.escape(part) for part in re.split(r"[\s-]+", phrase) if part]
    body = r"[\s-]+".join(parts)
    return re.compile(rf"\b{body}\b", re.IGNORECASE)


_BANNED = tuple((phrase, _phrase_pattern(phrase)) for phrase in BANNED_PHRASES)


@dataclass
class Finding:
    path: Path
    line: int
    message: str
    rank: int = 0

    def format(self) -> str:
        return f"{_display(self.path)}:{self.line}: {self.message}"


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def length_message(n: int) -> str:
    return f"description is {n} characters; need {DESC_MIN}-{DESC_MAX}"


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _fence_marker(line: str):
    stripped = line.lstrip()
    if stripped.startswith("```"):
        return "```"
    if stripped.startswith("~~~"):
        return "~~~"
    return None


def _visible_lines(lines: list):
    """Yield (index, line) for lines outside fenced code, with inline code removed."""
    in_fence = False
    marker = None
    for index, line in enumerate(lines):
        mark = _fence_marker(line)
        if mark:
            if not in_fence:
                in_fence = True
                marker = mark
            elif mark == marker:
                in_fence = False
                marker = None
            continue
        if in_fence:
            continue
        yield index, _CODE.sub("", line)


def _destination(raw: str):
    """Return a relative path to check, '' if empty, or None if it is not a file link."""
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("<"):
        end = raw.find(">")
        dest = raw[1:end].strip() if end != -1 else raw[1:].strip()
    else:
        dest = raw.split()[0]
    if not dest or dest.startswith("#"):
        return None if dest.startswith("#") else ""
    if dest.startswith("//") or _SCHEME.match(dest):
        return None
    path = dest.split("#", 1)[0].split("?", 1)[0]
    return path or None


def _link_finding(path: Path, line_no: int, target: str):
    if target == "":
        return Finding(path, line_no, "empty link target", 3)
    candidate = (path.parent / target).resolve()
    if not candidate.is_file():
        return Finding(path, line_no, f'relative link "{target}" does not resolve', 3)
    return None


def lint_text(text: str, path: Path) -> list:
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    findings = []

    if not lines or lines[0].strip() != "---":
        findings.append(Finding(path, 1, "missing frontmatter", 0))
        body_start = 0
    else:
        end = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                end = index
                break
        fields = {}
        stop = end if end is not None else len(lines)
        for index in range(1, stop):
            match = _KEY.match(lines[index].strip())
            if match:
                fields[match.group(1)] = (index + 1, _unquote(match.group(2)).strip())
        if end is None:
            findings.append(Finding(path, 1, "frontmatter is not closed", 0))
            body_start = len(lines)
        else:
            body_start = end + 1
            close_line = end + 1
            for key in ("name", "description"):
                if key not in fields or not fields[key][1]:
                    findings.append(Finding(path, close_line, f'frontmatter missing "{key}"', 0))
            if "description" in fields and fields["description"][1]:
                desc_line, desc = fields["description"]
                if not (DESC_MIN <= len(desc) <= DESC_MAX):
                    findings.append(Finding(path, desc_line, length_message(len(desc)), 1))

    for index, line in _visible_lines(lines):
        line_no = index + 1
        for phrase, pattern in _BANNED:
            if pattern.search(line):
                findings.append(Finding(path, line_no, f'banned phrase "{phrase}"', 2))
        if index < body_start:
            continue
        stripped = line.strip()
        ref = _REF.match(stripped)
        targets = []
        if ref:
            targets.append(ref.group(2))
        else:
            targets.extend(match.group(1) for match in _LINK.finditer(line))
        for raw in targets:
            dest = _destination(raw)
            if dest is None:
                continue
            found = _link_finding(path, line_no, dest)
            if found:
                findings.append(found)

    findings.sort(key=lambda item: (item.line, item.rank, item.message))
    return findings


def lint_path(raw: Path) -> list:
    if raw.is_dir() or raw.suffix.lower() != ".md":
        path = raw / "SKILL.md"
        missing = "SKILL.md not found"
    else:
        path = raw
        missing = "file not found"
    if not path.is_file():
        return [Finding(path, 1, missing, 0)]
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [Finding(path, 1, "SKILL.md is not valid UTF-8", 0)]
    return lint_text(text, path)


def _report(findings: list) -> int:
    if not findings:
        print("pass")
        return 0
    print("fail")
    for finding in findings:
        print(finding.format())
    return 1


_PASS_FIXTURES = ("pass-basic", "pass-external", "pass-relative")
_FAIL_SNIPPETS = {
    "fail-copy": (
        'frontmatter missing "name"',
        length_message(10),
        'banned phrase "delve"',
        'banned phrase "tapestry"',
        'banned phrase "unlock"',
        'banned phrase "game-changer"',
    ),
    "fail-link": (
        length_message(301),
        'relative link "docs/guide.md" does not resolve',
    ),
}


def _wrapped(desc, body="Body.", name="sample") -> str:
    front = ["---"]
    if name is not None:
        front.append(f'name: "{name}"')
    if desc is not None:
        front.append(f'description: "{desc}"')
    front.append("---")
    return "\n".join(front + ["", "# Title", "", body, ""])


def _self_check() -> list:
    errors = []

    def check(label, text, path, expected):
        got = [(item.line, item.message) for item in lint_text(text, path)]
        if got != expected:
            errors.append(f"{label}: expected {expected}, got {got}")

    sample = Path("self.md")
    twenty = "a" * 20
    check("19", _wrapped("a" * 19), sample, [(3, length_message(19))])
    check("20", _wrapped(twenty), sample, [])
    check("300", _wrapped("a" * 300), sample, [])
    check("301", _wrapped("a" * 301), sample, [(3, length_message(301))])
    check("no frontmatter", "# Title\n\nHello.\n", sample, [(1, "missing frontmatter")])
    check(
        "unclosed",
        '---\nname: "sample"\ndescription: "' + twenty + '"\n',
        sample,
        [(1, "frontmatter is not closed")],
    )
    check("no description", _wrapped(None), sample, [(3, 'frontmatter missing "description"')])
    check("no name", _wrapped(twenty, name=None), sample, [(3, 'frontmatter missing "name"')])
    check("phrase", _wrapped(twenty, "Please delve now."), sample, [(8, 'banned phrase "delve"')])
    check(
        "phrase case and separator",
        _wrapped(twenty, "DELVE is a game changer."),
        sample,
        [(8, 'banned phrase "delve"'), (8, 'banned phrase "game-changer"')],
    )
    check("word boundary", _wrapped(twenty, "delves into an unlocked file."), sample, [])
    check("inline code", _wrapped(twenty, "A filename can be `delve.txt` today."), sample, [])
    check("fence", _wrapped(twenty, "```\ndelve\n[missing](nope.md)\n```"), sample, [])

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "note.md").write_text("hello\n", encoding="utf-8")
        skill = root / "SKILL.md"
        check("good link", _wrapped(twenty, "See [note](note.md)."), skill, [])
        check("titled link", _wrapped(twenty, 'See [note](./note.md "note").'), skill, [])
        check("fragment link", _wrapped(twenty, "See [note](note.md#top)."), skill, [])
        check(
            "missing link",
            _wrapped(twenty, "See [missing](nope.md)."),
            skill,
            [(8, 'relative link "nope.md" does not resolve')],
        )
        check(
            "external and anchor",
            _wrapped(twenty, "See [web](https://example.com/a) and [here](#here)."),
            skill,
            [],
        )
        check("empty link", _wrapped(twenty, "See [x]()."), skill, [(8, "empty link target")])
        check(
            "ref link missing",
            _wrapped(twenty, "See the [note][n].\n\n[n]: missing-ref.md"),
            skill,
            [(10, 'relative link "missing-ref.md" does not resolve')],
        )
        check("ref link ok", _wrapped(twenty, "See the [note][n].\n\n[n]: note.md"), skill, [])
        check("image ok", _wrapped(twenty, "Look at ![alt](note.md)."), skill, [])
        check(
            "image missing",
            _wrapped(twenty, "Look at ![alt](nope.md)."),
            skill,
            [(8, 'relative link "nope.md" does not resolve')],
        )
        check(
            "link in inline code",
            _wrapped(twenty, "See `[nope.md](nope.md)` today."),
            skill,
            [],
        )
    return errors


def run_fixtures() -> int:
    if not FIXTURES.is_dir():
        print(f"fail\nfixtures directory not found: {FIXTURES}", file=sys.stderr)
        return 1
    dirs = sorted(path for path in FIXTURES.iterdir() if path.is_dir())
    names = [path.name for path in dirs]
    expected = sorted(list(_PASS_FIXTURES) + list(_FAIL_SNIPPETS))
    problems = 0
    if names != expected:
        print(f"fixture set: {names}")
        print(f"expected:    {expected}")
        problems += 1
    for directory in dirs:
        findings = lint_path(directory)
        messages = [item.message for item in findings]
        if directory.name in _PASS_FIXTURES:
            ok = not findings
            print(f"{directory.name}: {'pass' if ok else 'fail'}")
            if not ok:
                problems += 1
                for item in findings:
                    print(item.format())
            continue
        snippets = _FAIL_SNIPPETS.get(directory.name, ())
        missing = [snippet for snippet in snippets if snippet not in messages]
        leaked = directory.name == "fail-link" and any("present.md" in message for message in messages)
        ok = bool(findings) and not missing and not leaked
        print(f"{directory.name}: {'fail' if findings else 'pass'}")
        if not ok:
            problems += 1
            if missing:
                print(f"  missing: {missing}")
            if leaked:
                print("  present.md was reported")
            for item in findings:
                print(item.format())
    self_errors = _self_check()
    if self_errors:
        print("self-check: fail")
        for error in self_errors:
            print(error)
        problems += 1
    else:
        print("self-check: pass")
    if problems:
        return 1
    print(f"{len(_PASS_FIXTURES) + len(_FAIL_SNIPPETS)} fixtures ok")
    return 0


def main(argv: list) -> int:
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(
            "usage: python3 scripts/lint_skill.py <skill-dir-or-SKILL.md>\n"
            "       python3 scripts/lint_skill.py --fixtures",
            file=sys.stderr,
        )
        return 2
    if argv[1] == "--fixtures":
        return run_fixtures()
    return _report(lint_path(Path(argv[1])))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
