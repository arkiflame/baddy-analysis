"""The domain model: Match -> Game -> Rally -> Stroke.

Plain dataclasses, no ORM. Every analysis consumes either these objects or the flat
pandas table built from them by `loader.strokes_frame`. Positions are in court metres
(see court.py); never pixels.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

Point = tuple[float, float]  # (x, y) in court metres


@dataclass(slots=True)
class Stroke:
    number: int  # 1-based index within the rally (ball_round)
    hitter: str  # player name
    receiver: str
    shot: str  # English shot type, see shots.SHOT_TYPES
    shot_zh: str
    backhand: bool
    aroundhead: bool
    hit_height: int | None  # 1 = below net height, 2 = above
    landing_height: int | None
    hit: Point | None  # where the shuttle was struck (None for serves)
    landing: Point | None  # where it landed / was next struck
    hitter_pos: Point | None  # hitter's feet at contact
    receiver_pos: Point | None  # receiver's feet at contact
    hitter_half: str | None  # "far" | "near": the court half the hitter stands in
    flaw: bool
    time_s: float | None  # seconds into the broadcast video


@dataclass(slots=True)
class Rally:
    number: int  # rally index within the game
    strokes: list[Stroke]
    winner: str | None  # player name; None only if it cannot be inferred
    lose_reason: str | None  # English code, see shots.LOSE_REASON_ZH_TO_EN
    score_before: tuple[int, int]  # (player_a, player_b) when the rally started
    score_after: tuple[int, int]
    annotated: bool  # False for the placeholder "one unknown stroke" rallies
    has_unknown: bool  # any stroke of unknown type
    flawed: bool  # any stroke flagged by the annotators
    score_gap: bool  # score_before disagrees with the previous rally's score_after

    @property
    def length(self) -> int:
        return len(self.strokes)

    @property
    def server(self) -> str:
        return self.strokes[0].hitter

    @property
    def last(self) -> Stroke:
        return self.strokes[-1]


@dataclass(slots=True)
class Game:
    number: int
    rallies: list[Rally]

    @property
    def final_score(self) -> tuple[int, int]:
        return self.rallies[-1].score_after if self.rallies else (0, 0)


@dataclass(slots=True)
class Match:
    id: str  # "<dataset>:<id>", unique across datasets
    dataset: str
    video: str
    tournament: str
    round: str
    date: str  # ISO yyyy-mm-dd, may be empty
    player_a: str  # the match winner (the dataset's label A)
    player_b: str
    homography: np.ndarray = field(repr=False)
    games: list[Game] = field(default_factory=list)

    @property
    def players(self) -> tuple[str, str]:
        return (self.player_a, self.player_b)

    def rallies(self):
        for g in self.games:
            yield from g.rallies
