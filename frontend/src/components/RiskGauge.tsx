interface RiskGaugeProps {
  value: number; // 0..100
}

export function RiskGauge({ value }: RiskGaugeProps) {
  const clamped = Math.max(0, Math.min(100, value));
  // semi-circle gauge
  const radius = 80;
  const circumference = Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  const tone =
    clamped < 30
      ? "var(--success)"
      : clamped < 60
        ? "var(--warning)"
        : "var(--danger)";
  const label = clamped < 30 ? "Low" : clamped < 60 ? "Moderate" : "High";

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 110" className="w-full max-w-xs">
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="var(--muted)"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke={tone}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 700ms ease, stroke 400ms ease" }}
        />
        <text
          x="100"
          y="85"
          textAnchor="middle"
          className="fill-foreground"
          style={{ fontSize: 28, fontWeight: 700 }}
        >
          {clamped.toFixed(0)}%
        </text>
        <text
          x="100"
          y="103"
          textAnchor="middle"
          className="fill-muted-foreground"
          style={{ fontSize: 11 }}
        >
          {label} automation risk
        </text>
      </svg>
    </div>
  );
}
