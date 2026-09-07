import { promises as fs } from "node:fs";
import path from "node:path";

import type { Snapshot, Timeline } from "./types";

export const DATA_DIR = process.env.MACROVOL_DATA_DIR ?? path.join(process.cwd(), "data");

export async function loadSnapshot(): Promise<Snapshot | null> {
  try {
    const raw = await fs.readFile(path.join(DATA_DIR, "latest.json"), "utf8");
    return JSON.parse(raw) as Snapshot;
  } catch {
    return null;
  }
}

export async function loadTimeline(): Promise<Timeline> {
  try {
    const raw = await fs.readFile(path.join(DATA_DIR, "timeline.json"), "utf8");
    return JSON.parse(raw) as Timeline;
  } catch {
    return { dates: [], assets: {} };
  }
}

export async function listHistoryDates(): Promise<string[]> {
  try {
    const files = await fs.readdir(path.join(DATA_DIR, "history"));
    return files
      .filter((f) => f.endsWith(".json"))
      .map((f) => f.replace(/\.json$/, ""))
      .sort();
  } catch {
    return [];
  }
}
