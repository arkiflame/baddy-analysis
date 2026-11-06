"use client";

import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";
import type { IndexPlayer } from "@/lib/types";
import { int, pct } from "@/lib/format";

/** The search box (front and centre in the home page's navy band when `hero` is given) and the
 *  player grid it filters, which sits on the page below the band. */
export function PlayerSearch({ players, hero }: { players: IndexPlayer[]; hero?: ReactNode }) {
  const [q, setQ] = useState("");
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return needle ? players.filter((p) => p.player.toLowerCase().includes(needle)) : players;
  }, [players, q]);

  return (
    <>
      {hero ? (
        <section aria-labelledby="hero" className="bg-navy text-navy-ink">
          <div className="mx-auto max-w-6xl px-4 pb-10 pt-10 text-center md:pb-14 md:pt-14">
            {hero}
            <div className="mt-6 text-left">
              <SearchBox q={q} setQ={setQ} shown={shown.length} total={players.length} inBand />
            </div>
          </div>
        </section>
      ) : (
        <SearchBox q={q} setQ={setQ} shown={shown.length} total={players.length} />
      )}
      <div className="mx-auto max-w-6xl px-4 pt-8">
        <ul className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Players">
          {shown.map((p) => (
            <li key={p.slug}>
              <Link
                href={`/players/${p.slug}/`}
                className="card-surface group flex h-full items-center justify-between gap-3 p-4 transition-shadow hover:shadow-lg focus-visible:outline-3"
              >
                <span className="min-w-0">
                  <span className="block truncate text-lg font-semibold text-ink group-hover:text-link">{p.player}</span>
                  <span className="block text-sm text-ink-2">
                    {p.handedness}-handed · {p.n_top} {p.n_top === 1 ? "finding" : "findings"}
                    {p.n_tentative > 0 ? ` (${p.n_tentative} early)` : ""}
                  </span>
                </span>
                <span className="flex shrink-0 gap-4 text-right">
                  <span>
                    <span className="display block text-3xl text-ink">{int(p.matches)}</span>
                    <span className="block text-xs text-ink-2">matches</span>
                  </span>
                  <span>
                    <span className="display block text-3xl text-green">{pct(p.win_rate)}</span>
                    <span className="block text-xs text-ink-2">rallies won</span>
                  </span>
                </span>
              </Link>
            </li>
          ))}
          {shown.length === 0 && <li className="text-ink-2">No player matches “{q}”.</li>}
        </ul>
      </div>
    </>
  );
}

function SearchBox({
  q,
  setQ,
  shown,
  total,
  inBand = false,
}: {
  q: string;
  setQ: (v: string) => void;
  shown: number;
  total: number;
  inBand?: boolean;
}) {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-1">
      <label htmlFor="player-search" className={`text-sm font-medium ${inBand ? "text-white/85" : ""}`}>
        Find a player
      </label>
      <input
        id="player-search"
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="e.g. Axelsen"
        autoComplete="off"
        className="h-12 rounded-xl border border-line bg-surface px-4 text-lg text-ink shadow-card placeholder:text-ink-2/70"
      />
      <p className={`text-sm ${inBand ? "text-white/75" : "text-ink-2"}`} aria-live="polite">
        {shown} of {total} players
      </p>
    </div>
  );
}
