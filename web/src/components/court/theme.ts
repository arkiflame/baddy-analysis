/* The "dark tactics board" tokens (D33). Every court graphic reads its colours and sizes from
   here, and nothing else on the site does. The board is dark in both light and dark site mode. */

export const BOARD = {
  bg: "#0B1220", // the panel
  surface: "#111B2E", // the court inside the lines
  myHalf: "#13213A", // the scouted player's half, slightly lighter
  line: "#2DD4BF", // thin teal court lines
  net: "#F8FAFC", // off-white net
  text: "#94A3B8", // side labels and legends
  gold: "#FBBF24", // the thing that matters
  goldInk: "#0B1220", // dark text on gold
  me: "#E2E8F0", // the scouted player's shots: solid light grey
  opp: "#64748B", // the opponent's shots: dashed slate
  slateInk: "#F8FAFC", // light text on slate
  tealTint: "rgba(45, 212, 191, 0.26)", // "wins more here"
  goldTint: "rgba(251, 191, 36, 0.28)", // "loses more here"
  pill: "rgba(11, 18, 32, 0.88)", // dark pill behind a label on the surface
  radius: 10,
} as const;

/* Stroke widths and dot sizes, in viewBox units. The board is drawn at 100 units per metre and
   shown about 640 px wide, so one unit is about 0.45 px: 2 px on screen is ~4.5 units. */
export const SIZES = {
  lineW: 2.2, // court lines (~1 px on screen)
  netW: 6.6, // net (~3 px)
  shotW: 4.5, // ordinary shot (~2 px)
  keyW: 9, // the key shot (~4 px)
  dotR: 18, // numbered dot (~8 px)
  arrowMin: 4.5, // thinnest habit arrow (~2 px)
  arrowMax: 30,
  font: 28, // ~12 px at normal display size; scaled up in narrow containers by --court-font-scale
  fontSmall: 26,
} as const;

export const FONT = "var(--font-sans), Inter, system-ui, sans-serif";
