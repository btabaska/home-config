import { Hono } from "hono";
import fs from "node:fs/promises";
import path from "node:path";
import { config } from "../config.ts";
import { fileExists } from "../media.ts";

export const gifRoutes = new Hono();

// Self-hosted GIF folder (HANDOFF §4/§9: "proxy a provider OR a local folder").
// Drop .gif/.webp files into data/gifs and they become searchable by filename.
gifRoutes.get("/search", async (c) => {
  const q = (c.req.query("q") ?? "").toLowerCase().trim();
  let entries: string[] = [];
  try {
    entries = (await fs.readdir(config.gifsDir)).filter((f) =>
      /\.(gif|webp|mp4)$/i.test(f),
    );
  } catch {
    entries = [];
  }
  const matches = entries
    .filter((f) => (q ? f.toLowerCase().includes(q) : true))
    .slice(0, 40)
    .map((f) => ({
      id: f,
      name: f.replace(/\.[^.]+$/, ""),
      url: `/api/gifs/file/${encodeURIComponent(f)}`,
    }));
  return c.json({ gifs: matches });
});

gifRoutes.get("/file/:name", async (c) => {
  const name = path.basename(decodeURIComponent(c.req.param("name")));
  const abs = path.join(config.gifsDir, name);
  if (!fileExists(abs)) return c.notFound();
  const buf = await fs.readFile(abs);
  const type = name.endsWith(".webp")
    ? "image/webp"
    : name.endsWith(".mp4")
      ? "video/mp4"
      : "image/gif";
  return new Response(new Uint8Array(buf), {
    headers: { "content-type": type, "cache-control": "public, max-age=86400" },
  });
});
