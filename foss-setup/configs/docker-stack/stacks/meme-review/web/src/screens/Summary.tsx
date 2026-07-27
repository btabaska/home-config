import React from "react";
import { useStore } from "../store";
import { useApi } from "../lib";
import { ACHIEVEMENT_ICONS } from "./Achievements";

interface SummaryPayload {
  dropTitle: string;
  images: number;
  reacted: number;
  threads: number;
  topEmoji: { value: string; count: number } | null;
  timeToReviewMs: number | null;
  achievements: Array<{ id: string; userId: string; context: any }>;
}

export function Summary({ slug }: { slug: string }) {
  const { partner, navigate } = useStore();
  const { data } = useApi<SummaryPayload>(`/drops/${slug}/summary`);
  const partnerName = partner?.display_name ?? "them";

  const mins = data?.timeToReviewMs ? Math.max(1, Math.round(data.timeToReviewMs / 60000)) : null;

  return (
    <div className="phone-scroll" style={{ padding: "70px 20px 40px", display: "flex", flexDirection: "column", gap: 18 }}>
      <div>
        <div style={{ font: "500 11px/1 Inter", letterSpacing: ".14em", textTransform: "uppercase", color: "var(--color-accent-300)" }}>
          Review complete
        </div>
        <h3 style={{ margin: "8px 0 0" }}>{data?.dropTitle ?? "Drop"}, reviewed.</h3>
        <p style={{ fontSize: 13, color: "var(--color-neutral-400)", marginTop: 6 }}>
          {partnerName} gets a notification. Either of you can keep reacting — drops never close.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <Stat big={data ? String(data.reacted) : "—"} label="images reacted" />
        <Stat big={data?.topEmoji ? data.topEmoji.value : "—"} label={data?.topEmoji ? `top reaction (${data.topEmoji.count}×)` : "top reaction"} />
        <Stat big={data ? String(data.threads) : "—"} label="text threads opened" />
        <Stat big={mins ? `${mins}m` : "—"} label="time to review" />
      </div>

      {data && data.achievements.length > 0 && (
        <div>
          <div style={{ font: "600 10px ui-monospace,Menlo,monospace", letterSpacing: ".1em", color: "var(--color-neutral-500)", marginBottom: 8 }}>
            UNLOCKED
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.achievements.map((a, i) => (
              <div key={i} className="card" style={{ padding: 12, display: "flex", flexDirection: "row", gap: 12, alignItems: "center" }}>
                <div style={{ width: 42, height: 42, borderRadius: 10, background: "var(--color-accent-900)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, color: "var(--color-accent-300)" }}>
                  <i className={ACHIEVEMENT_ICONS[a.id] ?? "ph ph-trophy"} />
                </div>
                <div>
                  <div style={{ font: "500 14px Inter", textTransform: "capitalize" }}>{a.id.replace(/_/g, " ")}</div>
                  <div style={{ fontSize: 11, color: "var(--color-neutral-400)" }}>
                    {a.context?.filename ? `${a.context.filename} was already in Drop #${a.context.previousDropId}` : "Unlocked this review"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn btn-secondary" onClick={() => navigate(`/d/${slug}/all`)} style={{ flex: 1, height: 42 }}>
          See all reactions
        </button>
        <button className="btn btn-primary" onClick={() => navigate("/compose")} style={{ flex: 1, height: 42 }}>
          Send one back
        </button>
      </div>
    </div>
  );
}

function Stat({ big, label }: { big: string; label: string }) {
  return (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ font: "600 24px Inter" }}>{big}</div>
      <div style={{ fontSize: 11, color: "var(--color-neutral-400)" }}>{label}</div>
    </div>
  );
}
