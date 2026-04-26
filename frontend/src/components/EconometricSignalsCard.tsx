import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExternalLink } from "lucide-react";
import type { EconometricSignal } from "@/api";

interface Props {
  signals: EconometricSignal[];
}

export function EconometricSignalsCard({ signals }: Props) {
  // Hide the per-year series rows from the headline grid — they belong in the chart.
  const headline = signals.filter((s) => s.signal_type !== "Education Projection Series");

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
          {headline.map((s, i) => (
            <article
              key={`${s.signal_type}-${i}`}
              className="p-4 rounded-lg border bg-[var(--gradient-card)] flex flex-col gap-2"
            >
              <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">
                {s.signal_type}
              </p>
              <p className="text-xl font-bold text-foreground tabular-nums">{s.value}</p>
              <p className="text-sm text-muted-foreground flex-1">{s.description}</p>
              <a
                href={s.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline inline-flex items-center gap-1 mt-1"
              >
                Source: {s.source_name ?? "view"} <ExternalLink className="h-3 w-3" />
              </a>
            </article>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
