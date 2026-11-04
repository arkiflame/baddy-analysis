import type { Metadata } from "next";
import { PlayerView } from "@/components/PlayerView";
import { readIndex, readPlayer } from "@/lib/data";

type Params = { params: Promise<{ slug: string }> };

export const dynamicParams = false;

export async function generateStaticParams() {
  const idx = await readIndex();
  return idx.players.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const data = await readPlayer(slug);
  return {
    title: data.player,
    description: `How to play against ${data.surname}, what ${data.surname} should fix, habits, position maps and the evidence behind each claim.`,
  };
}

export default async function PlayerPage({ params }: Params) {
  const { slug } = await params;
  const data = await readPlayer(slug);
  return <PlayerView data={data} />;
}
