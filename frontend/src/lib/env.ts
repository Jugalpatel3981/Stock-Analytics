const DEFAULT_BACKEND_URL = "http://localhost:8000";
const DEFAULT_MARKET_STREAM_URL = "ws://localhost:8000/api/v1/market/stream";
const API_PREFIX = "/api/v1";

export function getBackendUrl() {
  return (process.env.BACKEND_URL ?? DEFAULT_BACKEND_URL).replace(/\/+$/, "");
}

export function getApiBaseUrl() {
  // Server components call the backend directly. The browser calls the same-origin
  // /api/v1 path, which next.config.ts rewrites to the backend, so the auth cookie is
  // first-party even when the frontend and backend are hosted on different domains.
  if (typeof window === "undefined") {
    return `${getBackendUrl()}${API_PREFIX}`;
  }

  return API_PREFIX;
}

export function getMarketStreamUrl() {
  return process.env.NEXT_PUBLIC_MARKET_STREAM_URL ?? DEFAULT_MARKET_STREAM_URL;
}
