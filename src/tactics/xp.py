"""xP, expected points: P(the hitter wins the rally | the shot just played).

Like football's xG, but for one shot in a rally. Two models, because the honest input set
depends on when you ask (DECISIONS D23):

* **xP-pre** (leak-free): only what is known BEFORE the shuttle lands. Shot type, how it was
  hit (backhand, around the head, contact height), where the hitter stood, where the receiver
  stood, how far the receiver was from their own base position, stroke index, and whether the
  hitter is the server. It is trained and evaluated on every stroke, including the final one,
  and it is the model behind every per-player claim ("Axelsen's rear-court smashes earn +0.08
  points more than a typical pro's").
* **xP-post**: adds where the shuttle landed (receiver-relative coach zone and metres), how
  far and in which direction the receiver had to move, the body flag and cross/straight. The
  landing of a final stroke IS the outcome (out, net, winner), so xP-post is trained and
  evaluated on NON-FINAL strokes only, where every landing is in play. It values the placement
  of shots that were returned.

Both use a logistic regression and a gradient-boosted tree model (scikit-learn's
HistGradientBoosting). Hyper-parameters are chosen on a match-level validation split inside the
development matches; final numbers come from the 14 ShuttleSet22 holdout matches that nothing
was tuned on. The leak check (xP-pre on final vs non-final strokes, and a deliberately leaky
variant with the final zone visible) is part of the output so the reader can see what masking
buys.

Per player, xP gives
* **situation quality**: mean xP of the shots the player chooses, by shot type and the court
  band it is hit from, next to other pros;
* **execution**: actual outcome minus xP ("points above expectation") per shot, which is the
  number quoted in the report;
* **xP added per rally**: the change in the hitter's win probability caused by each stroke,
  summed over a rally and compared with typical pros.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tactics.analyses import OUTCOME_ZONES  # noqa: E402
from tactics.config import ZoneConfig  # noqa: E402
from tactics.outcome_model import metrics  # noqa: E402
from tactics.splits import split  # noqa: E402
from tactics.stats import mean_ci, welch_diff_ci  # noqa: E402

PRE_CATS = ["shot", "hit_height", "backhand", "aroundhead", "hitter_is_server"]
PRE_NUMS = ["hit_depth", "hit_lat_fh", "recv_depth", "recv_lat_fh", "recv_from_base", "stroke_no"]
POST_CATS = PRE_CATS + ["land_zone", "move_dir", "body", "cross"]
POST_NUMS = PRE_NUMS + ["land_depth", "land_lat_fh", "recv_move"]

FEATURE_SETS = {"pre": (PRE_CATS, PRE_NUMS), "post": (POST_CATS, POST_NUMS)}


# ---------------------------------------------------------------------------------------
# Feature frame
# ---------------------------------------------------------------------------------------


def receiver_bases(df: pd.DataFrame) -> tuple[dict[str, tuple[float, float]], tuple[float, float]]:
    """Per-player base (median receive position when the opponent hits a non-serve stroke) in
    the receiver's forehand frame, plus the population median as the fallback."""
    d = df[df.annotated & df.rally_winner.notna() & ~df.is_serve].dropna(
        subset=["recv_depth", "recv_lat_fh"]
    )
    g = d.groupby(d.receiver.astype(str))
    med = g[["recv_lat_fh", "recv_depth"]].median()
    bases = {p: (float(r.recv_lat_fh), float(r.recv_depth)) for p, r in med.iterrows()}
    fallback = (float(d.recv_lat_fh.median()), float(d.recv_depth.median()))
    return bases, fallback


def feature_frame(
    df: pd.DataFrame,
    cfg: ZoneConfig,
    bases: dict[str, tuple[float, float]],
    fallback: tuple[float, float],
) -> pd.DataFrame:
    """One row per annotated stroke with a known winner: features, label and bookkeeping."""
    d = df[df.annotated & df.rally_winner.notna()].sort_values(["rally_id", "stroke_no"]).copy()
    half = d.hitter_half.astype(str)
    near, far = half == "near", half == "far"
    hand_left = d.hitter_handed.astype(str) == "left"
    hit_depth = np.where(
        near, d.hitter_y - cfg.net_y, np.where(far, cfg.net_y - d.hitter_y, np.nan)
    )
    hit_right = np.where(
        near, d.hitter_x - cfg.centre_x, np.where(far, cfg.centre_x - d.hitter_x, np.nan)
    )
    hit_lat_fh = np.where(hand_left, -hit_right, hit_right)
    recv = d.receiver.astype(str)
    base_lat = recv.map(lambda p: bases.get(p, fallback)[0]).to_numpy(float)
    base_depth = recv.map(lambda p: bases.get(p, fallback)[1]).to_numpy(float)
    zone = d.coach_zone.astype(object)
    out = pd.DataFrame(
        {
            "rally_id": d.rally_id.to_numpy(),
            "match_id": d.match_id.astype(str).to_numpy(),
            "stroke_no": d.stroke_no.to_numpy(),
            "n_strokes": d.n_strokes.to_numpy(),
            "is_last": d.is_last.to_numpy(),
            "hitter": d.hitter.astype(str).to_numpy(),
            "receiver": recv.to_numpy(),
            "hitter_won": d.hitter_won.astype(bool).to_numpy(),
            "hitter_is_server": (d.stroke_no % 2 == 1).to_numpy(),
            # --- known before the shuttle lands
            "shot": d.shot_coarse.astype(str).to_numpy(),
            "hit_height": d.hit_height.to_numpy(float),
            "backhand": d.backhand.astype(bool).to_numpy(),
            "aroundhead": d.aroundhead.astype(bool).to_numpy(),
            "hit_depth": hit_depth,
            "hit_lat_fh": hit_lat_fh,
            "recv_depth": d.recv_depth.to_numpy(float),
            "recv_lat_fh": d.recv_lat_fh.to_numpy(float),
            "recv_from_base": np.hypot(
                d.recv_lat_fh.to_numpy(float) - base_lat, d.recv_depth.to_numpy(float) - base_depth
            ),
            # --- known only after it lands
            "land_zone": zone.where(zone.notna(), "nozone").astype(str).to_numpy(),
            "land_depth": d.depth.to_numpy(float),
            "land_lat_fh": d.lat_fh.to_numpy(float),
            "recv_move": d.dist_to_receiver.to_numpy(float),
            "move_dir": d.move_dir.astype(object)
            .where(d.move_dir.notna(), "unknown")
            .astype(str)
            .to_numpy(),
            "body": d.body.fillna(False).astype(bool).to_numpy(),
            "cross": d.cross.astype(object)
            .where(d.cross.notna(), "unknown")
            .astype(str)
            .to_numpy(),
        }
    )
    out["hit_band"] = pd.cut(
        out.hit_depth,
        bins=[-np.inf] + [b.hi for b in cfg.coach_bands[:-1]] + [np.inf],
        labels=[b.name for b in cfg.coach_bands],
    ).astype(str)
    out["final_outcome_zone"] = out.land_zone.isin(OUTCOME_ZONES)
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------------------


def _pipeline(kind: str, cats: list[str], nums: list[str], seed: int, **hp):
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline, make_pipeline
    from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

    if kind == "logistic":
        pre = ColumnTransformer(
            [
                ("cat", OneHotEncoder(handle_unknown="ignore"), cats),
                ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), nums),
            ]
        )
        return Pipeline(
            [("pre", pre), ("clf", LogisticRegression(C=hp.get("C", 1.0), max_iter=2000))]
        )
    pre = ColumnTransformer(
        [
            (
                "cat",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=np.nan,
                    encoded_missing_value=np.nan,
                ),
                cats,
            ),
            ("num", "passthrough", nums),
        ]
    )
    clf = HistGradientBoostingClassifier(
        max_iter=hp.get("n_iter", 200),
        learning_rate=hp.get("lr", 0.05),
        max_leaf_nodes=hp.get("leaves", 31),
        min_samples_leaf=50,
        l2_regularization=1.0,
        categorical_features=list(range(len(cats))),
        early_stopping=False,
        random_state=seed,
    )
    return Pipeline([("pre", pre), ("clf", clf)])


GRIDS = {
    "logistic": [{"C": c} for c in (0.1, 1.0, 10.0)],
    "gbm": [{"n_iter": n, "lr": 0.05} for n in (100, 200, 400)],
}


def _rows(frame: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    """The training domain of a feature set: everything for pre, non-final strokes for post."""
    return frame if feature_set == "pre" else frame[~frame.is_last]


@dataclass(slots=True)
class FittedXP:
    feature_set: str
    kind: str
    hp: dict
    pipeline: object
    validation: pd.DataFrame  # per hp: log loss on the match-level validation split


def fit_one(dev: pd.DataFrame, feature_set: str, kind: str, seed: int = 0) -> FittedXP:
    cats, nums = FEATURE_SETS[feature_set]
    rows = _rows(dev, feature_set)
    # match-level validation split for the hyper-parameter choice
    matches = sorted(rows.match_id.unique())
    rng = np.random.default_rng(seed)
    rng.shuffle(matches)
    val_ids = set(matches[: max(1, round(0.2 * len(matches)))])
    tr, va = rows[~rows.match_id.isin(val_ids)], rows[rows.match_id.isin(val_ids)]
    records = []
    for hp in GRIDS[kind]:
        pipe = _pipeline(kind, cats, nums, seed, **hp).fit(tr[cats + nums], tr.hitter_won)
        p = pipe.predict_proba(va[cats + nums])[:, 1]
        m = metrics(va.hitter_won.to_numpy(), p)
        records.append({**hp, **m, "n_val": len(va)})
    validation = pd.DataFrame(records)
    best = GRIDS[kind][int(validation.log_loss.idxmin())]
    pipe = _pipeline(kind, cats, nums, seed, **best).fit(rows[cats + nums], rows.hitter_won)
    return FittedXP(feature_set, kind, best, pipe, validation)


def predict(fit: FittedXP, frame: pd.DataFrame) -> np.ndarray:
    cats, nums = FEATURE_SETS[fit.feature_set]
    return fit.pipeline.predict_proba(frame[cats + nums])[:, 1]


# ---------------------------------------------------------------------------------------
# Experiment: fit, evaluate on the holdout, leak check, calibration
# ---------------------------------------------------------------------------------------


@dataclass(slots=True)
class XPResult:
    frame: pd.DataFrame  # every stroke with xp_pre / xp_post (the chosen models) and is_holdout
    fits: dict[tuple[str, str], FittedXP]
    table: pd.DataFrame  # holdout metrics by (feature set, model, slice)
    leaky_auc: float  # post features on all strokes, final out / net zone visible
    leaky_auc_final: float  # the same, scored on final strokes only
    base_rate: float
    server_rate: float
    counts: dict
    timing: dict
    chosen: dict


def run_experiment(
    df: pd.DataFrame, cfg: ZoneConfig, seed: int = 0, holdout_ids: set[str] | None = None
) -> XPResult:
    t0 = time.time()
    if holdout_ids is None:
        dev_df, hold_df = split(df)
    else:
        mask = df.match_id.astype(str).isin(holdout_ids)
        dev_df, hold_df = df[~mask], df[mask]
    bases, fallback = receiver_bases(dev_df)  # bases from development matches only
    frame = feature_frame(df, cfg, bases, fallback)
    frame["is_holdout"] = frame.match_id.isin(set(hold_df.match_id.astype(str)))
    dev, hold = frame[~frame.is_holdout], frame[frame.is_holdout]
    base_rate = float(dev.hitter_won.mean())
    server_rate = float(dev[dev.stroke_no == 1].hitter_won.mean())

    fits: dict[tuple[str, str], FittedXP] = {}
    timing: dict[str, float] = {}
    rows = []
    for feature_set in ("pre", "post"):
        domain = _rows(hold, feature_set)
        rows.append(
            {
                "feature_set": feature_set,
                "model": "base rate",
                "slice": "domain",
                "n": len(domain),
                **metrics(domain.hitter_won.to_numpy(), np.full(len(domain), base_rate)),
            }
        )
        for kind in ("logistic", "gbm"):
            t = time.time()
            fit = fit_one(dev, feature_set, kind, seed)
            fits[(feature_set, kind)] = fit
            timing[f"{feature_set}/{kind}"] = time.time() - t
            p = predict(fit, hold)
            slices = {"domain": _rows(hold, feature_set).index}
            if feature_set == "pre":
                slices = {
                    "all strokes": hold.index,
                    "non-final strokes": hold.index[~hold.is_last],
                    "final strokes": hold.index[hold.is_last],
                }
            else:
                slices = {"non-final strokes": hold.index[~hold.is_last]}
            for name, idx in slices.items():
                pos = hold.index.get_indexer(idx)
                rows.append(
                    {
                        "feature_set": feature_set,
                        "model": kind,
                        "slice": name,
                        "n": len(idx),
                        **metrics(hold.loc[idx].hitter_won.to_numpy(), p[pos]),
                    }
                )
    table = pd.DataFrame(rows)

    # the deliberately leaky number: post features on ALL strokes, final out / net zone visible
    cats, nums = FEATURE_SETS["post"]
    leaky = _pipeline("logistic", cats, nums, seed, C=1.0).fit(dev[cats + nums], dev.hitter_won)
    p_leaky = leaky.predict_proba(hold[cats + nums])[:, 1]
    leaky_auc = metrics(hold.hitter_won.to_numpy(), p_leaky)["auc"]
    fin = hold.is_last.to_numpy()
    leaky_auc_final = metrics(hold.hitter_won.to_numpy()[fin], p_leaky[fin])["auc"]

    # chosen model per feature set = best holdout log loss between logistic and gbm? No: that
    # would tune on the holdout. The choice is made on the validation split (DECISIONS D23).
    chosen = {}
    for feature_set in ("pre", "post"):
        best = min(
            ("logistic", "gbm"),
            key=lambda k: float(fits[(feature_set, k)].validation.log_loss.min()),
        )
        chosen[feature_set] = best
        frame[f"xp_{feature_set}"] = predict(fits[(feature_set, best)], frame)
    frame.loc[frame.is_last, "xp_post"] = np.nan  # outside xP-post's domain

    counts = {
        "dev_matches": int(dev.match_id.nunique()),
        "holdout_matches": int(hold.match_id.nunique()),
        "dev_strokes": int(len(dev)),
        "holdout_strokes": int(len(hold)),
        "holdout_non_final": int((~hold.is_last).sum()),
        "holdout_final": int(hold.is_last.sum()),
        "players_with_dev_base": len(bases),
    }
    timing["total"] = time.time() - t0
    return XPResult(
        frame,
        fits,
        table,
        float(leaky_auc),
        float(leaky_auc_final),
        base_rate,
        server_rate,
        counts,
        timing,
        chosen,
    )


def calibration_plot(res: XPResult, path: Path, bins: int = 10) -> Path:
    """Reliability diagram on the holdout for the chosen xP-pre (all strokes) and xP-post
    (non-final) models: mean predicted vs observed win rate in equal-count bins."""
    hold = res.frame[res.frame.is_holdout]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.2), constrained_layout=True)
    for ax, (col, title, mask) in zip(
        axes,
        (
            (
                "xp_pre",
                f"xP-pre ({res.chosen['pre']}), all holdout strokes",
                np.ones(len(hold), bool),
            ),
            (
                "xp_post",
                f"xP-post ({res.chosen['post']}), non-final strokes",
                ~hold.is_last.to_numpy(),
            ),
        ),
        strict=True,
    ):
        d = hold[mask].dropna(subset=[col])
        q = pd.qcut(d[col], bins, duplicates="drop")
        g = d.groupby(q, observed=True)
        pred, obs, n = g[col].mean(), g.hitter_won.mean(), g.size()
        ax.plot([0, 1], [0, 1], color="#999999", lw=1, ls="--")
        ax.plot(pred, obs, color="#1f5fa8", lw=2, marker="o", ms=5)
        for x, y, k in zip(pred, obs, n, strict=True):
            ax.annotate(
                f"{k}",
                (x, y),
                textcoords="offset points",
                xytext=(6, -10),
                fontsize=7,
                color="#555555",
            )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("mean predicted P(hitter wins)")
        ax.set_ylabel("observed share won")
        ax.set_title(title, loc="left", fontsize=10)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.suptitle(
        "Calibration on the 14 holdout matches (labels = strokes per bin)",
        fontsize=10,
        x=0.01,
        ha="left",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------------------
# Per player
# ---------------------------------------------------------------------------------------
#
# Statistical unit = the RALLY, not the stroke. Every stroke a player hits in a rally shares that
# rally's outcome, so per-stroke residuals are not independent and stroke-level intervals would
# be far too narrow. Each measure is first averaged (or summed) within (hitter, rally) and the
# intervals are computed over rallies.


def xp_added(frame: pd.DataFrame, server_rate: float, col: str = "xp_pre") -> pd.Series:
    """Change in the HITTER's win probability caused by each stroke.

    v_i = P(server wins) after stroke i (= xP if the server hit it, else 1 - xP); v_0 = the
    training server win rate. The stroke's credit, from its hitter's side, is +(v_i - v_{i-1})
    for the server and -(v_i - v_{i-1}) for the receiver.
    """
    f = frame.sort_values(["rally_id", "stroke_no"])
    v = np.where(f.hitter_is_server, f[col], 1 - f[col])
    v_prev = (
        pd.Series(v, index=f.index).groupby(f.rally_id, observed=True).shift(1).fillna(server_rate)
    )
    added = (v - v_prev.to_numpy()) * np.where(f.hitter_is_server, 1.0, -1.0)
    return pd.Series(added, index=f.index).reindex(frame.index)


def _mean_row(label: str, a, b, min_n: int, extra: dict | None = None) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    m, lo, hi = mean_ci(a)
    rm, rlo, rhi = mean_ci(b)
    d, dlo, dhi = welch_diff_ci(a, b)
    ok = len(a) >= min_n and len(b) >= min_n
    return {
        "label": label,
        "n": int(len(a)),
        "mean": m,
        "lo": lo,
        "hi": hi,
        "ref_n": int(len(b)),
        "ref_mean": rm,
        "delta": d,
        "delta_lo": dlo,
        "delta_hi": dhi,
        "reliable": ok,
        "signal": ok and (dlo > 0 or dhi < 0),
        **(extra or {}),
    }


def _per_rally(f: pd.DataFrame, by: list[str], value: str, how: str = "mean") -> pd.DataFrame:
    g = f.groupby(["hitter", "rally_id", *by], observed=True)[value]
    return (g.mean() if how == "mean" else g.sum()).reset_index()


@dataclass(slots=True)
class PlayerXP:
    player: str
    overall: dict  # the player's overall points above expectation (per rally) and its CI
    by_shot_band: pd.DataFrame  # execution (actual - xP) by shot x hit band, vs other pros
    by_shot: pd.DataFrame
    finishing: pd.DataFrame  # final strokes only, where the model has signal
    situation: pd.DataFrame  # mean xP-pre by shot (what the player chooses), vs other pros
    added_per_rally: pd.DataFrame
    added_by_shot: pd.DataFrame
    n_shots: int
    n_rallies: int
    chosen: dict = field(default_factory=dict)


def player_xp(res: XPResult, player: str, min_n: int = 30) -> PlayerXP:
    f = res.frame.copy()
    f = f[f.shot != "unknown"]
    f["resid"] = f.hitter_won.astype(float) - f.xp_pre
    f["added"] = xp_added(f, res.server_rate)
    f["band"] = f.hit_band.astype(str)
    mine_mask = f.hitter == player
    if not mine_mask.any():
        raise ValueError(f"no strokes for {player!r}")

    # overall points above expectation per rally (the player's general edge over the model)
    r_all = _per_rally(f, [], "resid")
    own_all = r_all[r_all.hitter == player].resid.to_numpy()
    oth_all = r_all[r_all.hitter != player].resid.to_numpy()
    overall = dict(zip(("mean", "lo", "hi"), mean_ci(own_all), strict=True))
    overall["n"] = int(len(own_all))
    overall["ref_mean"] = float(np.mean(oth_all))

    def execution(by: list[str], label_fn) -> pd.DataFrame:
        r = _per_rally(f, by, "resid")
        xpr = _per_rally(f, by, "xp_pre")
        mine, others = r[r.hitter == player], r[r.hitter != player]
        rows = []
        for key, g in mine.groupby(by, observed=True):
            key = key if isinstance(key, tuple) else (key,)
            sel = np.ones(len(others), bool)
            selx = np.ones(len(xpr), bool)
            for c, v in zip(by, key, strict=True):
                sel &= others[c].to_numpy() == v
                selx &= xpr[c].to_numpy() == v
            o = others[sel]
            # within-player contrast: this shot's rallies vs all the player's rallies
            c, clo, chi = welch_diff_ci(g.resid.to_numpy(), own_all)
            rows.append(
                _mean_row(
                    label_fn(*key),
                    g.resid,
                    o.resid,
                    min_n,
                    {
                        "xp": float(xpr[selx & (xpr.hitter == player)].xp_pre.mean()),
                        "ref_xp": float(xpr[selx & (xpr.hitter != player)].xp_pre.mean())
                        if selx.any()
                        else np.nan,
                        "own_delta": c,
                        "own_lo": clo,
                        "own_hi": chi,
                        "own_signal": len(g) >= min_n and (clo > 0 or chi < 0),
                    },
                )
            )
        t = pd.DataFrame(rows)
        if t.empty:
            return t
        t["score"] = np.where(t.signal, np.minimum(t.delta_lo.abs(), t.delta_hi.abs()), 0.0)
        return t.sort_values(["signal", "score"], ascending=False).reset_index(drop=True)

    by_shot_band = execution(["shot", "band"], lambda s, b: f"{s} from {b}")
    by_shot = (
        execution(["shot"], lambda s: s).sort_values("n", ascending=False).reset_index(drop=True)
    )

    # finishing: final strokes only (one per rally, so strokes are the unit here)
    fin = f[f.is_last]
    rows = []
    for shot, g in fin[fin.hitter == player].groupby("shot", observed=True):
        o = fin[(fin.hitter != player) & (fin.shot == shot)]
        rows.append(
            _mean_row(
                shot,
                g.resid,
                o.resid,
                min_n,
                {
                    "xp": float(g.xp_pre.mean()),
                    "ref_xp": float(o.xp_pre.mean()) if len(o) else np.nan,
                    "won": float(g.hitter_won.mean()),
                },
            )
        )
    finishing = pd.DataFrame(rows)
    if not finishing.empty:
        finishing = finishing.sort_values("n", ascending=False).reset_index(drop=True)

    # situation quality: mean xP per rally by shot
    xr = _per_rally(f, ["shot"], "xp_pre")
    sit = [
        _mean_row(shot, g.xp_pre, xr[(xr.hitter != player) & (xr.shot == shot)].xp_pre, min_n)
        for shot, g in xr[xr.hitter == player].groupby("shot", observed=True)
    ]
    situation = pd.DataFrame(sit).sort_values("n", ascending=False).reset_index(drop=True)

    # xP added: per rally (sum over the player's strokes) and per shot type (sum per rally)
    pr = _per_rally(f, [], "added", "sum")
    added_per_rally = pd.DataFrame(
        [
            _mean_row(
                "xP added per rally",
                pr[pr.hitter == player].added,
                pr[pr.hitter != player].added,
                min_n,
            )
        ]
    )
    ps = _per_rally(f, ["shot"], "added", "sum")
    added_by_shot = (
        pd.DataFrame(
            [
                _mean_row(shot, g.added, ps[(ps.hitter != player) & (ps.shot == shot)].added, min_n)
                for shot, g in ps[ps.hitter == player].groupby("shot", observed=True)
            ]
        )
        .sort_values("n", ascending=False)
        .reset_index(drop=True)
    )

    return PlayerXP(
        player,
        overall,
        by_shot_band,
        by_shot,
        finishing,
        situation,
        added_per_rally,
        added_by_shot,
        int(mine_mask.sum()),
        int(len(own_all)),
        dict(res.chosen),
    )


# ---------------------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------------------


def _f(v, nd=2, sign=False):
    if pd.isna(v):
        return "-"
    return f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}"


def _mean_table(
    t: pd.DataFrame,
    label: str,
    value: str,
    with_xp: bool = False,
    with_own: bool = False,
    top: int | None = None,
    unit: str = "rallies",
) -> str:
    if t.empty:
        return "_no data_\n"
    d = t.head(top) if top else t
    cols = {label: d.label, unit: d.n.astype(int)}
    if with_xp:
        cols["xP"] = d.xp.map(lambda v: _f(v, 3))
    cols[value] = [
        f"{_f(m, 3, True)} ({_f(lo, 3, True)} to {_f(hi, 3, True)})"
        for m, lo, hi in zip(d["mean"], d.lo, d.hi, strict=True)
    ]
    cols["typical pros"] = [
        f"{_f(m, 3, True)} (n={int(n)})" for m, n in zip(d.ref_mean, d.ref_n, strict=True)
    ]
    cols["difference (95% CI)"] = [
        f"{_f(x, 3, True)} ({_f(lo, 3, True)} to {_f(hi, 3, True)})"
        for x, lo, hi in zip(d.delta, d.delta_lo, d.delta_hi, strict=True)
    ]
    if with_own:
        cols["vs own overall (95% CI)"] = [
            f"{_f(x, 3, True)} ({_f(lo, 3, True)} to {_f(hi, 3, True)})"
            for x, lo, hi in zip(d.own_delta, d.own_lo, d.own_hi, strict=True)
        ]
    flag = np.where(~d.reliable, "too few", np.where(d.signal, "signal", ""))
    if with_own:
        flag = np.where(
            d.own_signal & d.reliable, np.char.add(flag.astype(str), " / shot-specific"), flag
        )
    cols["flag"] = flag
    return pd.DataFrame(cols).to_markdown(index=False, disable_numparse=True) + "\n"


def metrics_markdown(res: XPResult) -> str:
    t = res.table.copy()
    for c in ("accuracy", "log_loss", "brier", "auc"):
        t[c] = t[c].map(lambda v: f"{v:.3f}")
    return t.to_markdown(index=False) + "\n"


def _auc(res: XPResult, feature_set: str, slice_name: str) -> float:
    t = res.table
    r = t[
        (t.feature_set == feature_set)
        & (t.model == res.chosen[feature_set])
        & (t.slice == slice_name)
    ]
    return float(r.auc.iloc[0]) if len(r) else float("nan")


def section(px: PlayerXP, me: str, res: XPResult, img_rel: str | None) -> list[str]:
    auc_nonfinal = _auc(res, "pre", "non-final strokes")
    auc_final = _auc(res, "pre", "final strokes")
    o = px.overall
    L = [
        "## Expected points (xP)\n",
        f"**Read this first: xP from shot and position data has no signal mid-rally in elite singles "
        f"(holdout AUC {auc_nonfinal:.2f} on strokes that did not end the rally).** The same features "
        f"reach AUC {auc_final:.2f} only on final strokes, where the task is classifying how an "
        "already-decisive stroke ends (winner or error), not predicting a rally. Nothing in this "
        "section is a working expected-points model. The tables stay because the 'Finishing' one is "
        "a real execution measure and the others show what a chance-level model does to per-shot "
        "claims.\n",
        f"xP is P(the hitter wins the rally | the shot just played), from a model trained on "
        f"{res.counts['dev_matches']} development matches and checked on the "
        f"{res.counts['holdout_matches']} holdout matches (`docs/XP.md`). Every number here uses "
        "**xP-pre**, which sees only what is known before the shuttle lands (shot type, how it was hit, "
        "both players' positions, the receiver's distance from base, stroke index); chosen model: "
        f"{px.chosen.get('pre', '?')}. Based on {px.n_shots} of {me}'s strokes in {px.n_rallies} rallies. "
        "Mid-rally the model's expectation is close to the base rate for every shot, so 'points above "
        "expectation' mostly measures how often the player wins rallies containing that shot; the "
        "column 'vs own overall' removes the player's general edge.\n",
        f"{me}'s overall points above expectation: {o['mean']:+.3f} per rally (95% CI {o['lo']:+.3f} to "
        f"{o['hi']:+.3f}, n={o['n']}); other pros {o['ref_mean']:+.3f}. Intervals are over rallies "
        "(every stroke in a rally shares its outcome).\n",
        "**Points above expectation by shot and the court band it was hit from** (actual outcome minus "
        "xP, averaged within each rally, then over rallies; 'typical pros' = all other players hitting "
        "the same shot from the same band):\n",
        _mean_table(
            px.by_shot_band,
            "shot, hit from",
            "points above expectation",
            with_xp=True,
            with_own=True,
            top=12,
        ),
        "By shot type alone:\n",
        _mean_table(px.by_shot, "shot", "points above expectation", with_xp=True, with_own=True),
        f"**Finishing** (final strokes only, one per rally): given that {me}'s stroke ended the rally, "
        "how often it was a winner rather than an error, minus what xP-pre expected from the shot type, "
        "position and the receiver's state.\n",
        _mean_table(
            px.finishing, "final shot", "points above expectation", with_xp=True, unit="strokes"
        ),
        f"**Situation quality**: mean xP of the shots {me} plays, by type (averaged per rally). A higher "
        f"value means {me} tends to play that shot from positions the model likes, regardless of what "
        "happens next.\n",
        _mean_table(px.situation, "shot", "mean xP"),
        f"**xP added**: the change in {me}'s win probability caused by each stroke (rally start = the "
        "training server win rate), summed over the player's strokes in a rally, and per shot type. With "
        "a model at chance mid-rally these are small by construction; they are reported for completeness.\n",
        _mean_table(px.added_per_rally, "measure", "mean"),
        _mean_table(px.added_by_shot, "shot", "xP added per rally"),
    ]
    if img_rel:
        L.insert(3, f"![calibration]({img_rel})\n")
    return L
