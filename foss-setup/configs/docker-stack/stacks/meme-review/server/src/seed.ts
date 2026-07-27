// Seed demo data so a fresh install is immediately explorable. Idempotent-ish:
// it wipes and rebuilds the demo rows every run. Safe on a throwaway DB.
import { createHash } from "node:crypto";
import { db } from "./db.ts";
import { hashPassword } from "./auth.ts";
import { uuid, dropSlug } from "./ids.ts";
import { emit } from "./events.ts";
import { ACHIEVEMENTS } from "./achievements.ts";

const DAY = 1000 * 60 * 60 * 24;
const nowTs = Date.now();
const hash = (s: string) => createHash("sha256").update(s).digest("hex");
const imgName = (n: number) => "IMG_" + (2050 + n * 37);

console.log("Seeding demo data…");

// wipe demo rows
for (const t of [
  "reactions",
  "messages",
  "images",
  "achievements",
  "events",
  "drops",
  "sessions",
  "stickers",
  "users",
]) {
  db.prepare(`DELETE FROM ${t}`).run();
}

// ── users ────────────────────────────────────────────────────────────────────
const you = uuid();
const sam = uuid();
const insertUser = db.prepare(
  "INSERT INTO users (id, display_name, handle, password_hash, avatar_emoji, is_owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
);
insertUser.run(you, "You", "you", hashPassword("meme"), "🫥", 1, nowTs - 120 * DAY);
insertUser.run(sam, "Sam", "sam", hashPassword("meme"), "🗿", 0, nowTs - 120 * DAY);

const BOOM_HASH = hash("shared-boomerang-meme");

interface SeedDrop {
  sender: string;
  recipient: string;
  count: number;
  daysAgo: number;
  hoursAgo?: number;
  caption?: string;
  boomAt?: number; // position that reuses BOOM_HASH
}

const seeds: SeedDrop[] = [
  { sender: you, recipient: sam, count: 8, daysAgo: 22, caption: "old batch", boomAt: 0 },
  { sender: sam, recipient: you, count: 3, daysAgo: 15, caption: "low effort" },
  { sender: you, recipient: sam, count: 61, daysAgo: 10, caption: "june dump" },
  { sender: you, recipient: sam, count: 112, daysAgo: 6, caption: "MEGA", boomAt: 4 },
  { sender: sam, recipient: you, count: 8, daysAgo: 3, caption: "certified" },
  { sender: sam, recipient: you, count: 24, daysAgo: 0, hoursAgo: 2, caption: "low effort tuesday" },
];

const insertDrop = db.prepare(
  "INSERT INTO drops (slug, sender_id, recipient_id, caption, source, created_at, first_opened_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
);
const insertImage = db.prepare(
  "INSERT INTO images (id, drop_id, position, immich_asset_id, file_path, content_hash, filename, width, height, taken_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
);
const insertReaction = db.prepare(
  "INSERT OR IGNORE INTO reactions (id, image_id, user_id, kind, value, created_at) VALUES (?, ?, ?, ?, ?, ?)",
);
const insertMessage = db.prepare(
  "INSERT INTO messages (id, image_id, user_id, body, created_at) VALUES (?, ?, ?, ?, ?)",
);

const emojis = ["💀", "😂", "❤️", "👍", "👎", "‼️", "🫠", "🔥", "🤡"];
const dropIds: number[] = [];

for (const s of seeds) {
  const created = nowTs - s.daysAgo * DAY - (s.hoursAgo ?? 0) * 3600 * 1000;
  const isTarget = s.daysAgo === 0;
  // the newest (target) drop is unopened; older ones are opened & reviewed
  const firstOpened = isTarget ? null : created + 3600 * 1000;
  const res = insertDrop.run(
    "pending",
    s.sender,
    s.recipient,
    s.caption ?? null,
    "immich",
    created,
    firstOpened,
    null,
  );
  const dropId = Number(res.lastInsertRowid);
  dropIds.push(dropId);
  db.prepare("UPDATE drops SET slug = ? WHERE id = ?").run(dropSlug(dropId), dropId);

  const imageIds: string[] = [];
  for (let p = 0; p < s.count; p++) {
    const id = uuid();
    const contentHash = s.boomAt === p ? BOOM_HASH : hash(`d${dropId}-p${p}`);
    insertImage.run(
      id,
      dropId,
      p,
      `immich-asset-${dropId}-${p}`,
      null,
      contentHash,
      imgName(p) + (p === s.boomAt ? "" : ""),
      1170,
      2532,
      created,
    );
    imageIds.push(id);
  }

  // fire drop.created through the real engine → mega_drop / boomerang unlock
  emit({ type: "drop.created", actorId: s.sender, dropId, payload: { count: s.count } });

  // reviewed drops get reactions from the recipient (+ some from the sender)
  if (!isTarget) {
    const react = (userId: string, density: number, shift: number) => {
      imageIds.forEach((imgId, i) => {
        if (i % density !== 0) return;
        const value = emojis[(i + dropId + shift) % emojis.length];
        insertReaction.run(uuid(), imgId, userId, "emoji", value, created + i * 1000 + 4000);
      });
    };
    react(s.recipient, 1, 0); // recipient reacts to (almost) everything
    // sender sprinkles a few back — mostly agreeing, occasionally not (so emoji
    // compatibility lands somewhere realistic rather than a flat 100%)
    react(s.sender, 2, dropId % 4 === 0 ? 1 : 0);
    // a couple of text threads
    if (imageIds[0]) {
      insertMessage.run(uuid(), imageIds[0], s.sender, "this is you at 7am", created + 5000);
      insertMessage.run(uuid(), imageIds[0], s.recipient, "unwell. deleting.", created + 9000);
    }
    if (imageIds[2]) insertMessage.run(uuid(), imageIds[2], s.recipient, "saved", created + 8000);
  }
}

// ── the target Drop #? gets a partial in-progress review (matches prototype) ──
const target = dropIds[dropIds.length - 1];
const targetImages = db
  .prepare("SELECT id, position FROM images WHERE drop_id = ? ORDER BY position ASC")
  .all(target) as { id: string; position: number }[];
// Sam (sender) pre-seeded a couple of their own reactions + a thread
insertReaction.run(uuid(), targetImages[0].id, sam, "emoji", "😂", nowTs - 3600 * 1000);
insertReaction.run(uuid(), targetImages[2].id, sam, "emoji", "❤️", nowTs - 3500 * 1000);
insertReaction.run(uuid(), targetImages[2].id, sam, "emoji", "‼️", nowTs - 3400 * 1000);
insertMessage.run(uuid(), targetImages[0].id, sam, "this is you at 7am", nowTs - 3300 * 1000);

// ── backfill a daily activity heartbeat for a 14-day streak (prototype: 14) ──
const insertEvent = db.prepare(
  "INSERT INTO events (type, actor_id, drop_id, image_id, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
);
for (let d = 0; d < 14; d++) {
  insertEvent.run("reaction.added", d % 2 ? sam : you, null, null, JSON.stringify({ seed: true }), nowTs - d * DAY - 43200000);
}

// ── directly grant a couple of the harder-to-seed achievements for display ───
const grant = (id: string, userId: string, context: object) =>
  db
    .prepare(
      "INSERT OR IGNORE INTO achievements (id, user_id, unlocked_at, context_json) VALUES (?, ?, ?, ?)",
    )
    .run(id, userId, nowTs - 2 * DAY, JSON.stringify(context));
grant("evergreen", you, { note: "seed", dropCount: 10 });
grant("skull_merchant", you, { emoji: "💀", count: 100 });
grant("novelist", sam, { count: 21 });

const counts = {
  users: 2,
  drops: dropIds.length,
  images: (db.prepare("SELECT COUNT(*) AS c FROM images").get() as { c: number }).c,
  reactions: (db.prepare("SELECT COUNT(*) AS c FROM reactions").get() as { c: number }).c,
  achievements: (db.prepare("SELECT COUNT(*) AS c FROM achievements").get() as { c: number }).c,
};
console.log("Seeded:", counts);
console.log("\nLogin with handle 'you' or 'sam', password 'meme'.");
const targetSlug = (db.prepare("SELECT slug FROM drops WHERE id = ?").get(target) as { slug: string }).slug;
console.log(`Review target: Drop #${target} → /d/${targetSlug}\n`);
