/**
 * Client-side countdown tick (no API calls).
 */
export const UI_TICK_MS = 500;

/**
 * Backend poll interval — keeps UI fresh without overwhelming API/Redis/DB.
 * Countdowns still update every 500ms via UI_TICK_MS.
 */
export const BACKEND_POLL_MS = 2000;

/** @deprecated Use BACKEND_POLL_MS for API polling and UI_TICK_MS for countdowns */
export const LIVE_POLL_MS = BACKEND_POLL_MS;

/** How often the backend auto-processes send queues (informational for UI). */
export const SCHEDULER_TICK_SECONDS = 30;
