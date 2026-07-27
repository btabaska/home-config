import { Hono } from "hono";
import fs from "node:fs/promises";
import path from "node:path";
import { requireUser, userFromRequest } from "../auth.ts";
import { db } from "../db.ts";
import { config } from "../config.ts";
import { uuid, now } from "../ids.ts";
import { fileExists } from "../media.ts";

export const stickerRoutes = new Hono();

stickerRoutes.get("/", (c) => {
  const rows = db.prepare("SELECT * FROM stickers ORDER BY created_at DESC").all() as any[];
  return c.json({
    stickers: rows.map((s) => ({
      id: s.id,
      name: s.name,
      ownerId: s.owner_id,
      url: `/api/stickers/${s.id}/image`,
    })),
  });
});

stickerRoutes.post("/", requireUser, async (c) => {
  const user = c.get("user") as { id: string };
  const body = await c.req.parseBody();
  const file = body["file"];
  const name = (body["name"] ?? "sticker").toString();
  if (!(file instanceof File)) return c.json({ error: "file required" }, 400);
  const ext = path.extname(file.name) || ".png";
  const stored = `sticker-${uuid()}${ext}`;
  await fs.writeFile(
    path.join(config.uploadsDir, stored),
    Buffer.from(await file.arrayBuffer()),
  );
  const id = uuid();
  db.prepare(
    "INSERT INTO stickers (id, owner_id, name, file_path, created_at) VALUES (?, ?, ?, ?, ?)",
  ).run(id, user.id, name, stored, now());
  return c.json({ id, name, url: `/api/stickers/${id}/image` }, 201);
});

stickerRoutes.get("/:id/image", async (c) => {
  const row = db.prepare("SELECT file_path FROM stickers WHERE id = ?").get(c.req.param("id")) as
    | { file_path: string }
    | undefined;
  if (!row) return c.notFound();
  const abs = path.join(config.uploadsDir, path.basename(row.file_path));
  if (!fileExists(abs)) return c.notFound();
  const buf = await fs.readFile(abs);
  return new Response(new Uint8Array(buf), {
    headers: { "cache-control": "public, max-age=31536000, immutable" },
  });
});
