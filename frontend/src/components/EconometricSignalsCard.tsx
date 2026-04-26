import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ExternalLink,
  Loader2,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronUp,
  KeyRound,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  compareNumeric,
  extractFirstNumber,
  getTavilyApiKey,
  setTavilyApiKey,
  TavilyError,
  tavilySearch,
  type NumericComparison,
  type TavilyResponse,
} from "@/lib/tavily";
import type { CountryCode, EconometricSignal } from "@/api";

interface Props {
  signals: EconometricSignal[];
  countryCode?: CountryCode;
}

const COUNTRY_NAME: Record<CountryCode, string> = {
  GHA: "Ghana",
  BGD: "Bangladesh",
};

const SECTOR_BY_COUNTRY: Record<CountryCode, string> = {
  GHA: "telecommunications and ICT services",
  BGD: "mobile repair and digital services",
};

/**
 * Build a focused Tavily query for a given econometric signal.
 * Pattern follows the example from the spec:
 *   "average monthly wage for mobile repair in Ghana 2025 ILO"
 */
function buildQuery(
  signal: EconometricSignal,
  countryCode?: CountryCode,
): string {
  const country = countryCode ? COUNTRY_NAME[countryCode] : "Ghana";
  const sector = countryCode ? SECTOR_BY_COUNTRY[countryCode] : "ICT services";
  const year = new Date().getFullYear();
  const type = signal.signal_type.toLowerCase();

  if (type.includes("wage")) {
    return `average monthly wage for ${sector} in ${country} ${year} ILO`;
  }
  if (type.includes("growth")) {
    return `${country} ICT services sector growth ${year} World Bank WDI`;
  }
  if (type.includes("education") || type.includes("literacy")) {
    return `${country} adult digital literacy rate ${year} UNESCO UIS`;
  }
  return `${signal.signal_type} ${country} ${year} statistics`;
}

interface VerificationState {
  loading: boolean;
  error?: string;
  response?: TavilyResponse;
  comparison?: NumericComparison;
  query?: string;
}

function AgreementBadge({ comparison }: { comparison: NumericComparison }) {
  const { agreement, deltaPct } = comparison;
  const sign = deltaPct >= 0 ? "+" : "";
  const Icon =
    agreement === "close"
      ? CheckCircle2
      : agreement === "moderate"
        ? AlertTriangle
        : XCircle;
  const label =
    agreement === "close"
      ? "Backend matches Tavily"
      : agreement === "moderate"
        ? "Partial match"
        : "Significant divergence";
  const tone =
    agreement === "close"
      ? "bg-success/10 text-success border-success/30"
      : agreement === "moderate"
        ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30"
        : "bg-destructive/10 text-destructive border-destructive/30";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs font-medium",
        tone,
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {label} ({sign}
      {deltaPct.toFixed(1)}%)
    </span>
  );
}

function TavilyKeyPrompt({ onSaved }: { onSaved: () => void }) {
  const [value, setValue] = useState("");
  return (
    <div className="rounded-md border border-dashed p-3 bg-muted/40 text-xs space-y-2">
      <div className="flex items-center gap-1.5 font-medium text-foreground">
        <KeyRound className="h-3.5 w-3.5" />
        Tavily API key required
      </div>
      <p className="text-muted-foreground">
        Provide a Tavily API key (uses your hackathon credits). It is stored
        only in this browser&rsquo;s localStorage.
      </p>
      <div className="flex gap-2">
        <Input
          type="password"
          placeholder="tvly-..."
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="h-8 text-xs"
        />
        <Button
          type="button"
          size="sm"
          disabled={!value.trim()}
          onClick={() => {
            setTavilyApiKey(value.trim());
            onSaved();
          }}
        >
          Save
        </Button>
      </div>
    </div>
  );
}

function SignalCard({
  signal,
  countryCode,
}: {
  signal: EconometricSignal;
  countryCode?: CountryCode;
}) {
  const [open, setOpen] = useState(false);
  const [needsKey, setNeedsKey] = useState(false);
  const [state, setState] = useState<VerificationState>({ loading: false });

  const query = useMemo(
    () => buildQuery(signal, countryCode),
    [signal, countryCode],
  );

  const verify = async () => {
    if (!getTavilyApiKey()) {
      setNeedsKey(true);
      setOpen(true);
      return;
    }
    setNeedsKey(false);
    setOpen(true);
    setState({ loading: true, query });

    try {
      const response = await tavilySearch(query, {
        searchDepth: "basic",
        maxResults: 5,
        includeAnswer: true,
      });

      const haystack = [
        response.answer ?? "",
        ...(response.results ?? []).map((r) => r.content),
      ].join(" \n ");
      const tavilyNum = extractFirstNumber(haystack);
      const backendNum =
        signal.numeric_value ?? extractFirstNumber(signal.value);
      const comparison =
        tavilyNum != null && backendNum != null
          ? compareNumeric(backendNum, tavilyNum)
          : undefined;

      setState({ loading: false, response, comparison, query });
    } catch (err) {
      const msg =
        err instanceof TavilyError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Verification failed.";
      setState({ loading: false, error: msg, query });
    }
  };

  return (
    <article className="p-4 rounded-lg border bg-[var(--gradient-card)] flex flex-col gap-2">
      <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">
        {signal.signal_type}
      </p>
      <p className="text-xl font-bold text-foreground tabular-nums">
        {signal.value}
      </p>
      <p className="text-sm text-muted-foreground flex-1">
        {signal.description}
      </p>
      <a
        href={signal.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-primary hover:underline inline-flex items-center gap-1 mt-1"
      >
        Source: {signal.source_name ?? "view"}{" "}
        <ExternalLink className="h-3 w-3" />
      </a>

      <div className="flex items-center gap-2 pt-2 border-t mt-1">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={verify}
          disabled={state.loading}
          className="flex-1"
        >
          {state.loading ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Verifying with Tavily…
            </>
          ) : (
            <>
              <Sparkles className="h-3.5 w-3.5" />
              Verify live with Tavily
            </>
          )}
        </Button>
        {(state.response || state.error || needsKey) && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={open ? "Collapse details" : "Expand details"}
            onClick={() => setOpen((o) => !o)}
          >
            {open ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>

      {open && (
        <div className="mt-1 space-y-3 text-sm">
          {needsKey && (
            <TavilyKeyPrompt
              onSaved={() => {
                setNeedsKey(false);
                void verify();
              }}
            />
          )}

          {state.query && !needsKey && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Query:</span>{" "}
              <span className="italic">&ldquo;{state.query}&rdquo;</span>
            </p>
          )}

          {state.error && !needsKey && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 text-destructive text-xs p-2.5">
              <p className="font-medium">Tavily error</p>
              <p className="opacity-90">{state.error}</p>
              <button
                type="button"
                className="underline mt-1"
                onClick={() => {
                  setNeedsKey(true);
                }}
              >
                Update API key
              </button>
            </div>
          )}

          {state.response && !needsKey && (
            <div className="space-y-2.5">
              {state.comparison && (
                <div className="flex flex-wrap items-center gap-2">
                  <AgreementBadge comparison={state.comparison} />
                  <span className="text-xs text-muted-foreground tabular-nums">
                    Backend:{" "}
                    <span className="font-medium text-foreground">
                      {state.comparison.backendValue.toLocaleString()}
                    </span>{" "}
                    · Tavily:{" "}
                    <span className="font-medium text-foreground">
                      {state.comparison.tavilyValue.toLocaleString()}
                    </span>
                  </span>
                </div>
              )}

              {state.response.answer && (
                <div className="rounded-md border bg-background/60 p-3">
                  <p className="text-xs font-semibold text-foreground mb-1 inline-flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    Tavily synthesis
                  </p>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {state.response.answer}
                  </p>
                </div>
              )}

              {state.response.results && state.response.results.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-foreground mb-1.5">
                    Sources
                  </p>
                  <ul className="space-y-1.5">
                    {state.response.results.slice(0, 5).map((r) => (
                      <li
                        key={r.url}
                        className="text-xs flex items-start gap-1.5"
                      >
                        <ExternalLink className="h-3 w-3 mt-0.5 shrink-0 text-muted-foreground" />
                        <a
                          href={r.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline break-words"
                          title={r.url}
                        >
                          {r.title || r.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!state.comparison && (
                <p className="text-[11px] text-muted-foreground italic">
                  Could not auto-extract a numeric value from Tavily&rsquo;s
                  response — review the sources above to compare manually.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

export function EconometricSignalsCard({ signals, countryCode }: Props) {
  const headline = signals.filter(
    (s) => s.signal_type !== "Education Projection Series",
  );

  return (
    <Card className="shadow-[var(--shadow-soft)]">
      <CardHeader>
        <CardTitle className="text-lg">Econometric Signals</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Live indicators sourced from ILO, World Bank &amp; UNESCO. Verify any
          value live with{" "}
          <a
            href="https://tavily.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            Tavily
          </a>
          .
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {headline.map((s, i) => (
            <SignalCard
              key={`${s.signal_type}-${i}`}
              signal={s}
              countryCode={countryCode}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
