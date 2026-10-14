// Thin REST client over structnode's local API (src/structnode/api/app.py).
// No FEM/validation logic here -- every call just forwards to the
// Python service layer and returns whatever it says. This UI has no
// authority to decide a model is valid or a result is correct; the
// backend does (see docs/ADR/0001-cem-as-source-of-truth.md).

import type { AnalysisResults } from "../cem/types";
import type { FullCemModel } from "../cem/fullTypes";

const LOCAL_DEFAULT_BASE_URL = "http://127.0.0.1:8000";
// Deployed backend for the GitHub Pages / juhongstructural.com build of the
// frontend, where there's no local `structnode api serve` to point at by
// default. Local dev (hostname is localhost/127.0.0.1) always defaults to
// the local API instead -- this only applies to a hosted deployment.
const DEPLOYED_DEFAULT_BASE_URL = "https://structnode-api.onrender.com";
const STORAGE_KEY = "structnode_api_base_url";

function defaultBaseUrl(): string {
  const { hostname } = window.location;
  if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]") {
    return LOCAL_DEFAULT_BASE_URL;
  }
  return DEPLOYED_DEFAULT_BASE_URL;
}

export function getApiBaseUrl(): string {
  return localStorage.getItem(STORAGE_KEY) ?? defaultBaseUrl();
}

export function setApiBaseUrl(url: string): void {
  localStorage.setItem(STORAGE_KEY, url);
}

export interface ApiResult<T> {
  ok: boolean;
  status: number;
  data: T | null;
  /** Network/parse-level error (backend unreachable, bad JSON). HTTP
   * error *bodies* still land in `data` -- the backend's own typed
   * errors (e.g. a validation failure) are not failures of the
   * request itself. */
  networkError: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  try {
    const resp = await fetch(`${getApiBaseUrl()}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    const data = (await resp.json().catch(() => null)) as T | null;
    return { ok: resp.ok, status: resp.status, data, networkError: null };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      data: null,
      networkError: err instanceof Error ? err.message : String(err),
    };
  }
}

export interface Capabilities {
  solvers: Record<string, Record<string, unknown>>;
  report_formats: string[];
}

export interface ValidateResult {
  status: "ok" | "error";
  errors: Array<{ code: string; message: string; path: string }>;
  warnings: Array<{ code: string; message: string; path: string }>;
  model_hash: string | null;
}

export function checkConnection(): Promise<ApiResult<Capabilities>> {
  return request<Capabilities>("/capabilities");
}

export function validateModel(cem: FullCemModel): Promise<ApiResult<ValidateResult>> {
  return request<ValidateResult>("/models/validate", {
    method: "POST",
    body: JSON.stringify({ cem }),
  });
}

export function runAnalysis(
  cem: FullCemModel,
  analysisCaseId: string,
  solver: string,
): Promise<ApiResult<AnalysisResults & ValidateResult>> {
  return request("/analysis/run", {
    method: "POST",
    body: JSON.stringify({ cem, analysis_case_id: analysisCaseId, solver }),
  });
}

export interface ReportResult {
  status: "ok" | "error";
  format?: string;
  content?: string;
  errors?: Array<{ code: string; message: string }>;
}

export function generateReport(
  results: Record<string, unknown>,
  format: "markdown" = "markdown",
): Promise<ApiResult<ReportResult>> {
  return request("/reports/generate", {
    method: "POST",
    body: JSON.stringify({ results, format }),
  });
}
