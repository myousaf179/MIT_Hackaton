// API integration for the UNMAPPED hackathon backend.
// Configure the backend URL via the `VITE_API_URL` environment variable
// (e.g. set in `.env.local` for development or in the Vercel dashboard for
// production). When unset we fall back to the in-browser mock dataset
// below — useful for local UI iteration without a running backend.

export const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

// Optional Tavily API key (read from env, never hardcoded). The frontend does
// not call Tavily directly today, but this constant is exposed so feature work
// (e.g. live econometric search) can use it without sprinkling env reads
// across the codebase.
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

function buildMock(req: AnalyzeRequest): AnalyzeResponse {
  const c = COUNTRY_DATA[req.country_code];
  const text = req.text.toLowerCase();

  // Naive skill detection from input text
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
  // Rural calibration: lower risk because manual/physical tasks dominate
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
        // attach series as JSON in description? We'll instead expose via a sibling field below
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
 * When set, we POST to `${API_BASE}/analyze` with CORS enabled.
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

  if (!API_BASE) {
    // Simulate slow network for realism
    await new Promise((r) => setTimeout(r, 900));
    return buildMock(payload);
  }

  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    mode: "cors",
    credentials: "omit",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Backend returned ${res.status}: ${res.statusText}`);
  }

  return (await res.json()) as AnalyzeResponse;
}
