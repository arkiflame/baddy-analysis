"use client";

import { useId, useMemo, useState } from "react";
import type { Grid, RateRow } from "@/lib/types";
import { int, pct, pctCi, pts, ptsCi, zoneWords } from "@/lib/format";

/* One half of a badminton court, drawn to scale (metres x 100), net at the top. The player's
   own half: y = metres from the net, x = metres from the centre line toward the player's own
   right. Real lines: doubles sidelines (+-3.05), singles sidelines (+-2.59), short service line
   (1.98), doubles long service line (5.94), centre line, baseline (6.70). The coach zones are
   the three depth bands x forehand / backhand side plus the body circle. */

export interface CourtFrame {
  singles_half_width_m: number;
  half_length_m: number;
  court_half_width_m: number;
  coach_bands: { name: string; lo: number; hi: number }[];
  body_radius_m: number;
}

export type CourtMode =
  | {
      kind: "zones";
      rows: RateRow[]; // one per zone (zone-alone rows, or one shot's rows)
      role: "faced" | "hit";
      me: string;
      within: number;
      minN: number;
      bodyAt: { x: number; y: number };
      bodyNote: string;
    }
  | {
      kind: "heat";
      grid: Grid;
      base: { x: number; y: number; xq1: number; xq3: number; yq1: number; yq3: number } | null;
      what: string;
    };

const S = 100; // px per metre
const X0 = -3.5;
const Y0 = -0.6;
const VW = 7 * S;
const VH = 7.7 * S;
const px = (x: number) => (x - X0) * S;
const py = (y: number) => (y - Y0) * S;

function fillFor(r: RateRow | undefined): string {
  if (!r || !r.reliable || !r.signal || r.delta === null) return "var(--div-mid)";
  const a = Math.abs(r.delta);
  const k = a < 0.05 ? 1 : a < 0.1 ? 2 : 3;
  return r.delta > 0 ? `var(--div-pos-${k})` : `var(--div-neg-${k})`;
}

interface Tip {
  x: number; // percent of width
  y: number; // percent of height
  title: string;
  lines: string[];
}

export function Court({
  frame,
  fhOnRight,
  sideLabels,
  mode,
  title,
}: {
  frame: CourtFrame;
  fhOnRight: boolean;
  sideLabels: { left: string; right: string };
  mode: CourtMode;
  title: string;
}) {
  const uid = useId();
  const [tip, setTip] = useState<Tip | null>(null);
  const minN = mode.kind === "zones" ? mode.minN : 0;
  const hw = frame.singles_half_width_m;
  const dw = frame.court_half_width_m;
  const L = frame.half_length_m;

  const zoneRows = useMemo(() => {
    if (mode.kind !== "zones") return new Map<string, RateRow>();
    return new Map(mode.rows.filter((r) => r.zone).map((r) => [r.zone as string, r]));
  }, [mode]);

  const heatMax = useMemo(() => {
    if (mode.kind !== "heat") return 1;
    let m = 1;
    for (const col of mode.grid.counts) for (const v of col) if (v > m) m = v;
    return m;
  }, [mode]);

  function zoneTip(zone: string, cx: number, cy: number): Tip {
    if (mode.kind !== "zones") return { x: 0, y: 0, title: "", lines: [] };
    const r = zoneRows.get(zone);
    const who = `${mode.me} loses`;
    const lines = r
      ? r.reliable
        ? [
            `${who} within ${mode.within} shots ${pct(r.rate)} of the time (95% CI ${pctCi(r.ci_lo, r.ci_hi)}, n=${int(r.n)})`,
            r.ref_rate !== null
              ? `Typical pros: ${pct(r.ref_rate)} (n=${int(r.ref_n)}); difference ${pts(r.delta)} points (95% CI ${ptsCi(r.delta_lo, r.delta_hi)})`
              : "No typical-pro reference",
            r.signal
              ? "Interval on the difference excludes zero"
              : "Interval on the difference includes zero: not a finding",
          ]
        : [`Only ${int(r.n)} strokes, fewer than the minimum of ${mode.minN}`]
      : ["No strokes in this zone"];
    return { x: (px(cx) / VW) * 100, y: (py(cy) / VH) * 100, title: zoneWords(zone), lines };
  }

  const zones: { zone: string; x: number; y: number; w: number; h: number }[] = [];
  if (mode.kind === "zones") {
    for (const b of frame.coach_bands) {
      for (const side of ["fh", "bh"] as const) {
        const right = side === "fh" ? fhOnRight : !fhOnRight;
        zones.push({
          zone: `${b.name}_${side}`,
          x: right ? 0 : -hw,
          y: b.lo,
          w: hw,
          h: Math.min(b.hi, L) - b.lo,
        });
      }
    }
  }

  const lineProps = { stroke: "var(--court-line)", strokeWidth: 3, fill: "none" } as const;

  return (
    <div className="relative mx-auto w-full max-w-[520px]">
      <svg
        viewBox={`0 0 ${VW} ${VH}`}
        role="img"
        aria-labelledby={`${uid}-title`}
        className="h-auto w-full select-none"
        onMouseLeave={() => setTip(null)}
      >
        <title id={`${uid}-title`}>{title}</title>
        <defs>
          <pattern
            id={`${uid}-hatch`}
            width="12"
            height="12"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <line x1="0" y1="0" x2="0" y2="12" stroke="var(--ink-2)" strokeWidth="1.5" opacity="0.45" />
          </pattern>
        </defs>

        {/* court surface */}
        <rect x={px(-dw)} y={py(0)} width={2 * dw * S} height={L * S} fill="var(--court)" />

        {/* heat cells (under the lines) */}
        {mode.kind === "heat" &&
          mode.grid.counts.map((col, ix) =>
            col.map((v, iy) => {
              if (!v) return null;
              const x = mode.grid.x0 + ix * mode.grid.bin;
              const y = mode.grid.y0 + iy * mode.grid.bin;
              return (
                <rect
                  key={`${ix}-${iy}`}
                  x={px(x)}
                  y={py(y)}
                  width={mode.grid.bin * S}
                  height={mode.grid.bin * S}
                  fill="var(--seq)"
                  fillOpacity={0.12 + 0.85 * (v / heatMax)}
                  onMouseEnter={() =>
                    setTip({
                      x: (px(x + mode.grid.bin / 2) / VW) * 100,
                      y: (py(y) / VH) * 100,
                      title: `${v} ${v === 1 ? "stroke" : "strokes"}`,
                      lines: [
                        `${y.toFixed(2)}–${(y + mode.grid.bin).toFixed(2)} m from the net, ${x.toFixed(2)}–${(x + mode.grid.bin).toFixed(2)} m from the centre line`,
                      ],
                    })
                  }
                />
              );
            }),
          )}

        {/* zone fills */}
        {zones.map((z) => {
          const r = zoneRows.get(z.zone);
          const t = zoneTip(z.zone, z.x + z.w / 2, z.y + z.h / 2);
          const hatched = r && r.reliable && !r.signal;
          // keep the rear labels above the doubles long service line (0.76 m from the baseline)
          const cy = z.y + z.h > L - 0.76 ? Math.min(z.y + z.h / 2, L - 0.76 - 0.45) : z.y + z.h / 2;
          return (
            <g
              key={z.zone}
              tabIndex={0}
              role="img"
              aria-label={`${t.title}: ${t.lines.join(". ")}`}
              onMouseEnter={() => setTip(t)}
              onFocus={() => setTip(t)}
              onBlur={() => setTip(null)}
            >
              <rect x={px(z.x)} y={py(z.y)} width={z.w * S} height={z.h * S} fill={fillFor(r)} />
              {hatched && (
                <rect
                  x={px(z.x)}
                  y={py(z.y)}
                  width={z.w * S}
                  height={z.h * S}
                  fill={`url(#${uid}-hatch)`}
                />
              )}
              <text
                x={px(z.x + z.w / 2)}
                y={py(cy) - 14}
                textAnchor="middle"
                fontSize="18"
                fill="var(--ink)"
              >
                {zoneWords(z.zone)}
              </text>
              <text
                x={px(z.x + z.w / 2)}
                y={py(cy) + 12}
                textAnchor="middle"
                fontSize="22"
                fontWeight="600"
                fill="var(--ink)"
              >
                {r && r.reliable && r.delta !== null ? `${pts(r.delta)} pts` : r ? `n<${minN}` : "–"}
              </text>
              <text
                x={px(z.x + z.w / 2)}
                y={py(cy) + 34}
                textAnchor="middle"
                fontSize="16"
                fill="var(--ink-2)"
              >
                {r ? `n=${int(r.n)}${r.signal ? " ●" : ""}` : ""}
              </text>
            </g>
          );
        })}

        {/* body zone */}
        {mode.kind === "zones" &&
          (() => {
            const r = zoneRows.get("body");
            const t = zoneTip("body", mode.bodyAt.x, mode.bodyAt.y);
            const hatched = r && r.reliable && !r.signal;
            const cx = px(mode.bodyAt.x);
            const cy = py(mode.bodyAt.y);
            const rr = frame.body_radius_m * S;
            return (
              <g
                tabIndex={0}
                role="img"
                aria-label={`Body (within ${frame.body_radius_m} m of the receiver; ${mode.bodyNote}): ${t.lines.join(". ")}`}
                onMouseEnter={() => setTip(t)}
                onFocus={() => setTip(t)}
                onBlur={() => setTip(null)}
              >
                <circle cx={cx} cy={cy} r={rr} fill={fillFor(r)} stroke="var(--ink)" strokeWidth="2" />
                {hatched && <circle cx={cx} cy={cy} r={rr} fill={`url(#${uid}-hatch)`} />}
                <text x={cx} y={cy - 6} textAnchor="middle" fontSize="15" fill="var(--ink)">
                  body
                </text>
                <text x={cx} y={cy + 14} textAnchor="middle" fontSize="16" fontWeight="600" fill="var(--ink)">
                  {r && r.reliable && r.delta !== null ? `${pts(r.delta)}${r.signal ? " ●" : ""}` : r ? `n<${minN}` : "–"}
                </text>
              </g>
            );
          })()}

        {/* lines */}
        <rect x={px(-dw)} y={py(0)} width={2 * dw * S} height={L * S} {...lineProps} />
        <line x1={px(-hw)} y1={py(0)} x2={px(-hw)} y2={py(L)} {...lineProps} />
        <line x1={px(hw)} y1={py(0)} x2={px(hw)} y2={py(L)} {...lineProps} />
        <line x1={px(-dw)} y1={py(1.98)} x2={px(dw)} y2={py(1.98)} {...lineProps} />
        <line x1={px(-dw)} y1={py(L - 0.76)} x2={px(dw)} y2={py(L - 0.76)} {...lineProps} />
        <line x1={px(0)} y1={py(1.98)} x2={px(0)} y2={py(L)} {...lineProps} />
        <line x1={px(-dw)} y1={py(0)} x2={px(dw)} y2={py(0)} stroke="var(--ink)" strokeWidth="8" />
        <text x={px(-dw) - 8} y={py(0) + 6} textAnchor="end" fontSize="16" fill="var(--ink-2)">
          net
        </text>

        {/* base position marker on heat maps */}
        {mode.kind === "heat" && mode.base && (
          <g aria-hidden="true">
            <rect
              x={px(mode.base.xq1)}
              y={py(mode.base.yq1)}
              width={(mode.base.xq3 - mode.base.xq1) * S}
              height={(mode.base.yq3 - mode.base.yq1) * S}
              fill="none"
              stroke="var(--ink)"
              strokeWidth="2"
              strokeDasharray="8 6"
            />
            <line x1={px(mode.base.x) - 14} y1={py(mode.base.y)} x2={px(mode.base.x) + 14} y2={py(mode.base.y)} stroke="var(--ink)" strokeWidth="4" />
            <line x1={px(mode.base.x)} y1={py(mode.base.y) - 14} x2={px(mode.base.x)} y2={py(mode.base.y) + 14} stroke="var(--ink)" strokeWidth="4" />
          </g>
        )}

        {/* side labels */}
        <text x={px(-hw / 2)} y={py(-0.25)} textAnchor="middle" fontSize="18" fill="var(--ink-2)">
          {sideLabels.left}
        </text>
        <text x={px(hw / 2)} y={py(-0.25)} textAnchor="middle" fontSize="18" fill="var(--ink-2)">
          {sideLabels.right}
        </text>
        <text x={px(0)} y={py(L) + 30} textAnchor="middle" fontSize="16" fill="var(--ink-2)">
          baseline, {L.toFixed(2)} m from the net
        </text>
      </svg>

      {tip && (
        <div
          role="tooltip"
          className="pointer-events-none absolute z-10 w-64 -translate-x-1/2 -translate-y-full rounded border border-line bg-surface p-2 text-xs shadow"
          style={{ left: `${Math.min(Math.max(tip.x, 25), 75)}%`, top: `${tip.y}%` }}
        >
          <div className="font-semibold">{tip.title}</div>
          {tip.lines.map((l, i) => (
            <div key={i} className="text-ink-2">
              {l}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Legend for the two modes; text and pattern carry the meaning, colour is reinforcement. */
export function CourtLegend({ mode }: { mode: "zones" | "heat" }) {
  if (mode === "heat") {
    return (
      <p className="text-xs text-ink-2">
        Darker cells hold more strokes (0.25 m grid, positions at hit time only). The cross is the
        base position (median receive position) and the dashed box its interquartile range.
      </p>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-ink-2">
      <span className="inline-flex items-center gap-1">
        <span className="inline-block h-3 w-5 border border-line" style={{ background: "var(--div-neg-2)" }} />
        loses less than typical pros (negative points)
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="inline-block h-3 w-5 border border-line" style={{ background: "var(--div-pos-2)" }} />
        loses more (positive points)
      </span>
      <span>● interval on the difference excludes zero</span>
      <span>hatched: interval includes zero</span>
      <span>stronger fill: larger difference (under 5, 5–10, over 10 points)</span>
    </div>
  );
}
