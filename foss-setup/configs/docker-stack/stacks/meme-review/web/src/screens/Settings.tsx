import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";
import { useApi } from "../lib";

interface ImmichConfig { baseUrl: string; apiKey: string; defaultAlbumId: string; enabled: boolean }
interface ImmichStatus { connected: boolean; serverVersion: string | null; albumCount: number; error?: string }

export function Settings() {
  const { me, navigate, logout } = useStore();
  const { data: cfg } = useApi<ImmichConfig>("/immich/config");
  const { data: users, reload: reloadUsers } = useApi<{ users: Array<{ id: string; display_name: string; is_owner: number; avatar_emoji: string | null }> }>("/users");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [albumId, setAlbumId] = useState("");
  const [status, setStatus] = useState<ImmichStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const stickerInput = useRef<HTMLInputElement>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [mHandle, setMHandle] = useState("");
  const [mName, setMName] = useState("");
  const [mPass, setMPass] = useState("");
  const [mErr, setMErr] = useState<string | null>(null);

  useEffect(() => {
    if (cfg) {
      setBaseUrl(cfg.baseUrl);
      setApiKey(cfg.apiKey);
      setAlbumId(cfg.defaultAlbumId);
    }
  }, [cfg]);

  const test = async () => {
    setSaving(true);
    try {
      const r = await api.post<{ status: ImmichStatus }>("/immich/config", { baseUrl, apiKey, defaultAlbumId: albumId });
      setStatus(r.status);
    } finally {
      setSaving(false);
    }
  };

  const addMember = async () => {
    setMErr(null);
    try {
      await api.post("/auth/register", { handle: mHandle, password: mPass, displayName: mName || mHandle, avatarEmoji: "🗿" });
      setMHandle(""); setMName(""); setMPass(""); setAddOpen(false);
      reloadUsers();
    } catch (err) {
      setMErr(err instanceof Error ? err.message : "failed");
    }
  };

  const uploadSticker = async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", file.name.replace(/\.[^.]+$/, ""));
    await fetch("/api/stickers", { method: "POST", credentials: "same-origin", body: fd });
  };

  return (
    <>
      <div style={{ padding: "56px 18px 8px", display: "flex", alignItems: "center", gap: 10 }}>
        <button className="btn btn-ghost btn-icon" onClick={() => navigate("/")} style={{ width: 34, height: 34 }}>
          <i className="ph ph-caret-left" />
        </button>
        <h4 style={{ margin: 0 }}>Settings</h4>
      </div>
      <div className="phone-scroll" style={{ padding: "12px 18px 120px", display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Immich */}
        <div className="card" style={{ padding: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ font: "500 14px Inter" }}>Immich</div>
            <span className={status?.connected || cfg?.enabled ? "tag tag-accent" : "tag tag-neutral"}>
              {status?.connected || cfg?.enabled ? "Connected" : "Off"}
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>
            <div className="field">
              <label>Server URL</label>
              <input className="input" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://photos.home.lan" style={{ fontSize: 12 }} />
            </div>
            <div className="field">
              <label>API key</label>
              <input className="input" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="paste key" style={{ fontSize: 12 }} />
            </div>
            <div className="field">
              <label>Album to browse</label>
              <input className="input" value={albumId} onChange={(e) => setAlbumId(e.target.value)} placeholder="album id (optional)" style={{ fontSize: 12 }} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button className="btn btn-secondary" onClick={test} disabled={saving} style={{ flex: 1, height: 36, fontSize: 12 }}>
              {saving ? "…" : "Test & save"}
            </button>
          </div>
          {status && (
            <div style={{ fontSize: 11, marginTop: 10, color: status.connected ? "var(--color-accent-300)" : "#e88" }}>
              {status.connected ? `Connected · ${status.albumCount} albums${status.serverVersion ? ` · v${status.serverVersion}` : ""}` : `Not connected${status.error ? ` — ${status.error}` : ""}`}
            </div>
          )}
          <div style={{ fontSize: 11, color: "var(--color-neutral-500)", marginTop: 10, lineHeight: 1.5 }}>
            Drops reference Immich asset IDs and stream thumbnails through this app, so nothing is duplicated. Leave blank to upload files into local storage instead.
          </div>
        </div>

        {/* Stickers */}
        <div className="card" style={{ padding: 14 }}>
          <div style={{ font: "500 14px Inter", marginBottom: 10 }}>Emoji &amp; stickers</div>
          <button className="btn btn-secondary" onClick={() => stickerInput.current?.click()} style={{ height: 38, fontSize: 12 }}>
            <i className="ph ph-plus" /> Upload sticker
          </button>
          <input
            ref={stickerInput}
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => e.target.files?.[0] && uploadSticker(e.target.files[0])}
          />
          <div style={{ fontSize: 11, color: "var(--color-neutral-500)", marginTop: 10 }}>
            Uploaded stickers are stored locally and available as reactions.
          </div>
        </div>

        {/* Household */}
        <div className="card" style={{ padding: 14 }}>
          <div style={{ font: "500 14px Inter", marginBottom: 10 }}>Household</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {(users?.users ?? []).map((u) => (
              <div key={u.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 30, height: 30, borderRadius: 20, background: u.is_owner ? "var(--color-accent-800)" : "var(--color-neutral-800)", display: "flex", alignItems: "center", justifyContent: "center", font: "600 11px Inter", color: u.is_owner ? "var(--color-accent-200)" : "var(--color-neutral-300)" }}>
                  {u.avatar_emoji ?? u.display_name.slice(0, 2).toUpperCase()}
                </div>
                <div style={{ flex: 1, fontSize: 13 }}>{u.id === me?.id ? "You" : u.display_name}</div>
                <span className="tag tag-outline">{u.is_owner ? "owner" : "member"}</span>
              </div>
            ))}
          </div>
          {me?.is_owner ? (
            addOpen ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>
                <input className="input" placeholder="Display name (e.g. Sam)" value={mName} onChange={(e) => setMName(e.target.value)} style={{ fontSize: 13 }} />
                <input className="input" placeholder="handle" autoCapitalize="none" value={mHandle} onChange={(e) => setMHandle(e.target.value)} style={{ fontSize: 13 }} />
                <input className="input" type="password" placeholder="password" value={mPass} onChange={(e) => setMPass(e.target.value)} style={{ fontSize: 13 }} />
                {mErr && <div style={{ fontSize: 11, color: "#e88" }}>{mErr}</div>}
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn btn-ghost" onClick={() => setAddOpen(false)} style={{ flex: 1, height: 34, fontSize: 12 }}>Cancel</button>
                  <button className="btn btn-primary" onClick={addMember} disabled={!mHandle || !mPass} style={{ flex: 1, height: 34, fontSize: 12 }}>Add member</button>
                </div>
              </div>
            ) : (
              <button className="btn btn-secondary btn-block" onClick={() => setAddOpen(true)} style={{ height: 36, fontSize: 12, marginTop: 12 }}>
                <i className="ph ph-user-plus" /> Add member
              </button>
            )
          ) : null}
          <div style={{ fontSize: 11, color: "var(--color-neutral-500)", marginTop: 10 }}>
            Guest links open a drop read-only for anyone with the URL.
          </div>
        </div>

        <button className="btn btn-secondary btn-block" onClick={logout} style={{ height: 40, fontSize: 13 }}>
          Sign out
        </button>
      </div>
    </>
  );
}
