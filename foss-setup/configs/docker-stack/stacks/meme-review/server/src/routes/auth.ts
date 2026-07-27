import { Hono } from "hono";
import { db } from "../db.ts";
import {
  hashPassword,
  verifyPassword,
  createSession,
  destroySession,
  userFromRequest,
} from "../auth.ts";
import { partnerOf } from "../users.ts";
import { uuid, now } from "../ids.ts";

export const authRoutes = new Hono();

authRoutes.post("/login", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const { handle, password } = body as { handle?: string; password?: string };
  if (!handle || !password) return c.json({ error: "handle and password required" }, 400);

  const user = db
    .prepare("SELECT * FROM users WHERE handle = ?")
    .get(handle.trim().toLowerCase()) as any;
  if (!user || !verifyPassword(password, user.password_hash)) {
    return c.json({ error: "invalid credentials" }, 401);
  }
  createSession(c, user.id);
  return c.json({ ok: true, user: publicShape(user) });
});

authRoutes.post("/logout", (c) => {
  destroySession(c);
  return c.json({ ok: true });
});

// First-run helper: create the very first (owner) account. Disabled once a user exists.
authRoutes.post("/register", async (c) => {
  const existing = (db.prepare("SELECT COUNT(*) AS c FROM users").get() as { c: number }).c;
  const body = await c.req.json().catch(() => ({}));
  const { handle, password, displayName, avatarEmoji } = body as Record<string, string>;
  if (!handle || !password || !displayName)
    return c.json({ error: "handle, password, displayName required" }, 400);
  // Only the first account may self-register; further members are added in Settings.
  if (existing > 0 && !userFromRequest(c)) return c.json({ error: "registration closed" }, 403);

  const id = uuid();
  db.prepare(
    "INSERT INTO users (id, display_name, handle, password_hash, avatar_emoji, is_owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
  ).run(
    id,
    displayName,
    handle.trim().toLowerCase(),
    hashPassword(password),
    avatarEmoji ?? null,
    existing === 0 ? 1 : 0,
    now(),
  );
  if (existing === 0) createSession(c, id);
  return c.json({ ok: true, id });
});

authRoutes.get("/me", (c) => {
  const user = userFromRequest(c);
  if (!user) return c.json({ user: null });
  const partner = partnerOf(user.id) ?? null;
  return c.json({ user, partner });
});

function publicShape(u: any) {
  return {
    id: u.id,
    display_name: u.display_name,
    handle: u.handle,
    avatar_emoji: u.avatar_emoji,
    is_owner: u.is_owner,
  };
}
