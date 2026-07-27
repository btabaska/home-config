import React from "react";
import { useStore } from "../store";
import { useApi } from "../lib";
import { ImageThumb } from "../components/ImageThumb";

interface StatsPayload {
  drops: number;
  images: number;
  streak: number;
  topReactions: Array<{ value: string; c: number }>;
  perUser: Array<{ userId: string; name: string; emoji: string | null; count: number }>;
  compatibility: { pct: number; sampled: number };
  topImage: null | { imageId: string; filename: string | null; dropId: number; reactionCount: number; threadCount: number; emojis: string; thumbUrl: string };
}

export function Stats() {
  const { partner } = useStore();
  const { data } = useApi<StatsPayload>("/stats");
  const partnerName = partner?.display_name ?? "them";
  const top = data?.topReactions ?? [];
  const max = top.length ? top[0].c : 1;

  return (
    <>
      <div style={{ padding: "56px 18px 8px" }}>
        <h3 style={{ margin: 0 }}>Stats</h3>
        <div style={{ fontSize: 12, color: "var(--color-neutral-500)", marginTop: 4 }}>All time · you &amp; {partnerName}</div>
      </div>
      <div className="phone-scroll" style={{ padding: "12px 18px 120px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 7 }}>
          <Mini big={data?.drops ?? 0} label="drops" />
          <Mini big={(data?.images ?? 0).toLocaleString()} label="images" />
          <Mini big={data?.streak ?? 0} label="day streak" />
        </div>

        <div className="card" style={{ padding: 14 }}>
          <div style={{ font: "600 10px ui-monospace,Menlo,monospace", letterSpacing: ".1em", color: "var(--color-neutral-500)" }}>EMOJI COMPATIBILITY</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 6 }}>
            <div style={{ font: "600 34px Inter" }}>{data?.compatibility.pct ?? 0}%</div>
            <div style={{ fontSize: 11, color: "var(--color-neutral-400)" }}>you react the same way {data?.compatibility.pct ?? 0}% of the time</div>
          </div>
          <div style={{ height: 5, borderRadius: 4, background: "var(--color-neutral-800)", marginTop: 10, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${data?.compatibility.pct ?? 0}%`, background: "var(--color-accent)" }} />
          </div>
        </div>

        <div className="card" style={{ padding: 14 }}>
          <div style={{ font: "600 10px ui-monospace,Menlo,monospace", letterSpacing: ".1em", color: "var(--color-neutral-500)", marginBottom: 10 }}>TOP REACTIONS</div>
          <div style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: "8px 10px", alignItems: "center", fontSize: 11 }}>
            {top.map((r) => (
              <React.Fragment key={r.value}>
                <span style={{ fontSize: 17 }}>{r.value}</span>
                <div style={{ height: 6, borderRadius: 4, background: "var(--color-neutral-800)", overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${Math.round((r.c / max) * 100)}%`, background: "var(--color-accent-500)" }} />
                </div>
                <span style={{ color: "var(--color-neutral-400)" }}>{r.c}</span>
              </React.Fragment>
            ))}
          </div>
          <div className="hr" />
          <div style={{ display: "flex", gap: 14, fontSize: 11, color: "var(--color-neutral-400)" }}>
            {(data?.perUser ?? []).map((u) => (
              <div key={u.userId}>
                {u.name} leans <span style={{ color: "var(--color-text)" }}>{u.emoji ?? "—"}</span>
              </div>
            ))}
          </div>
        </div>

        {data?.topImage && (
          <div className="card" style={{ padding: 14 }}>
            <div style={{ font: "600 10px ui-monospace,Menlo,monospace", letterSpacing: ".1em", color: "var(--color-neutral-500)", marginBottom: 10 }}>MOST-REACTED IMAGE, ALL TIME</div>
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <ImageThumb src={data.topImage.thumbUrl} filename={data.topImage.filename} style={{ width: 72, height: 72, borderRadius: 9, flex: "none" }} />
              <div>
                <div style={{ fontSize: 22, letterSpacing: "-1px" }}>{data.topImage.emojis || "—"}</div>
                <div style={{ fontSize: 11, color: "var(--color-neutral-400)", marginTop: 6 }}>
                  {data.topImage.reactionCount} reactions · {data.topImage.threadCount}-message thread · Drop #{data.topImage.dropId}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function Mini({ big, label }: { big: string | number; label: string }) {
  return (
    <div className="card" style={{ padding: 11 }}>
      <div style={{ font: "600 20px Inter" }}>{big}</div>
      <div style={{ fontSize: 10, color: "var(--color-neutral-400)" }}>{label}</div>
    </div>
  );
}
