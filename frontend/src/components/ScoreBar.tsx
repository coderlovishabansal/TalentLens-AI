interface ScoreBarProps {
  label: string;
  value: number;
}

function colorFor(value: number) {
  if (value >= 0.7) return "bg-emerald-500";
  if (value >= 0.4) return "bg-amber-500";
  return "bg-red-500";
}

export function ScoreBar({ label, value }: ScoreBarProps) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="mb-2">
      <div className="flex items-center justify-between text-xs text-slate-600 mb-1">
        <span>{label}</span>
        <span className="font-mono">{value.toFixed(2)}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-200">
        <div
          className={`h-1.5 rounded-full ${colorFor(value)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
