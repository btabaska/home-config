import React from "react";
import { useStore } from "../store";

export function AchievementPopup() {
  const { toast, dismissToast } = useStore();
  if (!toast) return null;
  return (
    <div
      onClick={dismissToast}
      style={{
        position: "absolute",
        inset: 0,
        background: "rgba(16,17,32,.72)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 26,
        animation: "fade .18s",
        zIndex: 90,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--color-surface)",
          borderRadius: 18,
          boxShadow: "var(--shadow-lg)",
          padding: "24px 20px",
          textAlign: "center",
          animation: "pop .34s cubic-bezier(.2,1.3,.4,1)",
          maxWidth: 300,
        }}
      >
        <div
          style={{
            font: "600 10px ui-monospace,Menlo,monospace",
            letterSpacing: ".14em",
            color: "var(--color-accent-300)",
          }}
        >
          ACHIEVEMENT UNLOCKED
        </div>
        <div
          style={{
            width: 62,
            height: 62,
            margin: "16px auto 0",
            borderRadius: 16,
            background: "var(--color-accent-900)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 30,
            color: "var(--color-accent-300)",
            boxShadow: "0 0 0 1px var(--color-accent-700),0 0 32px rgba(145,132,217,.35)",
          }}
        >
          <i className={toast.icon} />
        </div>
        <h4 style={{ margin: "14px 0 0" }}>{toast.name}</h4>
        <div
          style={{
            fontSize: 12.5,
            color: "var(--color-neutral-400)",
            marginTop: 6,
            lineHeight: 1.5,
          }}
        >
          {toast.description}
        </div>
        {toast.meta && (
          <div
            style={{
              font: "600 9px ui-monospace,Menlo,monospace",
              color: "var(--color-neutral-500)",
              marginTop: 12,
            }}
          >
            {toast.meta}
          </div>
        )}
        <button className="btn btn-primary btn-block" onClick={dismissToast} style={{ height: 40, marginTop: 18 }}>
          Nice
        </button>
      </div>
    </div>
  );
}
