// API integration for the UNMAPPED hackathon backend.
// Configure the backend URL via the `VITE_API_URL` environment variable
// (e.g. set in `.env.local` for development or in the Vercel dashboard for
// production). When unset we fall back to the in-browser mock dataset
// below — useful for local UI iteration without a running backend.

export const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

// Optional Tavily API key (read from env, never hardcoded). Some UI panels
// can call Tavily from the client for live verification; the backend can also
// use Tavily server-side (preferred for production).
export const TAVILY_API_KEY: string = import.meta.env.VITE_TAVILY_API_KEY ?? "";

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
  source_url: string;
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
  "@context"?: string | string[];
  type?: string | string[];
  issuer?: string;
  issuanceDate?: string;
  credentialSubject?: Record<string, unknown>;
  [k: string]: unknown;
}

/** Shape expected by the Lovable / TanStack UI components */
export interface AnalyzeResponse {
  profile: SkillMatch[];
  risk_assessment: RiskAssessment;
  econometric_signals: EconometricSignal[];
  portable_credential: PortableCredential;
  /** Only present when talking to the real FastAPI backend */
  _raw?: Record<string, unknown>;
}

export interface AnalyzeRequest {
  text: string;
  country_code: CountryCode;
  is_rural: boolean;
  language?: string;
}

const COUNTRY_DATA: Record<
  CountryCode,
  {
    name: string;
    currency: string;
    wage: string;
    wageDesc: string;
    growth: string;
    education: { year: number; value: number }[];
  }
> = {
  GHA: {
    name: "Ghana",
    currency: "GHS",
    wage: "GHS 2,200 / month",
    wageDesc: "Average wage in telecommunications & ICT services (Ghana, 2024)",
    growth: "+8.4% YoY",
    education: [
      { year: 2025, value: 62 },
      { year: 2027, value: 66 },
      { year: 2029, value: 71 },
      { year: 2031, value: 75 },
      { year: 2033, value: 79 },
      { year: 2035, value: 83 },
    ],
  },
  BGD: {
    name: "Bangladesh",
    currency: "BDT",
    wage: "BDT 28,500 / month",
    wageDesc: "Average wage in mobile repair & digital services (Bangladesh, 2024)",
    growth: "+11.2% YoY",
    education: [
      { year: 2025, value: 58 },
      { year: 2027, value: 63 },
      { year: 2029, value: 69 },
      { year: 2031, value: 74 },
      { year: 2033, value: 78 },
      { year: 2035, value: 82 },
    ],
  },
};

function escoCodeFromUri(uri: string | undefined): string {
  if (!uri) return "—";
  const seg = uri.split("/").filter(Boolean).pop() ?? "—";
  return seg.length > 24 ? seg.slice(0, 24) + "…" : seg;
}

const WB_LABELS: Record<string, string> = {
  "SL.UEM.1524.ZS": "Youth unemployment (WDI)",
  "SL.EMP.GROW": "Employment growth (WDI)",
  "NY.GDP.MKTP.KD.ZG": "GDP growth (WDI)",
  "IT.NET.USER.ZS": "Internet users (WDI)",
  "SE.SEC.CMPT.LO.ZS": "Lower-secondary completion (WDI)",
};

function humanizeSignalType(st: string): string {
  if (WB_LABELS[st]) return WB_LABELS[st];
  const map: Record<string, string> = {
    wage_floor: "Wage floor (sector)",
    education_projection: "Education projection (adults 15+)",
    sector_employment: "Sector employment (ILO ILOSTAT)",
  };
  if (map[st]) return map[st];
  return st.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Map FastAPI `POST /analyze` JSON to the flatter structure the UI was built
 * for (Lovable mock). Keeps the chart + cards working with real WDI/ILO data.
 */
export function mapBackendAnalyzeToUI(raw: Record<string, unknown>): AnalyzeResponse {
  const prof = raw.profile as
    | { skills?: Array<Record<string, unknown>> }
    | undefined;
  const risk = raw.risk_assessment as Record<string, unknown> | undefined;
  const econ = (raw.econometric_signals as Array<Record<string, unknown>>) ?? [];
  const eduTr = raw.education_trajectory as
    | { points?: Array<Record<string, unknown>>; source_name?: string }
    | undefined;
  const cred = (raw.portable_credential as Record<string, unknown>) ?? {};

  const skills = prof?.skills ?? [];
  const profile: SkillMatch[] = skills.map((s) => ({
    name: String(s.esco_label ?? s.name ?? "Skill"),
    isco_code: String(s.isco_code ?? ""),
    esco_code: escoCodeFromUri(s.esco_uri as string | undefined),
    confidence: typeof s.confidence === "number" ? s.confidence : 0,
  }));

  const basePct =
    typeof risk?.base_risk_percentage === "number"
      ? (risk.base_risk_percentage as number)
      : Number(risk?.base_risk ?? 0) * 100;
  const calPct =
    typeof risk?.overall_risk_percentage === "number"
      ? (risk.overall_risk_percentage as number)
      : Number(risk?.overall_risk ?? 0) * 100;

  const riskOut: RiskAssessment = {
    base_risk: Math.round(basePct * 10) / 10,
    calibrated_risk: Math.round(calPct * 10) / 10,
    reduction_pct: Math.max(0, Math.round((basePct - calPct) * 10) / 10),
    durable_skills: (risk?.durable_skills as string[]) ?? [],
    adjacent_skills: (risk?.adjacent_skills_suggested as string[]) ?? [],
  };

  const signalsOut: EconometricSignal[] = [];

  for (const sig of econ) {
    const st = String(sig.signal_type ?? "signal");
    if (st === "education_projection") {
      continue;
    }
    const val = sig.value;
    const unit = sig.unit != null && sig.unit !== "" ? ` ${sig.unit}` : "";
    const valueStr = val != null && val !== "" ? `${val}${unit}`.trim() : "—";
    const y =
      sig.year != null && sig.year !== ""
        ? Number(sig.year)
        : undefined;
    signalsOut.push({
      signal_type: humanizeSignalType(st),
      value: valueStr,
      numeric_value: typeof val === "number" ? val : undefined,
      year: y !== undefined && !Number.isNaN(y) ? y : undefined,
      description: String(
        (sig as { note?: string }).note ??
          (sig as { source_name?: string }).source_name ??
          "",
      ),
      source_url: String(
        (sig as { source_url?: string }).source_url ?? "",
      ),
      source_name: (sig as { source_name?: string }).source_name,
    });
  }

  for (const pt of eduTr?.points ?? []) {
    const y = pt.year != null ? Number(pt.year) : undefined;
    const v = pt.value != null ? Number(pt.value) : undefined;
    if (y == null || Number.isNaN(y) || v == null || Number.isNaN(v)) continue;
    signalsOut.push({
      signal_type: "Education Projection Series",
      value: `${v}%`,
      numeric_value: v,
      year: y,
      description: String(
        pt.label ?? "Projected share of adults with upper-secondary+ education",
      ),
      source_url: String(pt.source_url ?? ""),
      source_name: eduTr?.source_name ?? "Wittgenstein Centre",
    });
  }

  return {
    profile,
    risk_assessment: riskOut,
    econometric_signals: signalsOut,
    portable_credential: cred as PortableCredential,
    _raw: raw,
  };
}

function buildMock(req: AnalyzeRequest): AnalyzeResponse {
  const c = COUNTRY_DATA[req.country_code];
  const text = req.text.toLowerCase();

  const candidates: SkillMatch[] = [];
  if (/(repair|fix|electron|phone|hardware)/.test(text))
    candidates.push({
      name: "Mobile device repair & diagnostics",
      isco_code: "7421",
      esco_code: "S5.7.1",
      confidence: 0.92,
    });
  if (/(language|english|french|bangla|twi|speak)/.test(text))
    candidates.push({
      name: "Multilingual customer communication",
      isco_code: "4222",
      esco_code: "S2.4.1",
      confidence: 0.86,
    });
  if (/(python|code|program|software|youtube|self.?taught)/.test(text))
    candidates.push({
      name: "Self-directed software development (Python)",
      isco_code: "2512",
      esco_code: "S6.0.2",
      confidence: 0.74,
    });
  if (/(sell|market|trade|business|shop|customer)/.test(text))
    candidates.push({
      name: "Informal commerce & customer service",
      isco_code: "5223",
      esco_code: "S4.3.1",
      confidence: 0.81,
    });
  if (/(farm|crop|agri|harvest|livestock)/.test(text))
    candidates.push({
      name: "Agricultural production techniques",
      isco_code: "6111",
      esco_code: "S3.1.0",
      confidence: 0.83,
    });
  if (candidates.length === 0)
    candidates.push({
      name: "General problem-solving & adaptability",
      isco_code: "9999",
      esco_code: "T1.0.0",
      confidence: 0.6,
    });

  const baseRisk = req.country_code === "GHA" ? 48 : 54;
  const ruralAdj = req.is_rural ? 14 : 6;
  const calibrated = Math.max(8, baseRisk - ruralAdj);
  const reduction = baseRisk - calibrated;

  return {
    profile: candidates,
    risk_assessment: {
      base_risk: baseRisk,
      calibrated_risk: calibrated,
      reduction_pct: reduction,
      durable_skills: req.is_rural
        ? ["Hands-on repair", "Local language fluency", "Community trust networks"]
        : ["Customer empathy", "Multilingual communication", "Hands-on diagnostics"],
      adjacent_skills: [
        "Solar / off-grid electronics",
        "Mobile money agent operations",
        "Basic data entry & spreadsheets",
        "Digital marketing fundamentals",
      ],
    },
    econometric_signals: [
      {
        signal_type: "Average Wage",
        value: c.wage,
        description: c.wageDesc,
        source_url: "https://ilostat.ilo.org/",
        source_name: "ILOSTAT",
      },
      {
        signal_type: "Sector Growth",
        value: c.growth,
        description: `ICT services sector growth in ${c.name} (World Bank WDI, 2023)`,
        source_url: "https://data.worldbank.org/indicator/NV.IND.MANF.KD.ZG",
        source_name: "World Bank WDI",
      },
      {
        signal_type: "Education Projection",
        value: `${c.education[c.education.length - 1].value}% literacy by 2035`,
        description: `Projected adult digital literacy rate in ${c.name}, 2025–2035`,
        source_url: "https://uis.unesco.org/",
        source_name: "UNESCO UIS",
      },
      ...c.education.map<EconometricSignal>((p) => ({
        signal_type: "Education Projection Series",
        value: `${p.value}%`,
        numeric_value: p.value,
        year: p.year,
        description: `Projected digital literacy in ${c.name} for ${p.year}`,
        source_url: "https://uis.unesco.org/",
        source_name: "UNESCO UIS",
      })),
    ],
    portable_credential: {
      "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/unmapped/v1",
      ],
      type: ["VerifiableCredential", "SkillsProfileCredential"],
      issuer: "did:web:unmapped.worldbank.org",
      issuanceDate: new Date().toISOString(),
      credentialSubject: {
        id: `did:example:${Math.random().toString(36).slice(2, 10)}`,
        country: c.name,
        countryCode: req.country_code,
        context: req.is_rural ? "rural" : "urban",
        skills: candidates.map((s) => ({
          name: s.name,
          isco: s.isco_code,
          esco: s.esco_code,
          confidence: s.confidence,
        })),
        calibratedRisk: calibrated,
      },
    },
  };
}

/**
 * Analyze user-described skills against ISCO/ESCO and LMIC econometric signals.
 *
 * When API_BASE is empty we return mock data (good for local UI iteration).
 * When set, we POST to `${API_BASE}/analyze` with CORS enabled and map the
 * FastAPI response to the UI shape.
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
    language: "en",
  };

  if (!API_BASE) {
    await new Promise((r) => setTimeout(r, 900));
    return buildMock(payload);
  }

  const res = await fetch(`${API_BASE.replace(/\/$/, "")}/analyze`, {
    method: "POST",
    mode: "cors",
    credentials: "omit",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      text: payload.text,
      country_code: countryCode,
      is_rural: isRural,
      language: "en",
    }),
  });

  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(
      `Backend returned ${res.status}: ${t || res.statusText}`,
    );
  }

  const raw = (await res.json()) as Record<string, unknown>;
  if (raw.profile && (raw as { profile: { skills?: unknown } }).profile.skills) {
    return mapBackendAnalyzeToUI(raw);
  }
  return raw as unknown as AnalyzeResponse;
}
