"""Position maps: where a player stands when hitting and when the opponent hits.

What the data allows
--------------------
ShuttleSet records each player's feet position only at the moment a stroke is hit (the hitter's
own position and the receiver's position at that instant). Nothing is known about the path
between two strokes, so everything here is a POSITION map, never a footwork path, and the
"distance per rally" is a lower bound: the straight line between consecutive own-hit positions.

Frame
-----
Every position is expressed in the player's own half: `depth` metres from the net into the
player's half (net = 0, baseline = 6.70) and `lat_right` metres from the centre line toward the
player's own right. Nothing is mirrored for handedness (DECISIONS D21); instead the report labels
the lateral axis with the player's forehand and backhand side from config/players.toml, and
`lat_fh` (toward the forehand) is also provided.

Outputs
-------
* heatmaps of hit and receive positions on a court drawn to scale
* base position: the median receive position (where the player is when the opponent hits a
  non-serve stroke) and how far from it the player is pulled by the opponent's shot type
* distance per rally and per own stroke, split by game number and score pressure
All of it next to the same numbers for all other players ("typical pros").
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tactics.analyses import AnalysisSettings  # noqa: E402
from tactics.config import ZoneConfig  # noqa: E402
from tactics.stats import mean_ci, welch_diff_ci  # noqa: E402

SHORT_SERVICE_M = 1.98
LONG_SERVICE_DOUBLES_M = 0.76  # from the baseline


# ---------------------------------------------------------------------------------------
# All players' positions in one frame
# ---------------------------------------------------------------------------------------


def all_positions(
    df: pd.DataFrame, cfg: ZoneConfig, s: AnalysisSettings | None = None
) -> pd.DataFrame:
    """Two rows per annotated stroke: the hitter where they hit, the receiver where they stood.

    Columns: player, role ('hit' | 'receive'), handed, depth, lat_right, lat_fh, shot (the
    stroke being hit), incoming (for hit rows: the opponent's previous shot that the player is
    answering; for receive rows: the shot being hit at them), rally_id, match_id, game,
    stroke_no, n_strokes, is_serve, pressure, player_won.
    """
    s = s or AnalysisSettings()
    d = df[df.annotated & df.rally_winner.notna()].sort_values(["rally_id", "stroke_no"])
    prev_shot = d.groupby("rally_id", observed=True)["shot_coarse"].shift(1)
    pressure = np.maximum(d.score_before_hitter, d.score_before_receiver) >= s.pressure_from
    common = {
        "rally_id": d.rally_id.to_numpy(),
        "match_id": d.match_id.astype(str).to_numpy(),
        "game": d.game.to_numpy(),
        "stroke_no": d.stroke_no.to_numpy(),
        "n_strokes": d.n_strokes.to_numpy(),
        "is_serve": d.is_serve.to_numpy(),
        "pressure": np.asarray(pressure),
        "shot": d.shot_coarse.astype(str).to_numpy(),
    }
    hit_half = d.hitter_half.astype(str).to_numpy()
    recv_half = np.where(hit_half == "near", "far", np.where(hit_half == "far", "near", "nan"))
    hit = pd.DataFrame(
        {
            "player": d.hitter.astype(str).to_numpy(),
            "role": "hit",
            "handed": d.hitter_handed.astype(str).to_numpy(),
            "half": hit_half,
            "x": d.hitter_x.to_numpy(float),
            "y": d.hitter_y.to_numpy(float),
            "incoming": prev_shot.astype(str).where(prev_shot.notna(), None).to_numpy(),
            "player_won": (d.rally_winner.astype(str) == d.hitter.astype(str)).to_numpy(),
            **common,
        }
    )
    recv = pd.DataFrame(
        {
            "player": d.receiver.astype(str).to_numpy(),
            "role": "receive",
            "handed": d.receiver_handed.astype(str).to_numpy(),
            "half": recv_half,
            "x": d.recv_x.to_numpy(float),
            "y": d.recv_y.to_numpy(float),
            "incoming": d.shot_coarse.astype(str).to_numpy(),
            "player_won": (d.rally_winner.astype(str) == d.receiver.astype(str)).to_numpy(),
            **common,
        }
    )
    pos = pd.concat([hit, recv], ignore_index=True)
    near, far = pos.half == "near", pos.half == "far"
    pos["depth"] = np.where(near, pos.y - cfg.net_y, np.where(far, cfg.net_y - pos.y, np.nan))
    pos["lat_right"] = np.where(
        near, pos.x - cfg.centre_x, np.where(far, cfg.centre_x - pos.x, np.nan)
    )
    pos["lat_fh"] = np.where(pos.handed == "left", -pos.lat_right, pos.lat_right)
    pos = pos.dropna(subset=["depth", "lat_right"])
    return pos.sort_values(["player", "rally_id", "stroke_no"]).reset_index(drop=True)


# ---------------------------------------------------------------------------------------
# Base position, pull, distance
# ---------------------------------------------------------------------------------------


def base_positions(pos: pd.DataFrame) -> pd.DataFrame:
    """Per player: median receive position when the opponent hits a non-serve stroke."""
    r = pos[(pos.role == "receive") & ~pos.is_serve]
    g = r.groupby("player")
    out = g.agg(
        n=("depth", "size"),
        base_lat_right=("lat_right", "median"),
        base_depth=("depth", "median"),
        lat_q1=("lat_right", lambda v: v.quantile(0.25)),
        lat_q3=("lat_right", lambda v: v.quantile(0.75)),
        depth_q1=("depth", lambda v: v.quantile(0.25)),
        depth_q3=("depth", lambda v: v.quantile(0.75)),
    )
    return out.reset_index()


def pull_from_base(pos: pd.DataFrame, bases: pd.DataFrame) -> pd.DataFrame:
    """Hit rows with the distance between where the player hit and their own base position.

    Read with `incoming`: how far the opponent's lob / smash / net shot pulled the player away
    from base by the time they played their reply. Serves and replies to serves are excluded
    (the receiver of a serve starts in the service box, not at base).
    """
    h = pos[(pos.role == "hit") & ~pos.is_serve & pos.incoming.notna()]
    h = h[h.incoming.astype(str) != "short_service"]
    h = h[h.incoming.astype(str) != "long_service"]
    h = h.merge(bases[["player", "base_lat_right", "base_depth"]], on="player", how="inner")
    h["pull"] = np.hypot(h.lat_right - h.base_lat_right, h.depth - h.base_depth)
    return h


def distance_per_rally(pos: pd.DataFrame) -> pd.DataFrame:
    """Per (player, rally): sum of straight-line distances between consecutive own-hit
    positions (a LOWER bound on the distance covered), and the number of own hits."""
    h = pos[pos.role == "hit"].sort_values(["player", "rally_id", "stroke_no"])
    g = h.groupby(["player", "rally_id"], observed=True)
    dx = g.lat_right.diff()
    dy = g.depth.diff()
    h = h.assign(step=np.hypot(dx, dy))
    out = h.groupby(["player", "rally_id"], observed=True).agg(
        match_id=("match_id", "first"),
        game=("game", "first"),
        pressure=("pressure", "first"),
        n_strokes=("n_strokes", "first"),
        player_won=("player_won", "first"),
        own_hits=("step", "size"),
        distance=("step", "sum"),
    )
    return out.reset_index()


# ---------------------------------------------------------------------------------------
# Player vs typical pros
# ---------------------------------------------------------------------------------------


def _mean_row(label: str, a: np.ndarray, b: np.ndarray, min_n: int) -> dict:
    m, lo, hi = mean_ci(a)
    rm, rlo, rhi = mean_ci(b)
    d, dlo, dhi = welch_diff_ci(a, b)
    return {
        "label": label,
        "n": int(len(a)),
        "mean": m,
        "lo": lo,
        "hi": hi,
        "ref_n": int(len(b)),
        "ref_mean": rm,
        "ref_lo": rlo,
        "ref_hi": rhi,
        "delta": d,
        "delta_lo": dlo,
        "delta_hi": dhi,
        "reliable": len(a) >= min_n and len(b) >= min_n,
        "signal": (len(a) >= min_n and len(b) >= min_n) and (dlo > 0 or dhi < 0),
    }


@dataclass(slots=True)
class PositionSummary:
    player: str
    positions: pd.DataFrame  # the player's rows of all_positions
    base: pd.Series  # the player's row of base_positions
    ref_base: pd.DataFrame  # base_positions of all other players
    pull: pd.DataFrame  # by incoming shot type
    distance: pd.DataFrame  # overall, by game, by pressure
    per_hit: pd.DataFrame  # distance per own hit, same splits


def summarise(
    df: pd.DataFrame, player: str, cfg: ZoneConfig, s: AnalysisSettings | None = None
) -> PositionSummary:
    s = s or AnalysisSettings()
    min_n = s.rates.min_n
    pos = all_positions(df, cfg, s)
    if not (pos.player == player).any():
        raise ValueError(f"no positions for {player!r}")
    bases = base_positions(pos)
    base = bases[bases.player == player].iloc[0]
    ref_base = bases[bases.player != player].reset_index(drop=True)

    pulled = pull_from_base(pos, bases)
    mine, others = pulled[pulled.player == player], pulled[pulled.player != player]
    rows = [_mean_row("all shots", mine.pull.to_numpy(), others.pull.to_numpy(), min_n)]
    for shot in sorted(mine.incoming.astype(str).unique()):
        if shot == "unknown":
            continue
        a = mine[mine.incoming.astype(str) == shot].pull.to_numpy()
        b = others[others.incoming.astype(str) == shot].pull.to_numpy()
        rows.append(_mean_row(shot, a, b, min_n))
    pull = pd.DataFrame(rows)
    pull["order"] = np.where(pull.label == "all shots", -1, pull.n)
    pull = (
        pull.sort_values(["order", "n"], ascending=False)
        .drop(columns="order")
        .reset_index(drop=True)
    )

    dist = distance_per_rally(pos)
    mine_d, others_d = dist[dist.player == player], dist[dist.player != player]
    splits = [("all rallies", slice(None), slice(None))]
    for g in sorted(mine_d.game.unique()):
        splits.append((f"game {g}", mine_d.game == g, others_d.game == g))
    splits.append((f"at {s.pressure_from}+", mine_d.pressure, others_d.pressure))
    splits.append((f"before {s.pressure_from}", ~mine_d.pressure, ~others_d.pressure))
    distance = pd.DataFrame(
        [
            _mean_row(lab, mine_d[m].distance.to_numpy(), others_d[o].distance.to_numpy(), min_n)
            for lab, m, o in splits
        ]
    )
    per_hit = pd.DataFrame(
        [
            _mean_row(
                lab,
                (mine_d[m].distance / mine_d[m].own_hits.clip(lower=1)).to_numpy(),
                (others_d[o].distance / others_d[o].own_hits.clip(lower=1)).to_numpy(),
                min_n,
            )
            for lab, m, o in splits
        ]
    )
    return PositionSummary(
        player, pos[pos.player == player], base, ref_base, pull, distance, per_hit
    )


# ---------------------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------------------


def _draw_half_court(ax, cfg: ZoneConfig) -> None:
    hw, sw = cfg.court_width_m / 2, cfg.singles_half_width_m
    L = cfg.net_y
    line = dict(color="#444444", lw=1.0)
    ax.plot([-hw, hw], [0, 0], color="#111111", lw=2.0)  # net
    ax.plot([-hw, hw], [L, L], **line)  # baseline
    ax.plot([-hw, -hw], [0, L], **line)
    ax.plot([hw, hw], [0, L], **line)
    ax.plot([-sw, -sw], [0, L], **line)
    ax.plot([sw, sw], [0, L], **line)
    ax.plot([-hw, hw], [SHORT_SERVICE_M, SHORT_SERVICE_M], **line)
    ax.plot([-hw, hw], [L - LONG_SERVICE_DOUBLES_M, L - LONG_SERVICE_DOUBLES_M], **line)
    ax.plot([0, 0], [SHORT_SERVICE_M, L], **line)


def position_heatmap(
    summary: PositionSummary, cfg: ZoneConfig, path: Path, bin_m: float = 0.25
) -> Path:
    """Two panels: where the player stands when hitting, and when the opponent hits.
    Net at the top, baseline at the bottom; lateral axis labelled with the player's forehand
    and backhand side."""
    pos = summary.positions
    handed = str(pos.handed.iloc[0]) if len(pos) else "right"
    fh_right = handed == "right"
    xedges = np.arange(-3.5, 3.5 + 1e-9, bin_m)
    yedges = np.arange(-0.5, 7.5 + 1e-9, bin_m)
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 5.2), constrained_layout=True)
    for ax, role, title in (
        (axes[0], "hit", "when hitting"),
        (axes[1], "receive", "when the opponent hits"),
    ):
        d = pos[(pos.role == role) & ~pos.is_serve]
        h, _, _ = np.histogram2d(d.lat_right, d.depth, bins=[xedges, yedges])
        share = h / max(h.sum(), 1)
        ax.imshow(
            share.T,
            origin="lower",
            extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
            cmap="Blues",
            aspect="equal",
            interpolation="nearest",
        )
        _draw_half_court(ax, cfg)
        if role == "receive":
            ax.plot(
                summary.base.base_lat_right,
                summary.base.base_depth,
                marker="o",
                ms=9,
                mfc="white",
                mec="#111111",
                mew=1.5,
            )
        ax.set_xlim(xedges[0], xedges[-1])
        ax.set_ylim(yedges[-1], yedges[0])  # net at the top
        ax.set_title(f"{title} (n={len(d)})", loc="left", fontsize=10)
        ax.set_xlabel(
            f"{'backhand' if fh_right else 'forehand'} side  <-  m from centre  ->  "
            f"{'forehand' if fh_right else 'backhand'} side"
        )
        ax.set_ylabel("m from the net (own half)")
        for sp in ax.spines.values():
            sp.set_visible(False)
    fig.suptitle(
        f"{summary.player}: positions at hit time only ({handed}-handed); circle = base position",
        fontsize=10,
        x=0.01,
        ha="left",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------------------
# Report section
# ---------------------------------------------------------------------------------------


def _mean_table(t: pd.DataFrame, label: str, unit: str = "m") -> str:
    def f(v):
        return "-" if pd.isna(v) else f"{v:.2f}"

    out = pd.DataFrame(
        {
            label: t.label,
            "n": t.n,
            f"mean {unit}": t["mean"].map(f),
            "95% CI": [f"{f(lo)}-{f(hi)}" for lo, hi in zip(t.lo, t.hi, strict=True)],
            "typical pros": [f"{f(m)} (n={n})" for m, n in zip(t.ref_mean, t.ref_n, strict=True)],
            "difference (95% CI)": [
                f"{d:+.2f} ({lo:+.2f} to {hi:+.2f})" if not pd.isna(d) else "-"
                for d, lo, hi in zip(t.delta, t.delta_lo, t.delta_hi, strict=True)
            ],
            "flag": np.where(~t.reliable, "too few", np.where(t.signal, "signal", "")),
        }
    )
    return out.to_markdown(index=False, disable_numparse=True) + "\n"


def section(summary: PositionSummary, me: str, img_rel: str, s: AnalysisSettings) -> list[str]:
    b = summary.base
    rb = summary.ref_base
    side = (
        "forehand"
        if b.base_lat_right * (1 if str(summary.positions.handed.iloc[0]) == "right" else -1) >= 0
        else "backhand"
    )
    L = [
        "## Position maps (positions at hit time only)\n",
        "ShuttleSet records where each player stands only at the instant a stroke is hit, so these "
        "are position maps, not footwork paths, and every distance below is a lower bound (the "
        "straight line between consecutive own-hit positions). Positions are in the player's own "
        "half: metres from the net and metres from the centre line toward the player's own right; "
        f"the lateral axis is labelled with {me}'s forehand and backhand side from config/players.toml.\n",
        f"![{me}: position maps]({img_rel})\n",
        f"**Base position** (median position when the opponent hits a non-serve stroke, n={int(b.n)}): "
        f"{b.base_depth:.2f} m from the net, {abs(b.base_lat_right):.2f} m toward the {side} side "
        f"(interquartile range {b.depth_q1:.2f}-{b.depth_q3:.2f} m deep, "
        f"{b.lat_q1:+.2f} to {b.lat_q3:+.2f} m lateral). "
        f"Typical pros: median of the {len(rb)} other players' bases {rb.base_depth.median():.2f} m from the net "
        f"(players range {rb.base_depth.min():.2f}-{rb.base_depth.max():.2f} m), "
        f"{rb.base_lat_right.abs().median():.2f} m from the centre line.\n",
        f"**Pulled from base, by the opponent's shot** (distance between {me}'s base and where {me} "
        "played the reply; serves and serve returns excluded):\n",
        _mean_table(summary.pull, "opponent's shot"),
        f"**Distance per rally** (sum of straight lines between {me}'s consecutive hit positions, "
        f"a lower bound), split by game and by score pressure ({s.pressure_from}+):\n",
        _mean_table(summary.distance, "rallies"),
        "Per own stroke (controls for rally length):\n",
        _mean_table(summary.per_hit, "per own hit"),
    ]
    return L
