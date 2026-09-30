import type { JobDescription, RankRequest, RankResponse } from "./types";

// In dev, Vite proxies /api to the FastAPI backend (see vite.config.ts), so an
// empty base is fine. Set VITE_API_URL to point at a different backend origin.
const BASE_URL = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function fetchHealth() {
  return request<{ status: string }>("/api/health");
}

export function fetchJd() {
  return request<JobDescription>("/api/jd");
}

export function runRanking(payload: RankRequest) {
  return request<RankResponse>("/api/rank", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
