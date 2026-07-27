import { db } from "./db.ts";
import { now } from "./ids.ts";
import { insertRawEvent, broadcast, type AppEvent } from "./events.ts";

export interface AchievementDef {
  id: string;
  name: string;
  icon: string; // phosphor class, e.g. "ph ph-boomerang"
  description: string;
}

// Definitions live in code; unlocks live in the DB (HANDOFF §6).
export const ACHIEVEMENTS: Record<string, AchievementDef> = {
  boomerang: {
    id: "boomerang",
    name: "Boomerang",
    icon: "ph ph-boomerang",
    description: "Resent an image that appeared in an earlier drop.",
  },
  mega_drop: {
    id: "mega_drop",
    name: "Mega Meme Drop",
    icon: "ph ph-stack-plus",
    description: "Sent a drop of more than 100 images.",
  },
  evergreen: {
    id: "evergreen",
    name: "Evergreen",
    icon: "ph ph-tree",
    description: "Sent the same meme across 10 different drops.",
  },
  left_on_read: {
    id: "left_on_read",
    name: "Left on Read",
    icon: "ph ph-eye-slash",
    description: "Opened a drop and reacted to nothing for 48 hours.",
  },
  skull_merchant: {
    id: "skull_merchant",
    name: "Skull Merchant",
    icon: "ph ph-skull",
    description: "Used one emoji 100 times in a single week.",
  },
  novelist: {
    id: "novelist",
    name: "Novelist",
    icon: "ph ph-note-pencil",
    description: "A single image thread passed 20 messages.",
  },
  same_brain: {
    id: "same_brain",
    name: "Same Brain",
    icon: "ph ph-brain",
    description: "Both picked the identical reaction on 20 images in a row.",
  },
  speedrun: {
    id: "speedrun",
    name: "Speedrun",
    icon: "ph ph-timer",
    description: "Reviewed 100 images in under 3 minutes.",
  },
};

const DAY = 1000 * 60 * 60 * 24;

function unlock(achId: string, userId: string, context: Record<string, unknown>): void {
  const res = db
    .prepare(
      "INSERT OR IGNORE INTO achievements (id, user_id, unlocked_at, context_json) VALUES (?, ?, ?, ?)",
    )
    .run(achId, userId, now(), JSON.stringify(context));
  if (res.changes > 0) {
    const def = ACHIEVEMENTS[achId];
    const ev = insertRawEvent({
      type: "achievement.unlocked",
      actorId: userId,
      dropId: (context.dropId as number) ?? null,
      payload: {
        achievementId: achId,
        name: def.name,
        icon: def.icon,
        description: def.description,
        context,
      },
    });
    broadcast(ev);
  }
}

interface DropRow {
  id: number;
  sender_id: string;
  recipient_id: string | null;
  first_opened_at: number | null;
  completed_at: number | null;
}

function getDrop(id: number): DropRow | undefined {
  return db
    .prepare(
      "SELECT id, sender_id, recipient_id, first_opened_at, completed_at FROM drops WHERE id = ?",
    )
    .get(id) as DropRow | undefined;
}

// ── rules ────────────────────────────────────────────────────────────────────

function onDropCreated(dropId: number): void {
  const drop = getDrop(dropId);
  if (!drop) return;

  // mega_drop
  const count = (
    db.prepare("SELECT COUNT(*) AS c FROM images WHERE drop_id = ?").get(dropId) as {
      c: number;
    }
  ).c;
  if (count > 100) unlock("mega_drop", drop.sender_id, { dropId, count });

  // boomerang — a hash in this drop already sent by the same user in an earlier drop
  const boom = db
    .prepare(
      `SELECT i.filename AS filename, i.content_hash AS hash, prev.drop_id AS prevDrop
       FROM images i
       JOIN images prev ON prev.content_hash = i.content_hash
       JOIN drops pd ON pd.id = prev.drop_id
       WHERE i.drop_id = ? AND pd.sender_id = ? AND pd.id < ?
       ORDER BY pd.id ASC LIMIT 1`,
    )
    .get(dropId, drop.sender_id, dropId) as
    | { filename: string | null; hash: string; prevDrop: number }
    | undefined;
  if (boom) {
    unlock("boomerang", drop.sender_id, {
      dropId,
      filename: boom.filename,
      previousDropId: boom.prevDrop,
    });
  }

  // evergreen — a single hash now appears in >= 10 distinct drops
  const ever = db
    .prepare(
      `SELECT content_hash AS hash, COUNT(DISTINCT drop_id) AS c
       FROM images
       WHERE content_hash IN (SELECT content_hash FROM images WHERE drop_id = ?)
       GROUP BY content_hash HAVING c >= 10 ORDER BY c DESC LIMIT 1`,
    )
    .get(dropId) as { hash: string; c: number } | undefined;
  if (ever) unlock("evergreen", drop.sender_id, { dropId, hash: ever.hash, dropCount: ever.c });
}

function onReactionAdded(event: AppEvent): void {
  const payload = event.payload_json ? JSON.parse(event.payload_json) : {};
  // skull_merchant — same emoji 100x by this user in a rolling 7 days
  if (payload.kind === "emoji" && payload.value) {
    const since = now() - 7 * DAY;
    const c = (
      db
        .prepare(
          "SELECT COUNT(*) AS c FROM reactions WHERE user_id = ? AND kind = 'emoji' AND value = ? AND created_at >= ?",
        )
        .get(event.actor_id, payload.value, since) as { c: number }
    ).c;
    if (c >= 100) unlock("skull_merchant", event.actor_id, { emoji: payload.value, count: c });
  }

  // same_brain — 20 consecutive images where both members' first reaction is identical
  if (event.drop_id != null) checkSameBrain(event.drop_id);
}

function checkSameBrain(dropId: number): void {
  const drop = getDrop(dropId);
  if (!drop || !drop.recipient_id || drop.recipient_id === drop.sender_id) return;
  const a = drop.sender_id;
  const b = drop.recipient_id;

  const images = db
    .prepare("SELECT id, position FROM images WHERE drop_id = ? ORDER BY position ASC")
    .all(dropId) as { id: string; position: number }[];

  const firstReaction = db.prepare(
    "SELECT value FROM reactions WHERE image_id = ? AND user_id = ? ORDER BY created_at ASC LIMIT 1",
  );

  let run = 0;
  for (const img of images) {
    const ra = firstReaction.get(img.id, a) as { value: string } | undefined;
    const rb = firstReaction.get(img.id, b) as { value: string } | undefined;
    if (ra && rb && ra.value === rb.value) {
      run++;
      if (run >= 20) {
        unlock("same_brain", a, { dropId, run });
        unlock("same_brain", b, { dropId, run });
        return;
      }
    } else {
      run = 0;
    }
  }
}

function onMessageAdded(event: AppEvent): void {
  if (!event.image_id) return;
  const c = (
    db
      .prepare("SELECT COUNT(*) AS c FROM messages WHERE image_id = ?")
      .get(event.image_id) as { c: number }
  ).c;
  if (c > 20) unlock("novelist", event.actor_id, { imageId: event.image_id, count: c });
}

function onDropCompleted(event: AppEvent): void {
  if (event.drop_id == null) return;
  const drop = getDrop(event.drop_id);
  if (!drop || !drop.recipient_id || drop.first_opened_at == null || drop.completed_at == null)
    return;
  const reacted = (
    db
      .prepare(
        `SELECT COUNT(DISTINCT i.id) AS c FROM images i
         JOIN reactions r ON r.image_id = i.id AND r.user_id = ?
         WHERE i.drop_id = ?`,
      )
      .get(drop.recipient_id, event.drop_id) as { c: number }
  ).c;
  const elapsed = drop.completed_at - drop.first_opened_at;
  if (reacted >= 100 && elapsed < 3 * 60 * 1000) {
    unlock("speedrun", drop.recipient_id, { dropId: event.drop_id, reacted, elapsedMs: elapsed });
  }
}

// Dispatch, called by events.emit for every non-achievement event.
export function runAchievements(event: AppEvent): void {
  try {
    switch (event.type) {
      case "drop.created":
        if (event.drop_id != null) onDropCreated(event.drop_id);
        break;
      case "reaction.added":
        onReactionAdded(event);
        break;
      case "message.added":
        onMessageAdded(event);
        break;
      case "drop.completed":
        onDropCompleted(event);
        break;
    }
  } catch (err) {
    console.error("[achievements] evaluation failed", err);
  }
}

// Nightly sweep for the one time-based rule (HANDOFF §6: left_on_read).
export function runLeftOnReadSweep(): void {
  const cutoff = now() - 2 * DAY;
  const drops = db
    .prepare(
      `SELECT id, recipient_id, first_opened_at FROM drops
       WHERE first_opened_at IS NOT NULL AND first_opened_at < ?
         AND completed_at IS NULL AND recipient_id IS NOT NULL`,
    )
    .all(cutoff) as { id: number; recipient_id: string; first_opened_at: number }[];
  for (const d of drops) {
    const reacted = (
      db
        .prepare(
          `SELECT COUNT(*) AS c FROM reactions r
           JOIN images i ON i.id = r.image_id
           WHERE i.drop_id = ? AND r.user_id = ?`,
        )
        .get(d.id, d.recipient_id) as { c: number }
    ).c;
    if (reacted === 0) unlock("left_on_read", d.recipient_id, { dropId: d.id });
  }
}
