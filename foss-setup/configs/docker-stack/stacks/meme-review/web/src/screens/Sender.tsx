import React, { useMemo, useState } from "react";
import { useStore } from "../store";
import { useApi, useLiveReload } from "../lib";
import { ImageThumb } from "../components/ImageThumb";

interface Reaction { id: string; userId: string; kind: string; value: string }
interface Img { id: string; position: number; filename: string | null; thumbUrl: string; reactions: Reaction[]; threadCount: number }
interface DropPayload { drop: { id: number; title: string }; images: Img[] }

type Filter = "all" | "reacted" | "thread" | "none";

export function Sender({ slug }: { slug: string }) {
  const { navigate } = useStore();
  const { data, reload } = useApi<DropPayload>(`/drops/${slug}`);
  useLiveReload(reload, (t) => t.startsWith("reaction") || t.startsWith("message"));
  const [filter, setFilter] = useState<Filter>("all");

  const images = data?.images ?? [];
  const reactionsTotal = images.reduce((s, i) => s + i.reactions.length, 0);
  const threadsTotal = images.filter((i) => i.threadCount > 0).length;
  const reactedCount = images.filter((i) => i.reactions.length > 0).length;

  const shown = useMemo(
    () =>
      images.filter((i) => {
        if (filter === "reacted") return i.reactions.length > 0;
        if (filter === "thread") return i.threadCount > 0;
        if (filter === "none") return i.reactions.length === 0;
        return true;
      }),
    [images, filter],
  );

  const openAt = (position: number) => {
    localStorage.setItem(`mr:lastIdx:${slug}`, String(position));
    navigate(`/d/${slug}`);
  };

  const filters: Array<[Filter, string]> = [
    ["all", `All ${images.length}`],
    ["reacted", `Reacted ${reactedCount}`],
    ["thread", `Threads ${threadsTotal}`],
    ["none", `Ignored ${images.length - reactedCount}`],
  ];

  return (
    <>
      <div style={{ padding: "56px 18px 8px", display: "flex", alignItems: "center", gap: 10 }}>
        <button className="btn btn-ghost btn-icon" onClick={() => navigate("/")} style={{ width: 34, height: 34 }}>
          <i className="ph ph-caret-left" />
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ font: "500 15px Inter" }}>{data?.drop.title ?? "Drop"}</div>
          <div style={{ fontSize: 11, color: "var(--color-neutral-500)" }}>
            {images.length} images · {reactionsTotal} reactions · {threadsTotal} threads
          </div>
        </div>
        <button className="btn btn-ghost btn-icon" onClick={() => openAt(0)} style={{ width: 34, height: 34 }}>
          <i className="ph ph-play" />
        </button>
      </div>

      <div style={{ display: "flex", gap: 7, padding: "10px 18px", overflowX: "auto" }}>
        {filters.map(([key, label]) => (
          <button
            key={key}
            className="tap"
            onClick={() => setFilter(key)}
            style={{ padding: "4px 10px", borderRadius: 20, font: "500 11px Inter", whiteSpace: "nowrap", background: filter === key ? "var(--color-accent-900)" : "var(--color-surface)", color: filter === key ? "var(--color-accent-200)" : "var(--color-neutral-400)" }}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="phone-scroll" style={{ padding: "4px 14px 120px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 5 }}>
          {shown.map((i) => (
            <button key={i.id} className="tap" onClick={() => openAt(i.position)} style={{ position: "relative", aspectRatio: "1", borderRadius: 7, overflow: "hidden" }}>
              <ImageThumb src={i.thumbUrl} filename={i.filename} style={{ position: "absolute", inset: 0 }} />
              <span style={{ position: "absolute", left: 4, top: 4, display: "flex", gap: 2, fontSize: 12, textShadow: "0 1px 2px rgba(0,0,0,.6)" }}>
                {i.reactions.filter((r) => r.kind === "emoji").slice(0, 3).map((r) => r.value).join("")}
              </span>
              {i.threadCount > 0 && (
                <span style={{ position: "absolute", right: 4, bottom: 3, fontSize: 10, color: "var(--color-neutral-300)", textShadow: "0 1px 2px rgba(0,0,0,.6)" }}>💬</span>
              )}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
