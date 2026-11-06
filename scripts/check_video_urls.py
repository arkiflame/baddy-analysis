"""Check that every match video URL in the datasets is still live, without downloading anything.

    uv run python scripts/check_video_urls.py              # writes data/video_status.json

For each URL in ShuttleSet's and ShuttleSet22's match.csv the script asks YouTube's public
oEmbed endpoint (https://www.youtube.com/oembed?url=...), which answers 200 with the title for
a public video, 401 for a private one and 404 for a removed one. No API key, no quota, no
video bytes: it is the same request a page makes to render a link preview. The result file is
committed so the web export can run offline and the Methods page can say when the check ran.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tactics.config import PROJECT_ROOT  # noqa: E402
from tactics.footage import STATUS_FILE, match_meta, video_id  # noqa: E402

OEMBED = "https://www.youtube.com/oembed?format=json&url="
TIMEOUT_S = 20


def fetch_oembed(url: str) -> tuple[int, dict]:
    """(HTTP status, parsed JSON or {}) for one video URL."""
    req = urllib.request.Request(
        OEMBED + urllib.parse.quote(url, safe=""),
        headers={"User-Agent": "badminton-tactics url check"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {}
    except (urllib.error.URLError, TimeoutError, ValueError):
        return 0, {}


def classify(status_code: int) -> tuple[bool, str]:
    """oEmbed status -> (live, reason)."""
    if status_code == 200:
        return True, "public"
    if status_code == 401:
        return False, "private or restricted"
    if status_code == 404:
        return False, "removed"
    if status_code == 0:
        return False, "no answer"
    return False, f"http {status_code}"


def check_all(
    urls: list[str], fetch: Callable[[str], tuple[int, dict]] = fetch_oembed, pause_s: float = 0.2
) -> dict:
    """{url: {video_id, status_code, live, reason, title, author}} for every distinct URL."""
    out = {}
    for url in dict.fromkeys(u for u in urls if isinstance(u, str) and u.strip()):
        code, body = fetch(url)
        live, reason = classify(code)
        out[url] = {
            "video_id": video_id(url),
            "status_code": code,
            "live": live,
            "reason": reason,
            "title": body.get("title"),
            "author": body.get("author_name"),
        }
        if pause_s:
            time.sleep(pause_s)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(PROJECT_ROOT / STATUS_FILE))
    args = ap.parse_args(argv)
    meta = match_meta()
    urls = meta.url.dropna().tolist()
    t0 = time.perf_counter()
    videos = check_all(urls)
    live = sum(v["live"] for v in videos.values())
    result = {
        "checked": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "method": "YouTube oEmbed (https://www.youtube.com/oembed), one request per URL, no download",
        "matches": int(len(meta)),
        "with_url": int(len(urls)),
        "distinct_urls": len(videos),
        "live": live,
        "videos": videos,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    for url, v in videos.items():
        if not v["live"]:
            print(f"NOT LIVE {v['status_code']:>3} {v['reason']:<24} {url}")
    print(
        f"{live} of {len(videos)} URLs live ({len(urls)} matches with a URL out of {len(meta)}); "
        f"wrote {out} in {time.perf_counter() - t0:.0f} s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
