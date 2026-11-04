import { PlayerSearch } from "@/components/PlayerSearch";
import { readIndex } from "@/lib/data";
import { int } from "@/lib/format";

export default async function Home() {
  const idx = await readIndex();
  const d = idx.dataset;
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Players</h1>
        <p className="max-w-3xl text-ink-2">
          Scouting reports for {idx.players.length} professional singles players with at least{" "}
          {idx.settings.min_matches} annotated matches, built from {int(d.matches)} matches and{" "}
          {int(d.strokes)} strokes ({int(d.rallies_known_winner)} rallies with a known winner).
          Every claim compares the player with all other players in the same situation and
          carries its sample size and 95% interval. Generated {idx.generated}.
        </p>
      </div>
      <PlayerSearch players={idx.players} />
    </div>
  );
}
