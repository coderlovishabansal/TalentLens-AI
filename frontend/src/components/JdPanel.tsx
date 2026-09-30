import { useState } from "react";
import type { JobDescription } from "../types";

interface JdPanelProps {
  jd: JobDescription | null;
}

export function JdPanel({ jd }: JdPanelProps) {
  const [open, setOpen] = useState(false);

  if (!jd) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3 text-left"
      >
        <span className="text-sm font-semibold text-slate-900">
          📄 Job Description
        </span>
        <span className="text-slate-400 text-sm">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4">
          <pre className="whitespace-pre-wrap text-sm text-slate-700 font-sans mb-4">
            {jd.raw_text}
          </pre>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">
                Must-have skills
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {jd.must_have_skills.map((s) => (
                  <span
                    key={s}
                    className="text-xs bg-violet-50 text-violet-700 border border-violet-200 rounded-full px-2 py-0.5"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">
                Nice-to-have skills
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {jd.nice_to_have_skills.map((s) => (
                  <span
                    key={s}
                    className="text-xs bg-slate-100 text-slate-600 border border-slate-200 rounded-full px-2 py-0.5"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
