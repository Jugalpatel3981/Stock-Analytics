const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";
const DEFAULT_MARKET_STREAM_URL = "ws://localhost:8000/api/v1/market/stream";

export function getApiBaseUrl() {
  if (typeof window === "undefined") {
    return process.env.API_INTERNAL_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

export function getMarketStreamUrl() {
  return process.env.NEXT_PUBLIC_MARKET_STREAM_URL ?? DEFAULT_MARKET_STREAM_URL;
}
