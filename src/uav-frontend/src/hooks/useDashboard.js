import { useCallback, useEffect, useRef, useState } from 'react';
import { getDashboard } from '../api/dashboardApi';

/**
 * 2-second polling for one engine's dashboard payload.
 *
 * Returns { data, error, stale, lastUpdated, twinDown }.
 *  - `data` keeps the LAST good payload on a failed poll (so the screen does not
 *    blank), but `stale` goes true and `App` shows a banner.
 *  - `twinDown` is true when the payload arrived but the twin block is missing /
 *    flagged unavailable — the honesty requirement: show raw telemetry, say the
 *    twin is unavailable, do not present stale twin numbers as live.
 */
export function useDashboard(engineId, intervalMs = 2000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [stale, setStale] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const timer = useRef(null);
  const alive = useRef(true);

  const tick = useCallback(async () => {
    try {
      const d = await getDashboard(engineId);
      if (!alive.current) return;
      setData(d);
      setError(null);
      setStale(false);
      setLastUpdated(new Date());
    } catch (e) {
      if (!alive.current) return;
      setError(e);
      setStale(true);
    }
  }, [engineId]);

  useEffect(() => {
    alive.current = true;
    setData(null);
    setStale(false);
    tick();
    timer.current = setInterval(tick, intervalMs);
    return () => {
      alive.current = false;
      clearInterval(timer.current);
    };
  }, [tick, intervalMs]);

  const twinDown = !!data && (data.twinAvailable === false || !data.twin);

  return { data, error, stale, lastUpdated, twinDown, refresh: tick };
}
