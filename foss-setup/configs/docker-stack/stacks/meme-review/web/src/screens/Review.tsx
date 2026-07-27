import React, { useEffect, useMemo, useState, useCallback } from "react";
import { api } from "../api";
import { useStore } from "../store";
import { useApi, useLiveReload } from "../lib";
import { ImageThumb } from "../components/ImageThumb";

const QUICK = ["❤️", "👍", "👎", "😂", "‼️", "❓"];
const EMOJI_SET = ["💀","😂","❤️","👍","👎","‼️","❓","🫠","🥲","😭","🔥","🤌","🙃","😮‍💨","🫡","🧠","🚬","🗿","😳","🤡","💅","👀","🍽️","🐛","🫥","😤","🪦","📉"];

interface Reaction { id: string; userId: string; by: string; kind: string; value: string }
interface Img { id: string; position: number; filename: string | null; thumbUrl: string; screenUrl: string; reactions: Reaction[]; threadCount: number }
interface DropPayload {
  drop: { id: number; slug: string; title: string; caption: string | null; sender: any; recipient: any; firstOpenedAt: number | null };
  canReact: boolean;
  images: Img[];
}
interface Message { id: string; userId: string; by: string; body: string }

export function Review({ slug }: { slug: string }) {
  const { me, partner, navigate } = useStore();
  const { data, reload } = useApi<DropPayload>(`/drops/${slug}`);
  useLiveReload(reload, (t) => t.startsWith("reaction") || t.startsWith("message") || t.startsWith("drop"));

  const images = data?.images ?? [];
  const total = images.length;
  const storeKey = `mr:lastIdx:${slug}`;
  const [idx, setIdx] = useState(() => Number(localStorage.getItem(storeKey) ?? 0));
  const [sheet, setSheet] = useState<null | "emoji" | "sticker" | "gif" | "text">(null);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [gifs, setGifs] = useState<Array<{ id: string; name: string; url: string }>>([]);
  const [stickers, setStickers] = useState<Array<{ id: string; name: string; url: string }>>([]);

  // mark opened once
  useEffect(() => {
    api.post(`/drops/${slug}/opened`).catch(() => {});
  }, [slug]);

  const clampedIdx = Math.min(idx, Math.max(0, total - 1));
  const cur = images[clampedIdx];

  useEffect(() => {
    if (total) localStorage.setItem(storeKey, String(clampedIdx));
  }, [clampedIdx, total, storeKey]);

  const reviewed = useMemo(
    () => images.filter((i) => i.reactions.some((r) => r.userId === me?.id)).length,
    [images, me],
  );

  const mine = cur ? cur.reactions.filter((r) => r.userId === me?.id) : [];
  const theirs = cur ? cur.reactions.filter((r) => r.userId !== me?.id) : [];
  const myValues = new Set(mine.map((r) => r.value));

  const react = useCallback(
    async (value: string, kind: "emoji" | "sticker" | "gif" = "emoji") => {
      if (!cur) return;
      setSheet(null);
      try {
        await api.post(`/images/${cur.id}/reactions`, { kind, value });
      } finally {
        reload();
      }
    },
    [cur, reload],
  );

  const next = () => {
    if (clampedIdx >= total - 1) return navigate(`/d/${slug}/summary`);
    setIdx(clampedIdx + 1);
    setSheet(null);
  };
  const prev = () => {
    setIdx(Math.max(0, clampedIdx - 1));
    setSheet(null);
  };

  // load messages when the reply sheet opens
  useEffect(() => {
    if (sheet === "text" && cur) {
      api.get<{ messages: Message[] }>(`/images/${cur.id}/messages`).then((r) => setMessages(r.messages));
    }
    if (sheet === "gif") api.get<{ gifs: any[] }>(`/gifs/search?q=`).then((r) => setGifs(r.gifs));
    if (sheet === "sticker") api.get<{ stickers: any[] }>(`/stickers`).then((r) => setStickers(r.stickers));
  }, [sheet, cur]);

  const sendText = async () => {
    const t = draft.trim();
    if (!t || !cur) return;
    setDraft("");
    await api.post(`/images/${cur.id}/messages`, { body: t });
    const r = await api.get<{ messages: Message[] }>(`/images/${cur.id}/messages`);
    setMessages(r.messages);
    reload();
  };

  const progressPct = total ? Math.round((reviewed / total) * 100) : 0;
  const partnerName = data?.drop.sender?.display_name ?? partner?.display_name ?? "them";

  return (
    <>
      <div style={{ padding: "52px 14px 0" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="btn btn-ghost btn-icon" onClick={() => navigate("/")} style={{ width: 32, height: 32 }}>
            <i className="ph ph-caret-left" />
          </button>
          <div style={{ flex: 1 }}>
            <div style={{ height: 3, borderRadius: 3, background: "var(--color-neutral-800)", overflow: "hidden" }}>
              <div style={{ height: "100%", background: "var(--color-accent)", width: `${progressPct}%`, transition: "width .25s" }} />
            </div>
          </div>
          <span style={{ font: "600 11px ui-monospace,Menlo,monospace", color: "var(--color-neutral-400)" }}>
            {total ? clampedIdx + 1 : 0} / {total}
          </span>
          <button className="btn btn-ghost btn-icon" onClick={() => navigate(`/d/${slug}/all`)} style={{ width: 32, height: 32 }}>
            <i className="ph ph-squares-four" />
          </button>
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8 }}>
          <span style={{ fontSize: 12, color: "var(--color-neutral-400)" }}>
            {data?.drop.title ?? "Drop"} · from {partnerName}
          </span>
          <span style={{ font: "600 10px ui-monospace,Menlo,monospace", color: "var(--color-accent-300)" }}>
            {reviewed} of {total} reacted
          </span>
        </div>
      </div>

      {/* image */}
      <div style={{ flex: 1, position: "relative", margin: "12px 14px 0", borderRadius: 14, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
        {cur ? (
          <ImageThumb src={cur.screenUrl} filename={cur.filename} style={{ position: "absolute", inset: 0 }} />
        ) : (
          <div className="hatch-lg" style={{ position: "absolute", inset: 0 }} />
        )}
        {!cur && <div style={{ color: "var(--color-neutral-600)" }}>No images</div>}

        <button className="tap" onClick={prev} style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "32%" }} />
        <button className="tap" onClick={next} style={{ position: "absolute", right: 0, top: 0, bottom: 0, width: "32%" }} />

        {/* reaction chips */}
        <div style={{ position: "absolute", left: 10, bottom: 10, display: "flex", flexWrap: "wrap", gap: 6, maxWidth: "82%" }}>
          {[...mine, ...theirs].map((r) => (
            <span
              key={r.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 9px",
                borderRadius: 20,
                background: "rgba(22,24,38,.82)",
                boxShadow: r.userId === me?.id ? "0 0 0 1px var(--color-accent-700)" : "var(--shadow-sm)",
                fontSize: 14,
              }}
            >
              {r.kind === "emoji" ? r.value : "🖼️"}
              <span style={{ font: "600 9px ui-monospace,Menlo,monospace", color: "var(--color-neutral-300)" }}>{r.by}</span>
            </span>
          ))}
        </div>

        {cur && cur.threadCount > 0 && (
          <button
            className="tap"
            onClick={() => setSheet("text")}
            style={{ position: "absolute", right: 10, top: 10, display: "flex", alignItems: "center", gap: 5, padding: "5px 10px", borderRadius: 20, background: "rgba(22,24,38,.8)", boxShadow: "var(--shadow-sm)", font: "500 11px Inter", color: "var(--color-neutral-300)" }}
          >
            <i className="ph ph-chat-teardrop-text" /> {cur.threadCount}
          </button>
        )}
      </div>

      {/* reaction bar */}
      <div style={{ padding: "12px 14px 30px", display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center", justifyContent: "space-between" }}>
          {QUICK.map((e) => {
            const on = myValues.has(e);
            return (
              <button
                key={e}
                className="tap"
                onClick={() => react(e)}
                style={{ flex: 1, height: 46, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, background: on ? "var(--color-accent-900)" : "var(--color-surface)", boxShadow: on ? "0 0 0 1px var(--color-accent-600)" : "var(--shadow-sm)" }}
              >
                {e}
              </button>
            );
          })}
          <button className="btn btn-icon" onClick={() => setSheet("emoji")} style={{ width: 44, height: 46, borderRadius: 12 }}>
            <i className="ph ph-smiley-sticker" />
          </button>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-secondary" onClick={() => setSheet("text")} style={{ flex: 1, height: 38, fontSize: 12 }}>
            <i className="ph ph-chat-teardrop-text" /> Reply
          </button>
          <button className="btn btn-secondary" onClick={() => setSheet("gif")} style={{ flex: 1, height: 38, fontSize: 12 }}>
            <i className="ph ph-gif" /> GIF
          </button>
          <button className="btn btn-secondary" onClick={() => setSheet("sticker")} style={{ flex: 1, height: 38, fontSize: 12 }}>
            <i className="ph ph-sticker" /> Sticker
          </button>
          <button className="btn btn-primary" onClick={next} style={{ width: 46, height: 38 }}>
            <i className="ph ph-arrow-right" />
          </button>
        </div>
      </div>

      {/* picker sheet */}
      {sheet && (
        <>
          <div style={{ position: "absolute", inset: 0, background: "rgba(16,17,32,.6)", animation: "fade .16s ease-out", zIndex: 20 }} onClick={() => setSheet(null)} />
          <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, background: "var(--color-surface)", borderRadius: "18px 18px 0 0", boxShadow: "var(--shadow-lg)", padding: "12px 14px 34px", animation: "pop .22s ease-out", maxHeight: "76%", display: "flex", flexDirection: "column", zIndex: 21 }}>
            <div style={{ width: 38, height: 4, borderRadius: 4, background: "var(--color-neutral-700)", margin: "0 auto 12px" }} />
            <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
              {(["emoji", "sticker", "gif", "text"] as const).map((k) => (
                <button
                  key={k}
                  className="tap"
                  onClick={() => setSheet(k)}
                  style={{ padding: "6px 11px", borderRadius: 8, font: "500 12px Inter", background: sheet === k ? "var(--color-accent-900)" : "var(--color-bg)", color: sheet === k ? "var(--color-accent-200)" : "var(--color-neutral-400)" }}
                >
                  {k === "emoji" ? "Emoji" : k === "sticker" ? "Stickers" : k === "gif" ? "GIF" : "Reply"}
                </button>
              ))}
            </div>

            {sheet === "emoji" && (
              <div style={{ overflowY: "auto", display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 4 }}>
                {EMOJI_SET.map((e) => (
                  <button key={e} className="tap" onClick={() => react(e)} style={{ aspectRatio: "1", borderRadius: 9, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 21, background: myValues.has(e) ? "var(--color-accent-900)" : "transparent" }}>
                    {e}
                  </button>
                ))}
              </div>
            )}

            {sheet === "sticker" && (
              <div style={{ overflowY: "auto" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8 }}>
                  {stickers.length === 0 && <div style={{ gridColumn: "span 3", fontSize: 12, color: "var(--color-neutral-500)", padding: "10px 0" }}>No custom stickers yet.</div>}
                  {stickers.map((s) => (
                    <button key={s.id} className="tap" onClick={() => react(s.url, "sticker")} style={{ aspectRatio: "1", borderRadius: 10, overflow: "hidden" }}>
                      <img src={s.url} alt={s.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    </button>
                  ))}
                </div>
                <div style={{ fontSize: 11, color: "var(--color-neutral-500)", marginTop: 10 }}>Custom stickers live in Settings → Emoji &amp; stickers.</div>
              </div>
            )}

            {sheet === "gif" && (
              <div style={{ overflowY: "auto" }}>
                <input className="input" placeholder="Search GIFs" style={{ fontSize: 13, marginBottom: 8 }} onChange={(e) => api.get<{ gifs: any[] }>(`/gifs/search?q=${encodeURIComponent(e.target.value)}`).then((r) => setGifs(r.gifs))} />
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 6 }}>
                  {gifs.length === 0 && <div style={{ gridColumn: "span 2", fontSize: 12, color: "var(--color-neutral-500)", padding: "10px 0" }}>Drop .gif files into data/gifs to search them.</div>}
                  {gifs.map((g) => (
                    <button key={g.id} className="tap" onClick={() => react(g.url, "gif")} style={{ aspectRatio: "4/3", borderRadius: 10, overflow: "hidden" }}>
                      <img src={g.url} alt={g.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {sheet === "text" && (
              <>
                <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
                  {messages.length === 0 && <div style={{ fontSize: 12, color: "var(--color-neutral-500)" }}>No replies on this image yet.</div>}
                  {messages.map((m) => (
                    <div key={m.id} style={{ alignSelf: m.userId === me?.id ? "flex-end" : "flex-start", maxWidth: "78%", padding: "8px 11px", borderRadius: 14, background: m.userId === me?.id ? "var(--color-accent-800)" : "var(--color-bg)", fontSize: 13 }}>
                      <div style={{ font: "600 9px ui-monospace,Menlo,monospace", color: "var(--color-neutral-400)", marginBottom: 3 }}>{m.by}</div>
                      {m.body}
                    </div>
                  ))}
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <input className="input" placeholder="Reply on this image…" value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendText()} style={{ fontSize: 13 }} />
                  <button className="btn btn-primary" onClick={sendText} style={{ width: 44 }}>
                    <i className="ph ph-paper-plane-right" />
                  </button>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </>
  );
}
