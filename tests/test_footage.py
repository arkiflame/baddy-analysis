"""Example rallies and the URL check (D30): rallies are picked from the strokes the danger table
counted, show the claimed outcome, come from matches with live footage, and never involve a
download; the URL check classifies oEmbed answers without touching the network in tests."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from tactics import footage
from tactics.analyses import AnalysisSettings, player_strokes
from tests.synthetic import synthetic_strokes

ROOT = Path(__file__).resolve().parents[1]


def _with_video_columns(df: pd.DataFrame, seed: int = 3) -> pd.DataFrame:
    """The synthetic table plus the columns the real loader has: a time in the broadcast, a
    contact point (the hitter's feet) and a landing point in the other half."""
    rng = np.random.default_rng(seed)
    d = df.copy()
    d["time_s"] = np.arange(len(d), dtype=float) * 2 + 100
    d["hit_x"], d["hit_y"] = d.hitter_x, d.hitter_y
    d["land_x"] = rng.uniform(0.5, 5.6, len(d))
    near = d.hitter_half == "near"
    d["land_y"] = np.where(near, rng.uniform(0.5, 6.2, len(d)), rng.uniform(7.2, 12.9, len(d)))
    d["date"] = "2020-01-01"
    d["opponent"] = "Y"
    return d


def test_video_ids_and_urls():
    assert footage.video_id("https://www.youtube.com/watch?v=O669aZhH0LI") == "O669aZhH0LI"
    assert footage.video_id("https://youtu.be/-aOI9_JxoWc?t=12") == "-aOI9_JxoWc"
    assert footage.video_id("https://www.youtube.com/watch?v=eugfCRwSBJo&list=x") == "eugfCRwSBJo"
    assert footage.video_id(None) is None and footage.video_id("not a url") is None
    assert footage.embed_url("O669aZhH0LI", 649) == (
        "https://www.youtube-nocookie.com/embed/O669aZhH0LI?start=649&rel=0"
    )
    assert (
        footage.watch_url("O669aZhH0LI", 649)
        == "https://www.youtube.com/watch?v=O669aZhH0LI&t=649s"
    )


def test_only_checked_live_urls_get_a_button():
    meta = pd.DataFrame(
        {
            "match_id": ["ShuttleSet:1", "ShuttleSet:2", "ShuttleSet:3", "ShuttleSet22:1"],
            "dataset": ["ShuttleSet"] * 3 + ["ShuttleSet22"],
            "video": list("abcd"),
            "url": [
                "https://www.youtube.com/watch?v=AAAAAAAAAAA",
                "https://www.youtube.com/watch?v=BBBBBBBBBBB",
                "https://www.youtube.com/watch?v=CCCCCCCCCCC",
                None,
            ],
            "video_id": ["AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC", None],
            "tournament": ["T"] * 4,
            "round": ["Final"] * 4,
        }
    )
    status = {
        "checked": "2026-11-06T00:00:00+00:00",
        "videos": {
            "https://www.youtube.com/watch?v=AAAAAAAAAAA": {"live": True},
            "https://www.youtube.com/watch?v=BBBBBBBBBBB": {"live": False, "reason": "removed"},
            # C was never checked: hidden, not shown on hope
        },
    }
    live = footage.live_videos(meta, status)
    assert list(live) == ["ShuttleSet:1"] and live["ShuttleSet:1"]["video_id"] == "AAAAAAAAAAA"
    assert footage.live_videos(meta, {}) == {}
    summary = footage.footage_summary(meta, status, live)
    assert summary == {
        "matches": 4,
        "with_url": 3,
        "live": 1,
        "checked": status["checked"],
        "method": None,
    }


def test_examples_show_the_claim_from_matches_with_footage():
    df = _with_video_columns(synthetic_strokes())
    s = AnalysisSettings()
    ps = player_strokes(df, "X")
    videos = {
        m: {"video_id": "AAAAAAAAAAA", "url": "u", "tournament": "Open", "round": "Final"}
        for m in ps.match_id.astype(str).unique()
    }
    # the planted weakness: X loses within two shots after a push/rush to the rear backhand
    ex = footage.pick_examples(ps, "X", s, "faced", "push_rush", "rear_bh", None, True, videos)
    assert 1 <= len(ex) <= footage.MAX_EXAMPLES
    # distinct matches first, then more rallies from the same matches (X plays two matches)
    assert len({e["match_id"] for e in ex}) == min(len(ex), ps.match_id.nunique())
    for e in ex:
        assert e["outcome"] == "lost" and e["ends_in"] <= s.within
        assert e["start_s"] == max(0, e["at_s"] - footage.LEAD_IN_S)
        assert e["embed"].startswith("https://www.youtube-nocookie.com/embed/AAAAAAAAAAA?start=")
        assert e["watch"].startswith("https://www.youtube.com/watch?v=AAAAAAAAAAA&t=")
        assert e["label"] in ("vs Y, Open, Final", "vs Z, Open, Final")  # X plays Y and Z
        strokes = e["strokes"]
        hl = [st for st in strokes if st["highlight"]]
        assert len(hl) == 1 and hl[0]["no"] == e["stroke_no"]
        assert hl[0]["by"] == "opp" and hl[0]["shot"] == "push_rush" and hl[0]["zone"] == "rear_bh"
        # the pattern stroke is one of the last `within` + 1 strokes of a lost rally
        assert strokes[-1]["no"] - hl[0]["no"] <= s.within
        # oriented so X's half is the bottom half: X hits from y > net, the opponent from y < net
        for st in strokes:
            if st["from"] is not None:
                assert (st["from"][1] > 6.7) == (st["by"] == "me"), st
    # a strength: rallies X did not lose quickly and went on to win
    good = footage.pick_examples(ps, "X", s, "faced", None, None, None, False, videos)
    assert good and all(e["outcome"] == "won" for e in good)
    # no footage, no examples; a split narrows the candidates to that split
    assert footage.pick_examples(ps, "X", s, "faced", "push_rush", "rear_bh", None, True, {}) == []
    g3 = footage.pick_examples(ps, "X", s, "faced", None, None, "game3", True, videos)
    assert g3 == []  # the synthetic table has two games, so no deciding game
    # a matching rally is chosen only from matches with footage
    one = {k: v for k, v in list(videos.items())[:1]}
    only = footage.pick_examples(ps, "X", s, "faced", "push_rush", "rear_bh", None, True, one)
    assert only and all(e["match_id"] == next(iter(one)) for e in only)


def test_match_meta_reads_both_datasets_and_only_shuttleset_has_urls(tmp_path):
    for ds, extra in (("ShuttleSet", "url"), ("ShuttleSet22", "db")):
        (tmp_path / ds / "set").mkdir(parents=True)
        val = "https://www.youtube.com/watch?v=O669aZhH0LI" if extra == "url" else "0"
        (tmp_path / ds / "set" / "match.csv").write_text(
            f"id,video,tournament,round,year,month,day,set,duration,winner,loser,downcourt,{extra}\n"
            f"1,{ds}_vid,Open  2020,Finals,2020,1,1,3,80,A B,C D,0,{val}\n",
            encoding="utf-8",
        )
    meta = footage.match_meta(tmp_path)
    assert meta.match_id.tolist() == ["ShuttleSet:1", "ShuttleSet22:1"]
    assert meta.video_id.iloc[0] == "O669aZhH0LI" and pd.isna(meta.video_id.iloc[1])
    assert meta.tournament.iloc[0] == "Open 2020"


def _load_check_script():
    spec = importlib.util.spec_from_file_location(
        "check_video_urls", ROOT / "scripts" / "check_video_urls.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_url_check_classifies_oembed_answers_without_the_network():
    mod = _load_check_script()
    answers = {
        "https://www.youtube.com/watch?v=AAAAAAAAAAA": (
            200,
            {"title": "Final", "author_name": "BWF TV"},
        ),
        "https://www.youtube.com/watch?v=BBBBBBBBBBB": (401, {}),
        "https://www.youtube.com/watch?v=CCCCCCCCCCC": (404, {}),
        "https://www.youtube.com/watch?v=DDDDDDDDDDD": (0, {}),
    }
    calls = []

    def fake(url):
        calls.append(url)
        return answers[url]

    urls = list(answers) + [list(answers)[0], None, ""]  # duplicates and blanks are skipped
    out = mod.check_all(urls, fetch=fake, pause_s=0)
    assert calls == list(answers)
    a = out["https://www.youtube.com/watch?v=AAAAAAAAAAA"]
    assert a == {
        "video_id": "AAAAAAAAAAA",
        "status_code": 200,
        "live": True,
        "reason": "public",
        "title": "Final",
        "author": "BWF TV",
    }
    assert out["https://www.youtube.com/watch?v=BBBBBBBBBBB"]["reason"] == "private or restricted"
    assert out["https://www.youtube.com/watch?v=CCCCCCCCCCC"]["reason"] == "removed"
    assert out["https://www.youtube.com/watch?v=DDDDDDDDDDD"]["reason"] == "no answer"
    assert mod.classify(500) == (False, "http 500")
    # the result file this script writes is what footage.live_videos reads
    status = {"videos": out}
    meta = pd.DataFrame(
        [
            {
                "match_id": "ShuttleSet:1",
                "dataset": "ShuttleSet",
                "video": "a",
                "url": u,
                "video_id": footage.video_id(u),
                "tournament": "T",
                "round": "R",
            }
            for u in answers
        ]
    )
    assert list(footage.live_videos(meta, status)) == ["ShuttleSet:1"]
