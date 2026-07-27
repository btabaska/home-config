// Thin fetch wrapper. All requests are same-origin and carry the session cookie.
async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers: body ? { "content-type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) throw Object.assign(new Error(data.error ?? res.statusText), { status: res.status, data });
  return data as T;
}

export const api = {
  get: <T>(p: string) => req<T>("GET", p),
  post: <T>(p: string, body?: unknown) => req<T>("POST", p, body),
  del: <T>(p: string) => req<T>("DELETE", p),

  // multipart upload
  async upload(files: File[]): Promise<{ uploads: Array<{ uploadId: string; contentHash: string; filename: string }> }> {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    const res = await fetch("/api/uploads", { method: "POST", credentials: "same-origin", body: fd });
    if (!res.ok) throw new Error("upload failed");
    return res.json();
  },
};

export interface Me {
  user: null | { id: string; display_name: string; handle: string; avatar_emoji: string | null; is_owner: number };
  partner: null | { id: string; display_name: string; avatar_emoji: string | null };
}
