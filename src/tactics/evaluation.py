"""Out-of-sample replication of a player's top insights.

Three schemes (docs/EVALUATION.md):

* **holdout**: select the top-k on the development matches (ShuttleSet22's published
  validation + test ids held out), test each on the player's holdout matches.
* **leave-one-match-out (lomo)**: for each of the player's matches m, select the top-k without
  m and record the pattern's count on m alone. Each report insight is then tested on the
  pooled out-of-sample counts from the folds in which it was selected, and the number of folds
  that selected it says how stable the selection is.
* **leave-one-opponent-out (looo)**: the same with all matches against one opponent held out
  at once, which tests whether an insight is one opponent's style in disguise.

Verdict for an insight whose development difference versus typical pros has a sign:
* REPLICATES: the out-of-sample rate differs from the reference in the same direction and the
  Newcombe 95% interval of that difference excludes zero;
* SAME DIRECTION: same sign, interval includes zero;
* FAILS: opposite sign;
* UNTESTABLE: fewer than `min_test_n` out-of-sample instances.
The reference is the typical-pro rate from the development (or full-data) analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from tactics.analyses import AnalysisSettings, analyse_player
from tactics.report import describe, top_insights
from tactics.splits import split
from tactics.stats import newcombe_diff_ci, wilson_ci

VERDICTS = ("REPLICATES", "SAME DIRECTION", "FAILS", "UNTESTABLE")


@dataclass(slots=True)
class ReplicationResult:
    player: str
    scheme: str
    dev_matches: int
    test_matches: int
    test_rallies: int
    folds: int
    table: pd.DataFrame

    @property
    def summary(self) -> dict[str, int]:
        return self.table.verdict.value_counts().to_dict() if len(self.table) else {}


def _lookup(rep, analysis: str, key: str) -> tuple[int, int] | None:
    t = rep.tables.get(analysis)
    if t is None:
        return None
    hit = t[t.key == key]
    if hit.empty:
        return None
    return int(hit.iloc[0].wins), int(hit.iloc[0].n)


def verdict(dev_sign: float, k: int, n: int, ref_k: int, ref_n: int, min_test_n: int) -> dict:
    out = {"test_n": n, "test_wins": k, "test_rate": np.nan, "test_lo": np.nan, "test_hi": np.nan}
    out.update({"test_delta": np.nan, "test_delta_lo": np.nan, "test_delta_hi": np.nan})
    if n < min_test_n:
        out["verdict"] = "UNTESTABLE"
        return out
    rate = k / n
    lo, hi = wilson_ci(k, n)
    dlo, dhi = newcombe_diff_ci(k, n, ref_k, ref_n)
    delta = rate - ref_k / ref_n
    out.update(test_rate=rate, test_lo=float(lo), test_hi=float(hi))
    out.update(test_delta=delta, test_delta_lo=float(dlo), test_delta_hi=float(dhi))
    if delta * dev_sign < 0:
        out["verdict"] = "FAILS"
    elif dlo > 0 or dhi < 0:
        out["verdict"] = "REPLICATES"
    else:
        out["verdict"] = "SAME DIRECTION"
    return out


def _player_matches(df: pd.DataFrame, player: str) -> pd.DataFrame:
    d = df[((df.hitter == player) | (df.receiver == player)) & df.annotated]
    return d


def holdout_replication(
    df: pd.DataFrame,
    player: str,
    s: AnalysisSettings | None = None,
    k: int = 5,
    min_test_n: int = 10,
) -> ReplicationResult:
    s = s or AnalysisSettings()
    dev, hold = split(df)
    rep_dev = analyse_player(dev, player, s)
    top = top_insights(rep_dev, k=k)
    hold_p = _player_matches(hold, player)
    rep_hold = analyse_player(hold, player, s, with_population=False) if len(hold_p) else None
    rows = []
    for _, row in top.iterrows():
        rec = _dev_record(row, player, s)
        found = _lookup(rep_hold, row.analysis, row.key) if rep_hold is not None else None
        kk, n = found if found else (0, 0)
        rec.update(
            verdict(np.sign(row.delta), kk, n, int(row.ref_wins), int(row.ref_n), min_test_n)
        )
        rec["selected_folds"], rec["folds"] = 1, 1
        rows.append(rec)
    return ReplicationResult(
        player,
        "holdout",
        int(_player_matches(dev, player).match_id.nunique()),
        int(hold_p.match_id.nunique()),
        int(hold_p.rally_id.nunique()),
        1,
        pd.DataFrame(rows),
    )


def _units(mine: pd.DataFrame, player: str, by: str) -> dict[str, set[str]]:
    """Fold -> match ids held out: one per match ('match') or one per opponent ('opponent')."""
    if by == "match":
        return {m: {m} for m in sorted(mine.match_id.astype(str).unique())}
    opp = np.where(mine.hitter == player, mine.receiver.astype(str), mine.hitter.astype(str))
    return {o: set(mine[opp == o].match_id.astype(str).unique()) for o in sorted(set(opp.tolist()))}


def selection_frequency(
    df: pd.DataFrame,
    player: str,
    s: AnalysisSettings | None = None,
    k: int = 5,
    by: str = "match",
) -> pd.DataFrame:
    """How often each pattern enters the top-k when one match (or opponent) is left out.

    One row per pattern selected in at least one fold: analysis, key, selected_folds, folds.
    The report ranks only patterns selected in at least half of the leave-one-match-out folds
    and lists the rest as "less stable" (D27). Same folds and the same k as `leave_one_out`,
    so the counts match the ones printed by `tactics evaluate`.
    """
    s = s or AnalysisSettings()
    units = _units(_player_matches(df, player), player, by)
    counts: dict[tuple[str, str], int] = {}
    for matches in units.values():
        held = df.match_id.astype(str).isin(matches)
        for _, r in top_insights(analyse_player(df[~held], player, s), k=k).iterrows():
            counts[(r.analysis, r.key)] = counts.get((r.analysis, r.key), 0) + 1
    rows = [
        {"analysis": a, "key": key, "selected_folds": c, "folds": len(units)}
        for (a, key), c in counts.items()
    ]
    return pd.DataFrame(rows, columns=["analysis", "key", "selected_folds", "folds"])


def leave_one_out(
    df: pd.DataFrame,
    player: str,
    s: AnalysisSettings | None = None,
    k: int = 5,
    by: str = "match",
    min_test_n: int = 10,
) -> ReplicationResult:
    """by = 'match' (lomo) or 'opponent' (looo)."""
    s = s or AnalysisSettings()
    full = analyse_player(df, player, s)
    top = top_insights(full, k=k)
    mine = _player_matches(df, player)
    units = _units(mine, player, by)
    pooled: dict[tuple[str, str], dict] = {
        (r.analysis, r.key): {"selected": 0, "wins": 0, "n": 0} for _, r in top.iterrows()
    }
    for _, matches in units.items():
        held = df.match_id.astype(str).isin(matches)
        rep_in = analyse_player(df[~held], player, s)
        chosen = {(r.analysis, r.key) for _, r in top_insights(rep_in, k=k).iterrows()}
        rep_out = analyse_player(df[held], player, s, with_population=False)
        for ident, acc in pooled.items():
            if ident not in chosen:
                continue
            acc["selected"] += 1
            found = _lookup(rep_out, *ident)
            if found:
                acc["wins"] += found[0]
                acc["n"] += found[1]
    rows = []
    for _, row in top.iterrows():
        rec = _dev_record(row, player, s)
        acc = pooled[(row.analysis, row.key)]
        rec.update(
            verdict(
                np.sign(row.delta),
                acc["wins"],
                acc["n"],
                int(row.ref_wins),
                int(row.ref_n),
                min_test_n,
            )
        )
        rec["selected_folds"], rec["folds"] = acc["selected"], len(units)
        rows.append(rec)
    return ReplicationResult(
        player,
        "lomo" if by == "match" else "looo",
        int(mine.match_id.nunique()),
        int(mine.match_id.nunique()),
        int(mine.rally_id.nunique()),
        len(units),
        pd.DataFrame(rows),
    )


def _dev_record(row: pd.Series, player: str, s: AnalysisSettings) -> dict:
    return {
        "analysis": row.analysis,
        "key": row.key,
        "claim": describe(row, player, s),
        "dev_n": int(row.n),
        "dev_rate": float(row.rate),
        "dev_lo": float(row.ci_lo),
        "dev_hi": float(row.ci_hi),
        "ref_rate": float(row.ref_rate),
        "ref_n": int(row.ref_n),
        "dev_delta": float(row.delta),
    }


def replicate_all(
    df, player, s=None, k=5, schemes=("holdout", "lomo", "looo")
) -> list[ReplicationResult]:
    out = []
    for scheme in schemes:
        if scheme == "holdout":
            out.append(holdout_replication(df, player, s, k))
        else:
            out.append(
                leave_one_out(df, player, s, k, by="match" if scheme == "lomo" else "opponent")
            )
    return out


def result_markdown(res: ReplicationResult) -> str:
    what = {
        "holdout": (
            f"Development matches: {res.dev_matches}; holdout matches: {res.test_matches} "
            f"({res.test_rallies} rallies)."
        ),
        "lomo": (
            f"Leave-one-match-out over {res.folds} matches ({res.test_rallies} rallies); each "
            "insight is tested on the matches left out in the folds that selected it."
        ),
        "looo": f"Leave-one-opponent-out over {res.folds} opponents ({res.test_rallies} rallies).",
    }[res.scheme]
    L = [f"### {res.player}, {res.scheme}\n", what + "\n"]
    if res.table.empty:
        L.append("_No insight passed the selection rule._\n")
        return "\n".join(L)
    for i, r in res.table.iterrows():
        L.append(f"{i + 1}. **{r.verdict}** - {r.claim}")
        if r.verdict == "UNTESTABLE" and r.test_n:
            line = f"   - out of sample: only {int(r.test_n)} instances (fewer than 10)"
        elif r.test_n:
            line = (
                f"   - out of sample: {r.test_rate:.0%} (95% CI {r.test_lo:.0%}-{r.test_hi:.0%}, n={int(r.test_n)}) "
                f"vs typical pros {r.ref_rate:.0%}; difference {r.test_delta * 100:+.0f} "
                f"({r.test_delta_lo * 100:+.0f} to {r.test_delta_hi * 100:+.0f})"
            )
        else:
            line = "   - out of sample: pattern does not occur"
        if res.scheme != "holdout":
            line += f"; selected in {int(r.selected_folds)} of {int(r.folds)} folds"
        L.append(line)
    L.append("")
    L.append(
        "Verdicts: "
        + ", ".join(f"{v} {res.summary[v]}" for v in VERDICTS if v in res.summary)
        + "\n"
    )
    return "\n".join(L)


def summary_table(results: list[ReplicationResult]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append(
            {
                "player": r.player,
                "scheme": r.scheme,
                "folds": r.folds,
                **{v: r.summary.get(v, 0) for v in VERDICTS},
            }
        )
    return pd.DataFrame(rows)
