// Shapes of web/public/data/*.json as written by src/tactics/webexport.py.

export interface RateRow {
  label?: string;
  shot?: string | null;
  zone?: string | null;
  n: number;
  wins?: number;
  rate: number;
  ci_lo: number;
  ci_hi: number;
  ref_n: number | null;
  ref_rate: number | null;
  delta: number | null;
  delta_lo: number | null;
  delta_hi: number | null;
  reliable: boolean;
  ref_reliable?: boolean;
  delta_excludes_zero?: boolean;
  score?: number | null;
  signal?: boolean;
}

export interface Insight extends RateRow {
  rank: number | null;
  text: string;
  analysis: string;
  key: string;
  role: "faced" | "hit";
  split: string | null;
  selected_folds: number | null;
  folds: number | null;
  tentative: boolean;
  stable: boolean;
  borderline: boolean; // interval excludes zero by less than half a point (D29)
}

export interface CoachItem {
  title: string;
  detail: string;
  insight: Insight;
}

export interface SummaryItem {
  text: string; // one plain-language sentence, no numbers
  insight: Insight; // the numbers behind it
}

export interface DangerBlock {
  faced?: RateRow[];
  hit?: RateRow[];
  faced_zone?: RateRow[];
  hit_zone?: RateRow[];
  faced_shot?: RateRow[];
  hit_shot?: RateRow[];
  baseline_faced: number | null;
  baseline_hit: number | null;
}

export interface TendencyRow {
  situation: string;
  reply: string;
  n: number;
  wins: number;
  rate: number;
  ci_lo: number;
  ci_hi: number;
  ref_n: number;
  ref_rate: number;
  delta: number;
  delta_lo: number;
  delta_hi: number;
  reliable: boolean;
  ref_reliable: boolean;
  habit: boolean;
}

export interface PredictabilityRow {
  situation: string;
  n: number;
  entropy_bits: number;
  lo: number;
  hi: number;
  ref_entropy_bits: number;
  ref_lo: number;
  ref_hi: number;
  delta: number;
  effective_replies: number;
  more_predictable: boolean;
  less_predictable: boolean;
  top_reply: string;
  top_share: number;
}

export interface SetPlayRow {
  sequence: string;
  wins: number; // rallies that open this way
  n: number; // rallies in this role
  rate: number;
  ci_lo: number;
  ci_hi: number;
  ref_n: number;
  ref_rate: number | null;
  delta: number | null;
  delta_lo: number | null;
  delta_hi: number | null;
  win_rate: number;
  win_lo: number;
  win_hi: number;
  ref_win_rate: number | null;
  reliable: boolean;
  ref_reliable: boolean;
  candidate: boolean;
}

export interface MeanRow {
  label: string;
  n: number;
  mean: number | null;
  lo: number | null;
  hi: number | null;
  ref_n: number;
  ref_mean: number | null;
  ref_lo?: number | null;
  ref_hi?: number | null;
  delta: number | null;
  delta_lo: number | null;
  delta_hi: number | null;
  reliable: boolean;
  signal: boolean;
}

export interface XpRow extends MeanRow {
  xp?: number | null;
  own_delta?: number | null;
  own_lo?: number | null;
  own_hi?: number | null;
  own_signal?: boolean;
}

export interface Grid {
  x0: number;
  y0: number;
  bin: number;
  nx: number;
  ny: number;
  n: number;
  counts: number[][]; // counts[ix][iy]
}

export interface PlayerFile {
  player: string;
  slug: string;
  surname: string;
  generated: string;
  command: string;
  settings: {
    min_n: number;
    within: number;
    pressure_from: number;
    shot_vocabulary: string;
    stability: {
      min_share: number;
      tentative_ci_width: number;
      tentative_min_n: number;
      folds: number | null;
      checked: boolean;
    };
  };
  coverage: {
    matches: number;
    holdout_matches: number;
    rallies: number;
    strokes: number;
    win_rate: number;
    win_lo: number;
    win_hi: number;
    opponents: string[];
    handedness: "left" | "right";
    handedness_known: boolean;
  };
  insights: { top: Insight[]; less_stable: Insight[] };
  summary: SummaryItem[];
  coach: {
    against: CoachItem[]; // strengths: what an opponent should not do
    against_reference: string | null; // the one line that stands in for the weaknesses
    fix: CoachItem[]; // weaknesses as training priorities
    possible: CoachItem[]; // borderline candidates
    possible_note: string;
  };
  danger: Record<"all" | "game3" | "pressure", DangerBlock | undefined>;
  habits: {
    n_replies: number;
    by_shot: TendencyRow[];
    by_shot_zone: TendencyRow[];
    predictability: PredictabilityRow[];
    set_plays: Record<string, SetPlayRow[]>;
  };
  positions: {
    handedness: "left" | "right";
    frame: {
      singles_half_width_m: number;
      half_length_m: number;
      court_half_width_m: number;
      coach_bands: { name: string; lo: number; hi: number }[];
      body_radius_m: number;
    };
    base: {
      n: number;
      depth: number;
      lat_right: number;
      depth_q1: number;
      depth_q3: number;
      lat_q1: number;
      lat_q3: number;
    };
    ref_base: {
      players: number;
      depth_median: number;
      depth_min: number;
      depth_max: number;
      lat_abs_median: number;
    };
    grids: { hit: Grid; receive: Grid };
    pull: MeanRow[];
    distance: MeanRow[];
    per_hit: MeanRow[];
  };
  xp: {
    caveat: string;
    auc_nonfinal: number | null;
    auc_final: number | null;
    leaky_auc_final: number | null;
    chosen: Record<string, string>;
    dev_matches: number;
    holdout_matches: number;
    n_shots: number;
    n_rallies: number;
    overall: { mean: number; lo: number; hi: number; n: number; ref_mean: number; ref_n: number };
    by_shot: XpRow[];
    by_shot_band: XpRow[];
    finishing: XpRow[];
    situation: XpRow[];
  } | null;
}

export interface IndexPlayer {
  player: string;
  slug: string;
  surname: string;
  file: string;
  matches: number;
  holdout_matches: number;
  rallies: number;
  win_rate: number;
  win_lo: number;
  win_hi: number;
  handedness: string;
  n_top: number;
  n_tentative: number;
}

export interface EvaluationSummaryRow {
  player: string;
  scheme: "holdout" | "lomo" | "looo";
  folds: number;
  REPLICATES: number;
  "SAME DIRECTION": number;
  FAILS: number;
  UNTESTABLE: number;
}

export interface IndexFile {
  generated: string;
  command: string;
  dataset: {
    matches: number;
    strokes: number;
    rallies: number;
    rallies_known_winner: number;
    strokes_known_winner: number;
    players: number;
  };
  settings: {
    min_n: number;
    within: number;
    pressure_from: number;
    top_k: number;
    stability: {
      min_share: number;
      tentative_ci_width: number;
      tentative_min_n: number;
      checked: boolean;
    };
    min_matches: number;
  };
  xp: {
    auc_nonfinal: number | null;
    auc_final: number | null;
    leaky_auc_final: number | null;
    dev_matches: number;
    holdout_matches: number;
    metrics: {
      feature_set: string;
      model: string;
      slice: string;
      n: number;
      accuracy: number;
      log_loss: number;
      brier: number;
      auc: number;
    }[];
    chosen: Record<string, string>;
  };
  live: {
    file: string;
    pass: boolean;
    best_live_auc: number | null;
    pass_auc: number | null;
    command: string | null;
  }[];
  evaluation: {
    players: string[];
    summary: EvaluationSummaryRow[];
    totals: Omit<EvaluationSummaryRow, "player" | "folds">[];
    per_insight: {
      player: string;
      scheme: string;
      claim: string;
      verdict: string;
      test_n: number | null;
      test_rate: number | null;
      test_delta: number | null;
      test_delta_lo: number | null;
      test_delta_hi: number | null;
      selected_folds: number | null;
      folds: number | null;
    }[];
  } | null;
  players: IndexPlayer[];
}
