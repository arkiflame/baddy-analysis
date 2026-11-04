import fs from "node:fs/promises";
import path from "node:path";
import type { IndexFile, PlayerFile } from "./types";

// Read at build time only (static export). The JSON is produced by scripts/export_web.py.
const DATA_DIR = path.join(process.cwd(), "public", "data");

export async function readIndex(): Promise<IndexFile> {
  const text = await fs.readFile(path.join(DATA_DIR, "index.json"), "utf8");
  return JSON.parse(text) as IndexFile;
}

export async function readPlayer(slug: string): Promise<PlayerFile> {
  const text = await fs.readFile(path.join(DATA_DIR, "players", `${slug}.json`), "utf8");
  return JSON.parse(text) as PlayerFile;
}
