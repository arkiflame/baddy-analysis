// Formatting only: these helpers never compute a statistic, they print the exported ones.

export const pct = (v: number | null | undefined, digits = 0): string =>
  v === null || v === undefined || Number.isNaN(v) ? "–" : `${(v * 100).toFixed(digits)}%`;

export const pctCi = (lo: number | null | undefined, hi: number | null | undefined): string =>
  lo === null || lo === undefined || hi === null || hi === undefined
    ? "–"
    : `${pct(lo)}–${pct(hi)}`;

/** Difference in percentage points, with sign. */
export const pts = (v: number | null | undefined): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const r = Math.round(v * 100);
  return r > 0 ? `+${r}` : `${r === 0 ? 0 : r}`; // no "-0"
};

export const ptsCi = (lo: number | null | undefined, hi: number | null | undefined): string =>
  lo === null || lo === undefined || hi === null || hi === undefined
    ? "–"
    : `${pts(lo)} to ${pts(hi)}`;

export const num = (v: number | null | undefined, digits = 2, sign = false): string =>
  v === null || v === undefined || Number.isNaN(v)
    ? "–"
    : `${sign && v > 0 ? "+" : ""}${v.toFixed(digits)}`;

export const numCi = (
  lo: number | null | undefined,
  hi: number | null | undefined,
  digits = 2,
  sign = false,
): string =>
  lo === null || lo === undefined || hi === null || hi === undefined
    ? "–"
    : `${num(lo, digits, sign)} to ${num(hi, digits, sign)}`;

export const int = (v: number | null | undefined): string =>
  v === null || v === undefined ? "–" : v.toLocaleString("en-US");

const SHOTS: Record<string, string> = {
  push_rush: "pushes and rushes",
  smash: "smashes",
  net: "net shots",
  defensive: "defensive returns",
  drop: "drops",
  lob: "lobs",
  clear: "clears",
  drive: "drives",
  short_service: "short serves",
  long_service: "long serves",
};

export const shotWords = (shot: string | null | undefined): string =>
  !shot ? "any shot" : (SHOTS[shot] ?? shot.replace(/_/g, " "));

export const zoneWords = (zone: string | null | undefined): string => {
  if (!zone) return "anywhere";
  if (zone === "body" || zone === "out" || zone === "net_error") return zone.replace("_", " ");
  const [depth, side] = zone.split("_");
  return `${depth} ${side === "fh" ? "forehand" : "backhand"}`;
};

/** "P:short_service > O:net > P:lob" -> "short serve · opponent net · lob" with P/O kept. */
export const sequenceWords = (seq: string, me: string): string =>
  seq
    .split(" > ")
    .map((tok) => {
      const [who, shot] = tok.split(":");
      return `${who === "P" ? me : "opponent"} ${shot.replace(/_/g, " ")}`;
    })
    .join(" › ");

/* ---- Plain-language helpers (D30). Formatting only, mirroring src/tactics/plain.py. ---- */

const ONE_IN_BELOW = 0.3;
const pctInt = (p: number) => Math.floor(p * 100 + 0.5);

/** 0.07 -> "about 1 time in 14"; 0.45 -> "about 45% of the time". */
export const oneIn = (p: number | null | undefined): string => {
  if (p === null || p === undefined || Number.isNaN(p)) return "–";
  if (p <= 0) return "almost never";
  if (p >= 0.995) return "almost every time";
  if (p < ONE_IN_BELOW) return `about 1 time in ${Math.round(1 / p)}`;
  return `about ${pctInt(p)}% of the time`;
};

/** Two rates in the same form so they can be compared. */
export const freqPair = (p: number, q: number): [string, string] =>
  p < ONE_IN_BELOW && q < ONE_IN_BELOW
    ? [oneIn(p), oneIn(q)]
    : [`about ${pctInt(p)}% of the time`, `about ${pctInt(q)}% of the time`];

export const wholePct = (p: number | null | undefined): string =>
  p === null || p === undefined || Number.isNaN(p) ? "–" : `${pctInt(p)}%`;

const AREAS: Record<string, string> = {
  front_fh: "front forehand corner",
  front_bh: "front backhand corner",
  mid_fh: "middle of the court, forehand side",
  mid_bh: "middle of the court, backhand side",
  rear_fh: "back forehand corner",
  rear_bh: "back backhand corner",
  body: "body",
  out: "out",
  net_error: "into the net",
};

/** Court areas the way players name them; never a zone code. */
export const areaWords = (zone: string | null | undefined): string =>
  !zone ? "anywhere" : (AREAS[zone] ?? zone.replace(/_/g, " "));

/** Short labels that fit inside a drawn zone. */
const AREAS_SHORT: Record<string, string> = {
  front_fh: "front forehand",
  front_bh: "front backhand",
  mid_fh: "middle, forehand side",
  mid_bh: "middle, backhand side",
  rear_fh: "back forehand",
  rear_bh: "back backhand",
  body: "body",
};
export const areaShort = (zone: string): string => AREAS_SHORT[zone] ?? areaWords(zone);

/** "a clear", "a push or rush": the incoming shot as a noun. */
const A_SHOT: Record<string, string> = {
  push_rush: "a push or rush",
  smash: "a smash",
  net: "a net shot",
  defensive: "a defensive return",
  drop: "a drop",
  lob: "a lob",
  clear: "a clear",
  drive: "a drive",
  short_service: "a short serve",
  long_service: "a long serve",
};
export const aShot = (shot: string): string => A_SHOT[shot] ?? `a ${shot.replace(/_/g, " ")}`;

/** "clear -> rear_bh" -> "a clear to the back backhand corner"; "-> any" -> "a clear, wherever it lands". */
export const situationWords = (situation: string, poss = "the"): string => {
  const [shot, zone] = situation.split(" -> ");
  if (!zone || zone === "any") return `${aShot(shot)}, wherever it lands`;
  if (zone === "body") return `${aShot(shot)} straight at ${poss} body`;
  return `${aShot(shot)} ${toArea(zone, poss)}`;
};

/** "to Axelsen's back backhand corner" / "to the middle of Axelsen's forehand side". */
export const toArea = (zone: string, poss: string): string =>
  zone === "mid_fh" || zone === "mid_bh"
    ? `to the middle of ${poss} ${zone === "mid_fh" ? "forehand" : "backhand"} side`
    : `to ${poss} ${areaWords(zone)}`;

/** "smash -> mid_fh" -> "smash to the middle of the court, forehand side". */
export const replyWords = (reply: string): string => {
  const [shot, zone] = reply.split(" -> ");
  const s = shot.replace(/_/g, " ");
  return zone ? `${s} ${toArea(zone, "the opponent's")}` : s;
};
