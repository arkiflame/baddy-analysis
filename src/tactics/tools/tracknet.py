"""Thin wrapper around TrackNetV3 shuttle tracking (Chen & Wang, MMAsia 2023, MIT).

    uv run python -m tactics.tools.tracknet VIDEO --out outputs/track/<name>.csv [--cpu]

Only the network definition is imported from the upstream repo (`third_party/TrackNetV3/model.py`,
pure PyTorch). Frame preprocessing and heatmap decoding are re-implemented here from the
upstream `dataset.py` / `predict.py` so we do not inherit their pinned dependencies (pycocotools,
parse, torch 1.10). Checkpoints: `weights/tracknetv3/TrackNet_best.pt` (MIT, see
docs/research/shuttle-tracking-landscape.md for provenance and SHA-256).

Output CSV columns: frame, x, y, visible  (x, y in source-video pixels; TrackNet's own format is
Frame, Visibility, X, Y and is written too when --tracknet-csv is given).

Limitations: the upstream model expects a static camera (its "concat" background mode feeds the
per-video median frame). InpaintNet (gap filling) is not wrapped yet.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from tactics.config import PROJECT_ROOT

THIRD_PARTY = PROJECT_ROOT / "third_party" / "TrackNetV3"
DEFAULT_WEIGHTS = PROJECT_ROOT / "weights" / "tracknetv3" / "TrackNet_best.pt"
HEIGHT, WIDTH = 288, 512  # network input size, fixed by the checkpoint


def _import_tracknet_class():
    if not (THIRD_PARTY / "model.py").exists():
        raise FileNotFoundError(
            f"{THIRD_PARTY} missing: git clone --depth 1 https://github.com/qaz812345/TrackNetV3 {THIRD_PARTY}"
        )
    if str(THIRD_PARTY) not in sys.path:
        sys.path.insert(0, str(THIRD_PARTY))
    from model import TrackNet  # noqa: PLC0415  (upstream module)

    return TrackNet


@dataclass(slots=True)
class Tracker:
    net: object
    seq_len: int
    bg_mode: str
    device: object

    @classmethod
    def load(cls, weights: Path = DEFAULT_WEIGHTS, device: str = "auto") -> Tracker:
        import torch

        if not weights.exists():
            raise FileNotFoundError(f"{weights} missing: see docs/research for the download")
        dev = torch.device("cuda" if device == "auto" and torch.cuda.is_available() else
                           ("cpu" if device == "auto" else device))
        ckpt = torch.load(weights, map_location=dev, weights_only=False)
        seq_len, bg_mode = ckpt["param_dict"]["seq_len"], ckpt["param_dict"]["bg_mode"]
        TrackNet = _import_tracknet_class()
        in_dim = {"subtract": seq_len, "subtract_concat": seq_len * 4, "concat": (seq_len + 1) * 3}.get(
            bg_mode, seq_len * 3
        )
        net = TrackNet(in_dim=in_dim, out_dim=seq_len).to(dev)
        net.load_state_dict(ckpt["model"])
        net.eval()
        return cls(net=net, seq_len=seq_len, bg_mode=bg_mode, device=dev)

    # ---- preprocessing (mirrors upstream Video_IterableDataset.__process__) ---------------
    def _median(self, video: Path, max_samples: int = 300) -> np.ndarray:
        import cv2

        cap = cv2.VideoCapture(str(video))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, n // max_samples)
        frames = []
        for i in range(0, n, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, f = cap.read()
            if not ok:
                break
            frames.append(cv2.resize(f, (WIDTH, HEIGHT))[..., ::-1])
        cap.release()
        median = np.median(np.stack(frames), axis=0).astype(np.uint8)  # RGB, (H, W, 3)
        return np.moveaxis(median, -1, 0)  # (3, H, W)

    def _process(self, frames_bgr: list[np.ndarray], median: np.ndarray | None) -> np.ndarray:
        import cv2

        chans = []
        for f in frames_bgr:
            rgb = cv2.resize(f, (WIDTH, HEIGHT))[..., ::-1]
            if self.bg_mode in ("subtract", "subtract_concat"):
                diff = np.abs(rgb.astype(int) - np.moveaxis(median, 0, -1).astype(int)).sum(2)
                diff = np.clip(diff, 0, 255).astype(np.uint8)[None]
                chans.append(diff if self.bg_mode == "subtract" else np.concatenate([np.moveaxis(rgb, -1, 0), diff]))
            else:
                chans.append(np.moveaxis(rgb, -1, 0))
        x = np.concatenate(chans, axis=0)
        if self.bg_mode == "concat":
            x = np.concatenate([median, x], axis=0)
        return x.astype(np.float32) / 255.0

    # ---- decoding (mirrors upstream predict_location) -------------------------------------
    @staticmethod
    def _decode(heatmap: np.ndarray) -> tuple[int, int, int]:
        import cv2

        hm = (heatmap > 0.5).astype(np.uint8) * 255
        if hm.max() == 0:
            return 0, 0, 0
        cnts, _ = cv2.findContours(hm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        x, y, w, h = max((cv2.boundingRect(c) for c in cnts), key=lambda r: r[2] * r[3])
        return int(x + w / 2), int(y + h / 2), 1

    # ---- inference ------------------------------------------------------------------------
    def track(self, video: Path, batch_size: int = 8) -> pd.DataFrame:
        import cv2
        import torch

        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            raise FileNotFoundError(video)
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        sx, sy = w / WIDTH, h / HEIGHT
        median = self._median(video) if self.bg_mode else None

        rows: list[tuple[int, int, int, int]] = []
        window: list[np.ndarray] = []
        batch, batch_idx = [], []
        frame_i = 0

        def flush():
            if not batch:
                return
            x = torch.from_numpy(np.stack(batch)).to(self.device)
            with torch.no_grad():
                y = self.net(x).detach().cpu().numpy()  # (B, seq_len, H, W)
            for b, idxs in enumerate(batch_idx):
                for t, fi in enumerate(idxs):
                    if fi is None:
                        continue
                    cx, cy, vis = self._decode(y[b, t])
                    rows.append((fi, int(cx * sx), int(cy * sy), vis))
            batch.clear()
            batch_idx.clear()

        while True:
            ok, f = cap.read()
            if not ok:
                break
            window.append(f)
            frame_i += 1
            if len(window) == self.seq_len:
                batch.append(self._process(window, median))
                batch_idx.append(list(range(frame_i - self.seq_len, frame_i)))
                window = []
                if len(batch) == batch_size:
                    flush()
        if window:  # pad the tail by repeating the last frame, like upstream
            pad = self.seq_len - len(window)
            idxs = list(range(frame_i - len(window), frame_i)) + [None] * pad
            batch.append(self._process(window + [window[-1]] * pad, median))
            batch_idx.append(idxs)
        flush()
        cap.release()
        return pd.DataFrame(rows, columns=["frame", "x", "y", "visible"]).sort_values("frame").reset_index(drop=True)


def write_tracknet_csv(df: pd.DataFrame, path: Path) -> None:
    out = pd.DataFrame({"Frame": df.frame, "Visibility": df.visible, "X": df.x, "Y": df.y})
    out.to_csv(path, index=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--tracknet-csv", type=Path, default=None, help="also write TrackNet-format CSV")
    a = ap.parse_args(argv)
    tracker = Tracker.load(a.weights, device="cpu" if a.cpu else "auto")
    df = tracker.track(a.video)
    out = a.out or (PROJECT_ROOT / "outputs" / "track" / f"{a.video.stem}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    if a.tracknet_csv:
        write_tracknet_csv(df, a.tracknet_csv)
    print(f"{len(df)} frames, {int(df.visible.sum())} with a detection -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
