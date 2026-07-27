import { Hono } from "hono";
import { db } from "../db.ts";
import { requireUser } from "../auth.ts";
import { uuid, now } from "../ids.ts";
import { emit } from "../events.ts";
import { publicUser } from "../users.ts";
import { getImage, serveImage } from "../media.ts";

export const imageRoutes = new Hono();

interface DropRow {
  id: number;
  sender_id: string;
  recipient_id: string | null;
  completed_at: number | null;
}

function dropOfImage(imageId: string): DropRow | undefined {
  return db
    .prepare(
      `SELECT d.id, d.sender_id, d.recipient_id, d.completed_at
       FROM drops d JOIN images i ON i.drop_id = d.id WHERE i.id = ?`,
    )
    .get(imageId) as DropRow | undefined;
}

// ── reactions (toggle) ───────────────────────────────────────────────────────
imageRoutes.post("/:id/reactions", requireUser, async (c) => {
  const user = c.get("user") as { id: string };
  const imageId = c.req.param("id")!;
  const image = getImage(imageId);
  if (!image) return c.json({ error: "image not found" }, 404);

  const body = await c.req.json().catch(() => ({}));
  const kind = (body.kind ?? "emoji") as string;
  const value = body.value as string;
  if (!value) return c.json({ error: "value required" }, 400);
  if (!["emoji", "sticker", "gif"].includes(kind)) return c.json({ error: "bad kind" }, 400);

  const existing = db
    .prepare(
      "SELECT id FROM reactions WHERE image_id = ? AND user_id = ? AND kind = ? AND value = ?",
    )
    .get(imageId, user.id, kind, value) as { id: string } | undefined;

  if (existing) {
    db.prepare("DELETE FROM reactions WHERE id = ?").run(existing.id);
    emit({
      type: "reaction.removed",
      actorId: user.id,
      dropId: image.drop_id,
      imageId,
      payload: { kind, value },
    });
    return c.json({ added: false });
  }

  db.prepare(
    "INSERT INTO reactions (id, image_id, user_id, kind, value, created_at) VALUES (?, ?, ?, ?, ?, ?)",
  ).run(uuid(), imageId, user.id, kind, value, now());
  emit({
    type: "reaction.added",
    actorId: user.id,
    dropId: image.drop_id,
    imageId,
    payload: { kind, value },
  });
  maybeComplete(image.drop_id, user.id);
  return c.json({ added: true }, 201);
});

imageRoutes.delete("/:id/reactions/:rid", requireUser, (c) => {
  const user = c.get("user") as { id: string };
  const rid = c.req.param("rid");
  const row = db.prepare("SELECT * FROM reactions WHERE id = ?").get(rid) as any;
  if (!row) return c.json({ error: "not found" }, 404);
  if (row.user_id !== user.id) return c.json({ error: "not yours" }, 403);
  db.prepare("DELETE FROM reactions WHERE id = ?").run(rid);
  emit({
    type: "reaction.removed",
    actorId: user.id,
    dropId: getImage(row.image_id)?.drop_id ?? null,
    imageId: row.image_id,
    payload: { kind: row.kind, value: row.value },
  });
  return c.json({ ok: true });
});

// ── thread messages ──────────────────────────────────────────────────────────
imageRoutes.get("/:id/messages", (c) => {
  const imageId = c.req.param("id");
  const rows = db
    .prepare("SELECT * FROM messages WHERE image_id = ? ORDER BY created_at ASC")
    .all(imageId) as any[];
  return c.json({
    messages: rows.map((m) => ({
      id: m.id,
      userId: m.user_id,
      by: publicUser(m.user_id)?.display_name ?? "Someone",
      body: m.body,
      createdAt: m.created_at,
    })),
  });
});

imageRoutes.post("/:id/messages", requireUser, async (c) => {
  const user = c.get("user") as { id: string };
  const imageId = c.req.param("id")!;
  const image = getImage(imageId);
  if (!image) return c.json({ error: "image not found" }, 404);
  const body = await c.req.json().catch(() => ({}));
  const text = (body.body ?? "").toString().trim();
  if (!text) return c.json({ error: "body required" }, 400);
  const id = uuid();
  const ts = now();
  db.prepare(
    "INSERT INTO messages (id, image_id, user_id, body, created_at) VALUES (?, ?, ?, ?, ?)",
  ).run(id, imageId, user.id, text, ts);
  emit({ type: "message.added", actorId: user.id, dropId: image.drop_id, imageId });
  return c.json(
    { id, userId: user.id, by: publicUser(user.id)?.display_name ?? "You", body: text, createdAt: ts },
    201,
  );
});

// ── media ────────────────────────────────────────────────────────────────────
imageRoutes.get("/:id/thumb", async (c) => serveOr404(c.req.param("id"), "thumb"));
imageRoutes.get("/:id/screen", async (c) => serveOr404(c.req.param("id"), "screen"));
imageRoutes.get("/:id/orig", async (c) => serveOr404(c.req.param("id"), "orig"));

async function serveOr404(id: string, size: "thumb" | "screen" | "orig"): Promise<Response> {
  const image = getImage(id);
  if (!image) return new Response("not found", { status: 404 });
  return serveImage(image, size);
}

// When the recipient has reacted to every image, close the review pass.
function maybeComplete(dropId: number, actorId: string): void {
  const drop = db
    .prepare("SELECT id, recipient_id, completed_at FROM drops WHERE id = ?")
    .get(dropId) as DropRow | undefined;
  if (!drop || drop.completed_at) return;
  const recipient = drop.recipient_id ?? actorId;
  const total = (
    db.prepare("SELECT COUNT(*) AS c FROM images WHERE drop_id = ?").get(dropId) as { c: number }
  ).c;
  const reacted = (
    db
      .prepare(
        `SELECT COUNT(DISTINCT i.id) AS c FROM images i
         JOIN reactions r ON r.image_id = i.id AND r.user_id = ? WHERE i.drop_id = ?`,
      )
      .get(recipient, dropId) as { c: number }
  ).c;
  if (total > 0 && reacted >= total) {
    db.prepare("UPDATE drops SET completed_at = ? WHERE id = ?").run(now(), dropId);
    emit({ type: "drop.completed", actorId: recipient, dropId, payload: { reacted, total } });
  }
}
