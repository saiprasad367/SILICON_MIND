/**
 * api.ts - All backend API calls
 */

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:5000";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AnalysisResponse {
  design: {
    name: string;
    device: string;
    family: string;
    healthScore: number;
    bitstreamReadiness: number;
    designStatus: string;
    confidence: number;
    modelUsed: string;
    classProbabilities?: Record<string, number>;
  };
  power: {
    total: number;
    dynamic: number;
    static: number;
    breakdown: Array<{ name: string; value: number; color: string }>;
    modules: Array<{ name: string; power: number; hot?: boolean }>;
  };
  timing: {
    slack: number;
    status: "PASS" | "FAIL";
    targetFreq: number;
    achievedFreq: number;
    criticalPath: {
      delay: number;
      logicDelay?: number;
      routingDelay?: number;
      stages: Array<{ name: string; type: string; delay: number; bottleneck?: boolean }>;
    };
  };
  utilization: Array<{ name: string; used: number; total: number; pct: number }>;
  congestion: { overall: number; hotspots: Array<{ region: string; level: number }> };
  drc: Array<{ id: string; severity: "error" | "warning" | "info"; rule: string; message: string; fix: string }>;
  insights: Array<{ type: "issue" | "opportunity" | "warning"; title: string; text: string }>;
  recommendations: Array<{ priority: "high" | "medium" | "low"; title: string; impact: string; effort: string; reason: string }>;
  rootCause: string;
  bestStrategy: string;
  aiPrediction: string;
  rlInfo?: Record<string, unknown>;
  powerVsPerf: Array<{ freq: number; power: number; perf: number }>;
  clocks: Array<{ name: string; freq: number; domain: string; status: string }>;
  cdcViolations: number;
}

export interface WhatIfRequest {
  clock: number;
  pipeline: number;
  mode: "perf" | "balanced" | "power";
}

export interface WhatIfResponse {
  predicted_slack_ns: number;
  predicted_power_w: number;
  projected_fmax_mhz: number;
  lut_delta_pct: number;
  timing_status: "PASS" | "FAIL";
}

// ─── Upload ───────────────────────────────────────────────────────────────────

export async function uploadFiles(files: FileList | File[]): Promise<{ session_id: string; files_received: string[] }> {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append("files", f));
  const res = await fetch(`${BASE}/api/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error ?? `Upload failed (${res.status})`);
  }
  return res.json();
}

// ─── Fetch analysis ───────────────────────────────────────────────────────────

export async function fetchAnalysis(): Promise<AnalysisResponse> {
  const res = await fetch(`${BASE}/api/analyze`);
  if (res.status === 404) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error ?? "No analysis available");
  }
  if (!res.ok) throw new Error(`Analysis fetch failed (${res.status})`);
  return res.json();
}

// ─── What-If ─────────────────────────────────────────────────────────────────

export async function runWhatIf(params: WhatIfRequest): Promise<WhatIfResponse> {
  const res = await fetch(`${BASE}/api/whatif`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`What-if failed (${res.status})`);
  return res.json();
}

// ─── Report ───────────────────────────────────────────────────────────────────

export function reportUrl(designName?: string): string {
  return designName ? `${BASE}/api/report/${encodeURIComponent(designName)}` : `${BASE}/api/report`;
}

// ─── Retrain ──────────────────────────────────────────────────────────────────

export async function triggerRetrain(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${BASE}/api/retrain`, { method: "POST" });
  if (!res.ok) throw new Error(`Retrain failed (${res.status})`);
  return res.json();
}

// ─── Status ───────────────────────────────────────────────────────────────────

export async function fetchStatus(): Promise<{ status: string; analysis_ready: boolean }> {
  const res = await fetch(`${BASE}/api/status`);
  if (!res.ok) throw new Error("Status check failed");
  return res.json();
}
