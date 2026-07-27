import React from "react";

// Minimal iOS-style chrome (dynamic island + status bar + home indicator),
// distilled from the prototype's ios-frame.jsx. Dark theme only.
export function StatusBar() {
  const c = "#fff";
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: 54,
        zIndex: 40,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "18px 30px 0",
        pointerEvents: "none",
      }}
    >
      <span style={{ fontWeight: 600, fontSize: 15, color: c, letterSpacing: 0.2 }}>9:41</span>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <svg width="18" height="11" viewBox="0 0 19 12">
          <rect x="0" y="7.5" width="3.2" height="4.5" rx="0.7" fill={c} />
          <rect x="4.8" y="5" width="3.2" height="7" rx="0.7" fill={c} />
          <rect x="9.6" y="2.5" width="3.2" height="9.5" rx="0.7" fill={c} />
          <rect x="14.4" y="0" width="3.2" height="12" rx="0.7" fill={c} />
        </svg>
        <svg width="24" height="12" viewBox="0 0 27 13">
          <rect x="0.5" y="0.5" width="23" height="12" rx="3.5" stroke={c} strokeOpacity="0.35" fill="none" />
          <rect x="2" y="2" width="20" height="9" rx="2" fill={c} />
          <path d="M25 4.5V8.5C25.8 8.2 26.5 7.2 26.5 6.5C26.5 5.8 25.8 4.8 25 4.5Z" fill={c} fillOpacity="0.4" />
        </svg>
      </div>
    </div>
  );
}

export function PhoneChrome() {
  return (
    <>
      <div className="island" />
      <StatusBar />
      <div className="home-indicator" />
    </>
  );
}
