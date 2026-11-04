"""Shot type vocabulary.

ShuttleSet labels strokes in Chinese with 18 types plus an "unknown" marker. We keep the full
18 (coaches think in these terms) and offer the dataset authors' 10-way coarsening for analyses
that need more samples per category.
"""

from __future__ import annotations

UNKNOWN = "unknown"

ZH_TO_EN: dict[str, str] = {
    "放小球": "net_shot",
    "擋小球": "return_net",
    "殺球": "smash",
    "點扣": "wrist_smash",
    "挑球": "lob",
    "防守回挑": "defensive_return_lob",
    "長球": "clear",
    "平球": "drive",
    "小平球": "driven_flight",
    "後場抽平球": "back_court_drive",
    "切球": "drop",
    "過渡切球": "passive_drop",
    "過度切球": "passive_drop",  # spelling variant that appears in the data
    "推球": "push",
    "撲球": "rush",
    "防守回抽": "defensive_return_drive",
    "勾球": "cross_court_net_shot",
    "發短球": "short_service",
    "發長球": "long_service",
    "未知球種": UNKNOWN,
}

SHOT_TYPES: tuple[str, ...] = tuple(dict.fromkeys(ZH_TO_EN.values()))
SERVES = frozenset({"short_service", "long_service"})

# The 10-type grouping used by the ShuttleSet authors' own preprocessing.
COARSE: dict[str, str] = {
    "net_shot": "net", "cross_court_net_shot": "net",
    "return_net": "defensive", "defensive_return_lob": "defensive", "defensive_return_drive": "defensive",
    "smash": "smash", "wrist_smash": "smash",
    "lob": "lob",
    "clear": "clear",
    "drive": "drive", "driven_flight": "drive", "back_court_drive": "drive",
    "drop": "drop", "passive_drop": "drop",
    "push": "push_rush", "rush": "push_rush",
    "short_service": "short_service", "long_service": "long_service",
    UNKNOWN: UNKNOWN,
}

# Why the rally ended, from the LOSER's perspective, recorded on the final stroke.
LOSE_REASON_ZH_TO_EN: dict[str, str] = {
    "對手落地致勝": "opponent_winner",       # the final shot landed in: the hitter won
    "出界": "out",                            # hitter hit out
    "掛網": "net",                            # hitter hit into the net
    "未過網": "not_over_net",                 # hitter failed to clear the net
    "落點判斷失誤": "misjudged_landing",      # loser left a shuttle that was in
    "對手落地判斷失誤": "opponent_misjudged",  # rare; recorded from the other side
    "犯規": "fault",
}

# Did the hitter of the final stroke make an error? (None = depends on getpoint_player)
FINAL_HITTER_ERROR: dict[str, bool | None] = {
    "opponent_winner": False,
    "out": True,
    "net": True,
    "not_over_net": True,
    "misjudged_landing": False,
    "opponent_misjudged": False,
    "fault": None,
}


def to_english(zh: str) -> str:
    try:
        return ZH_TO_EN[zh]
    except KeyError as e:
        raise KeyError(f"unknown shot label {zh!r}; add it to shots.ZH_TO_EN") from e
