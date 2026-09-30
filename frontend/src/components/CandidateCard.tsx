import { useState } from "react";
import type { CandidateResult } from "../types";
import { ScoreBar } from "./ScoreBar";

interface CandidateCardProps {
  result: CandidateResult;
  defaultOpen: boolean;
}

export function CandidateCard({ result: r, defaultOpen }: CandidateCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  const isHoneypot = r.honeypot_penalty < 0.2;
  const dot = isHoneypot ? "🔴" : r.honeypot_penalty < 0.5 ? "🟡" : "🟢";

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left"
      >
        <span className="text-sm font-medium text-slate-900 truncate">
          #{r.rank} {dot} <span className="font-semibold">{r.current_title}</span>{" "}
          <span className="text-slate-400">— {r.years_of_experience}yrs</span>
        </span>
        <span className="flex items-center gap-3 shrink-0">
          <span className="text-sm font-mono text-slate-700">
            {r.display_score.toFixed(4)}
          </span>
          <span className="text-slate-400 text-xs">{open ? "▲" : "▼"}</span>
        </span>
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 grid md:grid-cols-[2fr_2fr_1fr] gap-6">
          <div>
            <p className="font-semibold text-slate-900">{r.name}</p>
            <p className="text-xs text-slate-500 mb-2">{r.headline}</p>
            <p className="text-sm text-slate-700">
              📍 {r.location} · 🏢 {r.current_company} ({r.current_industry})
            </p>
            <p className="text-sm text-slate-700 mb-2">
              🎓 {r.current_company_size} employees
            </p>
            {r.honeypot_flags.length > 0 && (
              <div className="text-xs bg-red-50 text-red-700 border border-red-200 rounded-md px-2 py-1.5 mt-2">
                ⚠️ Honeypot flags: {r.honeypot_flags.join("; ")}
              </div>
            )}
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase mb-2">
              Score Breakdown
            </p>
            <ScoreBar label="Semantic" value={r.semantic_score} />
            <ScoreBar label="Skills" value={r.structured.skill_score} />
            <ScoreBar label="Career" value={r.structured.career_score} />
            <ScoreBar label="Experience" value={r.structured.exp_score} />
            <ScoreBar label="Behavioral" value={r.behavioral.behavioral_score} />
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase mb-2">
              Availability
            </p>
            <dl className="space-y-1.5 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">Response Rate</dt>
                <dd className="font-mono">{Math.round(r.behavioral.response_rate * 100)}%</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Interview Rate</dt>
                <dd className="font-mono">
                  {Math.round(r.behavioral.interview_completion * 100)}%
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Notice</dt>
                <dd className="font-mono">{r.behavioral.notice_days}d</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Last Active</dt>
                <dd className="font-mono">{r.behavioral.inactive_days}d ago</dd>
              </div>
            </dl>
          </div>

          <div className="md:col-span-3 -mt-2">
            <div className="text-sm bg-blue-50 text-blue-800 border border-blue-200 rounded-md px-3 py-2">
              💡 <span className="font-medium">Why ranked here:</span> {r.reasoning}
            </div>
            {r.structured.matched_skills.length > 0 && (
              <div className="text-sm bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-md px-3 py-2 mt-2">
                ✅ JD skill matches: {r.structured.matched_skills.slice(0, 8).join(", ")}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
