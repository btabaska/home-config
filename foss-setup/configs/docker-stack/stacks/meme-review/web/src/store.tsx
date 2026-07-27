import React, {
  createContext,
  useContext,
  useEffect,
  useCallback,
  useState,
  useRef,
} from "react";
import { api, type Me } from "./api";

export interface AppEvent {
  id: number;
  type: string;
  actor_id: string;
  drop_id: number | null;
  image_id: string | null;
  payload_json: string | null;
  created_at: number;
}

export interface AchievementToast {
  name: string;
  icon: string;
  description: string;
  meta?: string;
}

interface Store {
  me: Me["user"];
  partner: Me["partner"];
  loading: boolean;
  route: Route;
  navigate: (path: string) => void;
  refreshMe: () => Promise<void>;
  logout: () => Promise<void>;
  // realtime
  lastEvent: AppEvent | null;
  subscribe: (fn: (e: AppEvent) => void) => () => void;
  // achievement popups (queued, shown one at a time)
  toast: AchievementToast | null;
  dismissToast: () => void;
  pushToast: (t: AchievementToast) => void;
}

export interface Route {
  path: string;
  name: string; // top-level screen key
  slug?: string; // for /d/:slug
  sub?: string; // e.g. 'all', 'summary'
}

function parse(path: string): Route {
  const clean = path.replace(/\/+$/, "") || "/";
  const parts = clean.split("/").filter(Boolean);
  if (parts[0] === "d" && parts[1]) return { path: clean, name: "review", slug: parts[1], sub: parts[2] };
  const name = parts[0] ?? "inbox";
  const map: Record<string, string> = {
    "": "inbox",
    compose: "compose",
    history: "history",
    stats: "stats",
    achievements: "achievements",
    settings: "settings",
    activity: "activity",
    login: "login",
  };
  return { path: clean, name: map[name] ?? "inbox" };
}

const Ctx = createContext<Store | null>(null);
export const useStore = () => {
  const s = useContext(Ctx);
  if (!s) throw new Error("useStore outside provider");
  return s;
};

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me["user"]>(null);
  const [partner, setPartner] = useState<Me["partner"]>(null);
  const [loading, setLoading] = useState(true);
  const [route, setRoute] = useState<Route>(parse(window.location.pathname));
  const [lastEvent, setLastEvent] = useState<AppEvent | null>(null);
  const [toast, setToast] = useState<AchievementToast | null>(null);
  const toastQueue = useRef<AchievementToast[]>([]);
  const subscribers = useRef(new Set<(e: AppEvent) => void>());

  const navigate = useCallback((path: string) => {
    window.history.pushState({}, "", path);
    setRoute(parse(path));
  }, []);

  useEffect(() => {
    const onPop = () => setRoute(parse(window.location.pathname));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const refreshMe = useCallback(async () => {
    const m = await api.get<Me>("/me");
    setMe(m.user);
    setPartner(m.partner);
  }, []);

  useEffect(() => {
    refreshMe().finally(() => setLoading(false));
  }, [refreshMe]);

  const pushToast = useCallback(
    (t: AchievementToast) => {
      setToast((cur) => {
        if (cur) {
          toastQueue.current.push(t);
          return cur;
        }
        return t;
      });
    },
    [],
  );

  const dismissToast = useCallback(() => {
    setToast(toastQueue.current.shift() ?? null);
  }, []);

  // SSE — only while signed in
  useEffect(() => {
    if (!me) return;
    const es = new EventSource("/api/stream");
    const handler = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data) as AppEvent;
        if (!data || typeof data.type !== "string") return;
        setLastEvent(data);
        subscribers.current.forEach((fn) => fn(data));
        if (data.type === "achievement.unlocked" && data.payload_json) {
          const p = JSON.parse(data.payload_json);
          // only surface the current user's own unlocks as popups
          if (data.actor_id === me.id) {
            pushToast({
              name: p.name,
              icon: p.icon,
              description: p.description,
              meta: p.context?.filename
                ? `${p.context.filename} · Drop #${p.context.previousDropId ?? p.context.dropId ?? "?"}`
                : undefined,
            });
          }
        }
      } catch {
        /* ignore malformed frames (ping/hello) */
      }
    };
    // listen to all named events plus the default
    ["message", "reaction.added", "reaction.removed", "message.added", "drop.created", "drop.opened", "drop.completed", "achievement.unlocked"].forEach(
      (name) => es.addEventListener(name, handler as EventListener),
    );
    return () => es.close();
  }, [me, pushToast]);

  const subscribe = useCallback((fn: (e: AppEvent) => void) => {
    subscribers.current.add(fn);
    return () => subscribers.current.delete(fn);
  }, []);

  const logout = useCallback(async () => {
    await api.post("/auth/logout");
    setMe(null);
    setPartner(null);
    navigate("/");
  }, [navigate]);

  const store: Store = {
    me,
    partner,
    loading,
    route,
    navigate,
    refreshMe,
    logout,
    lastEvent,
    subscribe,
    toast,
    dismissToast,
    pushToast,
  };
  return <Ctx.Provider value={store}>{children}</Ctx.Provider>;
}
