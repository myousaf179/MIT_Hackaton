// API integration for the UNMAPPED hackathon backend.
//
// Configuration:
//   - In development the Vite dev server proxies `/api/*` to the backend
//     (configured in `vite.config.ts`) so the browser never sees CORS.
//   - In production builds set `VITE_API_BASE` to the deployed backend origin
//     (e.g. "https://unmapped-backend.onrender.com"). When unset we fall
//     through to the same `/api` path which assumes the backend is hosted on
//     the same origin or behind a reverse proxy.

const RAW_API_BASE = (
  (import.meta as unknown as { env?: Record<string, string | undefined> }).env
    ?.VITE_API_BASE ?? ""
).trim();

// Default to the same-origin `/api` prefix (which the dev server proxies).
// When the user sets `VITE_API_BASE` we use that origin verbatim so it can
// point at the deployed backend in production.
export const API_BASE =
  RAW_API_BASE === "" ? "/api" : RAW_API_BASE.replace(/\/$/, "");

export type CountryCode = "GHA" | "BGD";

export interface SkillMatch {
  name: string;
  isco_code: string;
  esco_code: string;
  confidence: number; // 0..1
}

export interface EconometricSignal {
  signal_type: string;
  value: string;
  numeric_value?: number;
  year?: number;
  description: string;
  source_url?: string;
  source_name?: string;
}

export interface RiskAssessment {
  base_risk: number; // 0..100
  calibrated_risk: number; // 0..100
  reduction_pct: number;
  durable_skills: string[];
  adjacent_skills: string[];
}

export interface PortableCredential {
  "@context": string[];
  type: string[];
  issuer: string;
  issuanceDate: string;
  credentialSubject: Record<string, unknown>;
}

export interface AnalyzeResponse {
  profile: SkillMatch[];
  risk_assessment: RiskAssessment;
  econometric_signals: EconometricSignal[];
  portable_credential: PortableCredential;
}

export interface AnalyzeRequest {
  text: string;
  country_code: CountryCode;
  is_rural: boolean;
}

/**
 * Analyze user-described skills against ISCO/ESCO and LMIC econometric signals.
 *
 * Sends a POST to `${API_BASE}/analyze` with CORS enabled. Throws on any
 * non-2xx response so the caller can show an error / retry UI.
 */
export async function analyzeSkills(
  text: string,
  countryCode: CountryCode,
  isRural: boolean,
): Promise<AnalyzeResponse> {
  const payload: AnalyzeRequest = {
    text,
    country_code: countryCode,
    is_rural: isRural,
  };

  const url = `${API_BASE}/analyze`;
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      mode: "cors",
      credentials: "omit",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    // Network failure (offline, DNS, CORS preflight rejected). Surface a
    // friendly message; the caller decides whether to retry.
    const cause = err instanceof Error ? err.message : String(err);
    throw new Error(`Network error contacting analysis backend: ${cause}`);
  }

  if (!res.ok) {
    let detail = "";
    try {
      detail = await res.text();
    } catch {
      /* ignore */
    }
    const trimmed = detail.length > 200 ? `${detail.slice(0, 200)}…` : detail;
    throw new Error(
      `Backend returned ${res.status} ${res.statusText}${trimmed ? ` — ${trimmed}` : ""}`,
    );
  }

  return (await res.json()) as AnalyzeResponse;
}
