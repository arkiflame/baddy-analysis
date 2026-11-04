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
