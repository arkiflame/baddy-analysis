"""Holdout replication of a player's top insights.

Procedure (see docs/EVALUATION.md):
1. Run the full analysis on the development matches only and pick the top-k insights exactly
   as the report does.
2. Re-run the same analyses on the holdout matches and look up the same (analysis, key) rows.
3. An insight REPLICATES if the holdout effect has the same sign relative to the holdout
   baseline and the two 95% intervals overlap. It FAILS if the sign flips or the intervals are
   disjoint. It is UNTESTABLE if the holdout has fewer than `min_holdout_n` rallies for it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from tactics.analyses import AnalysisSettings, analyse_player
from tactics.report import describe, top_insights
from tactics.splits import split


@dataclass(slots=True)
class ReplicationResult:
    player: str
    dev_matches: int
    holdout_matches: int
    holdout_rallies: int
    table: pd.DataFrame

    @property
    def summary(self) -> dict[str, int]:
        return self.table.verdict.value_counts().to_dict() if len(self.table) else {}


def replicate(
    df: pd.DataFrame,
    player: str,
    s: AnalysisSettings | None = None,
    k: int = 5,
    min_holdout_n: int = 10,
) -> ReplicationResult:
    s = s or AnalysisSettings()
    dev, hold = split(df)
    rep_dev = analyse_player(dev, player, s)
    top = top_insights(rep_dev, k=k)

    hold_involved = hold[((hold.hitter == player) | (hold.receiver == player)) & hold.annotated]
    n_hold_matches = int(hold_involved.match_id.nunique())
    n_hold_rallies = int(hold_involved.rally_id.nunique())
    rep_hold = analyse_player(hold, player, s) if n_hold_rallies else None

    rows = []
    for _, row in top.iterrows():
        rec = {
            "analysis": row.analysis,
            "key": row.key,
            "claim": describe(row, player, s),
            "dev_n": int(row.n),
            "dev_rate": row.rate,
            "dev_ci_lo": row.ci_lo,
            "dev_ci_hi": row.ci_hi,
            "dev_baseline": row.baseline,
            "dev_lift": row.rate - row.baseline,
            "hold_n": 0,
            "hold_rate": None,
            "hold_ci_lo": None,
            "hold_ci_hi": None,
            "hold_baseline": None,
            "hold_lift": None,
            "verdict": "UNTESTABLE",
        }
        if rep_hold is not None and row.analysis in rep_hold.tables:
            t = rep_hold.tables[row.analysis]
            hit = t[t.key == row.key]
            if len(hit):
                h = hit.iloc[0]
                rec.update(
                    hold_n=int(h.n),
                    hold_rate=h.rate,
                    hold_ci_lo=h.ci_lo,
                    hold_ci_hi=h.ci_hi,
                    hold_baseline=h.baseline,
                    hold_lift=h.rate - h.baseline,
                )
                if h.n >= min_holdout_n:
                    same_sign = (h.rate - h.baseline) * (row.rate - row.baseline) > 0
                    overlap = (h.ci_lo <= row.ci_hi) and (row.ci_lo <= h.ci_hi)
                    rec["verdict"] = "REPLICATES" if (same_sign and overlap) else "FAILS"
        rows.append(rec)
    table = pd.DataFrame(rows)
    return ReplicationResult(
        player,
        int(dev[(dev.hitter == player) | (dev.receiver == player)].match_id.nunique()),
        n_hold_matches,
        n_hold_rallies,
        table,
    )


def result_markdown(res: ReplicationResult) -> str:
    L = [
        f"### {res.player}\n",
        f"Development matches: {res.dev_matches}; holdout matches: {res.holdout_matches} "
        f"({res.holdout_rallies} rallies).\n",
    ]
    if res.table.empty:
        L.append("_No insight passed the selection rule on the development set._\n")
        return "\n".join(L)
    for i, r in res.table.iterrows():
        L.append(f"{i + 1}. **{r.verdict}** - {r.claim}")
        if r.hold_n:
            L.append(
                f"   - holdout: {r.hold_rate:.0%} (95% CI {r.hold_ci_lo:.0%}-{r.hold_ci_hi:.0%}, n={r.hold_n}) "
                f"vs holdout baseline {r.hold_baseline:.0%}"
            )
        else:
            L.append("   - holdout: pattern does not occur")
    counts = res.summary
    L.append("")
    L.append("Verdicts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + "\n")
    return "\n".join(L)
