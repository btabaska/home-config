import { Hono } from "hono";
import { db } from "../db.ts";
import { requireUser, userFromRequest } from "../auth.ts";
import { uuid, now, dropSlug } from "../ids.ts";
import { emit } from "../events.ts";
import { publicUser, partnerOf } from "../users.ts";
import { config } from "../config.ts";
import { createHash } from "node:crypto";

export const dropRoutes = new Hono();

interface DropRow {
  id: number;
  slug: string;
  sender_id: string;
  recipient_id: string | null;
  caption: string | null;
  source: string;
  created_at: number;
  first_opened_at: number | null;
  completed_at: number | null;
}

// ── list (inbox) ─────────────────────────────────────────────────────────────
dropRoutes.get("/", requireUser, (c) => {
  const user = c.get("user") as { id: string };
  const filter = c.req.query("filter") ?? "all";
  const rows = db
    .prepare("SELECT * FROM drops ORDER BY created_at DESC")
    .all() as DropRow[];

  const list = rows
    .map((d) => summarizeForList(d, user.id))
    .filter((d) => {
      if (filter === "awaiting-me") return d.awaiting === "me";
      if (filter === "awaiting-them") return d.awaiting === "them";
      if (filter === "closed") return d.status === "reviewed";
      return true;
    });
  return c.json({ drops: list });
});

// ── create ───────────────────────────────────────────────────────────────────
dropRoutes.post("/", requireUser, async (c) => {
  const user = c.get("user") as { id: string };
  const body = await c.req.json().catch(() => ({}));
  const { source, caption, recipientId, items } = body as {
    source?: string;
    caption?: string;
    recipientId?: string | null;
    items?: Array<{ immichAssetId?: string; uploadId?: string; contentHash?: string; filename?: string; width?: number; height?: number }>;
  };
  if (source !== "immich" && source !== "upload")
    return c.json({ error: "source must be 'immich' or 'upload'" }, 400);
  if (!Array.isArray(items) || items.length === 0)
    return c.json({ error: "at least one item required" }, 400);
  if (items.length > 200) return c.json({ error: "max 200 images per drop" }, 400);

  const recipient = recipientId ?? partnerOf(user.id)?.id ?? null;

  const insertDrop = db.prepare(
    "INSERT INTO drops (slug, sender_id, recipient_id, caption, source, created_at) VALUES (?, ?, ?, ?, ?, ?)",
  );
  const insertImage = db.prepare(
    "INSERT INTO images (id, drop_id, position, immich_asset_id, file_path, content_hash, filename, width, height, taken_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
  );

  const tx = db.prepare("BEGIN");
  const commit = db.prepare("COMMIT");
  const rollback = db.prepare("ROLLBACK");
  tx.run();
  let dropId: number;
  try {
    // temp slug, corrected after we know the id
    const res = insertDrop.run("pending", user.id, recipient, caption ?? null, source, now());
    dropId = Number(res.lastInsertRowid);
    const slug = dropSlug(dropId);
    db.prepare("UPDATE drops SET slug = ? WHERE id = ?").run(slug, dropId);

    items.forEach((item, position) => {
      const hash =
        item.contentHash ||
        createHash("sha256")
          .update(item.immichAssetId ?? item.uploadId ?? `${dropId}:${position}`)
          .digest("hex");
      insertImage.run(
        uuid(),
        dropId,
        position,
        item.immichAssetId ?? null,
        item.uploadId ?? null,
        hash,
        item.filename ?? null,
        item.width ?? null,
        item.height ?? null,
        null,
      );
    });
    commit.run();
  } catch (err) {
    rollback.run();
    return c.json({ error: err instanceof Error ? err.message : "create failed" }, 500);
  }

  const drop = db.prepare("SELECT * FROM drops WHERE id = ?").get(dropId) as DropRow;
  // emit AFTER commit so achievement rules see the persisted images
  emit({ type: "drop.created", actorId: user.id, dropId, payload: { count: items.length } });

  // boomerangs detected at compose time (same-user resends)
  const boomerangs = db
    .prepare(
      `SELECT i.id AS imageId, i.filename AS filename, MIN(prev.drop_id) AS previousDropId
       FROM images i
       JOIN images prev ON prev.content_hash = i.content_hash
       JOIN drops pd ON pd.id = prev.drop_id
       WHERE i.drop_id = ? AND pd.sender_id = ? AND pd.id < ?
       GROUP BY i.id`,
    )
    .all(dropId, user.id, dropId);

  return c.json(
    {
      id: drop.id,
      slug: drop.slug,
      url: `${config.isProd ? "" : ""}/d/${drop.slug}`,
      boomerangs,
    },
    201,
  );
});

// ── read one (full payload) ──────────────────────────────────────────────────
dropRoutes.get("/:slug", (c) => {
  const viewer = userFromRequest(c);
  const drop = db.prepare("SELECT * FROM drops WHERE slug = ?").get(c.req.param("slug")) as
    | DropRow
    | undefined;
  if (!drop) return c.json({ error: "not found" }, 404);

  // guest links: read-only unless GUEST_REACTIONS=guests
  if (!viewer && drop.recipient_id && config.guestReactions !== "guests") {
    // still allow reading a specific recipient's drop by link
  }

  const images = db
    .prepare("SELECT * FROM images WHERE drop_id = ? ORDER BY position ASC")
    .all(drop.id) as any[];
  const imageIds = images.map((i) => i.id);

  const reactions = imageIds.length
    ? (db
        .prepare(
          `SELECT * FROM reactions WHERE image_id IN (${imageIds.map(() => "?").join(",")}) ORDER BY created_at ASC`,
        )
        .all(...imageIds) as any[])
    : [];
  const threadCounts = imageIds.length
    ? (db
        .prepare(
          `SELECT image_id, COUNT(*) AS c FROM messages WHERE image_id IN (${imageIds.map(() => "?").join(",")}) GROUP BY image_id`,
        )
        .all(...imageIds) as { image_id: string; c: number }[])
    : [];
  const threadMap = Object.fromEntries(threadCounts.map((t) => [t.image_id, t.c]));

  const reactionsByImage: Record<string, any[]> = {};
  for (const r of reactions) {
    (reactionsByImage[r.image_id] ??= []).push({
      id: r.id,
      userId: r.user_id,
      by: displayShort(r.user_id, viewer?.id),
      kind: r.kind,
      value: r.value,
      createdAt: r.created_at,
    });
  }

  return c.json({
    drop: {
      id: drop.id,
      slug: drop.slug,
      caption: drop.caption,
      source: drop.source,
      createdAt: drop.created_at,
      firstOpenedAt: drop.first_opened_at,
      completedAt: drop.completed_at,
      sender: publicUser(drop.sender_id) ?? null,
      recipient: drop.recipient_id ? publicUser(drop.recipient_id) ?? null : null,
      title: `Drop #${drop.id}`,
    },
    canReact: canReact(viewer, drop),
    images: images.map((i) => ({
      id: i.id,
      position: i.position,
      filename: i.filename,
      width: i.width,
      height: i.height,
      orphaned: !!i.orphaned,
      thumbUrl: `/api/images/${i.id}/thumb`,
      screenUrl: `/api/images/${i.id}/screen`,
      reactions: reactionsByImage[i.id] ?? [],
      threadCount: threadMap[i.id] ?? 0,
    })),
  });
});

// ── mark opened ──────────────────────────────────────────────────────────────
dropRoutes.post("/:slug/opened", (c) => {
  const viewer = userFromRequest(c);
  const drop = db.prepare("SELECT * FROM drops WHERE slug = ?").get(c.req.param("slug")) as
    | DropRow
    | undefined;
  if (!drop) return c.json({ error: "not found" }, 404);
  if (!drop.first_opened_at) {
    db.prepare("UPDATE drops SET first_opened_at = ? WHERE id = ?").run(now(), drop.id);
    emit({ type: "drop.opened", actorId: viewer?.id ?? drop.recipient_id ?? drop.sender_id, dropId: drop.id });
  }
  return c.json({ ok: true });
});

// ── summary ──────────────────────────────────────────────────────────────────
dropRoutes.get("/:slug/summary", (c) => {
  const drop = db.prepare("SELECT * FROM drops WHERE slug = ?").get(c.req.param("slug")) as
    | DropRow
    | undefined;
  if (!drop) return c.json({ error: "not found" }, 404);

  const imgCount = (
    db.prepare("SELECT COUNT(*) AS c FROM images WHERE drop_id = ?").get(drop.id) as { c: number }
  ).c;
  const reacted = (
    db
      .prepare(
        `SELECT COUNT(DISTINCT i.id) AS c FROM images i JOIN reactions r ON r.image_id = i.id WHERE i.drop_id = ?`,
      )
      .get(drop.id) as { c: number }
  ).c;
  const threads = (
    db
      .prepare(
        `SELECT COUNT(DISTINCT m.image_id) AS c FROM messages m JOIN images i ON i.id = m.image_id WHERE i.drop_id = ?`,
      )
      .get(drop.id) as { c: number }
  ).c;
  const topEmoji = db
    .prepare(
      `SELECT r.value AS value, COUNT(*) AS c FROM reactions r JOIN images i ON i.id = r.image_id
       WHERE i.drop_id = ? AND r.kind = 'emoji' GROUP BY r.value ORDER BY c DESC LIMIT 1`,
    )
    .get(drop.id) as { value: string; c: number } | undefined;

  const unlocked = db
    .prepare(
      `SELECT a.id, a.user_id, a.unlocked_at, a.context_json FROM achievements a
       WHERE a.context_json LIKE ? ORDER BY a.unlocked_at DESC`,
    )
    .all(`%"dropId":${drop.id}%`) as any[];

  const elapsed =
    drop.completed_at && drop.first_opened_at ? drop.completed_at - drop.first_opened_at : null;

  return c.json({
    dropTitle: `Drop #${drop.id}`,
    images: imgCount,
    reacted,
    threads,
    topEmoji: topEmoji ? { value: topEmoji.value, count: topEmoji.c } : null,
    timeToReviewMs: elapsed,
    achievements: unlocked.map((u) => ({
      id: u.id,
      userId: u.user_id,
      context: u.context_json ? JSON.parse(u.context_json) : {},
    })),
  });
});

// ── helpers ──────────────────────────────────────────────────────────────────
function canReact(viewer: { id: string } | null, drop: DropRow): boolean {
  if (viewer) return true;
  return config.guestReactions === "guests";
}

function displayShort(userId: string, viewerId?: string): string {
  if (viewerId && userId === viewerId) return "you";
  const u = publicUser(userId);
  return u ? u.display_name.toLowerCase() : "them";
}

function summarizeForList(d: DropRow, viewerId: string) {
  const count = (
    db.prepare("SELECT COUNT(*) AS c FROM images WHERE drop_id = ?").get(d.id) as { c: number }
  ).c;
  const iAmRecipient = d.recipient_id === viewerId;
  const iAmSender = d.sender_id === viewerId;

  const myReacted = (
    db
      .prepare(
        `SELECT COUNT(DISTINCT i.id) AS c FROM images i JOIN reactions r ON r.image_id = i.id AND r.user_id = ? WHERE i.drop_id = ?`,
      )
      .get(viewerId, d.id) as { c: number }
  ).c;
  const otherId = iAmSender ? d.recipient_id : d.sender_id;
  const otherReacted = otherId
    ? (
        db
          .prepare(
            `SELECT COUNT(DISTINCT i.id) AS c FROM images i JOIN reactions r ON r.image_id = i.id AND r.user_id = ? WHERE i.drop_id = ?`,
          )
          .get(otherId, d.id) as { c: number }
      ).c
    : 0;

  const topEmojis = db
    .prepare(
      `SELECT r.value AS value FROM reactions r JOIN images i ON i.id = r.image_id
       WHERE i.drop_id = ? AND r.kind = 'emoji' GROUP BY r.value ORDER BY COUNT(*) DESC LIMIT 4`,
    )
    .all(d.id) as { value: string }[];

  let status: "new" | "awaiting" | "reviewed" = "new";
  let awaiting: "me" | "them" | null = null;
  if (iAmRecipient && myReacted === 0) {
    status = "new";
    awaiting = "me";
  } else if (iAmSender && otherReacted === 0) {
    status = "awaiting";
    awaiting = "them";
  } else if (myReacted >= count || otherReacted >= count || myReacted + otherReacted > 0) {
    status = "reviewed";
  }

  return {
    id: d.id,
    slug: d.slug,
    title: `Drop #${d.id}`,
    from: iAmSender ? "You" : publicUser(d.sender_id)?.display_name ?? "Someone",
    fromYou: iAmSender,
    count,
    caption: d.caption,
    createdAt: d.created_at,
    status,
    awaiting,
    reviewedCount: iAmRecipient ? myReacted : otherReacted,
    emojis: topEmojis.map((e) => e.value).join(""),
  };
}
