import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RiskGauge } from "./RiskGauge";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import type { EconometricSignal, RiskAssessment } from "@/api";
import { ShieldCheck, Sparkles } from "lucide-react";

interface Props {
  risk: RiskAssessment;
  signals: EconometricSignal[];
}

export function AIReadinessCard({ risk, signals }: Props) {
  const series = signals
    .filter((s) => s.signal_type.includes("Education Projection") && s.year)
    .map((s) => ({ year: s.year!, value: s.numeric_value ?? 0 }))
    .sort((a, b) => a.year - b.year);

  return (
    <Card className="shadow-[var(--shadow-soft)]">
      <CardHeader>
        <CardTitle className="text-lg">AI Readiness Lens</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          Calibrated automation risk for your local labour market
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid md:grid-cols-2 gap-6 items-center">
          <RiskGauge value={risk.calibrated_risk} />
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Base global risk</span>
              <span className="font-medium tabular-nums">
                {risk.base_risk}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">LMIC calibrated</span>
              <span className="font-medium tabular-nums text-success">
                {risk.calibrated_risk}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Reduction</span>
              <span className="font-medium tabular-nums">
                −{risk.reduction_pct} pts
              </span>
            </div>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-lg border bg-[var(--gradient-card)]">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="h-4 w-4 text-success" />
              <h4 className="font-semibold text-sm">Durable skills</h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {risk.durable_skills.map((s) => (
                <Badge
                  key={s}
                  variant="secondary"
                  className="bg-success/10 text-success border-success/20"
                >
                  {s}
                </Badge>
              ))}
            </div>
          </div>
          <div className="p-4 rounded-lg border bg-[var(--gradient-card)]">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <h4 className="font-semibold text-sm">
                Adjacent skills to learn
              </h4>
            </div>
            <div className="flex flex-wrap gap-2">
              {risk.adjacent_skills.map((s) => (
                <Badge key={s} variant="outline">
                  {s}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        {series.length > 0 && (
          <figure className="space-y-1">
            <figcaption className="text-center">
              <h4 className="font-semibold text-sm text-foreground">
                Secondary school completion rate (%) – Wittgenstein projections
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5">
                Projected attainment, {series[0].year}–
                {series[series.length - 1].year}
              </p>
            </figcaption>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={series}
                  margin={{ top: 8, right: 24, left: 16, bottom: 28 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="year"
                    stroke="var(--muted-foreground)"
                    style={{ fontSize: 12 }}
                    tickMargin={6}
                    label={{
                      value: "Year",
                      position: "insideBottom",
                      offset: -10,
                      style: {
                        fill: "var(--muted-foreground)",
                        fontSize: 12,
                        fontWeight: 500,
                      },
                    }}
                  />
                  <YAxis
                    stroke="var(--muted-foreground)"
                    style={{ fontSize: 12 }}
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                    label={{
                      value: "Secondary school completion (%)",
                      angle: -90,
                      position: "insideLeft",
                      offset: 4,
                      style: {
                        fill: "var(--muted-foreground)",
                        fontSize: 12,
                        fontWeight: 500,
                        textAnchor: "middle",
                      },
                    }}
                  />
                  <Tooltip
                    cursor={{
                      stroke: "var(--primary)",
                      strokeWidth: 1,
                      strokeOpacity: 0.4,
                    }}
                    contentStyle={{
                      background: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                      boxShadow: "var(--shadow-soft)",
                    }}
                    labelStyle={{ color: "var(--foreground)", fontWeight: 600 }}
                    labelFormatter={(label) => `Year ${label}`}
                    formatter={(value: number) => [
                      `${value}% completion`,
                      "Wittgenstein projection",
                    ]}
                  />
                  <Legend
                    verticalAlign="top"
                    height={28}
                    iconType="circle"
                    wrapperStyle={{ fontSize: 12 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name="Secondary school completion (%)"
                    stroke="var(--primary)"
                    strokeWidth={2.5}
                    dot={{
                      r: 4,
                      fill: "var(--primary)",
                      strokeWidth: 2,
                      stroke: "var(--background)",
                    }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[11px] text-muted-foreground text-center">
              Source: Wittgenstein Centre Human Capital Data Explorer
            </p>
          </figure>
        )}

        <p className="text-xs text-muted-foreground italic border-t pt-3">
          Calibrated for LMIC context — risk reduced by {risk.reduction_pct}%
          based on ILO task indices.
        </p>
      </CardContent>
    </Card>
  );
}
