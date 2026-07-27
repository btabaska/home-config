import { Hono } from "hono";
import { requireUser } from "../auth.ts";
import {
  status,
  albums,
  albumAssets,
  assetImage,
  getImmichConfig,
  setImmichConfig,
  immichEnabled,
} from "../immich.ts";

export const immichRoutes = new Hono();

immichRoutes.get("/status", async (c) => c.json(await status()));

immichRoutes.get("/config", requireUser, (c) => {
  const cfg = getImmichConfig();
  return c.json({
    baseUrl: cfg.baseUrl,
    // never return the real key
    apiKey: cfg.apiKey ? "••••••••••••••••" : "",
    defaultAlbumId: cfg.defaultAlbumId,
    enabled: immichEnabled(),
  });
});

immichRoutes.post("/config", requireUser, async (c) => {
  const body = await c.req.json().catch(() => ({}));
  setImmichConfig({
    baseUrl: body.baseUrl,
    apiKey: body.apiKey,
    defaultAlbumId: body.defaultAlbumId,
  });
  return c.json({ ok: true, status: await status() });
});

immichRoutes.get("/albums", requireUser, async (c) => {
  if (!immichEnabled()) return c.json({ error: "immich not connected", albums: [] }, 200);
  try {
    return c.json({ albums: await albums() });
  } catch (err) {
    return c.json({ error: err instanceof Error ? err.message : "failed", albums: [] }, 502);
  }
});

immichRoutes.get("/albums/:id/assets", requireUser, async (c) => {
  if (!immichEnabled()) return c.json({ error: "immich not connected", assets: [] }, 200);
  try {
    return c.json({ assets: await albumAssets(c.req.param("id")!) });
  } catch (err) {
    return c.json({ error: err instanceof Error ? err.message : "failed", assets: [] }, 502);
  }
});

// Thumbnail proxy — keeps the API key on the server (HANDOFF §5).
immichRoutes.get("/assets/:id/thumbnail", async (c) => {
  try {
    const res = await assetImage(c.req.param("id"), "thumbnail", "preview");
    if (!res.ok) return c.body(null, 502);
    return new Response(res.body, {
      headers: {
        "content-type": res.headers.get("content-type") ?? "image/jpeg",
        "cache-control": "public, max-age=86400",
      },
    });
  } catch {
    return c.body(null, 502);
  }
});
