import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import { Hono } from "hono";
import { logger } from "hono/logger";
import fs from "node:fs";
import path from "node:path";
import { config } from "./config.ts";
import { db } from "./db.ts"; // importing also ensures the schema exists on boot
import { userFromRequest, requireUser } from "./auth.ts";
import { partnerOf, allUsers } from "./users.ts";
import { runLeftOnReadSweep } from "./achievements.ts";

import { authRoutes } from "./routes/auth.ts";
import { dropRoutes } from "./routes/drops.ts";
import { imageRoutes } from "./routes/images.ts";
import { uploadRoutes } from "./routes/uploads.ts";
import { stickerRoutes } from "./routes/stickers.ts";
import { gifRoutes } from "./routes/gifs.ts";
import { immichRoutes } from "./routes/immich.ts";
import { achievementRoutes } from "./routes/achievements.ts";
import { insightRoutes } from "./routes/insight.ts";
import { streamRoutes } from "./routes/stream.ts";

const app = new Hono();
if (!config.isProd) app.use("*", logger());

// ── API ──────────────────────────────────────────────────────────────────────
const api = new Hono();

api.get("/health", (c) => c.json({ ok: true, service: "meme-review" }));

api.get("/me", (c) => {
  const user = userFromRequest(c);
  if (!user) return c.json({ user: null, partner: null });
  return c.json({ user, partner: partnerOf(user.id) ?? null });
});

api.get("/users", requireUser, (c) => c.json({ users: allUsers() }));

api.get("/config", (c) => {
  const userCount = (db.prepare("SELECT COUNT(*) AS c FROM users").get() as { c: number }).c;
  return c.json({
    guestReactions: config.guestReactions,
    immichConfigured: !!config.immich.baseUrl,
    needsSetup: userCount === 0,
  });
});

api.route("/auth", authRoutes);
api.route("/drops", dropRoutes);
api.route("/images", imageRoutes);
api.route("/uploads", uploadRoutes);
api.route("/stickers", stickerRoutes);
api.route("/gifs", gifRoutes);
api.route("/immich", immichRoutes);
api.route("/achievements", achievementRoutes);
api.route("/stream", streamRoutes);
api.route("/", insightRoutes); // /stats, /history, /activity

app.route("/api", api);

// ── static SPA ───────────────────────────────────────────────────────────────
const hasBuild = fs.existsSync(path.join(config.distDir, "index.html"));
if (hasBuild) {
  app.use("/*", serveStatic({ root: path.relative(process.cwd(), config.distDir) || "." }));
  // SPA fallback for client-side routes (/d/:slug, /stats, …)
  app.get("*", (c) => {
    const html = fs.readFileSync(path.join(config.distDir, "index.html"), "utf8");
    return c.html(html);
  });
} else {
  app.get("*", (c) =>
    c.text(
      "Meme Review API is running. The web client isn't built yet — run `npm run build` (or `npm run dev` for the Vite dev server on :5173).",
    ),
  );
}

// ── nightly sweep for the one time-based achievement ─────────────────────────
runLeftOnReadSweep();
setInterval(runLeftOnReadSweep, 1000 * 60 * 60); // hourly

serve({ fetch: app.fetch, port: config.port }, (info) => {
  console.log(`\n  Meme Review → http://localhost:${info.port}`);
  console.log(`  API health  → http://localhost:${info.port}/api/health`);
  if (!hasBuild) console.log(`  Web client  → run 'npm run dev' (Vite :5173) or 'npm run build'`);
  console.log("");
});
