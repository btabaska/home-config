import fs from "node:fs";
import fs_p from "node:fs/promises";
import path from "node:path";
import { db } from "./db.ts";
import { config } from "./config.ts";
import { assetImage } from "./immich.ts";

export interface ImageRow {
  id: string;
  drop_id: number;
  position: number;
  immich_asset_id: string | null;
  file_path: string | null;
  content_hash: string;
  filename: string | null;
  width: number | null;
  height: number | null;
  orphaned: number;
}

export function getImage(id: string): ImageRow | undefined {
  return db.prepare("SELECT * FROM images WHERE id = ?").get(id) as ImageRow | undefined;
}

const IMMUTABLE = "public, max-age=31536000, immutable";

// HANDOFF §2: serve three sizes. Uploads are served as the original for every
// size (no re-encode dependency); Immich renditions are proxied and disk-cached.
export async function serveImage(
  image: ImageRow,
  size: "thumb" | "screen" | "orig",
): Promise<Response> {
  if (image.immich_asset_id) {
    const kind = size === "orig" ? "original" : "thumbnail";
    const immichSize = size === "thumb" ? "thumbnail" : "preview";

    // disk cache for the small renditions keyed by asset id
    if (size !== "orig") {
      const cacheFile = path.join(config.cacheDir, `${image.immich_asset_id}.${size}`);
      try {
        const buf = await fs_p.readFile(cacheFile);
        return new Response(new Uint8Array(buf), {
          headers: { "content-type": "image/jpeg", "cache-control": IMMUTABLE },
        });
      } catch {
        /* cache miss — fetch below */
      }
      const res = await assetImage(image.immich_asset_id, "thumbnail", immichSize);
      if (!res.ok) return new Response("upstream error", { status: 502 });
      const buf = Buffer.from(await res.arrayBuffer());
      fs_p.writeFile(cacheFile, buf).catch(() => {});
      return new Response(new Uint8Array(buf), {
        headers: {
          "content-type": res.headers.get("content-type") ?? "image/jpeg",
          "cache-control": IMMUTABLE,
        },
      });
    }

    const res = await assetImage(image.immich_asset_id, kind, immichSize);
    if (!res.ok) return new Response("upstream error", { status: 502 });
    return new Response(res.body, {
      headers: {
        "content-type": res.headers.get("content-type") ?? "application/octet-stream",
        "cache-control": IMMUTABLE,
      },
    });
  }

  if (image.file_path) {
    const abs = path.join(config.uploadsDir, path.basename(image.file_path));
    try {
      const buf = await fs_p.readFile(abs);
      return new Response(new Uint8Array(buf), {
        headers: { "content-type": guessType(abs), "cache-control": IMMUTABLE },
      });
    } catch {
      return new Response("not found", { status: 404 });
    }
  }

  return new Response("no source", { status: 404 });
}

function guessType(file: string): string {
  const ext = path.extname(file).toLowerCase();
  return (
    {
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".png": "image/png",
      ".gif": "image/gif",
      ".webp": "image/webp",
      ".heic": "image/heic",
      ".avif": "image/avif",
    }[ext] ?? "application/octet-stream"
  );
}

export function fileExists(p: string): boolean {
  try {
    fs.accessSync(p);
    return true;
  } catch {
    return false;
  }
}
