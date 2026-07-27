import React from "react";
import { useStore } from "../store";
import { useApi } from "../lib";

interface HistoryPayload {
  months: Array<{ label: string; rows: Array<{ id: number; slug: string; title: string; from: string; meta: string; emojis: string }> }>;
  totals: { drops: number; images: number; since: number | null };
}

export function History() {
  const { navigate } = useStore();
  const { data } = useApi<HistoryPayload>("/history");
  const totals = data?.totals;
  const since = totals?.since ? new Date(totals.since).toLocaleDateString("en-US", { month: "short", year: "numeric" }) : "—";

  return (
    <>
      <div style={{ padding: "56px 18px 8px" }}>
        <h3 style={{ margin: 0 }}>History</h3>
        <div style={{ fontSize: 12, color: "var(--color-neutral-500)", marginTop: 4 }}>
          {totals?.drops ?? 0} drops · {totals?.images ?? 0} images · since {since}
        </div>
      </div>
      <div className="phone-scroll" style={{ padding: "12px 18px 120px", display: "flex", flexDirection: "column", gap: 18 }}>
        {(data?.months ?? []).map((m) => (
          <div key={m.label}>
            <div style={{ font: "600 10px ui-monospace,Menlo,monospace", letterSpacing: ".1em", color: "var(--color-neutral-500)", marginBottom: 8 }}>
              {m.label}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {m.rows.map((r) => (
                <button
                  key={r.id}
                  className="tap"
                  onClick={() => navigate(`/d/${r.slug}/all`)}
                  style={{ display: "flex", alignItems: "center", gap: 10, padding: 8, borderRadius: 10, background: "var(--color-surface)" }}
                >
                  <div className="hatch" style={{ width: 34, height: 34, borderRadius: 7, flex: "none" }} />
                  <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
                    <div style={{ font: "500 13px Inter" }}>{r.title}</div>
                    <div style={{ fontSize: 10, color: "var(--color-neutral-500)" }}>{r.meta}</div>
                  </div>
                  <span style={{ fontSize: 13, whiteSpace: "nowrap" }}>{r.emojis}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
