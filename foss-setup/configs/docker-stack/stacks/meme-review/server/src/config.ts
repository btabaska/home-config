import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..");

function bool(v: string | undefined, dflt: boolean): boolean {
  if (v == null) return dflt;
  return /^(1|true|yes|on)$/i.test(v.trim());
}

const dataDir = path.resolve(repoRoot, process.env.DATA_DIR ?? "./data");

export const config = {
  repoRoot,
  port: Number(process.env.PORT ?? 8787),
  dataDir,
  dbPath: path.join(dataDir, "meme-review.sqlite"),
  uploadsDir: path.join(dataDir, "uploads"),
  cacheDir: path.join(dataDir, "cache"),
  gifsDir: path.join(dataDir, "gifs"),
  distDir: path.join(repoRoot, "dist"),
  sessionSecret: process.env.SESSION_SECRET ?? "dev-insecure-secret-change-me",
  cookieSecure: bool(process.env.COOKIE_SECURE, false),
  guestReactions: (process.env.GUEST_REACTIONS ?? "members") as "members" | "guests",
  immich: {
    baseUrl: process.env.IMMICH_BASE_URL ?? "",
    apiKey: process.env.IMMICH_API_KEY ?? "",
    defaultAlbumId: process.env.IMMICH_DEFAULT_ALBUM_ID ?? "",
  },
  isProd: process.env.NODE_ENV === "production",
};

export type Config = typeof config;
