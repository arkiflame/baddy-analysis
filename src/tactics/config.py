"""Loads the TOML config files in config/.

Design decision: thresholds (zone depths, body radius, ...) are data, not code. Keeping them
in TOML means a coach can tune them without touching Python, and every analysis reads the
same numbers. Python 3.11+ ships `tomllib`, so this costs no dependency.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_ROOT = PROJECT_ROOT / "data" / "raw" / "shuttleset"


@dataclass(frozen=True, slots=True)
class Band:
    name: str
    lo: float
    hi: float


@dataclass(frozen=True, slots=True)
class ZoneConfig:
    coach_bands: tuple[Band, ...]
    body_radius_m: float
    fine_bands: tuple[Band, ...]
    fine_lateral_bands: int
    move_min_m: float
    centre_band_m: float
    out_tolerance_m: float
    court_width_m: float
    court_length_m: float
    singles_margin_m: float

    @property
    def net_y(self) -> float:
        return self.court_length_m / 2

    @property
    def centre_x(self) -> float:
        return self.court_width_m / 2

    @property
    def singles_half_width_m(self) -> float:
        return self.court_width_m / 2 - self.singles_margin_m


def _bands(raw: list[dict]) -> tuple[Band, ...]:
    bands = tuple(Band(b["name"], float(b["lo"]), float(b["hi"])) for b in raw)
    for a, b in zip(bands, bands[1:], strict=False):
        if a.hi != b.lo:
            raise ValueError(f"depth bands must be contiguous: {a} -> {b}")
    return bands


def load_zone_config(path: Path = CONFIG_DIR / "zones.toml") -> ZoneConfig:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return ZoneConfig(
        coach_bands=_bands(raw["coach"]["depth_bands"]),
        body_radius_m=float(raw["coach"]["body_radius_m"]),
        fine_bands=_bands(raw["fine"]["depth_bands"]),
        fine_lateral_bands=int(raw["fine"]["lateral_bands"]),
        move_min_m=float(raw["features"]["move_min_m"]),
        centre_band_m=float(raw["features"]["centre_band_m"]),
        out_tolerance_m=float(raw["features"]["out_tolerance_m"]),
        court_width_m=float(raw["court"]["width_m"]),
        court_length_m=float(raw["court"]["length_m"]),
        singles_margin_m=float(raw["court"]["singles_margin_m"]),
    )


@dataclass(frozen=True, slots=True)
class PlayerConfig:
    handedness: dict[str, str]
    default_handedness: str
    unverified: frozenset[str]

    def handed(self, player: str) -> str:
        return self.handedness.get(player, self.default_handedness)


def load_player_config(path: Path = CONFIG_DIR / "players.toml") -> PlayerConfig:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    players = raw.get("players", {})
    unverified = {
        n
        for n, p in players.items()
        if "assum" in p.get("source", "") or "verify" in p.get("source", "")
    }
    return PlayerConfig(
        handedness={name: p["handedness"] for name, p in players.items()},
        default_handedness=raw.get("default", {}).get("handedness", "right"),
        unverified=frozenset(unverified),
    )
