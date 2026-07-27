import { Hono } from "hono";
import { streamSSE } from "hono/streaming";
import { subscribe, type AppEvent } from "../events.ts";

export const streamRoutes = new Hono();

// GET /api/stream — server-sent events for reaction/thread/drop/achievement
// activity, so both people watching a drop see reactions land live (HANDOFF §2).
streamRoutes.get("/", (c) =>
  streamSSE(c, async (stream) => {
    let open = true;
    const queue: AppEvent[] = [];
    let notify: (() => void) | null = null;

    const unsubscribe = subscribe((event) => {
      queue.push(event);
      notify?.();
    });

    stream.onAbort(() => {
      open = false;
      unsubscribe();
      notify?.();
    });

    await stream.writeSSE({ event: "hello", data: JSON.stringify({ ok: true }) });

    let ticks = 0;
    while (open) {
      while (queue.length) {
        const event = queue.shift()!;
        await stream.writeSSE({ event: event.type, data: JSON.stringify(event), id: String(event.id) });
      }
      // wake on the next event or every ~15s for a keep-alive comment
      await new Promise<void>((resolve) => {
        notify = resolve;
        setTimeout(resolve, 15000);
      });
      notify = null;
      if (open && queue.length === 0) {
        await stream.writeSSE({ event: "ping", data: String(ticks++) });
      }
    }
    unsubscribe();
  }),
);
