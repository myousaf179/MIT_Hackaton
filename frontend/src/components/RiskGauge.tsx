import {
  CircularProgressbarWithChildren,
  buildStyles,
} from "react-circular-progressbar";
import "react-circular-progressbar/dist/styles.css";

interface RiskGaugeProps {
  value: number; // 0..100
}

export function RiskGauge({ value }: RiskGaugeProps) {
  const clamped = Math.max(0, Math.min(100, value));

  const tone =
    clamped < 30
      ? "var(--success)"
      : clamped < 60
        ? "var(--warning)"
        : "var(--danger)";
  const label = clamped < 30 ? "Low" : clamped < 60 ? "Moderate" : "High";

  return (
    <div className="flex flex-col items-center">
      <div
        className="w-full max-w-[220px]"
        role="img"
        aria-label={`Automation risk ${clamped.toFixed(0)} percent (${label})`}
      >
        <CircularProgressbarWithChildren
          value={clamped}
          minValue={0}
          maxValue={100}
          strokeWidth={10}
          styles={buildStyles({
            pathColor: tone,
            trailColor: "var(--muted)",
            pathTransitionDuration: 0.7,
            strokeLinecap: "round",
          })}
        >
          <div className="flex flex-col items-center leading-none">
            <span
              className="text-foreground font-bold tabular-nums"
              style={{ fontSize: 32 }}
            >
              {clamped.toFixed(0)}%
            </span>
            <span
              className="text-muted-foreground mt-1"
              style={{ fontSize: 11 }}
            >
              {label} automation risk
            </span>
          </div>
        </CircularProgressbarWithChildren>
      </div>
    </div>
  );
}
