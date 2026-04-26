import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ExternalLink, AlertTriangle } from "lucide-react";
import type { EconometricSignal } from "@/api";

interface Props {
  signals: EconometricSignal[];
}

function isUsableUrl(url: string | undefined): url is string {
  if (!url) return false;
  const trimmed = url.trim();
  if (trimmed === "" || trimmed === "#") return false;
  return /^https?:\/\//i.test(trimmed);
}

export function EconometricSignalsCard({ signals }: Props) {
  // Hide the per-year series rows from the headline grid — they belong in the chart.
  const headline = signals.filter(
    (s) => s.signal_type !== "Education Projection Series",
  );

  return (
    <Card className="shadow-[var(--shadow-soft)]">
      <CardHeader>
        <CardTitle className="text-lg">Econometric Signals</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Live indicators sourced from ILO, World Bank & UNESCO
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {headline.map((s, i) => {
            const hasSource = isUsableUrl(s.source_url);
            const href = hasSource ? s.source_url : "#";
            const label =
              s.source_name ??
              (hasSource ? "View source" : "Source unavailable");

            return (
              <article
                key={`${s.signal_type}-${i}`}
                className="p-4 rounded-lg border bg-[var(--gradient-card)] flex flex-col gap-2"
              >
                <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">
                  {s.signal_type}
                </p>
                <p className="text-xl font-bold text-foreground tabular-nums">
                  {s.value}
                </p>
                <p className="text-sm text-muted-foreground flex-1">
                  {s.description}
                </p>

                <div className="mt-2 flex flex-col gap-1">
                  <Button
                    asChild
                    size="sm"
                    variant={hasSource ? "outline" : "ghost"}
                    className="self-start h-8 px-3 text-xs"
                    aria-disabled={!hasSource}
                  >
                    <a
                      href={href}
                      target={hasSource ? "_blank" : undefined}
                      rel={hasSource ? "noopener noreferrer" : undefined}
                      onClick={(e) => {
                        if (!hasSource) e.preventDefault();
                      }}
                      aria-label={
                        hasSource
                          ? `Open source for ${s.signal_type}: ${label}`
                          : `Source URL not provided for ${s.signal_type}`
                      }
                    >
                      <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                      Source: {label}
                    </a>
                  </Button>
                  {!hasSource && (
                    <p className="text-[11px] text-amber-600 dark:text-amber-500 inline-flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      No source URL provided by the backend for this signal.
                    </p>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
