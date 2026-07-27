import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useStore } from "../store";

export function Login() {
  const { refreshMe, navigate } = useStore();
  const [needsSetup, setNeedsSetup] = useState(false);
  const [handle, setHandle] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // first run: if there are no accounts yet, offer to create the owner account
  useEffect(() => {
    api
      .get<{ needsSetup: boolean }>("/config")
      .then((c) => setNeedsSetup(c.needsSetup))
      .catch(() => {});
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (needsSetup) {
        await api.post("/auth/register", {
          handle,
          password,
          displayName: displayName || handle,
          avatarEmoji: "🫥",
        });
      } else {
        await api.post("/auth/login", { handle, password });
      }
      await refreshMe();
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 28px 40px", gap: 18 }}>
      <div>
        <div style={{ font: "500 11px/1 Inter", letterSpacing: ".14em", textTransform: "uppercase", color: "var(--color-neutral-500)" }}>
          {needsSetup ? "First run" : "Sign in"}
        </div>
        <h2 style={{ margin: "8px 0 0", fontSize: 32 }}>Meme Review</h2>
        <p style={{ fontSize: 13, color: "var(--color-neutral-400)", marginTop: 6 }}>
          {needsSetup
            ? "Create the owner account. You can add the other household member afterwards in Settings."
            : "Two people, an endless exchange of images and the reactions they deserve."}
        </p>
      </div>

      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {needsSetup && (
          <div className="field">
            <label>Display name</label>
            <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Brandon" />
          </div>
        )}
        <div className="field">
          <label>Handle</label>
          <input className="input" autoCapitalize="none" autoCorrect="off" value={handle} onChange={(e) => setHandle(e.target.value)} placeholder="you" />
        </div>
        <div className="field">
          <label>Password</label>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        </div>
        {error && <div style={{ fontSize: 12, color: "#e88" }}>{error}</div>}
        <button className="btn btn-primary btn-block" style={{ height: 44 }} disabled={busy}>
          {busy ? "…" : needsSetup ? "Create account" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
