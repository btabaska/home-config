import { useEffect, useState, useCallback } from "react";
import { api } from "./api";
import { useStore } from "./store";

// Small data hook with refetch + live-reload on any SSE event.
export function useApi<T>(path: string | null, deps: unknown[] = []): {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!path) {
      setLoading(false);
      return;
    }
    let alive = true;
    setLoading(true);
    api
      .get<T>(path)
      .then((d) => alive && (setData(d), setError(null)))
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, tick, ...deps]);

  return { data, error, loading, reload };
}

// Reload a resource whenever a matching realtime event lands.
export function useLiveReload(reload: () => void, match?: (type: string) => boolean) {
  const { subscribe } = useStore();
  useEffect(
    () =>
      subscribe((e) => {
        if (!match || match(e.type)) reload();
      }),
    [subscribe, reload, match],
  );
}

export const Icon = ({ name, style }: { name: string; style?: React.CSSProperties }) => (
  <i className={name} style={style} />
);

// vars() — shorthand for the nocturne CSS custom properties used inline
export const c = (name: string) => `var(--color-${name})`;
