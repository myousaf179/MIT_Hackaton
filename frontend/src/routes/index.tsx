import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  ArrowRight,
  BadgeCheck,
  Globe2,
  Loader2,
  MapPinned,
  AlertCircle,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { analyzeSkills, type AnalyzeResponse, type CountryCode } from "@/api";
import { SkillsProfileCard } from "@/components/SkillsProfileCard";
import { AIReadinessCard } from "@/components/AIReadinessCard";
import { EconometricSignalsCard } from "@/components/EconometricSignalsCard";
import { PortableCredentialCard } from "@/components/PortableCredentialCard";

export const Route = createFileRoute("/")({
  component: Index,
});

const STORAGE_KEY = "unmapped:lastSkillsText";
const RESULTS_KEY = "unmapped:lastResults";
const MIN_SKILLS_LENGTH = 20;
const MAX_RETRIES = 4;

const COUNTRY_LABEL: Record<CountryCode, string> = {
  GHA: "Ghana",
  BGD: "Bangladesh",
};

const CONTEXT_LABEL = {
  urban: "Urban",
  rural: "Rural",
} as const;

interface PersistedResults {
  data: AnalyzeResponse;
  country: CountryCode;
  isRural: boolean;
  text: string;
  timestamp: number;
}

function Index() {
  const [country, setCountry] = useState<CountryCode>("GHA");
  const [isRural, setIsRural] = useState(false);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const hasSubmitted = useRef(false);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Restore saved text + last results
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) setText(saved);
    } catch {
      /* ignore */
    }
    try {
      const raw = localStorage.getItem(RESULTS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as PersistedResults;
        if (parsed?.data) {
          setData(parsed.data);
          setCountry(parsed.country);
          setIsRural(parsed.isRural);
          if (parsed.text) setText(parsed.text);
          hasSubmitted.current = true;
        }
      }
    } catch {
      /* ignore */
    }
    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current);
    };
  }, []);

  // Persist text on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, text);
    } catch {
      /* ignore */
    }
  }, [text]);

  const persistResults = (
    res: AnalyzeResponse,
    c: CountryCode,
    r: boolean,
    t: string,
  ) => {
    try {
      const payload: PersistedResults = {
        data: res,
        country: c,
        isRural: r,
        text: t,
        timestamp: Date.now(),
      };
      localStorage.setItem(RESULTS_KEY, JSON.stringify(payload));
    } catch {
      /* ignore */
    }
  };

  const runAnalysis = async (
    nextCountry: CountryCode,
    nextRural: boolean,
    nextText: string,
    attempt = 0,
  ) => {
    if (nextText.trim().length < MIN_SKILLS_LENGTH) {
      toast.error(
        `Please describe your skills in at least ${MIN_SKILLS_LENGTH} characters.`,
      );
      return;
    }
    if (retryTimer.current) {
      clearTimeout(retryTimer.current);
      retryTimer.current = null;
    }
    setLoading(true);
    setError(null);
    // NOTE: we intentionally keep `data` visible so users see the last
    // successful results while a retry is in flight.
    try {
      const res = await analyzeSkills(nextText, nextCountry, nextRural);
      setData(res);
      setRetryCount(0);
      setRetrying(false);
      hasSubmitted.current = true;
      persistResults(res, nextCountry, nextRural, nextText);
    } catch (e) {
      const message =
        e instanceof Error
          ? e.message
          : "Could not reach the server. Please try again.";
      setError(message);

      if (attempt < MAX_RETRIES) {
        const delay = Math.min(16000, 2 ** attempt * 1000); // 1s, 2s, 4s, 8s
        setRetryCount(attempt + 1);
        setRetrying(true);
        toast.info(
          `Retrying in ${Math.round(delay / 1000)}s (attempt ${attempt + 1} of ${MAX_RETRIES})…`,
        );
        retryTimer.current = setTimeout(() => {
          void runAnalysis(nextCountry, nextRural, nextText, attempt + 1);
        }, delay);
      } else {
        setRetrying(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void runAnalysis(country, isRural, text);
  };

  const handleCountryChange = (next: string) => {
    const c = next as CountryCode;
    setCountry(c);
    if (hasSubmitted.current && text.trim().length >= MIN_SKILLS_LENGTH) {
      toast.info(`Switched to ${COUNTRY_LABEL[c]} - no code change required.`);
      void runAnalysis(c, isRural, text);
    }
  };

  const handleRuralChange = (next: boolean) => {
    setIsRural(next);
    if (hasSubmitted.current && text.trim().length >= MIN_SKILLS_LENGTH) {
      toast.info(`Recalibrating for ${next ? "rural" : "urban"} context…`);
      void runAnalysis(country, next, text);
    }
  };

  const handleManualRetry = () => {
    if (retryTimer.current) {
      clearTimeout(retryTimer.current);
      retryTimer.current = null;
    }
    void runAnalysis(country, isRural, text, 0);
  };

  const charCount = text.trim().length;
  const isTooShort = charCount < MIN_SKILLS_LENGTH;
  const isEmpty = charCount === 0;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(0,125,105,0.12),_transparent_32rem),linear-gradient(180deg,#f6fbff_0%,#ffffff_40%,#f8fafc_100%)]">
      <header className="sticky top-0 z-40 border-b border-[#002F6C]/10 bg-white/90 shadow-[0_10px_40px_rgba(0,47,108,0.08)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <div
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#002F6C] text-white shadow-lg shadow-[#002F6C]/20"
              aria-hidden="true"
            >
              <MapPinned className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <a
                href="/"
                className="font-display text-2xl font-black tracking-tight"
                aria-label="unmapped-ai home"
              >
                <span className="text-[#002F6C]">unmapped</span>
                <span className="text-[#007D69]">-ai</span>
              </a>
              <p className="hidden text-xs font-medium text-slate-500 sm:block">
                Closing the distance between real skills & economic opportunity
              </p>
            </div>
          </div>

          <div
            className="flex flex-wrap items-center gap-2"
            aria-label="Analysis settings"
          >
            <div className="flex rounded-full border border-[#002F6C]/10 bg-slate-50 p-1 shadow-inner">
              {(Object.keys(COUNTRY_LABEL) as CountryCode[]).map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => handleCountryChange(code)}
                  aria-pressed={country === code}
                  className={`rounded-full px-3 py-1.5 text-sm font-semibold transition motion-safe:duration-200 ${
                    country === code
                      ? "bg-[#002F6C] text-white shadow-sm"
                      : "text-slate-600 hover:bg-white hover:text-[#002F6C]"
                  }`}
                >
                  {COUNTRY_LABEL[code]}
                </button>
              ))}
            </div>
            <div className="flex rounded-full border border-[#007D69]/15 bg-emerald-50 p-1 shadow-inner">
              {(["urban", "rural"] as const).map((context) => {
                const selected = context === "rural" ? isRural : !isRural;
                return (
                  <button
                    key={context}
                    type="button"
                    onClick={() => handleRuralChange(context === "rural")}
                    aria-pressed={selected}
                    className={`rounded-full px-3 py-1.5 text-sm font-semibold transition motion-safe:duration-200 ${
                      selected
                        ? "bg-[#007D69] text-white shadow-sm"
                        : "text-emerald-800 hover:bg-white"
                    }`}
                  >
                    {CONTEXT_LABEL[context]}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12">
        <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-[linear-gradient(135deg,#eaf4ff_0%,#ffffff_52%,#fff8ec_100%)] px-5 py-8 shadow-[0_24px_80px_rgba(0,47,108,0.12)] sm:px-8 lg:px-12 lg:py-14">
          <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-[#007D69]/10 blur-3xl" />
          <div className="absolute -bottom-32 left-1/3 h-80 w-80 rounded-full bg-[#002F6C]/10 blur-3xl" />

          <div className="relative grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#002F6C]/10 bg-white/80 px-4 py-2 text-xs font-bold uppercase tracking-[0.22em] text-[#002F6C] shadow-sm">
                <Globe2 className="h-4 w-4" />
                World Bank Youth Summit
              </div>
              <div className="space-y-4">
                <h1 className="font-display text-4xl font-black leading-[0.98] tracking-tight text-slate-950 sm:text-6xl lg:text-7xl">
                  Your skills deserve to be seen.
                </h1>
                <p className="max-w-2xl text-base leading-8 text-slate-600 sm:text-lg">
                  UNMAPPED helps young people in low- and middle-income
                  countries map informal skills to real opportunities,
                  understand AI risk, and access labor market signals.
                </p>
              </div>
              <div className="grid gap-3 text-sm font-medium text-slate-600 sm:grid-cols-3">
                <div className="flex items-center gap-2 rounded-2xl bg-white/75 p-3 shadow-sm">
                  <BadgeCheck className="h-5 w-5 text-[#007D69]" />
                  ESCO/ISCO profile
                </div>
                <div className="flex items-center gap-2 rounded-2xl bg-white/75 p-3 shadow-sm">
                  <Sparkles className="h-5 w-5 text-[#002F6C]" />
                  AI readiness lens
                </div>
                <div className="flex items-center gap-2 rounded-2xl bg-white/75 p-3 shadow-sm">
                  <Globe2 className="h-5 w-5 text-amber-600" />
                  Live signals
                </div>
              </div>
            </div>

            <form
              onSubmit={handleSubmit}
              className="rounded-[1.5rem] border border-white/80 bg-white/90 p-4 shadow-[0_18px_60px_rgba(15,23,42,0.12)] backdrop-blur sm:p-6"
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <Label
                    htmlFor="skills"
                    className="text-sm font-bold text-slate-950"
                  >
                    Describe what you can do
                  </Label>
                  <p className="mt-1 text-xs text-slate-500">
                    Selected: {COUNTRY_LABEL[country]} ·{" "}
                    {isRural ? "Rural" : "Urban"}
                  </p>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-bold tabular-nums ${
                    isTooShort
                      ? "bg-slate-100 text-slate-500"
                      : "bg-emerald-50 text-[#007D69]"
                  }`}
                >
                  {charCount}/{MIN_SKILLS_LENGTH}+
                </span>
              </div>
              <Textarea
                id="skills"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Describe what you can do... e.g., 'I repair phones, speak 3 languages, learned Python from YouTube'"
                className="min-h-44 resize-y rounded-2xl border-slate-200 bg-slate-50/70 p-4 text-base leading-7 shadow-inner focus-visible:ring-[#007D69]"
                aria-invalid={isTooShort}
                aria-describedby="skills-hint"
              />
              <p
                id="skills-hint"
                className={`mt-3 text-xs ${
                  isEmpty
                    ? "text-slate-500"
                    : isTooShort
                      ? "text-amber-700"
                      : "text-[#007D69]"
                }`}
              >
                {isEmpty
                  ? "Tell us what you do - even a sentence or two helps."
                  : isTooShort
                    ? `A little more detail helps - ${MIN_SKILLS_LENGTH - charCount} more character${
                        MIN_SKILLS_LENGTH - charCount === 1 ? "" : "s"
                      } to enable analysis.`
                    : "Looks good - ready to analyze."}
              </p>

              <Button
                type="submit"
                disabled={loading || isTooShort}
                className="mt-5 h-14 w-full rounded-2xl bg-[#007D69] text-base font-bold text-white shadow-lg shadow-[#007D69]/20 transition hover:-translate-y-0.5 hover:bg-[#006b59] hover:shadow-xl disabled:hover:translate-y-0 motion-safe:duration-200"
                size="lg"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    Analyze My Skills
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </>
                )}
              </Button>
            </form>
          </div>
        </section>

        <div className="mt-8 space-y-8">
          {/* States */}
          {loading && !data && (
            <div className="flex flex-col items-center py-12 text-muted-foreground">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="mt-3 text-sm">
                Matching your skills to ISCO/ESCO and pulling econometric
                signals…
              </p>
            </div>
          )}

          {error && !loading && (
            <div className="flex items-start gap-3 p-5 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold">Something went wrong</p>
                <p className="text-sm opacity-90">{error}</p>
                {retrying && retryCount > 0 && (
                  <p className="text-xs opacity-80 mt-1">
                    Auto-retrying… (attempt {retryCount} of {MAX_RETRIES})
                  </p>
                )}
                {data && (
                  <p className="text-xs opacity-80 mt-1">
                    Showing the last successful results below.
                  </p>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={handleManualRetry}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  Retry now
                </Button>
              </div>
            </div>
          )}

          {loading && data && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Refreshing analysis…
            </div>
          )}

          {data && (
            <div className="grid lg:grid-cols-2 gap-6">
              <SkillsProfileCard
                profile={data.profile}
                credential={data.portable_credential}
              />
              <AIReadinessCard
                risk={data.risk_assessment}
                signals={data.econometric_signals}
              />
              <div className="lg:col-span-2">
                <EconometricSignalsCard signals={data.econometric_signals} />
              </div>
              <div className="lg:col-span-2">
                <PortableCredentialCard credential={data.portable_credential} />
              </div>
            </div>
          )}
        </div>
      </main>

      <footer className="border-t mt-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 text-xs text-muted-foreground text-center">
          UNMAPPED · Built for the World Bank hackathon · Data sources: ILO,
          World Bank WDI, UNESCO UIS
        </div>
      </footer>
    </div>
  );
}
