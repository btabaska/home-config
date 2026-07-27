import React from "react";
import { useStore } from "../store";

const TABS: Array<[string, string, string]> = [
  ["inbox", "Drops", "ph ph-stack"],
  ["compose", "New", "ph ph-plus-circle"],
  ["history", "History", "ph ph-clock-counter-clockwise"],
  ["stats", "Stats", "ph ph-chart-bar"],
  ["achievements", "Badges", "ph ph-trophy"],
];

const PATH: Record<string, string> = {
  inbox: "/",
  compose: "/compose",
  history: "/history",
  stats: "/stats",
  achievements: "/achievements",
};

export function TabBar() {
  const { route, navigate } = useStore();
  return (
    <div
      style={{
        position: "absolute",
        left: 10,
        right: 10,
        bottom: 26,
        height: 60,
        borderRadius: 18,
        background: "rgba(35,37,50,.92)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        boxShadow: "var(--shadow-md)",
        display: "flex",
        alignItems: "center",
        padding: "0 6px",
        zIndex: 30,
      }}
    >
      {TABS.map(([key, label, icon]) => {
        const active = route.name === key;
        return (
          <button
            key={key}
            className="tap"
            onClick={() => navigate(PATH[key])}
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 3,
              padding: "8px 0",
              color: active ? "var(--color-accent-300)" : "var(--color-neutral-500)",
            }}
          >
            <i className={icon} style={{ fontSize: 19 }} />
            <span style={{ fontSize: 9.5, fontWeight: 500 }}>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
