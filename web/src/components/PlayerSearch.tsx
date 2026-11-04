"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { IndexPlayer } from "@/lib/types";
import { int, pct, pctCi } from "@/lib/format";

export function PlayerSearch({ players }: { players: IndexPlayer[] }) {
  const [q, setQ] = useState("");
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return needle ? players.filter((p) => p.player.toLowerCase().includes(needle)) : players;
  }, [players, q]);

  return (
    <div className="space-y-4">
      <div className="flex max-w-md flex-col gap-1">
        <label htmlFor="player-search" className="text-sm font-medium">
          Search players
        </label>
        <input
          id="player-search"
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. Axelsen"
          autoComplete="off"
          className="rounded border border-line bg-surface px-3 py-2"
        />
        <p className="text-sm text-ink-2" aria-live="polite">
          {shown.length} of {players.length} players
        </p>
      </div>
      <div className="overflow-x-auto rounded border border-line bg-surface">
        <table className="tbl">
          <caption className="sr-only">
            Players with coverage: matches, rallies, rally win rate with 95% interval, racket hand,
            number of top insights
          </caption>
          <thead>
            <tr>
              <th scope="col">Player</th>
              <th scope="col" className="num">
                Matches
              </th>
              <th scope="col" className="num">
                Rallies
              </th>
              <th scope="col" className="num">
                Win rate (95% CI)
              </th>
              <th scope="col">Hand</th>
              <th scope="col" className="num">
                Top insights
              </th>
            </tr>
          </thead>
          <tbody>
            {shown.map((p) => (
              <tr key={p.slug}>
                <th scope="row" className="font-medium">
                  <Link href={`/players/${p.slug}/`} className="text-accent underline">
                    {p.player}
                  </Link>
                </th>
                <td className="num">{int(p.matches)}</td>
                <td className="num">{int(p.rallies)}</td>
                <td className="num">
                  {pct(p.win_rate, 1)}{" "}
                  <span className="text-ink-2">({pctCi(p.win_lo, p.win_hi)})</span>
                </td>
                <td>{p.handedness}</td>
                <td className="num">
                  {p.n_top}
                  {p.n_tentative > 0 && (
                    <span className="text-ink-2"> ({p.n_tentative} tentative)</span>
                  )}
                </td>
              </tr>
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan={6} className="text-ink-2">
                  No player matches “{q}”.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
