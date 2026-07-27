import React, { useState } from "react";

// Renders a real image with a graceful hatch-pattern fallback (used when an
// Immich thumbnail is unreachable, or in the seeded demo where assets are stubs).
export function ImageThumb({
  src,
  filename,
  style,
  className,
}: {
  src: string;
  filename?: string | null;
  style?: React.CSSProperties;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <div
      className={`hatch ${className ?? ""}`}
      style={{ position: "relative", overflow: "hidden", ...style }}
    >
      {!failed && (
        <img
          src={src}
          alt={filename ?? ""}
          onError={() => setFailed(true)}
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
        />
      )}
      {filename && (
        <span
          style={{
            position: "absolute",
            left: 5,
            bottom: 4,
            font: "500 8px ui-monospace,Menlo,monospace",
            color: "var(--color-neutral-500)",
            textShadow: "0 1px 2px rgba(0,0,0,.6)",
          }}
        >
          {filename}
        </span>
      )}
    </div>
  );
}
