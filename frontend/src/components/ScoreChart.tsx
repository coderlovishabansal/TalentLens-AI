import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CandidateResult } from "../types";

interface ScoreChartProps {
  results: CandidateResult[];
}

export function ScoreChart({ results }: ScoreChartProps) {
  const data = results.map((r) => ({
    rank: r.rank,
    score: r.display_score,
    isHoneypot: r.honeypot_penalty < 0.2,
    name: r.name,
  }));

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-900 mb-3">
        Score Distribution
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
          <XAxis
            dataKey="rank"
            tick={{ fontSize: 11, fill: "#64748b" }}
            label={{ value: "Rank", position: "insideBottom", offset: -2, fontSize: 11, fill: "#64748b" }}
          />
          <YAxis tick={{ fontSize: 11, fill: "#64748b" }} domain={[0, 1]} />
          <Tooltip
            formatter={(value) => Number(value).toFixed(4)}
            labelFormatter={(label, payload) =>
              payload?.[0]
                ? `Rank ${label} — ${(payload[0].payload as { name: string }).name}`
                : `Rank ${label}`
            }
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
          />
          <Bar dataKey="score" radius={[3, 3, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.rank} fill={d.isHoneypot ? "#ef4444" : "#3b82f6"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-blue-500 inline-block" /> Normal
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-red-500 inline-block" /> Honeypot flagged
        </span>
      </div>
    </div>
  );
}
