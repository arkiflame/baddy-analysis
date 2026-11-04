"""Spatial features for every stroke, computed from the RECEIVER's point of view.

Three layers, all driven by config/zones.toml:
  (a) coach zones   {front, mid, rear} x {fh, bh} + body (+ out / net_error for rally enders)
                    -> the unit for statistics
  (b) fine grid     4 depth bands x 4 lateral bands -> heatmaps only, never ranked
  (c) receiver-relative features: distance to the receiver, movement direction, cross/straight

Why the receiver's view: a shot's tactical meaning is "where did it send the opponent", so
depth is measured from the net into the receiver's half and the lateral axis points toward
the receiver's forehand. A left-handed receiver flips the lateral axis; nothing else changes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from tactics import court
from tactics.config import ZoneConfig, load_zone_config

ENDER_ZONES = {"out": "out", "net": "net_error", "not_over_net": "net_error"}


def annotate(df: pd.DataFrame, cfg: ZoneConfig | None = None) -> pd.DataFrame:
    """Return a copy of the stroke table with zone / feature columns added."""
    cfg = cfg or load_zone_config()
    out = df.copy()

    recv_half = np.where(out["hitter_half"] == "far", "near", np.where(out["hitter_half"] == "near", "far", None))
    is_far = recv_half == "far"
    is_near = recv_half == "near"
    known = is_far | is_near
    hand_left = (out["receiver_handed"] == "left").to_numpy()

    def depth(y):  # distance from the net into the receiver's half
        return np.where(is_far, cfg.net_y - y, np.where(is_near, y - cfg.net_y, np.nan))

    def lat_fh(x):  # toward the receiver's forehand side
        right = np.where(is_near, x - cfg.centre_x, np.where(is_far, cfg.centre_x - x, np.nan))
        return np.where(hand_left, -right, right)

    land_x, land_y = out["land_x"].to_numpy(float), out["land_y"].to_numpy(float)
    recv_x, recv_y = out["recv_x"].to_numpy(float), out["recv_y"].to_numpy(float)

    out["depth"] = depth(land_y)
    out["lat_fh"] = lat_fh(land_x)
    out["recv_depth"] = depth(recv_y)
    out["recv_lat_fh"] = lat_fh(recv_y * 0 + recv_x)
    out["dist_to_receiver"] = np.hypot(land_x - recv_x, land_y - recv_y)

    # --- out of bounds (geometry) and rally-ender ground truth ----------------------------
    half_w = cfg.singles_half_width_m + cfg.out_tolerance_m
    out["out_geom"] = (np.abs(out["lat_fh"]) > half_w) | (out["depth"] > cfg.net_y + cfg.out_tolerance_m)
    out["short_of_net"] = out["depth"] < 0

    # --- body shot --------------------------------------------------------------------------
    d_lat = out["lat_fh"] - out["recv_lat_fh"]
    d_depth = out["depth"] - out["recv_depth"]
    out["body"] = (out["dist_to_receiver"] < cfg.body_radius_m) & ~out["short_of_net"]
    out["body_side"] = np.where(out["body"], np.where(d_lat >= 0, "fh", "bh"), None)

    # --- (a) coach zone ---------------------------------------------------------------------
    band = _band_name(out["depth"].to_numpy(), cfg.coach_bands)
    side = np.where(out["lat_fh"] >= 0, "fh", "bh")
    zone = np.where(pd.isna(band), None, np.char.add(np.char.add(band.astype(str), "_"), side.astype(str)))
    zone = np.where(out["body"], "body", zone)
    zone = np.where(out["out_geom"], "out", zone)
    zone = np.where(out["short_of_net"], "net_error", zone)
    # rally enders: trust the annotated reason over geometry
    ender = out["lose_reason"].map(ENDER_ZONES) if "lose_reason" in out else pd.Series(None, index=out.index)
    ender = ender.where(out["is_last"])
    zone = np.where(ender.notna(), ender, zone)
    zone = np.where(known, zone, None)
    out["coach_zone"] = pd.Categorical(zone, categories=coach_zone_order(cfg))

    # --- (b) fine grid ----------------------------------------------------------------------
    out["fine_depth"] = _band_name(out["depth"].to_numpy(), cfg.fine_bands)
    out["fine_lat"] = _lateral_band(out["lat_fh"].to_numpy(), cfg)

    # --- (c) receiver-relative movement, cross/straight -------------------------------------
    move_dist = np.hypot(d_lat, d_depth)
    direction = np.where(np.abs(d_depth) >= np.abs(d_lat), np.where(d_depth < 0, "forward", "back"), "lateral")
    direction = np.where(move_dist < cfg.move_min_m, "in_place", direction)
    out["move_dir"] = np.where(np.isnan(move_dist), None, direction)
    out["move_side"] = np.where(np.isnan(move_dist), None, np.where(d_lat >= 0, "fh", "bh"))
    out["move_dist"] = move_dist

    contact_x = out["hit_x"].fillna(out["hitter_x"]).to_numpy(float)
    oh, ol = contact_x - cfg.centre_x, land_x - cfg.centre_x
    cross = np.where(np.sign(oh) != np.sign(ol), "cross", "straight")
    cross = np.where((np.abs(oh) < cfg.centre_band_m) | (np.abs(ol) < cfg.centre_band_m), "centre", cross)
    out["cross"] = np.where(np.isnan(oh) | np.isnan(ol), None, cross)
    return out


def coach_zone_order(cfg: ZoneConfig) -> list[str]:
    return [f"{b.name}_{s}" for b in cfg.coach_bands for s in ("fh", "bh")] + ["body", "out", "net_error"]


def _band_name(v: np.ndarray, bands) -> np.ndarray:
    names = np.full(v.shape, None, dtype=object)
    for b in bands:
        names[(v >= b.lo) & (v < b.hi)] = b.name
    return names


def _lateral_band(lat_fh: np.ndarray, cfg: ZoneConfig) -> np.ndarray:
    """Equal bands across the singles width, from the backhand sideline to the forehand sideline."""
    n = cfg.fine_lateral_bands
    w = cfg.singles_half_width_m
    edges = np.linspace(-w, w, n + 1)
    labels = _lateral_labels(n)
    idx = np.digitize(lat_fh, edges) - 1
    names = np.full(lat_fh.shape, None, dtype=object)
    ok = (idx >= 0) & (idx < n) & ~np.isnan(lat_fh)
    names[ok] = np.array(labels, dtype=object)[idx[ok]]
    names[(~np.isnan(lat_fh)) & ~ok] = "out"
    return names


def _lateral_labels(n: int) -> list[str]:
    if n == 4:
        return ["bh_sideline", "bh_inner", "fh_inner", "fh_sideline"]
    half = n // 2
    return [f"bh_{half - i}" for i in range(half)] + [f"fh_{i + 1}" for i in range(n - half)]
