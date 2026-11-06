"use client";

import { useId, useMemo, useState } from "react";
import type { Grid } from "@/lib/types";
import { type Band, CourtLines, NET, S, SideLabels, px, py, sideLabelsFor, toFull, viewBox } from "./Geometry";

export interface HeatBase {
  x: number; // half-court frame: toward the player's right
  y: number; // from the net
  xq1: number;
  xq3: number;
  yq1: number;
  yq3: number;
}

/** Where the player stands at the moment of a hit: darker cells hold more strokes. */
export function HeatCourt({
  grid,
  base,
  me,
  fhOnRight,
  frame,
  title,
}: {
  grid: Grid;
  base: HeatBase | null;
  me: string;
  fhOnRight: boolean;
  frame: { coach_bands: Band[] };
  title: string;
}) {
  const uid = useId();
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  const v = viewBox("player");
  const labels = sideLabelsFor("player", me, fhOnRight);
  const max = useMemo(() => {
    let m = 1;
    for (const col of grid.counts) for (const c of col) if (c > m) m = c;
    return m;
  }, [grid]);
  void frame;

  return (
    <div className="court-wrap relative mx-auto w-full max-w-[560px]">
      <svg viewBox={v.vb} role="img" aria-labelledby={`${uid}-t`} className="h-auto w-full select-none" onMouseLeave={() => setTip(null)}>
        <title id={`${uid}-t`}>{title}</title>
        <CourtLines view="player" />
        {grid.counts.map((col, ix) =>
          col.map((c, iy) => {
            if (!c) return null;
            const x = grid.x0 + ix * grid.bin;
            const y = grid.y0 + iy * grid.bin;
            const p = toFull(x, y, "player");
            const X = px(p.X);
            const Y = py(p.Y);
            const text = `${c} ${c === 1 ? "shot" : "shots"} here`;
            return (
              <rect
                key={`${ix}-${iy}`}
                x={X}
                y={Y}
                width={grid.bin * S}
                height={grid.bin * S}
                fill="#0b0b0b"
                fillOpacity={0.12 + 0.7 * (c / max)}
                onMouseEnter={() =>
                  setTip({ x: ((X + (grid.bin * S) / 2 - v.x0) / v.w) * 100, y: ((Y - v.y0) / v.h) * 100, text })
                }
              />
            );
          }),
        )}
        {base && (
          <g aria-label={`${me}'s usual waiting spot`} role="img">
            {(() => {
              const a = toFull(base.xq1, base.yq1, "player");
              const b = toFull(base.xq3, base.yq3, "player");
              return (
                <rect
                  x={px(Math.min(a.X, b.X))}
                  y={py(Math.min(a.Y, b.Y))}
                  width={Math.abs(b.X - a.X) * S}
                  height={Math.abs(b.Y - a.Y) * S}
                  fill="none"
                  stroke="var(--court-white)"
                  strokeWidth="3"
                  strokeDasharray="10 8"
                />
              );
            })()}
            {(() => {
              const c = toFull(base.x, base.y, "player");
              return (
                <>
                  <line x1={px(c.X) - 16} y1={py(c.Y)} x2={px(c.X) + 16} y2={py(c.Y)} stroke="var(--court-white)" strokeWidth="5" />
                  <line x1={px(c.X)} y1={py(c.Y) - 16} x2={px(c.X)} y2={py(c.Y) + 16} stroke="var(--court-white)" strokeWidth="5" />
                </>
              );
            })()}
          </g>
        )}
        <SideLabels half="player" left={labels.left} right={labels.right} />
        <text x={px(0)} y={py(NET) - 28} style={{ fontSize: "calc(var(--court-font-scale, 1) * 15px)" }} fill="var(--court-white)" aria-hidden="true">
          darker = {me} stands here more often
        </text>
      </svg>
      {tip && (
        <div
          role="tooltip"
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded border border-line bg-surface px-2 py-1 text-xs shadow"
          style={{ left: `${Math.min(Math.max(tip.x, 15), 85)}%`, top: `${tip.y}%` }}
        >
          {tip.text}
        </div>
      )}
      <p className="mt-1 text-xs text-ink-2">
        The cross is where {me} usually waits; the dashed box is where {me} waits half of the time.
      </p>
    </div>
  );
}
