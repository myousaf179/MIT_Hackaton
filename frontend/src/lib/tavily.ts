// Tavily API client for live verification of econometric signals.
//
// Tavily docs: https://docs.tavily.com/docs/rest-api/api-reference
// We POST to https://api.tavily.com/search with an API key, a free-form
// query, and ask Tavily to include a synthesized answer plus source URLs.
//
// API key resolution order:
//   1. localStorage["tavily:apiKey"]      (user-provided override at runtime)
//   2. import.meta.env.VITE_TAVILY_API_KEY (build-time injection by Vite)
//
// The key lives in the browser by design — this is a hackathon-style
// "use the provided credits" feature, not a production secret store.

export interface TavilyResultItem {
  title: string;
  url: string;
  content: string;
  score?: number;
  published_date?: string;
}

export interface TavilyResponse {
  query: string;
  answer?: string;
  results: TavilyResultItem[];
  response_time?: number;
}

const TAVILY_ENDPOINT = "https://api.tavily.com/search";
const STORAGE_KEY = "tavily:apiKey";

export function getTavilyApiKey(): string | null {
  try {
    const override = localStorage.getItem(STORAGE_KEY);
    if (override && override.trim().length > 0) return override.trim();
  } catch {
    /* SSR or storage disabled */
  }
  const fromEnv = (import.meta.env.VITE_TAVILY_API_KEY ?? "") as string;
  return fromEnv && fromEnv.trim().length > 0 ? fromEnv.trim() : null;
}

export function setTavilyApiKey(key: string) {
  try {
    if (key.trim().length === 0) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, key.trim());
    }
  } catch {
    /* ignore */
  }
}

export class TavilyError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "TavilyError";
  }
}

export async function tavilySearch(
  query: string,
  options: {
    searchDepth?: "basic" | "advanced";
    maxResults?: number;
    includeAnswer?: boolean;
    signal?: AbortSignal;
  } = {},
): Promise<TavilyResponse> {
  const apiKey = getTavilyApiKey();
  if (!apiKey) {
    throw new TavilyError(
      "Tavily API key not configured. Set VITE_TAVILY_API_KEY at build time, or paste a key into the verifier.",
    );
  }

  const body = {
    api_key: apiKey,
    query,
    search_depth: options.searchDepth ?? "basic",
    max_results: options.maxResults ?? 5,
    include_answer: options.includeAnswer ?? true,
    include_raw_content: false,
    include_images: false,
  };

  const res = await fetch(TAVILY_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: options.signal,
  });

  if (!res.ok) {
    let detail = "";
    try {
      const data = (await res.json()) as { detail?: string; error?: string };
      detail = data.detail ?? data.error ?? "";
    } catch {
      detail = await res.text().catch(() => "");
    }
    throw new TavilyError(
      `Tavily request failed (${res.status})${detail ? `: ${detail}` : ""}`,
      res.status,
    );
  }

  return (await res.json()) as TavilyResponse;
}

/**
 * Pull the first plausible numeric value (with optional currency / unit)
 * out of free-form text, e.g. "GHS 2,450 per month" → 2450.
 *
 * We look for currency-prefixed amounts first because they're the most
 * trustworthy in wage queries, then fall back to plain numbers.
 */
export function extractFirstNumber(text: string): number | null {
  if (!text) return null;
  const cleaned = text.replace(/\s+/g, " ");

  const currencyMatch = cleaned.match(
    /(?:USD|US\$|\$|€|£|GHS|GH₵|GH¢|BDT|৳|₵|GH)\s?([0-9]{1,3}(?:[,. ][0-9]{3})*(?:\.[0-9]+)?)/i,
  );
  if (currencyMatch) {
    const n = parseFloat(currencyMatch[1].replace(/[, ]/g, ""));
    if (!Number.isNaN(n)) return n;
  }

  const percentMatch = cleaned.match(/([0-9]+(?:\.[0-9]+)?)\s?%/);
  if (percentMatch) {
    const n = parseFloat(percentMatch[1]);
    if (!Number.isNaN(n)) return n;
  }

  const plainMatch = cleaned.match(
    /([0-9]{1,3}(?:[, ][0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)/,
  );
  if (plainMatch) {
    const n = parseFloat(plainMatch[1].replace(/[, ]/g, ""));
    if (!Number.isNaN(n)) return n;
  }

  return null;
}

export interface NumericComparison {
  backendValue: number;
  tavilyValue: number;
  deltaPct: number;
  agreement: "close" | "moderate" | "far";
}

/**
 * Compare a backend numeric value with one extracted from Tavily.
 * - close:    within 10%
 * - moderate: within 30%
 * - far:      anything else
 */
export function compareNumeric(
  backend: number,
  tavily: number,
): NumericComparison {
  const denom = Math.max(Math.abs(backend), 1e-9);
  const deltaPct = ((tavily - backend) / denom) * 100;
  const abs = Math.abs(deltaPct);
  const agreement: NumericComparison["agreement"] =
    abs <= 10 ? "close" : abs <= 30 ? "moderate" : "far";
  return { backendValue: backend, tavilyValue: tavily, deltaPct, agreement };
}
