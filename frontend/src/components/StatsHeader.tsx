import type { RankResponse } from "../types";

interface StatsHeaderProps {
  data: RankResponse;
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "ok" | "warn";
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl px-5 py-4">
      <div className="text-xs font-medium text-slate-500 mb-1">{label}</div>
      <div
        className={`text-2xl font-semibold ${
          tone === "warn"
            ? "text-red-600"
            : tone === "ok"
              ? "text-emerald-600"
              : "text-slate-900"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

export function StatsHeader({ data }: StatsHeaderProps) {
  const honeypotsOk = data.honeypots_in_top <= 10;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <StatCard label="Total Candidates" value={data.total_candidates.toLocaleString()} />
      <StatCard label="Showing Top" value={String(data.top_n)} />
      <StatCard
        label="Honeypots in Top"
        value={String(data.honeypots_in_top)}
        tone={honeypotsOk ? "ok" : "warn"}
      />
      <StatCard label="Top Score" value={data.top_score.toFixed(4)} />
    </div>
  );
}
