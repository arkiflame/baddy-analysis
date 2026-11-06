"""The web export on the synthetic table: JSON-serialisable, and every number traceable to the
report's own tables."""

import json
from pathlib import Path

from tactics import webexport, xp
from tactics.analyses import AnalysisSettings, analyse_player
from tactics.config import load_player_config, load_zone_config
from tactics.evaluation import selection_frequency
from tactics.report import coach_sections, rank_with_stability
from tests.synthetic import synthetic_annotated, synthetic_strokes


def test_player_export_matches_the_report(tmp_path):
    df = synthetic_strokes()
    cfg, pcfg, s = load_zone_config(), load_player_config(), AnalysisSettings()
    data = webexport.export_player(df, "X", cfg, pcfg, s, None, with_stability=True, command="t")
    text = json.dumps(data)  # must be serialisable with no NaN
    assert "NaN" not in text
    assert data["slug"] == "x" and data["coverage"]["matches"] == 2 and data["xp"] is None
    # top insights are the same rows the Markdown report ranks, with the same fold counts
    rep = analyse_player(df, "X", s)
    top, _ = rank_with_stability(rep, selection_frequency(df, "X", s))
    assert [i["key"] for i in data["insights"]["top"]] == top.key.tolist()
    key = "faced push_rush -> rear_bh"  # the planted pattern
    first = next(i for i in data["insights"]["top"] if i["key"] == key)
    row = top[top.key == key].iloc[0]
    assert first["role"] == "faced" and first["shot"] == "push_rush" and first["zone"] == "rear_bh"
    assert first["folds"] == 2 and first["selected_folds"] == 2 and first["stable"]
    assert first["n"] == int(row.n) and first["delta"] == float(row.delta)
    assert first["rank"] == int(top.index[top.key == key][0]) + 1
    # coach bullets split into title / detail and carry their insight (with its fold counts)
    against, fix, possible = coach_sections(rep, s)
    c = data["coach"]
    assert len(c["against"]) == len(against) and len(c["fix"]) == len(fix)
    assert len(c["possible"]) == len(possible) and c["possible_note"]
    assert c["fix"][0]["title"].rstrip(".") in fix[0]
    assert c["fix"][0]["insight"]["delta"] > 0 and c["fix"][0]["insight"]["folds"] == 2
    assert c["against_reference"] and "What X should fix" in c["against_reference"]
    fix_keys = {i["insight"]["key"] for i in c["fix"]}
    assert not fix_keys & {i["insight"]["key"] for i in c["against"]}
    # the scouting summary: stable, non-tentative top insights, numbers only in the record
    for item in data["summary"]:
        assert item["insight"]["stable"] and not item["insight"]["tentative"]
        assert not any(ch.isdigit() for ch in item["text"])
        assert item["insight"]["key"] in {i["key"] for i in data["insights"]["top"]}
    # danger tables: zone-alone rows exist for the court view
    assert data["danger"]["all"]["faced_zone"] and data["danger"]["all"]["hit"]
    zone_row = data["danger"]["all"]["faced_zone"][0]
    assert zone_row["zone"] and zone_row["shot"] is None and "delta_lo" in zone_row
    # positions: grids have the declared shape and never count more than their source rows
    g = data["positions"]["grids"]["hit"]
    assert len(g["counts"]) == g["nx"] and len(g["counts"][0]) == g["ny"]
    assert sum(map(sum, g["counts"])) <= g["n"]
    # habits and set plays are present as records
    assert isinstance(data["habits"]["by_shot"], list) and "serve3" in data["habits"]["set_plays"]
    # files
    webexport.write_json(tmp_path / "p.json", data)
    assert json.loads((tmp_path / "p.json").read_text(encoding="utf-8"))["player"] == "X"


def test_xp_block_carries_the_caveat_and_metrics():
    df = synthetic_annotated()
    cfg = load_zone_config()
    res = xp.run_experiment(df, cfg, seed=0, holdout_ids={"syn:4"})
    block = webexport.xp_json(xp.player_xp(res, "X", 30), res)
    assert block["caveat"].startswith("Read this first")
    assert block["auc_nonfinal"] is not None and block["auc_final"] is not None
    assert block["n_rallies"] > 0 and "NaN" not in json.dumps(block)


def test_web_slug():
    assert webexport.web_slug("Viktor AXELSEN") == "viktor-axelsen"
    assert webexport.web_slug("PUSARLA V. Sindhu") == "pusarla-v-sindhu"


def test_dataset_counts_and_live_block():
    df = synthetic_strokes()
    d = webexport.dataset_json(df)
    assert d["matches"] == df.match_id.nunique() and d["strokes"] == len(df) and d["players"] >= 2
    assert d["rallies_known_winner"] <= d["rallies"]
    assert webexport.live_json(Path("/nonexistent")) == []
