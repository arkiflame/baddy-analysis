"""The jargon check (D30): the parser keeps the main text, drops what is one click away, and
finds every banned term; and the built site, when present, has none left."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "jargon_check", ROOT / "scripts" / "jargon_check.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PAGE = """<!doctype html><html><head><title>t</title><style>.x{}</style></head><body>
<p>Axelsen loses the point quickly about 1 time in 14.</p>
<div data-technical=""><p>n=97, 95% CI -18 to -5, selected in 11 of 20 folds</p></div>
<details data-technical=""><summary>Show the numbers</summary><p>Wilson interval, entropy 2.1 bits</p></details>
<details><summary>Habits</summary><p>After a clear, Axelsen smashes 3 times in 4 (holdout).</p></details>
<div hidden=""><p>holdout AUC 0.50</p></div>
<p>The receiver-relative frame and the typical pros.</p>
<li>We re-checked it leaving out one match at a time.</li>
<svg><text>n=5</text></svg>
</body></html>"""


def test_parser_separates_main_text_from_the_technical_layer(tmp_path):
    mod = _mod()
    out = tmp_path / "out"
    (out / "players" / "x").mkdir(parents=True)
    (out / "players" / "x" / "index.html").write_text(PAGE, encoding="utf-8")
    (out / "404.html").write_text("<p>n=1 CI</p>", encoding="utf-8")
    hits = mod.scan(out)
    terms = [h["term"] for h in hits]
    assert terms == [
        "holdout",
        "receiver-relative",
        "typical pros",
    ]  # a plain <details> body still counts
    assert hits[0]["page"] == "players/x/index.html" and "holdout" in hits[0]["context"]
    assert mod.main(["--out", str(out)]) == 1
    (out / "players" / "x" / "index.html").write_text("<p>plain words only</p>", encoding="utf-8")
    assert mod.main(["--out", str(out)]) == 0
    assert mod.main(["--out", str(tmp_path / "missing")]) == 2


def test_built_site_has_no_jargon_in_the_main_text():
    out = ROOT / "web" / "out"
    if not (out / "index.html").exists():
        pytest.skip("web/out not built")
    mod = _mod()
    hits = mod.scan(out)
    assert hits == [], "\n".join(f"{h['page']}: {h['term']}: {h['context']}" for h in hits)
