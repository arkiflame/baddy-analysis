import { useId } from "react";
import { areaShort, shotWords } from "@/lib/format";
import { type Band, type Half, Board, CourtLines, HALF_W, HalfLabels, NET, Pill, SCALE_WITH_CONTAINER, fromHalf, px, py, zoneCentre } from "./Geometry";
import { BOARD, FONT, SIZES } from "./theme";

export interface HeroItem {
  n: number;
  role: "faced" | "hit";
  zone?: string | null;
  shot?: string | null;
  split?: string | null; // "game3" | "pressure" | null
  kind: "strong" | "weak"; // strong = the thing to avoid, weak = the way to beat the player
}

const SPLIT_WORDS: Record<string, string> = { game3: "deciding game", pressure: "late in a game" };

/** Three or four words for the pill: "1 · clears, deciding game", "✕ · body". */
export function heroLabel(it: HeroItem): string {
  const what = it.shot ? shotWords(it.shot) : it.zone ? areaShort(it.zone) : "";
  const when = it.split ? SPLIT_WORDS[it.split] : "";
  const mark = it.kind === "weak" ? String(it.n) : "✕";
  return `${mark} · ${[what, when].filter(Boolean).join(", ")}`;
}

/**
 * The "In short" board: the number one way to beat the player as a gold numbered badge in the
 * area it is about, and the number one thing to avoid as a slate badge with a cross, each with
 * a short pill label. Faced shots sit on the player's half, the player's own shots on the
 * opponent's half; shot-only items sit near the net on the relevant half.
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
  bodyAt?: { x: number; y: number }; // half-court frame; where the body badge is drawn
}) {
  const uid = useId();
  const shown = items.slice(0, 3);
  const stacked: Record<string, number> = {};
  const placed = shown.map((it) => {
    const half: Half = it.role === "faced" ? "player" : "opponent";
    let c: { X: number; Y: number };
    if (it.zone === "body" && bodyAt && half === "player") c = fromHalf(bodyAt.x, bodyAt.y, "player");
    else if (it.zone) c = zoneCentre(it.zone, frame.coach_bands, half, fhOnRight);
    else {
      const k = stacked[half] ?? 0;
      stacked[half] = k + 1;
      c = { X: half === "player" ? NET - 1.3 : NET + 1.3, Y: HALF_W - 1.4 + k * 1.4 };
    }
    const key = `${half}:${it.zone ?? "shot"}`;
    const dup = stacked[key] ?? 0;
    stacked[key] = dup + 1;
    return { it, c: { X: c.X, Y: c.Y + dup * 0.9 } };
  });
  const legend = `Gold badge: the number one way to beat ${me} · slate ✕: the number one thing to avoid`;

  return (
    <Board uid={uid} title={title} legend={legend}>
      <CourtLines />
      <HalfLabels me={me} />
      {placed.map(({ it, c }) => {
        const gold = it.kind === "weak";
        const r = SIZES.dotR * 1.25;
        const label = heroLabel(it);
        return (
          <g key={it.n} role="img" aria-label={`${label}: ${gold ? "the number one way to beat" : "the number one thing to avoid against"} ${me}`}>
            <g style={SCALE_WITH_CONTAINER}>
              <circle cx={px(c.X)} cy={py(c.Y)} r={r} fill={gold ? BOARD.gold : BOARD.opp} stroke={BOARD.bg} strokeWidth={3} />
              <text
                x={px(c.X)}
                y={py(c.Y) + SIZES.font * 0.36}
                textAnchor="middle"
                fill={gold ? BOARD.goldInk : BOARD.slateInk}
                style={{ fontSize: `${SIZES.font}px`, fontFamily: FONT, fontWeight: 700 }}
              >
                {gold ? it.n : "✕"}
              </text>
            </g>
            <Pill x={px(c.X)} y={py(c.Y) + r + SIZES.fontSmall * 1.15} text={label} gold={gold} />
          </g>
        );
      })}
    </Board>
  );
}
