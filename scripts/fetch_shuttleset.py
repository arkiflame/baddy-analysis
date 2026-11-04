"""Download ShuttleSet and ShuttleSet22 into data/raw/shuttleset/.

Both datasets are plain CSV files inside the CoachAI-Projects GitHub repo (MIT license).
We cannot simply `git clone` it on Windows: another folder in that repo contains a file
whose name has a colon, which NTFS refuses, so any checkout of the full tree aborts.
`git archive` on just the sub-trees we need sidesteps that entirely.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "https://github.com/wywyWang/CoachAI-Projects.git"
SUBTREES = {
    "ShuttleSet": "ShuttleSet",
    "ShuttleSet22": "CoachAI-Challenge-IJCAI2023/ShuttleSet22",
}
ROOT_FILES = ["LICENSE", "CITATIONS.bib"]

PROJECT = Path(__file__).resolve().parents[1]
DEST = PROJECT / "data" / "raw" / "shuttleset"


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kw)


def main() -> int:
    if DEST.exists() and any(DEST.iterdir()):
        print(f"{DEST} already exists; delete it to re-download.")
        return 0
    DEST.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "repo"
        print("Cloning metadata only (blobs are fetched lazily by git archive)...")
        # --filter=blob:none + --sparse avoids downloading the whole repo; no files are checked out.
        run(["git", "clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse", REPO, str(clone)])

        for name, subtree in SUBTREES.items():
            out = DEST / name
            out.mkdir()
            print(f"Extracting {subtree} -> {out}")
            archive = run(["git", "-C", str(clone), "archive", "--format=tar", f"HEAD:{subtree}"],
                          capture_output=True)
            run(["tar", "-x", "-C", str(out)], input=archive.stdout)

        for f in ROOT_FILES:
            content = run(["git", "-C", str(clone), "show", f"HEAD:{f}"], capture_output=True).stdout
            (DEST / f).write_bytes(content)

    n_ss = len([p for p in (DEST / "ShuttleSet" / "set").iterdir() if p.is_dir()])
    n_ss22 = len([p for p in (DEST / "ShuttleSet22" / "set").iterdir() if p.is_dir()])
    print(f"Done. ShuttleSet: {n_ss} match folders, ShuttleSet22: {n_ss22} match folders.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        shutil.rmtree(DEST, ignore_errors=True)
        print(f"Command failed: {' '.join(e.cmd)}", file=sys.stderr)
        sys.exit(1)
