import { Hono } from "hono";
import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { requireUser } from "../auth.ts";
import { config } from "../config.ts";
import { uuid } from "../ids.ts";

export const uploadRoutes = new Hono();

// multipart upload of one or more images. Originals are never re-encoded
// (HANDOFF §2). Returns {uploadId, contentHash, filename} per file — the
// uploadId is passed back to POST /api/drops as item.uploadId.
uploadRoutes.post("/", requireUser, async (c) => {
  const body = await c.req.parseBody({ all: true });
  const raw = body["files"] ?? body["file"];
  const files = (Array.isArray(raw) ? raw : [raw]).filter(
    (f): f is File => f instanceof File,
  );
  if (files.length === 0) return c.json({ error: "no files" }, 400);

  const results = [];
  for (const file of files) {
    const buf = Buffer.from(await file.arrayBuffer());
    const contentHash = createHash("sha256").update(buf).digest("hex");
    const ext = path.extname(file.name) || ".bin";
    const stored = `${uuid()}${ext}`;
    await fs.writeFile(path.join(config.uploadsDir, stored), buf);
    results.push({
      uploadId: stored,
      contentHash,
      filename: file.name,
      size: buf.length,
    });
  }
  return c.json({ uploads: results }, 201);
});
