import { scryptSync, randomBytes, timingSafeEqual } from "node:crypto";
import type { Context, Next } from "hono";
import { getCookie, setCookie, deleteCookie } from "hono/cookie";
import { db } from "./db.ts";
import { uuid, now } from "./ids.ts";
import { config } from "./config.ts";

const SESSION_TTL = 1000 * 60 * 60 * 24 * 90; // 90 days — this is a two-person LAN app
const COOKIE = "mr_session";

export interface User {
  id: string;
  display_name: string;
  handle: string;
  avatar_emoji: string | null;
  is_owner: number;
  created_at: number;
}

// scrypt instead of argon2id (HANDOFF §3) to avoid a native dependency; salted,
// timing-safe compare, format: scrypt$<saltHex>$<hashHex>.
export function hashPassword(password: string): string {
  const salt = randomBytes(16);
  const hash = scryptSync(password, salt, 64);
  return `scrypt$${salt.toString("hex")}$${hash.toString("hex")}`;
}

export function verifyPassword(password: string, stored: string): boolean {
  const [scheme, saltHex, hashHex] = stored.split("$");
  if (scheme !== "scrypt" || !saltHex || !hashHex) return false;
  const expected = Buffer.from(hashHex, "hex");
  const actual = scryptSync(password, Buffer.from(saltHex, "hex"), expected.length);
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}

export function createSession(c: Context, userId: string): void {
  const token = uuid() + uuid().replace(/-/g, "");
  const created = now();
  db.prepare(
    "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
  ).run(token, userId, created, created + SESSION_TTL);
  setCookie(c, COOKIE, token, {
    httpOnly: true,
    sameSite: "Lax",
    secure: config.cookieSecure,
    path: "/",
    maxAge: SESSION_TTL / 1000,
  });
}

export function destroySession(c: Context): void {
  const token = getCookie(c, COOKIE);
  if (token) db.prepare("DELETE FROM sessions WHERE token = ?").run(token);
  deleteCookie(c, COOKIE, { path: "/" });
}

export function userFromRequest(c: Context): User | null {
  const token = getCookie(c, COOKIE);
  if (!token) return null;
  const session = db
    .prepare("SELECT user_id, expires_at FROM sessions WHERE token = ?")
    .get(token) as { user_id: string; expires_at: number } | undefined;
  if (!session) return null;
  if (session.expires_at < now()) {
    db.prepare("DELETE FROM sessions WHERE token = ?").run(token);
    return null;
  }
  return (
    (db
      .prepare(
        "SELECT id, display_name, handle, avatar_emoji, is_owner, created_at FROM users WHERE id = ?",
      )
      .get(session.user_id) as User | undefined) ?? null
  );
}

// Guard for routes that require a signed-in member.
export async function requireUser(c: Context, next: Next) {
  const user = userFromRequest(c);
  if (!user) return c.json({ error: "unauthorized" }, 401);
  c.set("user", user);
  await next();
}
