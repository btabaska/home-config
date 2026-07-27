import { db } from "./db.ts";
import { now } from "./ids.ts";
import { runAchievements } from "./achievements.ts";

export type EventType =
  | "drop.created"
  | "drop.opened"
  | "drop.completed"
  | "reaction.added"
  | "reaction.removed"
  | "message.added"
  | "achievement.unlocked";

export interface AppEvent {
  id: number;
  type: EventType;
  actor_id: string;
  drop_id: number | null;
  image_id: string | null;
  payload_json: string | null;
  created_at: number;
}

export interface EmitInput {
  type: EventType;
  actorId: string;
  dropId?: number | null;
  imageId?: string | null;
  payload?: Record<string, unknown>;
}

// ── SSE fan-out ──────────────────────────────────────────────────────────────
type Subscriber = (event: AppEvent) => void;
const subscribers = new Set<Subscriber>();

export function subscribe(fn: Subscriber): () => void {
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}

export function broadcast(event: AppEvent): void {
  for (const fn of subscribers) {
    try {
      fn(event);
    } catch {
      /* a dead writer shouldn't take down the others */
    }
  }
}

// ── event insert (the achievement engine's input stream) ─────────────────────
export function insertRawEvent(input: EmitInput): AppEvent {
  const created = now();
  const res = db
    .prepare(
      "INSERT INTO events (type, actor_id, drop_id, image_id, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
    )
    .run(
      input.type,
      input.actorId,
      input.dropId ?? null,
      input.imageId ?? null,
      input.payload ? JSON.stringify(input.payload) : null,
      created,
    );
  return {
    id: Number(res.lastInsertRowid),
    type: input.type,
    actor_id: input.actorId,
    drop_id: input.dropId ?? null,
    image_id: input.imageId ?? null,
    payload_json: input.payload ? JSON.stringify(input.payload) : null,
    created_at: created,
  };
}

// Insert an event, broadcast it over SSE, then evaluate achievements against it.
// Achievement unlocks emit their own achievement.unlocked events (not re-evaluated).
export function emit(input: EmitInput): AppEvent {
  const event = insertRawEvent(input);
  broadcast(event);
  if (event.type !== "achievement.unlocked") {
    runAchievements(event);
  }
  return event;
}
