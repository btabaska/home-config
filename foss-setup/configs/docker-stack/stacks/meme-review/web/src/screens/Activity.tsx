import React from "react";
import { useStore } from "../store";
import { useApi, useLiveReload } from "../lib";

interface Payload {
  activity: Array<{ icon: string; text: string; when: string }>;
}

export function Activity() {
  const { navigate } = useStore();
  const { data, reload } = useApi<Payload>("/activity");
  useLiveReload(reload);
  const items = data?.activity ?? [];

  return (
    <>
      <div style={{ padding: "56px 18px 8px", display: "flex", alignItems: "center", gap: 10 }}>
        <button className="btn btn-ghost btn-icon" onClick={() => navigate("/")} style={{ width: 34, height: 34 }}>
          <i className="ph ph-caret-left" />
        </button>
        <h4 style={{ margin: 0 }}>Activity</h4>
      </div>
      <div className="phone-scroll" style={{ padding: "12px 18px 40px", display: "flex", flexDirection: "column", gap: 8 }}>
        {items.length === 0 && (
          <div style={{ textAlign: "center", color: "var(--color-neutral-500)", fontSize: 13, padding: "40px 0" }}>
            No activity yet. The share link is the notification.
          </div>
        )}
        {items.map((a, i) => (
          <div key={i} style={{ display: "flex", gap: 11, padding: 11, borderRadius: 11, background: i === 0 ? "var(--color-accent-900)" : "var(--color-surface)" }}>
            <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--color-neutral-900)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15, flex: "none" }}>
              {a.icon}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, lineHeight: 1.4 }}>{a.text}</div>
              <div style={{ font: "600 9px ui-monospace,Menlo,monospace", color: "var(--color-neutral-500)", marginTop: 4 }}>{a.when}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
