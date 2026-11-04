"""Live advantage experiment: does per-stroke STATE add signal to live rally prediction?

M3 (`docs/M3_BASELINE.md`) showed that shot / zone tokens predict the winner of a rally in
progress no better than the base rate (AUC 0.50-0.52 on live prefixes). This module repeats the
live setting with state features attached to every stroke:

* both players' positions at hit time (hitter and receiver, each in their own forehand frame),
* each player's distance from their own base position (bases from development matches),
* how far the receiver moved since their last hit, and over the hit before that,
* how far the hitter moved since their last hit,
* stroke index.

Two models: a logistic regression on bag-of-tokens + the last two strokes' state, and the M3 GRU
with the state vector concatenated to each token embedding. Same match-level split, same 14
holdout matches, same metrics. Pass condition (set before running): live-prefix AUC >= 0.60 on
the holdout. The result decides whether a live advantage bar is built (DECISIONS D24).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from tactics import xp
from tactics.config import ZoneConfig
from tactics.outcome_model import (
    PAD,
    GRUConfig,
    RallySeq,
    Vocab,
    _device,
    bag_features,
    evaluate_by_slice,
    labels,
    match_split,
    prefixes,
)
from tactics.splits import split

STATE_COLS = [
    "hit_lat_fh",
    "hit_depth",
    "recv_lat_fh",
    "recv_depth",
    "hitter_from_base",
    "recv_from_base",
    "recv_moved_last",
    "recv_moved_prev",
    "hitter_moved_last",
]
PASS_AUC = 0.60


# ---------------------------------------------------------------------------------------
# State features per stroke
# ---------------------------------------------------------------------------------------


def state_frame(df: pd.DataFrame, cfg: ZoneConfig) -> pd.DataFrame:
    """xp.feature_frame plus movement features. Bases come from development matches only."""
    dev_df, _ = split(df)
    bases, fallback = xp.receiver_bases(dev_df)
    f = xp.feature_frame(df, cfg, bases, fallback).sort_values(["rally_id", "stroke_no"])
    hb_lat = f.hitter.map(lambda p: bases.get(p, fallback)[0]).to_numpy(float)
    hb_dep = f.hitter.map(lambda p: bases.get(p, fallback)[1]).to_numpy(float)
    f["hitter_from_base"] = np.hypot(f.hit_lat_fh - hb_lat, f.hit_depth - hb_dep)
    g = f.groupby("rally_id", observed=True)
    # the receiver of stroke i hit stroke i-1: where they were then vs where they stand now
    prev_lat, prev_dep = g.hit_lat_fh.shift(1), g.hit_depth.shift(1)
    f["recv_moved_last"] = np.hypot(f.recv_lat_fh - prev_lat, f.recv_depth - prev_dep)
    # ... and the move before that: between their hits at i-3 and i-1
    f["recv_moved_prev"] = np.hypot(
        prev_lat - g.hit_lat_fh.shift(3), prev_dep - g.hit_depth.shift(3)
    )
    # the hitter's own move since their previous hit at i-2
    f["hitter_moved_last"] = np.hypot(
        f.hit_lat_fh - g.hit_lat_fh.shift(2), f.hit_depth - g.hit_depth.shift(2)
    )
    f["rally_has_unknown"] = f.rally_id.map(
        df.groupby("rally_id", observed=True).rally_has_unknown.first()
    ).to_numpy()
    f["server"] = f.rally_id.map(g.hitter.first()).to_numpy()
    f["rally_winner"] = f.rally_id.map(
        df.groupby("rally_id", observed=True).rally_winner.first().astype(str)
    ).to_numpy()
    f["land_tok"] = np.where(
        f.final_outcome_zone | (f.land_zone == "nozone"), "nozone", f.land_zone
    )
    return f.reset_index(drop=True)


@dataclass(slots=True)
class StateSeq:
    seq: RallySeq
    state: np.ndarray  # (n, F) raw features, NaN allowed


def build_state_sequences(f: pd.DataFrame) -> list[StateSeq]:
    out = []
    for rid, g in f[~f.rally_has_unknown].groupby("rally_id", sort=False, observed=True):
        if len(g) < 2:
            continue
        first = g.iloc[0]
        who = np.where(g.hitter_is_server, "S", "R")
        toks = [f"{w}|{s}|{z}" for w, s, z in zip(who, g.shot, g.land_tok, strict=True)]
        seq = RallySeq(
            rally_id=rid,
            match_id=first.match_id,
            tokens=toks,
            server_won=bool(first.rally_winner == first.server),
            score_server=0,
            score_receiver=0,
        )
        out.append(StateSeq(seq, g[STATE_COLS].to_numpy(float)))
    return out


class Scaler:
    def __init__(self, seqs: list[StateSeq]):
        allx = np.vstack([s.state for s in seqs])
        self.mean = np.nanmean(allx, axis=0)
        self.std = np.nanstd(allx, axis=0) + 1e-6

    def __call__(self, x: np.ndarray) -> np.ndarray:
        z = (x - self.mean) / self.std
        return np.nan_to_num(z, nan=0.0)


# ---------------------------------------------------------------------------------------
# Logistic regression: bag of tokens + last two strokes' state
# ---------------------------------------------------------------------------------------


def lr_features(items: list[tuple[StateSeq, int]], vocab: Vocab, scaler: Scaler) -> np.ndarray:
    bag = bag_features([(s.seq, k) for s, k in items], vocab)
    F = len(STATE_COLS)
    extra = np.zeros((len(items), 2 * F + 1), dtype=np.float32)
    for i, (s, k) in enumerate(items):
        z = scaler(s.state[:k])
        extra[i, :F] = z[k - 1]
        if k >= 2:
            extra[i, F : 2 * F] = z[k - 2]
        extra[i, -1] = k / 20.0
    return np.hstack([bag, extra])


def fit_lr(items, vocab, scaler, C: float = 0.3):
    from sklearn.linear_model import LogisticRegression

    X = lr_features(items, vocab, scaler)
    return LogisticRegression(C=C, max_iter=3000).fit(X, labels([(s.seq, k) for s, k in items]))


# ---------------------------------------------------------------------------------------
# GRU with state concatenated to the token embedding
# ---------------------------------------------------------------------------------------


def _tensors(items, vocab, scaler, device):
    import torch

    L = max(k for _, k in items)
    F = len(STATE_COLS)
    X = torch.full((len(items), L), PAD, dtype=torch.long)
    S = torch.zeros((len(items), L, F), dtype=torch.float32)
    for i, (s, k) in enumerate(items):
        X[i, :k] = torch.tensor(vocab.encode(s.seq.tokens[:k]))
        S[i, :k] = torch.tensor(scaler(s.state[:k]), dtype=torch.float32)
    lengths = torch.tensor([k for _, k in items])
    y = torch.tensor(labels([(s.seq, k) for s, k in items]), dtype=torch.float32)
    return X.to(device), S.to(device), lengths.to(device), y.to(device)


def build_net(vocab_size: int, cfg: GRUConfig):
    import torch
    from torch import nn

    F = len(STATE_COLS)

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(vocab_size, cfg.emb, padding_idx=PAD)
            self.gru = nn.GRU(cfg.emb + F, cfg.hidden, batch_first=True)
            self.head = nn.Sequential(
                nn.Dropout(cfg.dropout), nn.Linear(cfg.hidden + 1, 32), nn.ReLU(), nn.Linear(32, 1)
            )

        def forward(self, x, state, lengths):
            e = torch.cat([self.emb(x), state], dim=2)
            packed = nn.utils.rnn.pack_padded_sequence(
                e, lengths.cpu(), batch_first=True, enforce_sorted=False
            )
            _, h = self.gru(packed)
            feats = torch.cat([h[-1], (lengths.float() / 20.0).unsqueeze(1)], dim=1)
            return self.head(feats).squeeze(1)

    return Net()


def fit_net(train_items, val_items, vocab, scaler, cfg: GRUConfig):
    import torch
    from torch import nn

    torch.manual_seed(cfg.seed)
    device = _device(cfg)
    net = build_net(len(vocab), cfg).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.lr, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss()
    Xtr, Str, Ltr, ytr = _tensors(train_items, vocab, scaler, device)
    Xva, Sva, Lva, yva = _tensors(val_items, vocab, scaler, device)
    best, best_state, bad = float("inf"), None, 0
    n = len(train_items)
    for epoch in range(cfg.epochs):
        net.train()
        perm = torch.randperm(n, device=device)
        t0 = time.time()
        for i in range(0, n, cfg.batch):
            idx = perm[i : i + cfg.batch]
            opt.zero_grad()
            loss = loss_fn(net(Xtr[idx], Str[idx], Ltr[idx]), ytr[idx])
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
        net.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(net(Xva, Sva, Lva), yva))
        cfg.history.append(
            {"epoch": epoch + 1, "val_log_loss": val_loss, "seconds": round(time.time() - t0, 1)}
        )
        if val_loss < best - 1e-4:
            best, bad = val_loss, 0
            best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= cfg.patience:
                break
    net.load_state_dict(best_state)
    net.eval()
    return net


def predict_net(net, items, vocab, scaler, cfg: GRUConfig) -> np.ndarray:
    import torch

    device = _device(cfg)
    X, S, L, _ = _tensors(items, vocab, scaler, device)
    out = []
    with torch.no_grad():
        for i in range(0, len(items), 2048):
            out.append(
                torch.sigmoid(net(X[i : i + 2048], S[i : i + 2048], L[i : i + 2048])).cpu().numpy()
            )
    return np.concatenate(out)


# ---------------------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------------------


def _prefix_items(seqs: list[StateSeq]) -> list[tuple[StateSeq, int]]:
    by_id = {s.seq.rally_id: s for s in seqs}
    return [(by_id[r.rally_id], k) for r, k in prefixes([s.seq for s in seqs])]


def run_experiment(
    df: pd.DataFrame, cfg: ZoneConfig, gru_cfg: GRUConfig | None = None, seeds=(0, 1, 2)
) -> dict:
    t_all = time.time()
    f = state_frame(df, cfg)
    f["is_holdout"] = f.match_id.isin(set(split(df)[1].match_id.astype(str)))
    dev = build_state_sequences(f[~f.is_holdout])
    hold = build_state_sequences(f[f.is_holdout])
    train, val = match_split_state(dev, 0.12, seed=0)
    vocab = Vocab([s.seq for s in train])
    scaler = Scaler(train)
    gru_cfg = gru_cfg or GRUConfig()

    tr, va, te = _prefix_items(train), _prefix_items(val), _prefix_items(hold)
    y_te = labels([(s.seq, k) for s, k in te])
    k_te = np.array([k for _, k in te])
    n_te = np.array([s.seq.n for s, _ in te])
    base = float(np.mean([s.seq.server_won for s in train]))

    results, timing, histories = [], {}, {}
    results.append(evaluate_by_slice("base rate", y_te, np.full(len(y_te), base), k_te, n_te))
    t0 = time.time()
    lr = fit_lr(tr + va, vocab, scaler)
    p_lr = lr.predict_proba(lr_features(te, vocab, scaler))[:, 1]
    timing["logistic_seconds"] = time.time() - t0
    results.append(
        evaluate_by_slice("logistic: tokens + state of last 2 strokes", y_te, p_lr, k_te, n_te)
    )

    probs, secs = [], 0.0
    for seed in seeds:
        c = GRUConfig(
            **{
                **{k: getattr(gru_cfg, k) for k in GRUConfig.__slots__ if k != "history"},
                "seed": seed,
            }
        )
        t0 = time.time()
        net = fit_net(tr, va, vocab, scaler, c)
        secs += time.time() - t0
        probs.append(predict_net(net, te, vocab, scaler, c))
        histories[f"seed{seed}"] = c.history
    timing["gru_seconds"] = secs
    p_gru = np.mean(probs, axis=0)
    results.append(
        evaluate_by_slice(
            f"GRU: tokens + state (mean of {len(seeds)} seeds)", y_te, p_gru, k_te, n_te
        )
    )
    for seed, p in zip(seeds, probs, strict=True):
        results.append(evaluate_by_slice(f"GRU seed {seed}", y_te, p, k_te, n_te))
    table = pd.concat(results, ignore_index=True)

    live = table[table["slice"] == "all prefixes"].set_index("model").auc
    best_live_auc = float(
        max(
            live["logistic: tokens + state of last 2 strokes"],
            live[f"GRU: tokens + state (mean of {len(seeds)} seeds)"],
        )
    )
    timing["total_seconds"] = time.time() - t_all
    return {
        "table": table,
        "pass": best_live_auc >= PASS_AUC,
        "best_live_auc": best_live_auc,
        "pass_auc": PASS_AUC,
        "counts": {
            "dev_matches": len({s.seq.match_id for s in dev}),
            "holdout_matches": len({s.seq.match_id for s in hold}),
            "train_rallies": len(train),
            "val_rallies": len(val),
            "holdout_rallies": len(hold),
            "train_prefixes": len(tr),
            "holdout_prefixes": len(te),
            "state_features": STATE_COLS,
            "vocab": len(vocab),
            "base_rate_train": base,
        },
        "timing": timing,
        "gru_histories": histories,
        "gru_config": {k: getattr(gru_cfg, k) for k in GRUConfig.__slots__ if k != "history"},
        "device": str(_device(gru_cfg)),
    }


def match_split_state(seqs: list[StateSeq], frac: float, seed: int = 0):
    a, b = match_split([s.seq for s in seqs], frac, seed)
    ids_b = {s.rally_id for s in b}
    return [s for s in seqs if s.seq.rally_id not in ids_b], [
        s for s in seqs if s.seq.rally_id in ids_b
    ]
