import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Loader2, Globe2, AlertCircle, RefreshCw } from "lucide-react";
import {
  analyzeSkills,
  type AnalyzeResponse,
  type CountryCode,
} from "@/api";
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
      toast.info(
        `Now viewing ${COUNTRY_LABEL[c]} data – no code change required.`,
      );
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
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <header className="bg-[var(--gradient-hero)] text-primary-foreground">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-16">
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest opacity-90 mb-3">
            <Globe2 className="h-4 w-4" />
            World Bank · UNMAPPED Hackathon
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold leading-tight max-w-3xl">
            Map invisible skills into a portable, AI-ready profile.
          </h1>
          <p className="mt-3 text-base sm:text-lg opacity-90 max-w-2xl">
            For workers in informal economies — translate lived experience into
            ISCO/ESCO-aligned credentials, calibrated for your local labour market.
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-8">
        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="bg-card border rounded-2xl p-5 sm:p-7 shadow-[var(--shadow-elegant)] space-y-5"
        >
          <div className="grid sm:grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label htmlFor="country">Country</Label>
              <Select value={country} onValueChange={handleCountryChange}>
                <SelectTrigger id="country">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="GHA">Ghana</SelectItem>
                  <SelectItem value="BGD">Bangladesh</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rural">Context</Label>
              <div className="flex items-center justify-between rounded-md border h-10 px-3">
                <span className="text-sm">
                  {isRural ? "Rural" : "Urban"}
                </span>
                <Switch
                  id="rural"
                  checked={isRural}
                  onCheckedChange={handleRuralChange}
                  aria-label="Toggle urban/rural"
                />
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="skills">Describe your skills</Label>
              <span
                className={`text-xs tabular-nums ${
                  isTooShort ? "text-muted-foreground" : "text-success"
                }`}
              >
                {charCount}/{MIN_SKILLS_LENGTH}+
              </span>
            </div>
            <Textarea
              id="skills"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Describe your skills... e.g., 'I repair mobile phones, speak 3 languages, learned Python from YouTube'"
              className="min-h-32 resize-y"
              aria-invalid={isTooShort}
              aria-describedby="skills-hint"
            />
            <p
              id="skills-hint"
              className={`text-xs ${
                isEmpty
                  ? "text-muted-foreground"
                  : isTooShort
                    ? "text-amber-600 dark:text-amber-500"
                    : "text-muted-foreground"
              }`}
            >
              {isEmpty
                ? "Tell us what you do — even a sentence or two helps. Example: \"I sell SIM cards, fix simple electronics, and speak Twi and English.\""
                : isTooShort
                  ? `A little more detail helps — ${MIN_SKILLS_LENGTH - charCount} more character${
                      MIN_SKILLS_LENGTH - charCount === 1 ? "" : "s"
                    } to enable analysis.`
                  : "Looks good — ready to analyze."}
            </p>
          </div>

          <Button
            type="submit"
            disabled={loading || isTooShort}
            className="w-full sm:w-auto bg-primary hover:bg-primary/90"
            size="lg"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Analyzing…
              </>
            ) : (
              "Analyze my skills"
            )}
          </Button>
        </form>

        {/* States */}
        {loading && !data && (
          <div className="flex flex-col items-center py-12 text-muted-foreground">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="mt-3 text-sm">
              Matching your skills to ISCO/ESCO and pulling econometric signals…
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
