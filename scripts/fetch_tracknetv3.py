"""Fetch the TrackNetV3 source (MIT) and pretrained weights (MIT) used by tactics.tools.tracknet.

    uv run python scripts/fetch_tracknetv3.py

* Source: https://github.com/qaz812345/TrackNetV3 -> third_party/TrackNetV3 (git clone, depth 1)
* Weights: GitHub release mirror with published SHA-256 sums
  https://github.com/Agastyasingh1106/Badminton-AI/releases/tag/tracknetv3-weights
  (unmodified copies of the author's Google Drive files) -> weights/tracknetv3/
Both locations are git-ignored. Checksums are verified after download.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT / "third_party" / "TrackNetV3"
WEIGHTS_DIR = PROJECT / "weights" / "tracknetv3"
SRC_REPO = "https://github.com/qaz812345/TrackNetV3.git"
RELEASE = "https://github.com/Agastyasingh1106/Badminton-AI/releases/download/tracknetv3-weights"
WEIGHTS = {
    "TrackNet_best.pt": "df867641a02712b021f04548ff4b1208ddfdb47f629ab2094ceb978667e83b1a",
    "InpaintNet_best.pt": "5749b66b8002f3ad9e0af841604004706fc796df30599e6bf01952696009688c",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if (SRC_DIR / "model.py").exists():
        print(f"source already present: {SRC_DIR}")
    else:
        SRC_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", SRC_REPO, str(SRC_DIR)], check=True
        )
        print(f"cloned TrackNetV3 -> {SRC_DIR}")

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, expected in WEIGHTS.items():
        dest = WEIGHTS_DIR / name
        if not dest.exists():
            print(f"downloading {name} ...")
            urllib.request.urlretrieve(f"{RELEASE}/{name}", dest)  # noqa: S310 (fixed https URL)
        got = sha256(dest)
        if got != expected:
            dest.unlink()
            print(f"checksum mismatch for {name}: {got} != {expected}", file=sys.stderr)
            return 1
        print(f"ok  {name}  sha256={got[:12]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
