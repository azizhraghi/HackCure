import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState as RNAppState } from 'react-native';
import { useApi } from '../context/AppState';
import { ApiError } from '../services/backend';

/** Loads once, then every `intervalMs` (0 = once) while the app is in the foreground. */
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number, deps: unknown[], enabled = true) {
  const [data, setData] = useState<T | undefined>();
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(enabled);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      setData(await fetcherRef.current());
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(String(e), 0));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    setLoading(true);
    refresh();
    const timer = intervalMs > 0
      ? setInterval(() => { if (RNAppState.currentState === 'active') refresh(); }, intervalMs)
      : undefined;
    const sub = RNAppState.addEventListener('change', s => { if (s === 'active') refresh(); });
    return () => {
      if (timer) clearInterval(timer);
      sub.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, refresh, ...deps]);

  return { data, error, loading, refresh };
}

export function useMyProfile() {
  const api = useApi();
  return usePolling(() => api.me(), 30000, [api]);
}

/** Family side: first patient followed by the signed-in family member */
export function useFollowedPatient() {
  const api = useApi();
  const result = usePolling(() => api.followedPatients(), 30000, [api]);
  return { ...result, patient: result.data?.[0] ?? null };
}

export function useLatestTelemetry(patientId: string | null | undefined) {
  const api = useApi();
  return usePolling(() => api.latestTelemetry(patientId!), 2000, [api, patientId], !!patientId);
}

export function useAlerts(patientId: string | null | undefined, intervalMs = 10000) {
  const api = useApi();
  return usePolling(() => api.alerts(patientId!), intervalMs, [api, patientId], !!patientId);
}
