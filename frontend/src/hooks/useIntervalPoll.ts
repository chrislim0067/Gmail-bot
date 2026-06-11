"use client";

import { useCallback, useEffect, useRef } from "react";
import { isUnauthorizedError } from "@/lib/api";

/**
 * Poll `fetcher` on an interval without overlapping in-flight requests.
 * Skips a tick if the previous request is still running (prevents pile-up crashes).
 */
export function useIntervalPoll(
  fetcher: (options?: { silent?: boolean }) => Promise<void>,
  intervalMs: number,
  enabled = true
) {
  const inFlight = useRef(false);
  const fetcherRef = useRef(fetcher);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const run = useCallback(async (options?: { silent?: boolean }) => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      await fetcherRef.current(options);
    } catch (err) {
      if (isUnauthorizedError(err)) return;
      if (process.env.NODE_ENV === "development") {
        console.warn("[useIntervalPoll]", err);
      }
    } finally {
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    void run();
    const timer = setInterval(() => {
      void run({ silent: true });
    }, intervalMs);
    return () => clearInterval(timer);
  }, [enabled, intervalMs, run]);

  return { refresh: run };
}
