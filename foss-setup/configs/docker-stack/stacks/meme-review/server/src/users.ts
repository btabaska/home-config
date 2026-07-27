import { db } from "./db.ts";

export interface PublicUser {
  id: string;
  display_name: string;
  handle: string;
  avatar_emoji: string | null;
  is_owner: number;
}

export function publicUser(id: string): PublicUser | undefined {
  return db
    .prepare(
      "SELECT id, display_name, handle, avatar_emoji, is_owner FROM users WHERE id = ?",
    )
    .get(id) as PublicUser | undefined;
}

export function allUsers(): PublicUser[] {
  return db
    .prepare(
      "SELECT id, display_name, handle, avatar_emoji, is_owner FROM users ORDER BY is_owner DESC, created_at ASC",
    )
    .all() as PublicUser[];
}

// The "other" household member relative to a user — the partner in a 2-person setup.
export function partnerOf(userId: string): PublicUser | undefined {
  return db
    .prepare(
      "SELECT id, display_name, handle, avatar_emoji, is_owner FROM users WHERE id != ? ORDER BY is_owner DESC, created_at ASC LIMIT 1",
    )
    .get(userId) as PublicUser | undefined;
}

export function displayName(id: string | null | undefined): string {
  if (!id) return "Someone";
  const u = publicUser(id);
  return u ? u.display_name : "Someone";
}
