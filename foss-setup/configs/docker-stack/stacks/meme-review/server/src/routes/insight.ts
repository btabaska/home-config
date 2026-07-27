import { Hono } from "hono";
import { db } from "../db.ts";
import { allUsers, publicUser, displayName } from "../users.ts";

export const insightRoutes = new Hono();

// ── /api/stats ───────────────────────────────────────────────────────────────
insightRoutes.get("/stats", (c) => {
  const drops = (db.prepare("SELECT COUNT(*) AS c FROM drops").get() as { c: number }).c;
  const images = (db.prepare("SELECT COUNT(*) AS c FROM images").get() as { c: number }).c;
  const streak = dayStreak();

  const topReactions = db
    .prepare(
      "SELECT value, COUNT(*) AS c FROM reactions WHERE kind = 'emoji' GROUP BY value ORDER BY c DESC LIMIT 6",
    )
    .all() as { value: string; c: number }[];

  const users = allUsers();
  const perUser = users.map((u) => {
    const top = db
      .prepare(
        "SELECT value, COUNT(*) AS c FROM reactions WHERE user_id = ? AND kind = 'emoji' GROUP BY value ORDER BY c DESC LIMIT 1",
      )
      .get(u.id) as { value: string; c: number } | undefined;
    return { userId: u.id, name: u.display_name, emoji: top?.value ?? null, count: top?.c ?? 0 };
  });

  const compatibility = emojiCompatibility(users.map((u) => u.id));
  const topImage = mostReactedImage();

  return c.json({
    drops,
    images,
    streak,
    topReactions,
    perUser,
    compatibility,
    topImage,
  });
});

// ── /api/history?groupBy=month ───────────────────────────────────────────────
insightRoutes.get("/history", (c) => {
  const rows = db
    .prepare(
      `SELECT d.id, d.slug, d.sender_id, d.caption, d.created_at,
              (SELECT COUNT(*) FROM images i WHERE i.drop_id = d.id) AS imageCount,
              (SELECT COUNT(*) FROM reactions r JOIN images i ON i.id = r.image_id WHERE i.drop_id = d.id) AS reactionCount,
              (SELECT COUNT(DISTINCT m.image_id) FROM messages m JOIN images i ON i.id = m.image_id WHERE i.drop_id = d.id) AS threadCount
       FROM drops d ORDER BY d.created_at DESC`,
    )
    .all() as any[];

  const groups = new Map<string, any[]>();
  for (const d of rows) {
    const label = new Date(d.created_at)
      .toLocaleDateString("en-US", { month: "long", year: "numeric" })
      .toUpperCase();
    const emojis = (
      db
        .prepare(
          `SELECT r.value AS value FROM reactions r JOIN images i ON i.id = r.image_id
           WHERE i.drop_id = ? AND r.kind = 'emoji' GROUP BY r.value ORDER BY COUNT(*) DESC LIMIT 3`,
        )
        .all(d.id) as { value: string }[]
    )
      .map((e) => e.value)
      .join("");
    const meta =
      `${d.imageCount} image${d.imageCount === 1 ? "" : "s"} · ${d.reactionCount} reactions` +
      (d.threadCount ? ` · ${d.threadCount} threads` : "");
    (groups.get(label) ?? groups.set(label, []).get(label)!).push({
      id: d.id,
      slug: d.slug,
      title: `Drop #${d.id}`,
      from: displayName(d.sender_id),
      meta,
      emojis,
    });
  }

  return c.json({
    months: [...groups.entries()].map(([label, rows]) => ({ label, rows })),
    totals: {
      drops: rows.length,
      images: rows.reduce((s, d) => s + d.imageCount, 0),
      since: rows.length ? rows[rows.length - 1].created_at : null,
    },
  });
});

// ── /api/activity ────────────────────────────────────────────────────────────
insightRoutes.get("/activity", (c) => {
  const rows = db
    .prepare(
      `SELECT * FROM events
       WHERE type NOT IN ('reaction.removed')
         AND (payload_json IS NULL OR payload_json NOT LIKE '%"seed":true%')
       ORDER BY created_at DESC LIMIT 40`,
    )
    .all() as any[];
  return c.json({ activity: rows.map(formatEvent) });
});

// ── helpers ──────────────────────────────────────────────────────────────────
function dayStreak(): number {
  const days = (
    db
      .prepare(
        "SELECT DISTINCT date(created_at / 1000, 'unixepoch', 'localtime') AS d FROM events ORDER BY d DESC",
      )
      .all() as { d: string }[]
  ).map((r) => r.d);
  if (days.length === 0) return 0;
  const today = new Date().toLocaleDateString("en-CA"); // YYYY-MM-DD
  let streak = 0;
  let cursor = new Date(today + "T00:00:00");
  const set = new Set(days);
  // allow the streak to count even if nothing happened yet *today* but did yesterday
  if (!set.has(fmt(cursor))) cursor.setDate(cursor.getDate() - 1);
  while (set.has(fmt(cursor))) {
    streak++;
    cursor.setDate(cursor.getDate() - 1);
  }
  return streak;
}

function fmt(d: Date): string {
  return d.toLocaleDateString("en-CA");
}

function emojiCompatibility(userIds: string[]): { pct: number; sampled: number } {
  if (userIds.length < 2) return { pct: 0, sampled: 0 };
  const [a, b] = userIds;
  const rows = db
    .prepare(
      `SELECT image_id, user_id, value, MIN(created_at) AS t
       FROM reactions WHERE kind = 'emoji' AND user_id IN (?, ?)
       GROUP BY image_id, user_id`,
    )
    .all(a, b) as { image_id: string; user_id: string; value: string }[];
  const byImage = new Map<string, { [uid: string]: string }>();
  for (const r of rows) {
    const e = byImage.get(r.image_id) ?? {};
    e[r.user_id] = r.value;
    byImage.set(r.image_id, e);
  }
  let both = 0;
  let match = 0;
  for (const e of byImage.values()) {
    if (e[a] && e[b]) {
      both++;
      if (e[a] === e[b]) match++;
    }
  }
  return { pct: both ? Math.round((match / both) * 100) : 0, sampled: both };
}

function mostReactedImage() {
  const top = db
    .prepare(
      "SELECT image_id, COUNT(*) AS c FROM reactions GROUP BY image_id ORDER BY c DESC LIMIT 1",
    )
    .get() as { image_id: string; c: number } | undefined;
  if (!top) return null;
  const img = db.prepare("SELECT * FROM images WHERE id = ?").get(top.image_id) as any;
  if (!img) return null;
  const emojis = (
    db
      .prepare(
        "SELECT value FROM reactions WHERE image_id = ? AND kind = 'emoji' ORDER BY created_at ASC",
      )
      .all(top.image_id) as { value: string }[]
  )
    .map((e) => e.value)
    .join("");
  const threadCount = (
    db.prepare("SELECT COUNT(*) AS c FROM messages WHERE image_id = ?").get(top.image_id) as {
      c: number;
    }
  ).c;
  return {
    imageId: img.id,
    filename: img.filename,
    dropId: img.drop_id,
    reactionCount: top.c,
    threadCount,
    emojis,
    thumbUrl: `/api/images/${img.id}/thumb`,
  };
}

function formatEvent(e: any) {
  const actor = displayName(e.actor_id);
  const payload = e.payload_json ? JSON.parse(e.payload_json) : {};
  const when = relative(e.created_at);
  switch (e.type) {
    case "drop.created":
      return { icon: "🆕", text: `${actor} sent Drop #${e.drop_id} — ${payload.count ?? "?"} images`, when };
    case "drop.opened":
      return { icon: "👀", text: `${actor} opened Drop #${e.drop_id}`, when };
    case "drop.completed":
      return { icon: "✅", text: `${actor} finished reviewing Drop #${e.drop_id}`, when };
    case "reaction.added":
      return { icon: payload.value ?? "💬", text: `${actor} reacted ${payload.value ?? ""} on an image`, when };
    case "message.added":
      return { icon: "💬", text: `${actor} replied on an image`, when };
    case "achievement.unlocked":
      return { icon: "🏆", text: `${actor} unlocked ${payload.name ?? "an achievement"}`, when };
    default:
      return { icon: "•", text: `${actor} — ${e.type}`, when };
  }
}

function relative(ts: number): string {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d === 1) return "Yesterday";
  if (d < 7) return `${d}d ago`;
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
