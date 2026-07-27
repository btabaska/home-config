import { DatabaseSync } from "node:sqlite";
import fs from "node:fs";
import { config } from "./config.ts";

for (const dir of [config.dataDir, config.uploadsDir, config.cacheDir, config.gifsDir]) {
  fs.mkdirSync(dir, { recursive: true });
}

const raw = new DatabaseSync(config.dbPath);

// Thin facade so prepared statements return `any` — the query result shapes are
// asserted at each call site (`... as SomeRow`) rather than fought with the
// generic `Record<string, SQLOutputValue>` node:sqlite hands back.
interface Stmt {
  get(...params: unknown[]): any;
  all(...params: unknown[]): any[];
  run(...params: unknown[]): { changes: number | bigint; lastInsertRowid: number | bigint };
}
export const db = {
  prepare(sql: string): Stmt {
    return raw.prepare(sql) as unknown as Stmt;
  },
  exec(sql: string): void {
    raw.exec(sql);
  },
};

db.exec(`
  PRAGMA journal_mode = WAL;
  PRAGMA foreign_keys = ON;
  PRAGMA busy_timeout = 5000;
`);

// ── Schema (see HANDOFF.md §3). Idempotent — safe to run on every boot. ──────
db.exec(`
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  handle TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  avatar_emoji TEXT,
  is_owner INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS drops (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  sender_id TEXT NOT NULL REFERENCES users(id),
  recipient_id TEXT REFERENCES users(id),
  caption TEXT,
  source TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  first_opened_at INTEGER,
  completed_at INTEGER
);

CREATE TABLE IF NOT EXISTS images (
  id TEXT PRIMARY KEY,
  drop_id INTEGER NOT NULL REFERENCES drops(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  immich_asset_id TEXT,
  file_path TEXT,
  content_hash TEXT NOT NULL,
  filename TEXT,
  width INTEGER,
  height INTEGER,
  taken_at INTEGER,
  orphaned INTEGER NOT NULL DEFAULT 0,
  UNIQUE (drop_id, position)
);
CREATE INDEX IF NOT EXISTS images_hash ON images(content_hash);
CREATE INDEX IF NOT EXISTS images_drop ON images(drop_id);

CREATE TABLE IF NOT EXISTS reactions (
  id TEXT PRIMARY KEY,
  image_id TEXT NOT NULL REFERENCES images(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id),
  kind TEXT NOT NULL,
  value TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  UNIQUE (image_id, user_id, kind, value)
);
CREATE INDEX IF NOT EXISTS reactions_image ON reactions(image_id);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  image_id TEXT NOT NULL REFERENCES images(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id),
  body TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_image ON messages(image_id);

CREATE TABLE IF NOT EXISTS stickers (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS achievements (
  id TEXT NOT NULL,
  user_id TEXT NOT NULL REFERENCES users(id),
  unlocked_at INTEGER NOT NULL,
  context_json TEXT,
  PRIMARY KEY (id, user_id)
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  drop_id INTEGER,
  image_id TEXT,
  payload_json TEXT,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS events_created ON events(created_at);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
`);

// ── tiny helpers ─────────────────────────────────────────────────────────────
export function getSetting(key: string): string | null {
  const row = db.prepare("SELECT value FROM settings WHERE key = ?").get(key) as
    | { value: string }
    | undefined;
  return row ? row.value : null;
}

export function setSetting(key: string, value: string): void {
  db.prepare(
    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
  ).run(key, value);
}
