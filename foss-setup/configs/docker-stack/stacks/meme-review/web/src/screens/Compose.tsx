import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";

type Source = "immich" | "upload";

interface Item {
  key: string;
  immichAssetId?: string;
  uploadId?: string;
  contentHash?: string;
  filename: string;
  previewUrl: string;
}

interface CreateResult {
  id: number;
  slug: string;
  url: string;
  boomerangs: Array<{ imageId: string; filename: string | null; previousDropId: number }>;
}

export function Compose() {
  const { partner, navigate } = useStore();
  const [source, setSource] = useState<Source>("upload");
  const [items, setItems] = useState<Item[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [caption, setCaption] = useState("");
  const [albums, setAlbums] = useState<Array<{ id: string; name: string; assetCount: number }>>([]);
  const [albumId, setAlbumId] = useState<string>("");
  const [immichError, setImmichError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<CreateResult | null>(null);
  const [copied, setCopied] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const partnerName = partner?.display_name ?? "them";

  // load immich albums when switching to that source
  useEffect(() => {
    if (source !== "immich") return;
    setImmichError(null);
    api
      .get<{ albums: any[]; error?: string }>("/immich/albums")
      .then((r) => {
        setAlbums(r.albums ?? []);
        if (r.error) setImmichError(r.error);
        if (r.albums?.[0] && !albumId) setAlbumId(r.albums[0].id);
      })
      .catch((e) => setImmichError(e.message));
  }, [source]);

  useEffect(() => {
    if (source !== "immich" || !albumId) return;
    api
      .get<{ assets: any[]; error?: string }>(`/immich/albums/${albumId}/assets`)
      .then((r) => {
        setItems(
          (r.assets ?? []).map((a) => ({
            key: a.id,
            immichAssetId: a.id,
            contentHash: a.checksum ?? undefined,
            filename: a.filename,
            previewUrl: a.thumbUrl,
          })),
        );
        setSelected(new Set());
      })
      .catch((e) => setImmichError(e.message));
  }, [albumId, source]);

  const switchSource = (s: Source) => {
    setSource(s);
    setItems([]);
    setSelected(new Set());
  };

  const onFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const arr = Array.from(files);
    const { uploads } = await api.upload(arr);
    const newItems: Item[] = uploads.map((u, i) => ({
      key: u.uploadId,
      uploadId: u.uploadId,
      contentHash: u.contentHash,
      filename: u.filename,
      previewUrl: URL.createObjectURL(arr[i]),
    }));
    setItems((prev) => [...prev, ...newItems]);
    setSelected((prev) => new Set([...prev, ...newItems.map((i) => i.key)]));
  };

  const toggle = (key: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

  const selectAll = () => setSelected(new Set(items.map((i) => i.key)));

  const create = async () => {
    const chosen = items.filter((i) => selected.has(i.key));
    if (chosen.length === 0) return;
    setCreating(true);
    try {
      const res = await api.post<CreateResult>("/drops", {
        source,
        caption: caption.trim() || undefined,
        items: chosen.map((i) => ({
          immichAssetId: i.immichAssetId,
          uploadId: i.uploadId,
          contentHash: i.contentHash,
          filename: i.filename,
        })),
      });
      setResult(res);
    } finally {
      setCreating(false);
    }
  };

  const shareUrl = result ? `${window.location.host}/d/${result.slug}` : "";
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/d/${result!.slug}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard needs https; ignore on http */
    }
  };

  const selCount = selected.size;

  return (
    <>
      <div style={{ padding: "56px 18px 10px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <button className="btn btn-ghost btn-icon" onClick={() => navigate("/")} style={{ width: 34, height: 34 }}>
          <i className="ph ph-x" />
        </button>
        <span style={{ font: "500 15px Inter" }}>New drop</span>
        <button className="btn btn-ghost" onClick={create} disabled={selCount === 0} style={{ fontSize: 13 }}>
          Next
        </button>
      </div>

      <div className="seg" style={{ margin: "8px 18px 0" }}>
        <button className="seg-opt" onClick={() => switchSource("immich")} style={{ background: source === "immich" ? "var(--color-accent-900)" : "transparent" }}>
          <i className="ph ph-hard-drives" /> Immich
        </button>
        <button className="seg-opt" onClick={() => switchSource("upload")} style={{ background: source === "upload" ? "var(--color-accent-900)" : "transparent" }}>
          <i className="ph ph-upload-simple" /> Upload
        </button>
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 18px 8px" }}>
        <span style={{ fontSize: 12, color: "var(--color-neutral-400)" }}>
          <i className="ph ph-folder-simple" />{" "}
          {source === "immich"
            ? albums.find((a) => a.id === albumId)?.name ?? "Immich"
            : "Uploads · this device"}
        </span>
        {source === "upload" ? (
          <button className="btn btn-ghost" onClick={() => fileInput.current?.click()} style={{ fontSize: 12 }}>
            Add photos
          </button>
        ) : (
          <button className="btn btn-ghost" onClick={selectAll} style={{ fontSize: 12 }}>
            Select all
          </button>
        )}
      </div>

      <input ref={fileInput} type="file" accept="image/*" multiple hidden onChange={(e) => onFiles(e.target.files)} />

      <div className="phone-scroll" style={{ padding: "0 14px 190px" }}>
        {source === "immich" && immichError && (
          <div className="card" style={{ padding: 20, textAlign: "center", marginTop: 8 }}>
            <div style={{ fontSize: 24, color: "var(--color-neutral-600)" }}>
              <i className="ph ph-hard-drives" />
            </div>
            <div style={{ font: "500 14px Inter", marginTop: 10 }}>Immich not connected</div>
            <div style={{ fontSize: 11.5, color: "var(--color-neutral-400)", marginTop: 5 }}>
              Add your server URL and API key in Settings, or switch to Upload.
            </div>
            <button className="btn btn-primary" onClick={() => navigate("/settings")} style={{ height: 34, fontSize: 12, marginTop: 12 }}>
              Connect Immich
            </button>
          </div>
        )}
        {source === "upload" && items.length === 0 && (
          <div className="card" style={{ padding: 20, textAlign: "center", marginTop: 8 }}>
            <div style={{ fontSize: 24, color: "var(--color-neutral-600)" }}>
              <i className="ph ph-upload-simple" />
            </div>
            <div style={{ font: "500 14px Inter", marginTop: 10 }}>Pick some images</div>
            <div style={{ fontSize: 11.5, color: "var(--color-neutral-400)", marginTop: 5 }}>
              They upload straight into local storage — Immich optional.
            </div>
            <button className="btn btn-primary" onClick={() => fileInput.current?.click()} style={{ height: 34, fontSize: 12, marginTop: 12 }}>
              Choose photos
            </button>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 4 }}>
          {items.map((t) => {
            const on = selected.has(t.key);
            return (
              <button
                key={t.key}
                className="tap"
                onClick={() => toggle(t.key)}
                style={{ position: "relative", aspectRatio: "1", borderRadius: 6, overflow: "hidden", outline: on ? "2px solid var(--color-accent)" : "1px solid rgba(233,233,237,.08)", outlineOffset: -2 }}
              >
                <img src={t.previewUrl} alt={t.filename} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                <span style={{ position: "absolute", left: 5, bottom: 4, font: "500 8px ui-monospace,Menlo,monospace", color: "#fff", textShadow: "0 1px 2px rgba(0,0,0,.7)" }}>
                  {t.filename.slice(0, 10)}
                </span>
                <span style={{ position: "absolute", top: 5, right: 5, width: 18, height: 18, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, background: on ? "var(--color-accent-300)" : "transparent", color: "#161826", boxShadow: "0 0 0 1px rgba(233,233,237,.35)" }}>
                  {on ? "✓" : ""}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* bottom bar */}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: "14px 18px 30px", background: "linear-gradient(to top,#161826 65%,transparent)", display: "flex", flexDirection: "column", gap: 10 }}>
        <input className="input" placeholder="Caption (optional) — “low effort tuesday”" value={caption} onChange={(e) => setCaption(e.target.value)} style={{ fontSize: 13 }} />
        <button className="btn btn-primary btn-block" onClick={create} disabled={selCount === 0 || creating} style={{ height: 44 }}>
          {creating ? "Creating…" : `Create drop · ${selCount} images`}
        </button>
      </div>

      {/* share-link sheet */}
      {result && (
        <>
          <div style={{ position: "absolute", inset: 0, background: "rgba(16,17,32,.65)", animation: "fade .16s", zIndex: 20 }} onClick={() => setResult(null)} />
          <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, background: "var(--color-surface)", borderRadius: "18px 18px 0 0", boxShadow: "var(--shadow-lg)", padding: "14px 16px 34px", animation: "pop .22s ease-out", zIndex: 21 }}>
            <div style={{ width: 38, height: 4, borderRadius: 4, background: "var(--color-neutral-700)", margin: "0 auto 14px" }} />
            <div style={{ font: "500 16px Inter" }}>Drop #{result.id} is ready</div>
            <div style={{ fontSize: 12, color: "var(--color-neutral-400)", marginTop: 4 }}>
              {selCount} images · expires never · reactions stay forever
            </div>
            {result.boomerangs.length > 0 && (
              <div style={{ display: "flex", gap: 9, alignItems: "flex-start", background: "var(--color-accent-900)", borderRadius: 10, padding: "10px 12px", marginTop: 12 }}>
                <i className="ph ph-boomerang" style={{ color: "var(--color-accent-300)", marginTop: 2 }} />
                <div>
                  <div style={{ font: "500 12px Inter", color: "var(--color-accent-200)" }}>
                    {result.boomerangs.length} of these were sent before
                  </div>
                  <div style={{ fontSize: 11, color: "var(--color-neutral-400)" }}>
                    {result.boomerangs.slice(0, 2).map((b) => `${b.filename ?? "image"} in Drop #${b.previousDropId}`).join(" · ")} — you earned Boomerang
                  </div>
                </div>
              </div>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 14, padding: "10px 12px", borderRadius: 10, background: "var(--color-bg)", boxShadow: "var(--shadow-sm)" }}>
              <span style={{ flex: 1, font: "500 11.5px ui-monospace,Menlo,monospace", color: "var(--color-accent-300)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {shareUrl}
              </span>
              <button className="btn btn-secondary" onClick={copy} style={{ height: 30, fontSize: 11 }}>
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="btn btn-secondary" onClick={() => navigate("/")} style={{ flex: 1, height: 42 }}>
                Done
              </button>
              <button className="btn btn-primary" onClick={() => navigate(`/d/${result.slug}`)} style={{ flex: 1, height: 42 }}>
                Preview as {partnerName}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
