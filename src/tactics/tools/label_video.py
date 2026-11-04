"""Manual labelling tool: shuttle positions, hit frames and shot types -> ShuttleSet schema.

    uv run python -m tactics.tools.label_video VIDEO --out data/own/<match>/set1.csv

Keys (OpenCV window)
  a / d        previous / next frame          A / D   jump 10 frames back / forward
  left click   shuttle position in this frame (also used as the hit point on a hit frame)
  h            mark this frame as a HIT by the current player (then press a shot key)
  0-9          shot type for the last hit (see SHOT_KEYS; 10 coarse types)
  tab          switch current player (A / B)
  p / o        next click sets the hitter's / opponent's feet position for the last hit
  w / l        rally over: player A won / player B won (ends the rally, bumps the score)
  x            delete the last hit        s  save        q  save and quit

Design: all state lives in `LabelSession`, a plain class with no OpenCV in it, so the logic
(score keeping, rally numbering, landing = next hit point) is unit-tested and the session can
be saved to JSON and resumed. The exporter writes the same columns as ShuttleSet's set{n}.csv,
with shot types as the dataset's Chinese labels, so `tactics.loader` reads our files unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from tactics.shots import ZH_TO_EN

# Coarse shot types on number keys. Chinese labels are the dataset's, chosen to map to the
# authors' 10-way grouping (see shots.COARSE).
SHOT_KEYS: dict[str, str] = {
    "1": "發短球",  # short service
    "2": "發長球",  # long service
    "3": "放小球",  # net shot
    "4": "挑球",  # lob
    "5": "長球",  # clear
    "6": "切球",  # drop
    "7": "殺球",  # smash
    "8": "平球",  # drive
    "9": "推球",  # push / rush
    "0": "擋小球",  # defensive return
}
assert all(v in ZH_TO_EN for v in SHOT_KEYS.values())

SET_COLUMNS = [
    "rally",
    "ball_round",
    "time",
    "frame_num",
    "roundscore_A",
    "roundscore_B",
    "player",
    "server",
    "type",
    "aroundhead",
    "backhand",
    "hit_height",
    "hit_area",
    "hit_x",
    "hit_y",
    "landing_height",
    "landing_area",
    "landing_x",
    "landing_y",
    "lose_reason",
    "win_reason",
    "getpoint_player",
    "flaw",
    "player_location_area",
    "player_location_x",
    "player_location_y",
    "opponent_location_area",
    "opponent_location_x",
    "opponent_location_y",
    "db",
]


@dataclass(slots=True)
class Hit:
    frame: int
    player: str  # "A" | "B"
    shot: str | None = None  # Chinese label
    x: float | None = None  # shuttle at contact (pixels)
    y: float | None = None
    hitter_xy: tuple[float, float] | None = None
    opponent_xy: tuple[float, float] | None = None
    backhand: bool = False


@dataclass(slots=True)
class RallyLabel:
    number: int
    hits: list[Hit] = field(default_factory=list)
    winner: str | None = None  # "A" | "B"
    score_after: tuple[int, int] | None = None


@dataclass(slots=True)
class LabelSession:
    video: str
    fps: float
    shuttle: dict[int, tuple[float, float]] = field(default_factory=dict)  # frame -> (x, y)
    rallies: list[RallyLabel] = field(default_factory=list)
    score: tuple[int, int] = (0, 0)
    current_player: str = "A"

    # ---- editing ------------------------------------------------------------------------
    def click(self, frame: int, x: float, y: float) -> None:
        """A shuttle position for this frame; also fills the hit point of a hit on this frame."""
        self.shuttle[frame] = (float(x), float(y))
        for h in self._open_hits():
            if h.frame == frame:
                h.x, h.y = float(x), float(y)

    def add_hit(self, frame: int, player: str | None = None) -> Hit:
        player = player or self.current_player
        if not self.rallies or self.rallies[-1].winner is not None:
            self.rallies.append(RallyLabel(number=len(self.rallies) + 1))
        hit = Hit(frame=frame, player=player)
        if frame in self.shuttle:
            hit.x, hit.y = self.shuttle[frame]
        self.rallies[-1].hits.append(hit)
        self.current_player = "B" if player == "A" else "A"
        return hit

    def set_shot(self, key: str) -> None:
        if key in SHOT_KEYS and self._last_hit():
            self._last_hit().shot = SHOT_KEYS[key]

    def set_position(self, who: str, x: float, y: float) -> None:
        h = self._last_hit()
        if h is None:
            return
        if who == "hitter":
            h.hitter_xy = (float(x), float(y))
        else:
            h.opponent_xy = (float(x), float(y))

    def end_rally(self, winner: str) -> None:
        if not self.rallies or self.rallies[-1].winner is not None:
            return
        a, b = self.score
        self.score = (a + 1, b) if winner == "A" else (a, b + 1)
        self.rallies[-1].winner = winner
        self.rallies[-1].score_after = self.score
        # the winner of a rally serves the next one
        self.current_player = winner

    def delete_last_hit(self) -> None:
        if self.rallies and self.rallies[-1].winner is None and self.rallies[-1].hits:
            h = self.rallies[-1].hits.pop()
            self.current_player = h.player
            if not self.rallies[-1].hits:
                self.rallies.pop()

    def toggle_player(self) -> None:
        self.current_player = "B" if self.current_player == "A" else "A"

    def _open_hits(self) -> list[Hit]:
        return self.rallies[-1].hits if self.rallies and self.rallies[-1].winner is None else []

    def _last_hit(self) -> Hit | None:
        return self.rallies[-1].hits[-1] if self.rallies and self.rallies[-1].hits else None

    # ---- export -------------------------------------------------------------------------
    def strokes_frame(self) -> pd.DataFrame:
        """ShuttleSet set{n}.csv rows. landing of stroke k = hit point of stroke k+1."""
        rows = []
        for r in self.rallies:
            n = len(r.hits)
            for i, h in enumerate(r.hits):
                nxt = r.hits[i + 1] if i + 1 < n else None
                last = i == n - 1
                t = h.frame / self.fps
                rows.append(
                    {
                        "rally": r.number,
                        "ball_round": i + 1,
                        "time": f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d}",
                        "frame_num": h.frame,
                        "roundscore_A": (r.score_after or self.score)[0],
                        "roundscore_B": (r.score_after or self.score)[1],
                        "player": h.player,
                        "server": 1 if i == 0 else (3 if last else 2),
                        "type": h.shot or "未知球種",
                        "aroundhead": None,
                        "backhand": 1 if h.backhand else None,
                        "hit_height": None,
                        "hit_area": None,
                        "hit_x": h.x,
                        "hit_y": h.y,
                        "landing_height": None,
                        "landing_area": None,
                        "landing_x": nxt.x if nxt else None,
                        "landing_y": nxt.y if nxt else None,
                        "lose_reason": None,
                        "win_reason": None,
                        "getpoint_player": r.winner if last else None,
                        "flaw": None,
                        "player_location_area": None,
                        "player_location_x": h.hitter_xy[0] if h.hitter_xy else None,
                        "player_location_y": h.hitter_xy[1] if h.hitter_xy else None,
                        "opponent_location_area": None,
                        "opponent_location_x": h.opponent_xy[0] if h.opponent_xy else None,
                        "opponent_location_y": h.opponent_xy[1] if h.opponent_xy else None,
                        "db": 0,
                    }
                )
        return pd.DataFrame(rows, columns=SET_COLUMNS)

    def shuttle_frame(self) -> pd.DataFrame:
        """Per-frame shuttle labels in TrackNet's CSV format (Frame, Visibility, X, Y)."""
        rows = [
            {"Frame": f, "Visibility": 1, "X": x, "Y": y}
            for f, (x, y) in sorted(self.shuttle.items())
        ]
        return pd.DataFrame(rows, columns=["Frame", "Visibility", "X", "Y"])

    # ---- persistence --------------------------------------------------------------------
    def to_json(self) -> str:
        d = asdict(self)
        d["shuttle"] = {str(k): v for k, v in self.shuttle.items()}
        return json.dumps(d, indent=1)

    @classmethod
    def from_json(cls, text: str) -> LabelSession:
        d = json.loads(text)
        s = cls(
            video=d["video"],
            fps=d["fps"],
            score=tuple(d["score"]),
            current_player=d["current_player"],
        )
        s.shuttle = {int(k): tuple(v) for k, v in d["shuttle"].items()}
        for r in d["rallies"]:
            hits = [
                Hit(
                    **{
                        **h,
                        "hitter_xy": tuple(h["hitter_xy"]) if h["hitter_xy"] else None,
                        "opponent_xy": tuple(h["opponent_xy"]) if h["opponent_xy"] else None,
                    }
                )
                for h in r["hits"]
            ]
            s.rallies.append(
                RallyLabel(
                    number=r["number"],
                    hits=hits,
                    winner=r["winner"],
                    score_after=tuple(r["score_after"]) if r["score_after"] else None,
                )
            )
        return s


# -------------------------------------------------------------------------------------------
# OpenCV loop
# -------------------------------------------------------------------------------------------


def run(video: Path, out_csv: Path, session_path: Path | None = None) -> int:
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise FileNotFoundError(video)
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    session_path = session_path or out_csv.with_suffix(".session.json")
    s = (
        LabelSession.from_json(session_path.read_text())
        if session_path.exists()
        else LabelSession(video.name, fps)
    )

    idx, pending = 0, None  # pending: "hitter" | "opponent" position click
    win = f"label {video.name}"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    def on_mouse(event, x, y, flags, param):
        nonlocal pending
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if pending:
            s.set_position(pending, x, y)
            pending = None
        else:
            s.click(idx, x, y)

    cv2.setMouseCallback(win, on_mouse)

    def save():
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        s.strokes_frame().to_csv(out_csv, index=False)
        s.shuttle_frame().to_csv(out_csv.with_name(out_csv.stem + "_shuttle.csv"), index=False)
        session_path.write_text(s.to_json())

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            idx = max(0, idx - 1)
            continue
        img = frame.copy()
        if idx in s.shuttle:
            x, y = s.shuttle[idx]
            cv2.circle(img, (int(x), int(y)), 6, (0, 255, 255), 2)
        hits = [h for r in s.rallies for h in r.hits]
        on_hit = next((h for h in hits if h.frame == idx), None)
        rally_no = (
            s.rallies[-1].number
            if s.rallies and s.rallies[-1].winner is None
            else len(s.rallies) + 1
        )
        here = f"  HIT here: {on_hit.player} {on_hit.shot or '?'}" if on_hit else ""
        hud = [
            f"frame {idx}/{n_frames}  rally {rally_no}  score A {s.score[0]} - B {s.score[1]}"
            f"  next hitter: {s.current_player}",
            f"shuttle labels {len(s.shuttle)}  hits {len(hits)}{here}",
            "a/d frame  A/D x10  click shuttle  h hit  0-9 shot  tab player  p/o positions",
            "w/l rally won by A/B  x undo  s save  q quit",
        ]
        if pending:
            hud.append(f"click the {pending}'s feet")
        for i, line in enumerate(hud):
            cv2.putText(
                img, line, (10, 25 + 24 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
            )
        cv2.imshow(win, img)
        key = cv2.waitKey(0) & 0xFF
        if key == ord("q"):
            save()
            break
        elif key == ord("s"):
            save()
        elif key == ord("d"):
            idx = min(n_frames - 1, idx + 1)
        elif key == ord("a"):
            idx = max(0, idx - 1)
        elif key == ord("D"):
            idx = min(n_frames - 1, idx + 10)
        elif key == ord("A"):
            idx = max(0, idx - 10)
        elif key == ord("h"):
            s.add_hit(idx)
        elif chr(key) in SHOT_KEYS:
            s.set_shot(chr(key))
        elif key == 9:  # tab
            s.toggle_player()
        elif key == ord("p"):
            pending = "hitter"
        elif key == ord("o"):
            pending = "opponent"
        elif key == ord("w"):
            s.end_rally("A")
        elif key == ord("l"):
            s.end_rally("B")
        elif key == ord("x"):
            s.delete_last_hit()
    cap.release()
    cv2.destroyAllWindows()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("video", type=Path)
    ap.add_argument(
        "--out", type=Path, required=True, help="strokes CSV, e.g. data/own/match1/set1.csv"
    )
    a = ap.parse_args(argv)
    return run(a.video, a.out)


if __name__ == "__main__":
    sys.exit(main())
