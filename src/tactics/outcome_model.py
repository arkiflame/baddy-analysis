"""Milestone 3 baseline: predict who wins the rally from the strokes so far.

Framing
-------
* Reference player = the SERVER of the rally, so every rally has one fixed point of view and
  no player identity leaks in. Label: did the server win.
* A training example is a PREFIX of a rally: strokes 1..k with k <= n-1. The final stroke is
  never an input because its landing zone is the outcome (out / into the net / winner).
* Split is by MATCH: the 14 ShuttleSet22 holdout matches are the test set; development
  matches are used for training and (for the neural model) a match-level validation split.

Models
------
* base rate       : predict the training-set server win rate for everything
* logistic        : bag of (who, shot, zone) token counts + last-stroke one-hots + score + length
* gru             : embedded token sequence -> GRU -> logit (small, trains in minutes on a GPU)

Metrics: accuracy, log loss, Brier score, ROC AUC. Reported on (a) all prefixes pooled, (b) the
longest legal prefix per rally (n-1 strokes), (c) fixed prefix lengths k = 2, 4, 6.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from tactics.splits import split

PAD, UNK = 0, 1


# ---------------------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------------------


@dataclass(slots=True)
class RallySeq:
    rally_id: str
    match_id: str
    tokens: list[str]  # one token per stroke: "S|smash|mid_fh" (S = server hit it)
    server_won: bool
    score_server: int
    score_receiver: int

    @property
    def n(self) -> int:
        return len(self.tokens)


def build_sequences(df: pd.DataFrame) -> list[RallySeq]:
    """One RallySeq per annotated rally with a known winner and at least 2 strokes."""
    d = df[df.annotated & df.rally_winner.notna() & ~df.rally_has_unknown].copy()
    d = d.sort_values(["rally_id", "stroke_no"])
    d["who"] = np.where(d.hitter == d.server, "S", "R")
    d["zone"] = d.coach_zone.astype(object).where(d.coach_zone.notna(), "nozone")
    d["tok"] = d.who + "|" + d.shot_coarse.astype(str) + "|" + d.zone.astype(str)
    out: list[RallySeq] = []
    for rid, g in d.groupby("rally_id", sort=False, observed=True):
        if len(g) < 2:
            continue
        first = g.iloc[0]
        out.append(
            RallySeq(
                rally_id=rid,
                match_id=first.match_id,
                tokens=g.tok.tolist(),
                server_won=bool(first.rally_winner == first.server),
                score_server=int(first.score_before_hitter),
                score_receiver=int(first.score_before_receiver),
            )
        )
    return out


def prefixes(seqs: list[RallySeq], max_len: int | None = None) -> list[tuple[RallySeq, int]]:
    """All (rally, k) with 1 <= k <= n-1, optionally capped."""
    out = []
    for s in seqs:
        top = s.n - 1 if max_len is None else min(s.n - 1, max_len)
        out.extend((s, k) for k in range(1, top + 1))
    return out


# ---------------------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------------------


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    out = {
        "n": int(len(y)),
        "accuracy": float(((p >= 0.5).astype(int) == y).mean()),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "brier": float(brier_score_loss(y, p)),
    }
    out["auc"] = float(roc_auc_score(y, p)) if len(set(y.tolist())) == 2 else float("nan")
    return out


def evaluate_by_slice(
    name: str, y: np.ndarray, p: np.ndarray, k: np.ndarray, n: np.ndarray
) -> pd.DataFrame:
    rows = [{"model": name, "slice": "all prefixes", **metrics(y, p)}]
    full = k == n - 1
    rows.append({"model": name, "slice": "longest prefix (n-1)", **metrics(y[full], p[full])})
    for kk in (2, 4, 6):
        m = k == kk
        if m.sum() >= 50:
            rows.append({"model": name, "slice": f"k = {kk}", **metrics(y[m], p[m])})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------
# Logistic regression on bag-of-tokens
# ---------------------------------------------------------------------------------------


class Vocab:
    def __init__(self, seqs: list[RallySeq]):
        toks = sorted({t for s in seqs for t in s.tokens})
        self.index = {t: i + 2 for i, t in enumerate(toks)}  # 0 = PAD, 1 = UNK

    def __len__(self) -> int:
        return len(self.index) + 2

    def encode(self, tokens: list[str]) -> list[int]:
        return [self.index.get(t, UNK) for t in tokens]


def bag_features(items: list[tuple[RallySeq, int]], vocab: Vocab) -> np.ndarray:
    """Counts of each token in the prefix, one-hot of the last token, score and length."""
    v = len(vocab)
    X = np.zeros((len(items), 2 * v + 4), dtype=np.float32)
    for i, (s, k) in enumerate(items):
        ids = vocab.encode(s.tokens[:k])
        for t in ids:
            X[i, t] += 1
        X[i, v + ids[-1]] = 1
        X[i, 2 * v] = k
        X[i, 2 * v + 1] = s.score_server - s.score_receiver
        X[i, 2 * v + 2] = max(s.score_server, s.score_receiver)
        X[i, 2 * v + 3] = 1.0 if k % 2 == 1 else 0.0  # whose shot was last: odd k = server
    return X


def labels(items: list[tuple[RallySeq, int]]) -> np.ndarray:
    return np.array([s.server_won for s, _ in items], dtype=int)


def fit_logistic(items, vocab, C: float = 0.3):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    model = make_pipeline(StandardScaler(with_mean=False), LogisticRegression(C=C, max_iter=2000))
    model.fit(bag_features(items, vocab), labels(items))
    return model


# ---------------------------------------------------------------------------------------
# GRU
# ---------------------------------------------------------------------------------------


@dataclass(slots=True)
class GRUConfig:
    emb: int = 32
    hidden: int = 64
    layers: int = 1
    dropout: float = 0.2
    lr: float = 2e-3
    batch: int = 256
    epochs: int = 30
    patience: int = 5
    seed: int = 0
    device: str = "auto"
    history: list[dict] = field(default_factory=list)


def _device(cfg: GRUConfig):
    import torch

    if cfg.device != "auto":
        return torch.device(cfg.device)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _tensors(items, vocab, device):
    import torch

    L = max(k for _, k in items)
    X = torch.full((len(items), L), PAD, dtype=torch.long)
    extra = torch.zeros((len(items), 3), dtype=torch.float32)
    for i, (s, k) in enumerate(items):
        ids = vocab.encode(s.tokens[:k])
        X[i, :k] = torch.tensor(ids)
        extra[i] = torch.tensor(
            [s.score_server - s.score_receiver, max(s.score_server, s.score_receiver), k]
        )
    lengths = torch.tensor([k for _, k in items])
    y = torch.tensor(labels(items), dtype=torch.float32)
    return X.to(device), extra.to(device), lengths.to(device), y.to(device)


def build_gru(vocab_size: int, cfg: GRUConfig):
    import torch
    from torch import nn

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(vocab_size, cfg.emb, padding_idx=PAD)
            self.gru = nn.GRU(
                cfg.emb,
                cfg.hidden,
                num_layers=cfg.layers,
                batch_first=True,
                dropout=cfg.dropout if cfg.layers > 1 else 0.0,
            )
            self.head = nn.Sequential(
                nn.Dropout(cfg.dropout), nn.Linear(cfg.hidden + 3, 32), nn.ReLU(), nn.Linear(32, 1)
            )

        def forward(self, x, extra, lengths):
            e = self.emb(x)
            packed = nn.utils.rnn.pack_padded_sequence(
                e, lengths.cpu(), batch_first=True, enforce_sorted=False
            )
            _, h = self.gru(packed)
            feats = torch.cat(
                [h[-1], extra / torch.tensor([21.0, 21.0, 20.0], device=extra.device)], dim=1
            )
            return self.head(feats).squeeze(1)

    return Net()


def fit_gru(train_items, val_items, vocab, cfg: GRUConfig):
    import torch
    from torch import nn

    torch.manual_seed(cfg.seed)
    device = _device(cfg)
    net = build_gru(len(vocab), cfg).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=cfg.lr, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss()
    Xtr, Etr, Ltr, ytr = _tensors(train_items, vocab, device)
    Xva, Eva, Lva, yva = _tensors(val_items, vocab, device)
    best, best_state, bad = float("inf"), None, 0
    n = len(train_items)
    for epoch in range(cfg.epochs):
        net.train()
        perm = torch.randperm(n, device=device)
        t0 = time.time()
        for i in range(0, n, cfg.batch):
            idx = perm[i : i + cfg.batch]
            opt.zero_grad()
            loss = loss_fn(net(Xtr[idx], Etr[idx], Ltr[idx]), ytr[idx])
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
        net.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(net(Xva, Eva, Lva), yva))
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


def predict_gru(net, items, vocab, cfg: GRUConfig) -> np.ndarray:
    import torch

    device = _device(cfg)
    X, E, L, _ = _tensors(items, vocab, device)
    out = []
    with torch.no_grad():
        for i in range(0, len(items), 2048):
            out.append(
                torch.sigmoid(net(X[i : i + 2048], E[i : i + 2048], L[i : i + 2048])).cpu().numpy()
            )
    return np.concatenate(out)


# ---------------------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------------------


def match_split(
    seqs: list[RallySeq], frac: float, seed: int = 0
) -> tuple[list[RallySeq], list[RallySeq]]:
    rng = np.random.default_rng(seed)
    matches = sorted({s.match_id for s in seqs})
    rng.shuffle(matches)
    held = set(matches[: max(1, int(round(frac * len(matches))))])
    return [s for s in seqs if s.match_id not in held], [s for s in seqs if s.match_id in held]


SETTINGS = {
    "live": "all prefixes k <= n-1: the model does not know when the rally ends",
    "prefinal": "the n-1 strokes before the decisive stroke: given the next shot ends it, who wins",
    "full_masked": "all n strokes with the final stroke's landing zone masked (closest to Shot Influence)",
}


def mask_last_zone(s: RallySeq) -> RallySeq:
    who, shot, _ = s.tokens[-1].split("|")
    return RallySeq(
        s.rally_id,
        s.match_id,
        s.tokens[:-1] + [f"{who}|{shot}|nozone"],
        s.server_won,
        s.score_server,
        s.score_receiver,
    )


def items_for(seqs: list[RallySeq], setting: str) -> list[tuple[RallySeq, int]]:
    if setting == "live":
        return prefixes(seqs)
    if setting == "prefinal":
        return [(s, s.n - 1) for s in seqs]
    if setting == "full_masked":
        return [(mask_last_zone(s), s.n) for s in seqs]
    raise ValueError(setting)


def last_hitter_rates(items) -> dict[str, float]:
    """P(server wins | the last stroke of the prefix was hit by S / R), from training items."""
    y = labels(items)
    last_is_s = np.array([s.tokens[k - 1].startswith("S|") for s, k in items])
    return {"S": float(y[last_is_s].mean()), "R": float(y[~last_is_s].mean())}


def heuristic_probs(items, rates: dict[str, float]) -> np.ndarray:
    return np.array(
        [rates["S"] if s.tokens[k - 1].startswith("S|") else rates["R"] for s, k in items]
    )


def _slices(name: str, setting: str, y, p, k, n) -> pd.DataFrame:
    if setting == "live":
        t = evaluate_by_slice(name, y, p, k, n)
    else:
        t = pd.DataFrame([{"model": name, "slice": "all", **metrics(y, p)}])
    t.insert(0, "setting", setting)
    return t


def run_experiment(
    df: pd.DataFrame, gru_cfg: GRUConfig | None = None, seeds: tuple[int, ...] = (0, 1, 2)
) -> dict:
    dev_df, hold_df = split(df)
    dev, hold = build_sequences(dev_df), build_sequences(hold_df)
    train, val = match_split(dev, 0.12, seed=0)
    vocab = Vocab(train + [mask_last_zone(s) for s in train])
    gru_cfg = gru_cfg or GRUConfig()
    base_rate = float(np.mean([s.server_won for s in train]))

    results, histories, timing = [], {}, {}
    for setting in SETTINGS:
        tr, va, te = items_for(train, setting), items_for(val, setting), items_for(hold, setting)
        y_te = labels(te)
        k_te = np.array([k for _, k in te])
        n_te = np.array([s.n for s, _ in te])

        results.append(
            _slices(
                "base rate (train server win %)",
                setting,
                y_te,
                np.full(len(y_te), base_rate),
                k_te,
                n_te,
            )
        )
        rates = last_hitter_rates(tr)
        results.append(
            _slices(
                "heuristic: last hitter wins (train rates)",
                setting,
                y_te,
                heuristic_probs(te, rates),
                k_te,
                n_te,
            )
        )

        t0 = time.time()
        lr = fit_logistic(tr + va, vocab)
        p_lr = lr.predict_proba(bag_features(te, vocab))[:, 1]
        timing[f"{setting}_logistic_seconds"] = time.time() - t0
        results.append(
            _slices("logistic regression (bag of tokens)", setting, y_te, p_lr, k_te, n_te)
        )

        probs, gru_seconds = [], 0.0
        for seed in seeds:
            cfg = GRUConfig(
                **{
                    **{k: getattr(gru_cfg, k) for k in GRUConfig.__slots__ if k != "history"},
                    "seed": seed,
                }
            )
            t0 = time.time()
            net = fit_gru(tr, va, vocab, cfg)
            gru_seconds += time.time() - t0
            probs.append(predict_gru(net, te, vocab, cfg))
            histories[f"{setting}_seed{seed}"] = cfg.history
        timing[f"{setting}_gru_seconds"] = gru_seconds
        results.append(
            _slices(
                f"GRU (mean of {len(seeds)} seeds)",
                setting,
                y_te,
                np.mean(probs, axis=0),
                k_te,
                n_te,
            )
        )
        for seed, p in zip(seeds, probs, strict=True):
            results.append(_slices(f"GRU seed {seed}", setting, y_te, p, k_te, n_te))

    table = pd.concat(results, ignore_index=True)
    live_tr, live_te = items_for(train, "live"), items_for(hold, "live")
    return {
        "table": table,
        "settings": SETTINGS,
        "counts": {
            "dev_matches": len({s.match_id for s in dev}),
            "holdout_matches": len({s.match_id for s in hold}),
            "train_rallies": len(train),
            "val_rallies": len(val),
            "holdout_rallies": len(hold),
            "train_prefixes_live": len(live_tr),
            "holdout_prefixes_live": len(live_te),
            "vocab": len(vocab),
            "base_rate_train": base_rate,
            "holdout_server_win_rate": float(np.mean([s.server_won for s in hold])),
            "last_hitter_rates_prefinal_train": last_hitter_rates(items_for(train, "prefinal")),
        },
        "timing": timing,
        "gru_histories": histories,
        "gru_config": {k: getattr(gru_cfg, k) for k in GRUConfig.__slots__ if k != "history"},
        "device": str(_device(gru_cfg)),
    }
