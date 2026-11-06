"""List every banned statistics term that appears in the site's main text (DECISIONS D30).

    uv run python scripts/jargon_check.py            # after `npm run build` in web/
    uv run python scripts/jargon_check.py --json     # machine-readable

Reads every HTML page under web/out, drops everything that is one click away from the main
text (elements with a `data-technical` attribute, the bodies of <details>, hidden elements,
<script> and <style>), and searches what is left for the banned terms. Exit code 1 when any
remain, with the page, the term and the sentence it sits in, so each one can be fixed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "out"

BANNED = [
    r"\bCI\b",
    r"\bconfidence intervals?\b",
    r"\bn\s?=",
    r"\bentropy\b",
    r"\bbits?\b",
    r"\bAUC\b",
    r"\bhold-?out\b",
    r"\bleave-one-(?:match|opponent)-out\b",
    r"\bfolds?\b",
    r"\bpopulation baseline\b",
    r"\bbaseline\b",
    r"\bxP\b",
    r"\breceiver-relative\b",
    r"\bhomography\b",
    r"\bWilson\b",
    r"\bNewcombe\b",
    r"\btypical[- ]pro reference\b",
    r"\btypical pros?\b",
    r"\b(?:front|mid|rear)_(?:fh|bh)\b",
    r"\bpercentage points\b",
    r"\bp-value\b",
    r"\bsignifican(?:t|ce)\b",
]
BANNED_RE = re.compile("|".join(f"(?:{b})" for b in BANNED))

# Elements whose whole subtree is one click away or not text at all.
SKIP_ATTR = "data-technical"
SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
HIDE_IN = {"details"}  # the body of a <details> is collapsed; its <summary> is visible
BLOCK_TAGS = {
    "p",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "td",
    "th",
    "dt",
    "dd",
    "div",
    "article",
    "section",
    "button",
    "label",
    "legend",
    "caption",
}


class MainText(HTMLParser):
    """Collects the visible main text of a page, one string per block element."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0  # inside a skipped subtree
        self.stack: list[tuple[str, bool]] = []  # (tag, counts toward skip)
        self.in_summary = 0
        self.details_depth = 0
        self.blocks: list[str] = []
        self.buf: list[str] = []
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        skip = tag in SKIP_TAGS or SKIP_ATTR in a or a.get("hidden") is not None or (tag in HIDE_IN)
        self.stack.append((tag, skip))
        if tag == "title":
            self.in_title = True
        if tag == "summary":
            self.in_summary += 1
        if skip:
            self.skip_depth += 1
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "summary":
            self.in_summary -= 1
        # pop to the matching tag
        while self.stack:
            t, skip = self.stack.pop()
            if skip:
                self.skip_depth -= 1
            if t == tag:
                break
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self.in_title:
            self.title += data
            return
        # a <summary> is visible even though its <details> body is not
        visible = self.skip_depth == 0 or (self.in_summary and self.skip_depth == 1)
        if visible and data.strip():
            self.buf.append(data)

    def _flush(self):
        text = " ".join(" ".join(self.buf).split())
        if text:
            self.blocks.append(text)
        self.buf = []

    def close(self):
        super().close()
        self._flush()


def _context(block: str, start: int, end: int) -> str:
    head = "…" if start else ""
    tail = "…" if end < len(block) else ""
    return head + block[start:end].strip() + tail


def scan_page(path: Path, out: Path = OUT) -> list[dict]:
    parser = MainText()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    found = []
    for block in parser.blocks:
        for m in BANNED_RE.finditer(block):
            s = max(0, m.start() - 70)
            found.append(
                {
                    "page": str(path.relative_to(out)).replace("\\", "/"),
                    "term": m.group(0),
                    "context": _context(block, s, m.end() + 70),
                }
            )
    return found


def scan(out: Path = OUT) -> list[dict]:
    pages = sorted(p for p in out.rglob("*.html") if "404" not in p.name)
    hits = []
    for p in pages:
        hits += scan_page(p, out)
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if not out.exists():
        print(f"{out} does not exist; run `npm run build` in web/ first", file=sys.stderr)
        return 2
    hits = scan(out)
    pages = len([p for p in out.rglob("*.html") if "404" not in p.name])
    if args.json:
        print(json.dumps({"pages": pages, "hits": hits}, indent=1, ensure_ascii=False))
    else:
        for h in hits:
            print(f"{h['page']}: “{h['term']}” in: {h['context']}")
        print(f"{len(hits)} banned terms in the main text of {pages} pages")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
