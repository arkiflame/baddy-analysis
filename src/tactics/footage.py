"""Example rallies and YouTube links for the web UI (DECISIONS D30).

ShuttleSet's match.csv carries each match's YouTube URL (ShuttleSet22's does not), and every
stroke has its time in seconds in that broadcast. This module picks, for one insight, up to
three rallies that show the pattern and builds a link that starts the public YouTube player a
few seconds before the rally. Only embeds and links are produced: no video is downloaded, no
frame is stored, nothing from a broadcast enters the repository.

A rally qualifies for an insight when its pattern stroke is one of the strokes the danger table
counted (same filters as `analyses._danger_frame`), the outcome shows the claim (a weakness: the
player lost the point within two shots; a strength: the player did not, and won the rally), and
the match has a URL that `scripts/check_video_urls.py` found live.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from tactics.analyses import AnalysisSettings, _danger_frame, stroke_pressure
from tactics.config import DATA_ROOT
from tactics.court import COURT_LENGTH_M, COURT_WIDTH_M
from tactics.report import surname

DATASETS = ("ShuttleSet", "ShuttleSet22")
LEAD_IN_S = 5  # start the player this many seconds before the pattern stroke
MAX_EXAMPLES = 3
STATUS_FILE = Path("data") / "video_status.json"
YOUTUBE_ID = re.compile(r"(?:v=|youtu\.be/|/embed/|/shorts/|/live/)([A-Za-z0-9_-]{11})")


# ---------------------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------------------


def video_id(url: str | None) -> str | None:
    if not isinstance(url, str):
        return None
    m = YOUTUBE_ID.search(url.strip())
    return m.group(1) if m else None


def watch_url(vid: str, start_s: int) -> str:
    return f"https://www.youtube.com/watch?v={vid}&t={int(start_s)}s"


def embed_url(vid: str, start_s: int) -> str:
    """youtube-nocookie.com sets no tracking cookie until the viewer presses play."""
    return f"https://www.youtube-nocookie.com/embed/{vid}?start={int(start_s)}&rel=0"


def match_meta(root: Path = DATA_ROOT, datasets: tuple[str, ...] = DATASETS) -> pd.DataFrame:
    """One row per match: match_id (as the loader names it), url (may be missing), tournament,
    round, date. Matches present in both datasets keep the first dataset's row, like the loader."""
    rows, seen = [], set()
    for ds in datasets:
        path = root / ds / "set" / "match.csv"
        if not path.exists():
            continue
        m = pd.read_csv(path)
        for _, r in m.iterrows():
            if r.video in seen:
                continue
            seen.add(r.video)
            url = r["url"] if "url" in m.columns and isinstance(r.get("url"), str) else None
            rows.append(
                {
                    "match_id": f"{ds}:{int(r.id)}",
                    "dataset": ds,
                    "video": r.video,
                    "url": url,
                    "video_id": video_id(url),
                    "tournament": " ".join(str(r.tournament).split()),
                    "round": " ".join(str(r["round"]).split()),
                }
            )
    return pd.DataFrame(
        rows, columns=["match_id", "dataset", "video", "url", "video_id", "tournament", "round"]
    )


def load_status(path: Path = STATUS_FILE) -> dict:
    """The output of scripts/check_video_urls.py, or {} when it has not been run."""
    if not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def live_videos(meta: pd.DataFrame, status: dict) -> dict[str, dict]:
    """match_id -> {video_id, url, tournament, round} for matches whose URL was checked and
    found live. A URL that was never checked counts as not live: the button is hidden rather
    than shown on hope."""
    checked = status.get("videos", {})
    out = {}
    for r in meta.itertuples(index=False):
        if not isinstance(r.video_id, str):
            continue
        st = checked.get(r.url) or checked.get(r.video_id)
        if not st or not st.get("live"):
            continue
        out[r.match_id] = {
            "video_id": r.video_id,
            "url": r.url,
            "tournament": r.tournament,
            "round": r.round,
        }
    return out


def footage_summary(meta: pd.DataFrame, status: dict, videos: dict[str, dict]) -> dict:
    return {
        "matches": int(len(meta)),
        "with_url": int(meta.url.notna().sum()),
        "live": int(len(videos)),
        "checked": status.get("checked"),
        "method": status.get("method"),
    }


# ---------------------------------------------------------------------------------------
# Picking rallies
# ---------------------------------------------------------------------------------------


def candidates(
    ps: pd.DataFrame,
    s: AnalysisSettings,
    role: str,
    shot: str | None,
    zone: str | None,
    split: str | None,
) -> pd.DataFrame:
    """The strokes the danger table counted for this condition, with `lost_within`."""
    d = _danger_frame(ps, s, hit_by_player=(role == "hit"))
    if split == "game3":
        d = d[d.game == 3]
    elif split == "pressure":
        d = d[stroke_pressure(d, s)]
    if shot:
        d = d[d[s.shot_col].astype(str) == shot]
    if zone:
        d = d[d.coach_zone.astype(str) == zone]
    return d


def pick_examples(
    ps: pd.DataFrame,
    player: str,
    s: AnalysisSettings,
    role: str,
    shot: str | None,
    zone: str | None,
    split: str | None,
    worse: bool,
    videos: dict[str, dict],
    k: int = MAX_EXAMPLES,
) -> list[dict]:
    """Up to k example rallies from distinct matches with live footage, shortest wait first.

    worse=True (the player loses more than most pros here): rallies the player lost within
    `s.within` shots of the pattern stroke. worse=False (a strength): rallies the player did not
    lose quickly and went on to win, so the viewer sees the pattern fail to hurt.
    """
    if not videos or "time_s" not in ps.columns:
        return []
    d = candidates(ps, s, role, shot, zone, split)
    d = d[d.lost_within] if worse else d[~d.lost_within & d.player_won]
    d = d[d.match_id.astype(str).isin(videos) & d.time_s.notna()]
    if d.empty:
        return []
    d = d.sort_values(["strokes_to_end", "match_id", "rally_id", "stroke_no"], kind="stable")
    d = d.drop_duplicates("rally_id")
    first_per_match = d.drop_duplicates("match_id")
    rest = d[~d.index.isin(first_per_match.index)]
    chosen = pd.concat([first_per_match, rest]).head(k)
    return [
        example_json(ps, row, player, videos[str(row.match_id)]) for _, row in chosen.iterrows()
    ]


def example_json(ps: pd.DataFrame, row: pd.Series, player: str, video: dict) -> dict:
    start = max(0, int(math.floor(float(row.time_s))) - LEAD_IN_S)
    opp = surname(str(row.opponent)) if "opponent" in row.index else "the opponent"
    return {
        "match_id": str(row.match_id),
        "label": f"vs {opp}, {video['tournament']}, {video['round']}",
        "date": str(row.date) if "date" in row.index else None,
        "game": int(row.game),
        "rally_no": int(row.rally_no) if "rally_no" in row.index else None,
        "stroke_no": int(row.stroke_no),
        "at_s": int(math.floor(float(row.time_s))),
        "start_s": start,
        "outcome": "won" if bool(row.player_won) else "lost",
        "ends_in": int(row.strokes_to_end),
        "video_id": video["video_id"],
        "watch": watch_url(video["video_id"], start),
        "embed": embed_url(video["video_id"], start),
        "strokes": rally_json(ps, str(row.rally_id), player, int(row.stroke_no)),
    }


def _pt(x, y, flip: bool) -> list[float] | None:
    if x is None or y is None or pd.isna(x) or pd.isna(y):
        return None
    if flip:
        x, y = COURT_WIDTH_M - float(x), COURT_LENGTH_M - float(y)
    return [round(float(x), 2), round(float(y), 2)]


def rally_json(ps: pd.DataFrame, rally_id: str, player: str, highlight: int) -> list[dict]:
    """Every stroke of the rally as an arrow from the contact point to the landing point, in a
    full-court frame (x across 0..6.10, y along 0..13.40) oriented so the player's half is the
    bottom half (y > 6.70). Serves have no contact point in the data; the hitter's position
    stands in."""
    r = ps[ps.rally_id.astype(str) == rally_id].sort_values("stroke_no")
    mine = r[r.hitter.astype(str) == player]
    my_half = str(mine.hitter_half.mode().iloc[0]) if len(mine) else None
    flip = my_half == "far"
    out = []
    for st in r.itertuples(index=False):
        hx = getattr(st, "hit_x", np.nan)
        hy = getattr(st, "hit_y", np.nan)
        if pd.isna(hx) or pd.isna(hy):
            hx, hy = getattr(st, "hitter_x", np.nan), getattr(st, "hitter_y", np.nan)
        out.append(
            {
                "no": int(st.stroke_no),
                "by": "me" if str(st.hitter) == player else "opp",
                "shot": str(st.shot_coarse),
                "from": _pt(hx, hy, flip),
                "to": _pt(getattr(st, "land_x", np.nan), getattr(st, "land_y", np.nan), flip),
                "zone": None if pd.isna(st.coach_zone) else str(st.coach_zone),
                "highlight": int(st.stroke_no) == highlight,
            }
        )
    return out
