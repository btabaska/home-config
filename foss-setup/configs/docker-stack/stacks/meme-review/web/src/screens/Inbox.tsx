import React, { useMemo, useState } from "react";
import { useStore } from "../store";
import { useApi, useLiveReload } from "../lib";

interface DropListItem {
  id: number;
  slug: string;
  title: string;
  from: string;
  fromYou: boolean;
  count: number;
  caption: string | null;
  createdAt: number;
  status: "new" | "awaiting" | "reviewed";
  awaiting: "me" | "them" | null;
  reviewedCount: number;
  emojis: string;
}

const PILL: Record<string, [string, string]> = {
  new: ["var(--color-accent-900)", "var(--color-accent-200)"],
  awaiting: ["var(--color-neutral-900)", "var(--color-neutral-300)"],
  reviewed: ["transparent", "var(--color-neutral-500)"],
};

export function Inbox() {
  const { partner, navigate } = useStore();
  const partnerName = partner?.display_name ?? "them";
  const { data, reload } = useApi<{ drops: DropListItem[] }>("/drops");
  useLiveReload(reload, (t) => t.startsWith("drop") || t.startsWith("reaction"));
  const [filter, setFilter] = useState<"all" | "me" | "them" | "closed">("all");

  const drops = data?.drops ?? [];
  const awaitingMe = drops.filter((d) => d.awaiting === "me").length;

  const shown = useMemo(
    () =>
      drops.filter((d) => {
        if (filter === "me") return d.awaiting === "me";
        if (filter === "them") return d.awaiting === "them";
        if (filter === "closed") return d.status === "reviewed";
        return true;
      }),
    [drops, filter],
  );

  const openDrop = (d: DropListItem) =>
    navigate(d.fromYou ? `/d/${d.slug}/all` : `/d/${d.slug}`);

  const pillLabel = (d: DropListItem) => {
    if (d.awaiting === "them") return `AWAITING ${partnerName.toUpperCase()}`;
    if (d.status === "reviewed") return "REVIEWED";
    return `NEW · ${d.reviewedCount} REVIEWED`;
  };

  const chip = (key: typeof filter, label: string) => (
    <span
      className={filter === key ? "tag tag-accent" : "tag tag-outline"}
      style={{ cursor: "pointer", whiteSpace: "nowrap" }}
      onClick={() => setFilter(key)}
    >
      {label}
    </span>
  );

  return (
    <>
      <div style={{ padding: "56px 18px 10px", display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
        <div>
          <div style={{ font: "500 11px/1 Inter", letterSpacing: ".14em", textTransform: "uppercase", color: "var(--color-neutral-500)" }}>
            Drops
          </div>
          <h3 style={{ margin: "6px 0 0", fontSize: 26 }}>Meme Review</h3>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-ghost btn-icon" onClick={() => navigate("/activity")} style={{ position: "relative", width: 38, height: 38 }}>
            <i className="ph ph-bell" />
            <span style={{ position: "absolute", top: 6, right: 6, width: 7, height: 7, borderRadius: 9, background: "var(--color-accent)" }} />
          </button>
          <button className="btn btn-ghost btn-icon" onClick={() => navigate("/settings")} style={{ width: 38, height: 38 }}>
            <i className="ph ph-gear" />
          </button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 7, padding: "12px 18px 6px", overflowX: "auto" }}>
        {chip("all", "All")}
        {chip("me", `Awaiting you ${awaitingMe || ""}`.trim())}
        {chip("them", `Awaiting ${partnerName}`)}
        {chip("closed", "Closed")}
      </div>

      <div className="phone-scroll" style={{ padding: "8px 18px 120px", display: "flex", flexDirection: "column", gap: 10 }}>
        {shown.length === 0 && (
          <div style={{ textAlign: "center", color: "var(--color-neutral-500)", fontSize: 13, padding: "40px 0" }}>
            Nothing here. <a style={{ cursor: "pointer" }} onClick={() => navigate("/compose")}>Send a drop →</a>
          </div>
        )}
        {shown.map((d) => {
          const [pillBg, pillFg] = PILL[d.status];
          return (
            <button
              key={d.id}
              className="tap"
              onClick={() => openDrop(d)}
              style={{ display: "block", background: "var(--color-surface)", borderRadius: 14, boxShadow: "var(--shadow-sm)", padding: 12 }}
            >
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <div style={{ position: "relative", width: 74, height: 74, flex: "none" }}>
                  <div className="hatch" style={{ position: "absolute", inset: 0, transform: "rotate(-7deg)", borderRadius: 8, boxShadow: "var(--shadow-sm)" }} />
                  <div className="hatch" style={{ position: "absolute", inset: 0, transform: "rotate(4deg) translate(3px,1px)", borderRadius: 8, boxShadow: "var(--shadow-sm)" }} />
                  <div className="hatch" style={{ position: "absolute", inset: 0, borderRadius: 8, boxShadow: "var(--shadow-sm)", display: "flex", alignItems: "flex-end", justifyContent: "center", paddingBottom: 5 }}>
                    <span style={{ font: "600 10px ui-monospace,Menlo,monospace", color: "var(--color-neutral-400)" }}>{d.count}</span>
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ font: "500 15px Inter" }}>{d.title}</span>
                    <span style={{ fontSize: 11, color: "var(--color-neutral-500)" }}>· {relTime(d)}</span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--color-neutral-400)", marginTop: 3 }}>
                    from {d.from} · {d.count} images
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
                    <span style={{ font: "600 10px ui-monospace,Menlo,monospace", padding: "3px 7px", borderRadius: 5, background: pillBg, color: pillFg }}>
                      {pillLabel(d)}
                    </span>
                    <span style={{ fontSize: 15, whiteSpace: "nowrap" }}>{d.emojis}</span>
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </>
  );
}

function relTime(d: DropListItem): string {
  const diff = Date.now() - d.createdAt;
  const h = Math.floor(diff / 3600000);
  if (h < 1) return `${Math.max(1, Math.floor(diff / 60000))}m`;
  if (h < 24) return `${h}h`;
  const days = Math.floor(h / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d`;
  return `${Math.floor(days / 7)}w`;
}
