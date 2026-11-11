// @ts-check
/**
 * Pure constants and URL helpers for the XeroxUAV WHEP browser player.
 * Zero magic numbers and zero hardcoded IP addresses.
 */

export const DEFAULT_WEBRTC_HTTP_PORT = 8889;
export const DEFAULT_STREAM_PATH = "cam";
export const ICE_GATHER_TIMEOUT_MS = 2000;
export const HTTP_STATUS_NOT_FOUND = 404;
export const HTTP_STATUS_UNAUTHORIZED = 401;
export const HTTP_STATUS_FORBIDDEN = 403;

/** @enum {string} */
export const PlayerState = Object.freeze({
  IDLE: "idle",
  CONNECTING: "connecting",
  LIVE: "live",
  ERROR: "error",
});

/**
 * State labels in Persian for the GCS status badge.
 * @type {Readonly<Record<string, string>>}
 */
export const STATE_LABELS_FA = Object.freeze({
  [PlayerState.IDLE]: "آماده اتصال",
  [PlayerState.CONNECTING]: "در حال اتصال...",
  [PlayerState.LIVE]: "پخش زنده",
  [PlayerState.ERROR]: "خطای ارتباط",
});

/**
 * Derive the default MediaMTX WHEP URL dynamically from the current page URL.
 * Supports overriding via `?whep=<url>` query parameter without hardcoding IPs.
 *
 * @param {{ hostname: string, protocol: string, search: string }} pageLocation
 * @returns {string}
 */
export function buildDefaultWhepUrl(pageLocation) {
  const params = new URLSearchParams(pageLocation.search);
  const overrideUrl = params.get("whep");
  if (overrideUrl && overrideUrl.trim().length > 0) {
    return overrideUrl.trim();
  }
  const host = pageLocation.hostname || "localhost";
  const scheme = pageLocation.protocol === "https:" ? "https:" : "http:";
  return `${scheme}//${host}:${DEFAULT_WEBRTC_HTTP_PORT}/${DEFAULT_STREAM_PATH}/whep`;
}
