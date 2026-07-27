import { config } from "./config.ts";
import { getSetting, setSetting } from "./db.ts";

// Runtime config: env is the default, Settings overrides persist in the DB.
export interface ImmichConfig {
  baseUrl: string;
  apiKey: string;
  defaultAlbumId: string;
}

export function getImmichConfig(): ImmichConfig {
  return {
    baseUrl: (getSetting("immich.baseUrl") ?? config.immich.baseUrl).replace(/\/+$/, ""),
    apiKey: getSetting("immich.apiKey") ?? config.immich.apiKey,
    defaultAlbumId: getSetting("immich.defaultAlbumId") ?? config.immich.defaultAlbumId,
  };
}

export function setImmichConfig(patch: Partial<ImmichConfig>): void {
  if (patch.baseUrl !== undefined) setSetting("immich.baseUrl", patch.baseUrl.replace(/\/+$/, ""));
  if (patch.apiKey !== undefined && patch.apiKey !== "" && !/^•+$/.test(patch.apiKey))
    setSetting("immich.apiKey", patch.apiKey);
  if (patch.defaultAlbumId !== undefined) setSetting("immich.defaultAlbumId", patch.defaultAlbumId);
}

export function immichEnabled(): boolean {
  const c = getImmichConfig();
  return Boolean(c.baseUrl && c.apiKey);
}

async function api(path: string, init: RequestInit = {}): Promise<Response> {
  const c = getImmichConfig();
  if (!c.baseUrl || !c.apiKey) throw new Error("immich-not-configured");
  return fetch(`${c.baseUrl}/api${path}`, {
    ...init,
    headers: { "x-api-key": c.apiKey, Accept: "application/json", ...(init.headers ?? {}) },
  });
}

export interface ImmichStatus {
  connected: boolean;
  serverVersion: string | null;
  albumCount: number;
  error?: string;
}

export async function status(): Promise<ImmichStatus> {
  if (!immichEnabled()) return { connected: false, serverVersion: null, albumCount: 0 };
  try {
    const [versionRes, albumsRes] = await Promise.all([
      api("/server/about").catch(() => api("/server-info/version")),
      api("/albums"),
    ]);
    const version = versionRes.ok ? await versionRes.json().catch(() => ({})) : {};
    const albums = albumsRes.ok ? await albumsRes.json().catch(() => []) : [];
    return {
      connected: albumsRes.ok,
      serverVersion: version.version ?? version.serverVersion ?? null,
      albumCount: Array.isArray(albums) ? albums.length : 0,
      error: albumsRes.ok ? undefined : `HTTP ${albumsRes.status}`,
    };
  } catch (err) {
    return {
      connected: false,
      serverVersion: null,
      albumCount: 0,
      error: err instanceof Error ? err.message : "unreachable",
    };
  }
}

export interface ImmichAlbum {
  id: string;
  name: string;
  assetCount: number;
  thumbnailAssetId: string | null;
}

export async function albums(): Promise<ImmichAlbum[]> {
  const res = await api("/albums");
  if (!res.ok) throw new Error(`immich albums HTTP ${res.status}`);
  const raw = (await res.json()) as any[];
  return raw.map((a) => ({
    id: a.id,
    name: a.albumName ?? a.name ?? "Untitled",
    assetCount: a.assetCount ?? (Array.isArray(a.assets) ? a.assets.length : 0),
    thumbnailAssetId: a.albumThumbnailAssetId ?? null,
  }));
}

export interface ImmichAsset {
  id: string;
  checksum: string | null;
  filename: string;
  width: number | null;
  height: number | null;
  takenAt: number | null;
  thumbUrl: string;
}

export async function albumAssets(albumId: string): Promise<ImmichAsset[]> {
  const res = await api(`/albums/${encodeURIComponent(albumId)}`);
  if (!res.ok) throw new Error(`immich album HTTP ${res.status}`);
  const album = (await res.json()) as any;
  const assets = Array.isArray(album.assets) ? album.assets : [];
  return assets
    .filter((a: any) => (a.type ?? "IMAGE") === "IMAGE")
    .map((a: any) => ({
      id: a.id,
      checksum: a.checksum ?? null,
      filename: a.originalFileName ?? a.originalPath?.split("/").pop() ?? a.id,
      width: a.exifInfo?.exifImageWidth ?? null,
      height: a.exifInfo?.exifImageHeight ?? null,
      takenAt: a.fileCreatedAt ? Date.parse(a.fileCreatedAt) : null,
      // proxied through this server — never expose the direct Immich URL/key
      thumbUrl: `/api/immich/assets/${a.id}/thumbnail`,
    }));
}

// Stream a thumbnail/original straight through, keeping the API key server-side.
export async function assetImage(
  assetId: string,
  kind: "thumbnail" | "original",
  size: "preview" | "thumbnail" = "preview",
): Promise<Response> {
  const path =
    kind === "original"
      ? `/assets/${encodeURIComponent(assetId)}/original`
      : `/assets/${encodeURIComponent(assetId)}/thumbnail?size=${size}`;
  return api(path);
}
