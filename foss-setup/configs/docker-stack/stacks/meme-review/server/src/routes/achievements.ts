import { Hono } from "hono";
import { db } from "../db.ts";
import { ACHIEVEMENTS } from "../achievements.ts";
import { allUsers, displayName } from "../users.ts";

export const achievementRoutes = new Hono();

// GET /api/achievements — every definition plus who has unlocked it.
achievementRoutes.get("/", (c) => {
  const unlocks = db
    .prepare("SELECT id, user_id, unlocked_at, context_json FROM achievements")
    .all() as any[];
  const byId = new Map<string, any[]>();
  for (const u of unlocks) (byId.get(u.id) ?? byId.set(u.id, []).get(u.id)!).push(u);

  const users = allUsers();
  const list = Object.values(ACHIEVEMENTS).map((def) => {
    const rows = byId.get(def.id) ?? [];
    return {
      ...def,
      unlocked: rows.length > 0,
      unlockedBy: rows.map((r) => ({
        userId: r.user_id,
        name: displayName(r.user_id),
        unlockedAt: r.unlocked_at,
        context: r.context_json ? JSON.parse(r.context_json) : {},
      })),
    };
  });

  return c.json({
    achievements: list,
    users: users.map((u) => ({ id: u.id, name: u.display_name })),
    unlockedCount: list.filter((a) => a.unlocked).length,
    total: list.length,
  });
});
