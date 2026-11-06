import { useId } from "react";
import { areaShort, shotWords } from "@/lib/format";
import {
  type Band,
  type Half,
  CourtLines,
  HALF_W,
  L,
  NET,
  S,
  SideLabels,
  px,
  py,
  sideLabelsFor,
  toFull,
  viewBox,
  zoneCentre,
  zoneRects,
} from "./Geometry";

export interface HeroItem {
  n: number; // 1..3, matches the caption list
  role: "faced" | "hit";
  zone?: string | null;
  shot?: string | null;
  kind: "strong" | "weak"; // strong = the player wins more here, weak = loses more
}

/**
 * The page's hero image: a full court with the biggest takeaways drawn where they happen.
 * Shots the player receives are on the bottom half, shots the player plays on the top half.
 */
export function HeroCourt({
  items,
  me,
  fhOnRight,
  frame,
  title,
  bodyAt,
}: {
  items: HeroItem[];
  me: string;
  fhOnRight: boolean;
  frame: { coach_bands: Band[] };
  title: string;
  bodyAt?: { x: number; y: number }; // half-court frame; where the body circle is drawn
}) {
  const uid = useId();
  const v = viewBox("full");
  const bottom = sideLabelsFor("player", me, fhOnRight);
  const top = sideLabelsFor("opponent", me, fhOnRight);
  const shown = items.slice(0, 3);
  const offsets: Record<string, number> = {};

  return (
    <figure className="mx-auto w-full max-w-[560px]">
      <svg viewBox={v.vb} role="img" aria-labelledby={`${uid}-t`} className="h-auto w-full select-none">
        <title id={`${uid}-t`}>{title}</title>
        <CourtLines view="full" />
        <SideLabels half="opponent" left={top.left} right={top.right} />
        <SideLabels half="player" left={bottom.left} right={bottom.right} />
        <text x={px(HALF_W)} y={py(0) - 42} textAnchor="middle" fontSize="15" fill="var(--court-white)" aria-hidden="true">
          where {me}&apos;s shots land
        </text>
        <text x={px(0)} y={py(NET) - 28} fontSize="15" fill="var(--court-white)" aria-hidden="true">
          {me}&apos;s half: shots {me} receives
        </text>
        {shown.map((it) => {
          const half: Half = it.role === "faced" ? "player" : "opponent";
          const fill = it.kind === "strong" ? "var(--zone-strong)" : "var(--zone-weak)";
          const words = it.kind === "strong" ? `${me} wins more` : `${me} loses more`;
          const rect = it.zone && it.zone !== "body" ? zoneRects(frame.coach_bands, half, fhOnRight).find((z) => z.zone === it.zone) : undefined;
          let c = zoneCentre(it.zone ?? null, frame.coach_bands, half, fhOnRight);
          if (it.zone === "body" && bodyAt && half === "player") c = toFull(bodyAt.x, bodyAt.y, "player");
          if (!it.zone) {
            // shot-only insight: a badge near the net on the relevant half, stacked if several
            const key = half;
            const k = offsets[key] ?? 0;
            offsets[key] = k + 1;
            c = { X: HALF_W - 1.6 + k * 1.6, Y: half === "player" ? NET + 1.0 : NET - 1.0 };
          }
          const label = `${it.n}. ${it.zone ? areaShort(it.zone) : shotWords(it.shot ?? null)}: ${words}`;
          return (
            <g key={it.n} role="img" aria-label={label}>
              {rect && (
                <rect x={px(rect.x) + 4} y={py(rect.y) + 4} width={rect.w * S - 8} height={rect.h * S - 8} rx={6} fill={fill} fillOpacity="0.9" />
              )}
              {it.zone === "body" && <circle cx={px(c.X)} cy={py(c.Y)} r={0.5 * S} fill={fill} fillOpacity="0.9" stroke="var(--court-white)" strokeWidth="3" />}
              {!it.zone && (
                <rect x={px(c.X) - 70} y={py(c.Y) - 24} width={140} height={48} rx={8} fill={fill} fillOpacity="0.9" />
              )}
              <circle cx={px(c.X) - (it.zone ? 0 : 46)} cy={py(c.Y)} r={20} fill="#ffffff" stroke="var(--stroke-outline)" strokeWidth="2" />
              <text x={px(c.X) - (it.zone ? 0 : 46)} y={py(c.Y) + 8} textAnchor="middle" fontSize="22" fontWeight="700" fill="#0b0b0b">
                {it.n}
              </text>
              {!it.zone && (
                <text x={px(c.X) + 4} y={py(c.Y) + 6} textAnchor="middle" fontSize="15" fontWeight="600" fill="var(--zone-ink)">
                  {shotWords(it.shot ?? null)}
                </text>
              )}
              {rect && (
                <text x={px(rect.x + rect.w / 2)} y={py(Math.min(rect.y + rect.h / 2 + 0.42, L - 1.0))} textAnchor="middle" fontSize="15" fill="var(--zone-ink)">
                  {words}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
