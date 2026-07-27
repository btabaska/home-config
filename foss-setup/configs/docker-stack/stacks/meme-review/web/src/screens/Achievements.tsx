import React from "react";
import { useStore } from "../store";
import { useApi, useLiveReload } from "../lib";

export const ACHIEVEMENT_ICONS: Record<string, string> = {
  boomerang: "ph ph-boomerang",
  mega_drop: "ph ph-stack-plus",
  evergreen: "ph ph-tree",
  left_on_read: "ph ph-eye-slash",
  skull_merchant: "ph ph-skull",
  novelist: "ph ph-note-pencil",
  same_brain: "ph ph-brain",
  speedrun: "ph ph-timer",
};

interface Badge {
  id: string;
  name: string;
  icon: string;
  description: string;
  unlocked: boolean;
  unlockedBy: Array<{ name: string; unlockedAt: number }>;
}
interface Payload {
  achievements: Badge[];
  unlockedCount: number;
  total: number;
}

export function Achievements() {
  const { pushToast } = useStore();
  const { data, reload } = useApi<Payload>("/achievements");
  useLiveReload(reload, (t) => t === "achievement.unlocked");
  const list = data?.achievements ?? [];

  return (
    <>
      <div style={{ padding: "56px 18px 8px" }}>
        <h3 style={{ margin: 0 }}>Achievements</h3>
        <div style={{ fontSize: 12, color: "var(--color-neutral-500)", marginTop: 4 }}>
          {data?.unlockedCount ?? 0} of {data?.total ?? 0} unlocked
        </div>
      </div>
      <div className="phone-scroll" style={{ padding: "12px 18px 120px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, alignContent: "start" }}>
        {list.map((b) => (
          <div
            key={b.id}
            style={{
              borderRadius: 12,
              padding: 12,
              background: b.unlocked ? "var(--color-surface)" : "transparent",
              boxShadow: "var(--shadow-sm)",
              opacity: b.unlocked ? 1 : 0.55,
            }}
          >
            <div style={{ width: 34, height: 34, borderRadius: 9, background: b.unlocked ? "var(--color-accent-900)" : "var(--color-neutral-900)", display: "flex", alignItems: "center", justifyContent: "center", color: b.unlocked ? "var(--color-accent-300)" : "var(--color-neutral-600)", fontSize: 17 }}>
              <i className={b.icon} />
            </div>
            <div style={{ font: "500 13px Inter", marginTop: 9 }}>{b.name}</div>
            <div style={{ fontSize: 10.5, color: "var(--color-neutral-400)", marginTop: 3, lineHeight: 1.4 }}>{b.description}</div>
            <div style={{ font: "600 9px ui-monospace,Menlo,monospace", color: "var(--color-neutral-500)", marginTop: 7 }}>
              {b.unlocked ? `UNLOCKED${b.unlockedBy[0] ? " · " + b.unlockedBy[0].name : ""}` : "LOCKED"}
            </div>
          </div>
        ))}
        <button
          className="btn btn-secondary btn-block"
          onClick={() =>
            pushToast({
              name: "Evergreen",
              icon: "ph ph-tree",
              description: "The same meme has now appeared in 10 separate drops. It refuses to die.",
              meta: "IMG_0912 · drops #6, 11, 18, 23, 29, 31, 37, 40, 44, 47",
            })
          }
          style={{ gridColumn: "span 2", height: 40, marginTop: 4, fontSize: 12 }}
        >
          Demo: fire an unlock popup
        </button>
      </div>
    </>
  );
}
